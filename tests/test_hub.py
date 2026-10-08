"""One Textual app for the Wheel, Builder, Settings and Words: modes are built once, kept, and switching is quick."""
import asyncio
import contextlib
import fcntl
import os
import select
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path

import pytest

from storywheel import hub as hubmod, modes, state, store, vault, writer
from storywheel.engine import Engine
from storywheel.ratings import Ratings
from conftest import screen_text

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def world(home):
    u = vault.create_universe("Thornwood", ["western"])
    u.new_entity("character", "Stacie Anderson", {"job": "land clerk"})
    u.new_entity("place", "Red Draw", {"kind": "town"})
    s = u.new_story("The Last Clause", {"genre": "western"}, {"Premise": "A clerk finds a clause."})
    s.add_scene("Opening", "Stacie ran down the road.")
    modes.TRAIL.clear()
    return u, s


def run_hub(script, start=("builder", {"universe": "thornwood", "story": "the-last-clause"}), size=(190, 50)):
    async def go():
        app = hubmod.Hub(start, lambda: Engine(seed=3), lambda: Ratings())
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


def flat(text):
    return " ".join(text.split())


async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


def test_the_function_keys_switch_modes_inside_one_app(home, world):
    async def script(app, pilot):
        seen = [app.mode_name]
        for key in ("f4", "f5", "f1", "f2"):
            await press(pilot, key)
            seen.append((app.mode_name, type(app.screen).__name__))
        return seen
    assert run_hub(script) == ["builder", ("settings", "SettingsScreen"), ("words", "WordsScreen"), ("wheel", "MainScreen"), ("builder", "BuilderScreen")]


def test_each_mode_is_built_once_and_kept(home, world):
    async def script(app, pilot):
        first = {}
        for key, name in (("f4", "settings"), ("f5", "words"), ("f1", "wheel"), ("f2", "builder")):
            await press(pilot, key)
            first[name] = app.screen
        built = dict(app.screens_built)
        for key in ("f4", "f5", "f1", "f2", "f4", "f2"):
            await press(pilot, key)
        return built, {n: app.screens_built[n] for n in built}, first
    built, later, first = run_hub(script)
    assert set(built) == {"builder", "settings", "words", "wheel"}
    assert all(built[n] is later[n] for n in built) and all(first[n] is built[n] for n in first)


def test_modes_are_built_only_when_first_opened(home, world):
    async def script(app, pilot):
        return sorted(app.screens_built)
    assert run_hub(script) == ["builder"]


def test_each_mode_keeps_its_place(home, world):
    async def script(app, pilot):
        b = app.screens_built["builder"]
        await press(pilot, "2")                                          # the Places tab
        b.entity = b.universe.entity("red-draw")
        b.refresh_all()
        await pilot.pause()
        await press(pilot, "f4")
        s = app.screen
        s.query_one("#tabs").active = "t-export"
        await pilot.pause()
        await press(pilot, "f5")
        w = app.screen
        w.query_one("#word").value = "lantern"
        await press(pilot, "f1")
        await press(pilot, "k")                                          # the Wheel keeps one step
        step = app.session.i
        await press(pilot, "f4")
        settings_tab = app.screen.query_one("#tabs").active
        await press(pilot, "f5")
        word = app.screen.query_one("#word").value
        await press(pilot, "f1")
        step_back = app.session.i
        await press(pilot, "f2")
        return b.type, b.entity.id, settings_tab, word, step, step_back
    typ, ent, tab, word, step, step_back = run_hub(script)
    assert (typ, ent, tab, word) == ("place", "red-draw", "t-export", "lantern") and step == step_back and step >= 1


def test_the_builder_refreshes_when_you_come_back(home, world):
    u, s = world
    async def script(app, pilot):
        await press(pilot, "f4")
        u.new_entity("character", "Added Elsewhere", {})
        s.add_scene("Two", "More words than before here.")
        await press(pilot, "f2")
        return flat(screen_text(app))
    text = run_hub(script)
    assert "Characters (2)" in text


def test_settings_shows_what_other_modes_changed(home, world):
    from storywheel import settings
    async def script(app, pilot):
        await press(pilot, "f4")
        box = app.screen.query_one("#f-legal_name")
        before = box.value
        await press(pilot, "f2")
        settings.save_global({"legal_name": "Ada Voss"})
        await press(pilot, "f4")
        return before, app.screen.query_one("#f-legal_name").value
    assert run_hub(script) == ("", "Ada Voss")


def test_q_goes_back_along_the_trail_and_Q_asks_before_quitting(home, world):
    async def script(app, pilot):
        await press(pilot, "f4")
        await press(pilot, "f5")
        await press(pilot, "escape")                                     # leave the word box
        app.screen.set_focus(None)
        await press(pilot, "q")
        first = app.mode_name
        await press(pilot, "q")
        second = app.mode_name
        await press(pilot, "Q")
        asked = flat(screen_text(app))
        await press(pilot, "n")
        return first, second, "Quit storywheel" in asked, app.is_running
    first, second, asked, running = run_hub(script)
    assert (first, second) == ("settings", "builder") and asked and running


def test_a_quit_ends_the_app_with_the_wheels_message(home, world):
    async def script(app, pilot):
        await press(pilot, "f1")
        await press(pilot, "Q")
        await press(pilot, "d", "y")                                     # nothing kept: delete the draft (d asks first)
        return None
    async def go():
        app = hubmod.Hub(("builder", {"universe": "thornwood"}), lambda: Engine(seed=3), lambda: Ratings())
        async with app.run_test(size=(190, 50)) as pilot:
            await pilot.pause()
            await script(app, pilot)
        return app.return_value
    assert "Nothing was kept" in (asyncio.run(go()) or "")


def test_promoting_from_the_wheel_lands_in_the_builder_with_a_message(home):
    async def script(app, pilot):                                          # (it starts in the Wheel: F1 here would open the Wheel's help)
        for _ in range(12):
            if app.session.step.key == "premise":
                break
            await press(pilot, "k")
        await press(pilot, "Q", "n", "enter", "p")
        await pilot.pause()
        return app.mode_name, flat(screen_text(app))
    mode, text = run_hub(script, start=("wheel", {"new": True}))
    assert mode == "builder" and "Promoted into the universe" in text


def test_a_new_wheel_draft_from_the_builder_replaces_the_draft_in_the_kept_wheel(home, world):
    async def script(app, pilot):
        await press(pilot, "f1")
        await press(pilot, "k")
        first = app.session.story["id"]
        await press(pilot, "f2")
        await press(pilot, "down", "enter")                              # (it offers to send the draft first: just go)
        assert app.mode_name == "builder"
        app.go("wheel", {"new": True, "universe": "thornwood"})
        await pilot.pause()
        await pilot.pause()
        return first, app.session.story["id"], app.session.story.get("universes"), app.mode_name, (type(app.screen).__name__, app.screens_built["wheel"] is app.screen)
    first, second, universes, mode, same_screen = run_hub(script)
    assert first != second and universes == ["thornwood"] and mode == "wheel" and same_screen == ("MainScreen", True), same_screen


# --- the Writer from the hub ----------------------------------------------------------------------------------------------------

def patch_writer(monkeypatch, answer, handover=None, edit=None):
    calls = []
    def fake_run(story, scene=None, replace=None):
        calls.append((story.slug, scene, replace))
        if edit:
            edit(story)
        fake_run.handover = handover
        writer.run.handover = handover
        return answer
    monkeypatch.setattr(writer, "run", fake_run)
    monkeypatch.setattr(writer, "check", lambda: None)
    monkeypatch.setattr(hubmod, "quiet_suspend", lambda app: contextlib.nullcontext())
    return calls


def test_f3_from_any_mode_opens_the_writer_and_the_builder_shows_the_return(home, world, monkeypatch):
    u, s = world
    calls = patch_writer(monkeypatch, "builder", edit=lambda story: story.add_scene("Added", "Four new words here."))
    async def script(app, pilot):
        await press(pilot, "f4")
        await press(pilot, "f3")
        return app.mode_name, flat(screen_text(app)), state.State().data["mode"]
    mode, text, saved = run_hub(script)
    assert calls[0][0] == "the-last-clause" and mode == "builder" and saved == "builder"
    assert "Back from the Writer" in text and "9 words in 2 scene" in text


def test_the_writer_can_hand_a_word_to_words_and_settings_back_goes_to_the_writer(home, world, monkeypatch):
    handover = {"word": "dry", "replace": {"file": "x", "row": 1, "start": 0, "end": 3, "text": "dry"}}
    calls = patch_writer(monkeypatch, "words", handover=handover)
    async def script(app, pilot):
        await press(pilot, "f3")
        word = app.screen.query_one("#word").value
        return app.mode_name, word, app.screen.handover == handover, app.screens_built["words"] is app.screen
    mode, word, ok, kept = run_hub(script)
    assert (mode, word, ok, kept) == ("words", "dry", True, True) and len(calls) == 1


def test_the_writer_returning_wheel_settings_or_quit(home, world, monkeypatch):
    for answer, mode in (("wheel", "wheel"), ("settings", "settings")):
        patch_writer(monkeypatch, answer)
        async def script(app, pilot):
            await press(pilot, "f3")
            return app.mode_name
        assert run_hub(script) == mode
    patch_writer(monkeypatch, "quit")
    async def go():
        app = hubmod.Hub(("builder", {"universe": "thornwood"}), lambda: Engine(seed=3), lambda: Ratings())
        async with app.run_test(size=(190, 50)) as pilot:
            await pilot.pause()
            await press(pilot, "f3")
        return app.is_running
    assert asyncio.run(go()) is False


def test_without_a_story_or_neovim_the_writer_says_why_and_nothing_changes(home, world, monkeypatch):
    patch_writer(monkeypatch, "builder")
    monkeypatch.setattr(writer, "check", lambda: "Neovim isn't installed (test).")
    async def script(app, pilot):
        await press(pilot, "f3")
        return app.mode_name, flat(screen_text(app))
    mode, text = run_hub(script)
    assert mode == "builder" and "Neovim isn't installed (test)." in text


def test_quiet_suspend_keeps_the_alternate_screen(monkeypatch):
    """The driver's 'leave the alternate screen' becomes 'clear the screen' while the other program runs."""
    written = []
    class Driver:
        def write(self, data):
            written.append(data)
    class App:
        _driver = Driver()
        @contextlib.contextmanager
        def suspend(self):
            self._driver.write("\x1b[?1049l")                           # what stopping application mode writes
            yield
            written.append("<resumed>")
    app = App()
    stdout_writes = []
    monkeypatch.setattr(os, "write", lambda fd, data: stdout_writes.append(data))
    with hubmod.quiet_suspend(app):
        written.append("<other program runs>")
    assert written[0] == "\x1b[2J\x1b[H" and "\x1b[?1049l" not in written and written[1] == "<other program runs>"
    assert stdout_writes == [b"\x1b[?1049h\x1b[2J\x1b[H"] and app._driver.write.__name__ == "write"


# --- start-up, lazy loading, speed -------------------------------------------------------------------------------------------------

def test_starting_in_the_builder_does_not_load_the_dictionary_or_wordfreq(home, world):
    code = ("import sys, asyncio\n"
            "from storywheel import hub\nfrom storywheel.engine import Engine\nfrom storywheel.ratings import Ratings\n"
            "async def go():\n"
            "    app = hub.Hub(('builder', {'universe': 'thornwood'}), lambda: Engine(seed=1), lambda: Ratings())\n"
            "    async with app.run_test(size=(190, 50)) as pilot:\n"
            "        await pilot.pause()\n"
            "        print('LOADED', sorted(m for m in ('storywheel.words_app','storywheel.dictionary','storywheel.learn','wordfreq','storywheel.grammar','storywheel.settings_app') if m in sys.modules))\n"
            "asyncio.run(go())\n")
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "home"), STORYWHEEL_LIBRARY=str(home / "library"), PYTHONPATH=str(ROOT))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=str(ROOT)).stdout
    assert "LOADED []" in out, out


def test_switching_back_to_a_kept_mode_is_quick(home, world):
    async def script(app, pilot):
        for key in ("f4", "f5", "f1", "f2"):                              # the first visits build things
            await press(pilot, key)
        times = []
        for _ in range(3):
            for key in ("f4", "f5", "f1", "f2"):
                t = time.perf_counter()
                await press(pilot, key)
                times.append((time.perf_counter() - t) * 1000)
        return sorted(times)
    times = run_hub(script)
    assert times[len(times) // 2] < 400, times                          # (the real figure is about 100 ms; this only catches a rebuild)


# --- in a real terminal -------------------------------------------------------------------------------------------------------------

def raw_run(argv, env, keys, rows=40, cols=140):
    """Run a program in a pty, send keys (with a pause after each), return everything it wrote."""
    import pty
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe(argv[0], argv, env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    out = b""

    def drain(seconds):
        nonlocal out
        end = time.time() + seconds
        while time.time() < end:
            if select.select([fd], [], [], 0.1)[0]:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    return
                if not chunk:
                    return
                out += chunk
    drain(3.0)
    for k, wait in keys:
        os.write(fd, k)
        drain(wait)
    end = time.time() + 8
    while time.time() < end:
        try:
            p, st = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            break
        if p:
            break
        drain(0.2)
    else:
        os.kill(pid, 9)
        os.waitpid(pid, 0)
    return out


@pytest.mark.skipif(not hasattr(os, "fork"), reason="needs a terminal")
def test_switching_modes_never_leaves_the_alternate_screen_until_you_quit(home, world):
    state.State().update(mode="builder", universe="thornwood", story="the-last-clause")
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "home"), STORYWHEEL_LIBRARY=str(home / "library"), STORYWHEEL_OUT=str(home / "out"),
               PYTHONPATH=str(ROOT), TERM="xterm-256color", COLUMNS="140", LINES="40")
    env.pop("KITTY_WINDOW_ID", None)
    keys = [(b"\x1bOS", 1.0), (b"\x1b[15~", 1.0), (b"\x1bOP", 1.0), (b"\x1bOQ", 1.0), (b"Q", 0.8), (b"y", 1.0)]          # F4 F5 F1 F2 then quit
    out = raw_run([sys.executable, "-m", "storywheel"], env, keys)
    assert out.count(b"\x1b[?1049h") == 1 and out.count(b"\x1b[?1049l") == 1, (out.count(b"\x1b[?1049h"), out.count(b"\x1b[?1049l"))
    assert b"Universe Builder" in out and b"Settings" in out and b"Words" in out


@pytest.mark.skipif(not hasattr(os, "fork") or writer.check() is not None, reason="needs a terminal and Neovim")
def test_the_writer_round_trip_never_shows_the_shell_between(home, world):
    state.State().update(mode="builder", universe="thornwood", story="the-last-clause")
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "home"), STORYWHEEL_LIBRARY=str(home / "library"), STORYWHEEL_OUT=str(home / "out"),
               PYTHONPATH=str(ROOT), TERM="xterm-256color", COLUMNS="140", LINES="40")
    env.pop("KITTY_WINDOW_ID", None)
    keys = [(b"\x1bOR", 4.0), (b"\x1bOQ", 2.0), (b"Q", 0.8), (b"y", 1.0)]                         # F3 (Neovim), F2 back, quit
    out = raw_run([sys.executable, "-m", "storywheel"], env, keys)
    # Textual enters once; Neovim enters and leaves itself; we re-enter and clear; Textual leaves once at the end. A plain suspend would
    # leave the alternate screen one more time (the shell showing) before Neovim started.
    assert out.count(b"\x1b[?1049l") == 2, out.count(b"\x1b[?1049l")
    assert b"\x1b[?1049h\x1b[2J\x1b[H" in out


def test_a_kept_screen_does_not_restyle_everything_when_it_returns_unless_the_look_changed(home, world):
    async def script(app, pilot):
        b = app.screens_built["builder"]
        calls = []
        real = b.update_node_styles
        b.update_node_styles = lambda animate=False: (calls.append(1), real(animate=animate))[1]
        await press(pilot, "f4")
        await press(pilot, "f2")
        quiet = len(calls)                                               # back with the look unchanged: no restyling
        await press(pilot, "f4")
        app.screen.save("transparent_background", False)                 # Settings > Appearance
        await pilot.pause()
        await press(pilot, "f2")
        return quiet, len(calls), b._styled_version == app.style_version
    quiet, after, current = run_hub(script)
    assert quiet == 0 and after == 1 and current


def test_the_switch_report_tool_runs(home):
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "measure_switch.py"), "hub"], capture_output=True, text=True, cwd=str(ROOT))
    assert out.returncode == 0 and "repeat visit" in out.stdout and "settings (first visit)" in out.stdout, out.stderr


# --- batch 11: clickable mode entries, and a burst of F-keys ends on the last --------------------------------------------------------

def test_a_burst_of_function_keys_ends_on_the_last_one_pressed(home, world):
    async def script(app, pilot):
        await press(pilot, "f5")                                            # (build a second mode first)
        await pilot.press("f2", "f4")                                       # quickly, with no pause between
        await pilot.pause()
        await pilot.pause()
        first = (app.mode_name, type(app.screen).__name__)
        await pilot.press("f1", "f5", "f2", "f4", "f1")
        await pilot.pause()
        await pilot.pause()
        return first, (app.mode_name, type(app.screen).__name__), app.st.get("mode")
    first, second, saved = run_hub(script)
    assert first == ("settings", "SettingsScreen") and second == ("wheel", "MainScreen")


def test_the_screen_is_switched_before_the_mode_refreshes(home, world):
    async def script(app, pilot):
        await press(pilot, "f4")
        order = []
        screen = app.screens_built["builder"]
        real = screen.enter
        screen.enter = lambda payload: order.append(("enter", type(app.screen).__name__)) or real(payload)
        await press(pilot, "f2")
        return order
    assert run_hub(script) == [("enter", "BuilderScreen")]                 # (the Builder was already showing when it refreshed)


def test_each_mode_is_its_own_clickable_footer_entry(home, world):
    async def script(app, pilot):
        from textual.widgets._footer import FooterKey
        keys = {k.action: k.description for k in app.screen.query(FooterKey)}
        await pilot.click("FooterKey#" + "") if False else None
        target = next(k for k in app.screen.query(FooterKey) if k.description == "Settings")
        await pilot.click(target)
        await pilot.pause()
        await pilot.pause()
        return keys, type(app.screen).__name__
    keys, now = run_hub(script)
    assert [d for d in keys.values()][:7] == ["Wheel", "Builder", "Writer", "Settings", "Words", "Help", "Back"]
    assert now == "SettingsScreen"


def test_footers_hold_the_modes_help_back_and_at_most_three_keys(home, world):
    async def script(app, pilot):
        from textual.widgets._footer import FooterKey
        out = {}
        for key in ("f1", "f2", "f4", "f5"):
            await press(pilot, key)
            out[key] = [k.description for k in app.screen.query(FooterKey)]
        return out
    for key, names in run_hub(script).items():
        assert names[:5] == ["Wheel", "Builder", "Writer", "Settings", "Words"] and len(names) <= 10, (key, names)
        if key != "f5":                                                      # (in Words a text box has the focus and takes ? and q as letters)
            assert names[5:7] == ["Help", "Back"], (key, names)
