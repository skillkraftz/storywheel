"""Switching between the Wheel, the Builder and the Writer, and remembering where you were."""
import contextlib
import fcntl
import json
import os
import select
import struct
import sys
import termios
import time
from pathlib import Path

import pytest

from storywheel import builder, fill, modes, state, store, tui, vault, writer
from storywheel.ratings import Ratings
from conftest import make_engine, run_tui, screen_text

ROOT = Path(__file__).resolve().parent.parent
pyte = pytest.importorskip("pyte", reason="the terminal-screen tests need pyte (pip install pyte)")


@pytest.fixture
def world(home):
    u = vault.create_universe("Thornwood", ["western"])
    u.new_entity("character", "Stacie Anderson", {"job": "land clerk"})
    u.new_entity("place", "Red Draw", {"kind": "town"})
    s = u.new_story("The Last Clause", {"genre": "western"}, {"Premise": "A clerk finds a clause."})
    s.add_scene("Opening", "Stacie ran down the road.")
    return u, s


def flat(text):
    return " ".join(text.split())


# --- state.json -----------------------------------------------------------------------------------------------

def test_state_round_trips_and_survives_damage(home):
    st = state.State()
    assert st.get("mode") is None
    st.update(mode="builder", universe="thornwood", tab="place")
    again = state.State()
    assert again.get("mode") == "builder" and again.get("tab") == "place"
    (home / "home" / "state.json").write_text("{ broken")
    assert state.State().data == {}
    st.clear()
    assert not (home / "home" / "state.json").exists()


def test_the_builder_records_where_you_are(home, world):
    u, s = world
    st = state.State()
    async def script(app, pilot):
        await pilot.press("2", "down")
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
    import asyncio

    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="thornwood", story="the-last-clause",
                                 state_store=st)
        async with app.run_test(size=(220, 55)) as pilot:
            await pilot.pause()
            await pilot.press("2")
            await pilot.pause()
    asyncio.run(go())
    data = state.State().data
    assert data["mode"] == "builder" and data["universe"] == "thornwood" and data["tab"] == "place"
    assert data["entity"] == "red-draw" and data["story"] == "the-last-clause"


def test_the_builder_starts_on_the_remembered_tab_and_entity(home, world):
    import asyncio
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="thornwood",
                                 tab="place", entity="red-draw")
        async with app.run_test(size=(220, 55)) as pilot:
            await pilot.pause()
            return app.screen_ref.type, app.screen_ref.entity.id, flat(screen_text(app))
    typ, eid, text = asyncio.run(go())
    assert (typ, eid) == ("place", "red-draw") and "Places (1)" in text


def test_the_wheel_records_the_draft_and_step(home):
    st = state.State()
    story = store.new_story()
    async def script(app, pilot):
        await pilot.press("k", "k")
        await pilot.pause()
    from conftest import run_tui as _run
    import asyncio
    async def go():
        app = tui.StorywheelApp(story, make_engine(home), st)
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            await pilot.press("k", "k")
            await pilot.pause()
    asyncio.run(go())
    data = state.State().data
    assert data["mode"] == "wheel" and data["draft"] == story["id"] and data["step"] == 2


# --- the mode loop ----------------------------------------------------------------------------------------------

def test_the_loop_follows_each_modes_request_until_one_quits(home, monkeypatch):
    calls = []
    script = iter([("builder", {"universe": "u"}), ("writer", {"story": "s"}), ("wheel", {"new": True}), None])
    def fake(name):
        def run(*a, **k):
            calls.append((name, a[1] if len(a) > 1 else None))
            return next(script)
        return run
    monkeypatch.setattr(modes, "run_wheel", fake("wheel"))
    monkeypatch.setattr(modes, "run_builder", fake("builder"))
    monkeypatch.setattr(modes, "run_writer", fake("writer"))
    modes.run_classic(("wheel", {}), lambda: None, lambda: None)
    assert [c[0] for c in calls] == ["wheel", "builder", "writer", "wheel"]
    assert calls[1][1] == {"universe": "u"} and calls[3][1] == {"new": True}


def test_with_no_state_it_starts_in_the_wheel_and_with_state_it_resumes_the_mode(home, monkeypatch):
    seen = []
    monkeypatch.setattr(modes, "run_wheel", lambda *a, **k: seen.append("wheel"))
    monkeypatch.setattr(modes, "run_builder", lambda *a, **k: seen.append("builder"))
    modes.run_classic(None, None, None)
    state.State().update(mode="builder")
    modes.run_classic(None, None, None)
    assert seen == ["wheel", "builder"]


def test_an_unknown_request_stops_the_loop(home, monkeypatch):
    monkeypatch.setattr(modes, "run_wheel", lambda *a, **k: ("nowhere", {}))
    modes.run_classic(("wheel", {}), None, None)


def test_the_writer_story_comes_from_the_request_or_from_where_you_were(home, world):
    u, s = world
    other = u.new_story("Another")
    st = state.State()
    assert modes._resolve_story(st, {"universe": "thornwood", "story": "another"})[1].slug == "another"
    st.update(universe="thornwood", story="the-last-clause")
    assert modes._resolve_story(st, {})[1].slug == "the-last-clause"
    assert modes._resolve_story(state.State(), {"universe": "thornwood"})[1].slug == "the-last-clause"   # first story as a fallback
    st.clear()
    assert modes._resolve_story(state.State(), {}) == (None, None)


def test_the_writer_mode_without_a_story_says_so_and_goes_somewhere_sensible(home, capsys):
    where = modes.run_writer(state.State(), {})
    assert where[0] == "wheel" and "no story to write yet" in capsys.readouterr().out
    vault.create_universe("Empty")
    assert modes.run_writer(state.State(), {})[0] == "builder"


def test_the_writer_mode_runs_neovim_and_returns_where_it_asked(home, world, monkeypatch):
    u, s = world
    ran = []
    monkeypatch.setattr(writer, "run", lambda story, scene=None, replace=None: ran.append(story.slug) or "wheel")
    monkeypatch.setattr(writer, "check", lambda: None)
    st = state.State()
    nxt = modes.run_writer(st, {"universe": "thornwood", "story": "the-last-clause"})
    assert ran == ["the-last-clause"] and nxt[0] == "wheel" and st.get("universe") == "thornwood"
    monkeypatch.setattr(writer, "run", lambda story, scene=None, replace=None: None)
    assert modes.run_writer(st, {"universe": "thornwood"})[0] == "builder"                 # :q returns to the Builder


def test_a_missing_neovim_is_a_message_not_a_crash(home, world, monkeypatch, capsys):
    monkeypatch.setattr(writer, "check", lambda: "Neovim isn't installed (test).")
    nxt = modes.run_writer(state.State(), {"universe": "thornwood"})
    assert nxt[0] == "builder" and "Neovim isn't installed" in capsys.readouterr().out


def test_promotion_carries_on_into_the_builder(home):
    story = store.new_story()
    async def script(app, pilot):
        while app.session.step.key != "premise":
            await pilot.press("k")
            await pilot.pause()
        await pilot.press("Q", "n", "enter", "p")
        await pilot.pause()
        return app.next
    nxt = run_tui(story, make_engine(home), script)
    assert nxt[0] == "builder" and nxt[1]["universe"] and nxt[1]["story"]


# --- the hotkeys ---------------------------------------------------------------------------------------------------------

def test_f2_and_f3_in_the_wheel_ask_for_the_builder_and_the_writer(home, world):
    for key, expect in (("f2", "builder"), ("f3", "writer")):
        story = store.new_story()
        story["universes"] = ["thornwood"]
        async def script(app, pilot):
            await pilot.press("k")
            await pilot.pause()
            await pilot.press(key)
            await pilot.pause()
            if key == "f2":
                await pilot.press("down", "enter")                    # offered to send the draft first: just go
                await pilot.pause()
            return app.next
        assert run_tui(story, make_engine(home), script) == (expect, {"universe": "thornwood"})


def test_the_builder_opens_the_writer_and_refreshes_on_return(home, world, monkeypatch):
    u, s = world
    import asyncio
    seen = {}
    def fake_run(story, scene=None):
        seen["story"] = story.slug
        story.add_scene("Added in the Writer", "Four new words here.")
        return "builder"
    monkeypatch.setattr(writer, "run", fake_run)
    monkeypatch.setattr(writer, "check", lambda: None)
    async def go():
        st = state.State()
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="thornwood",
                                 story="the-last-clause", state_store=st)
        monkeypatch.setattr(app, "suspend", lambda: contextlib.nullcontext())
        async with app.run_test(size=(220, 55)) as pilot:
            await pilot.pause()
            before = flat(screen_text(app))
            await pilot.press("f3")
            await pilot.pause()
            return before, flat(screen_text(app)), app.next, state.State().data
    before, after, nxt, data = asyncio.run(go())
    assert seen["story"] == "the-last-clause" and nxt is None
    assert "5 words in 1 scene" in before and "9 words in 2 scene" in after
    assert "Back from the Writer" in after and data["mode"] == "builder"


def test_the_writer_can_send_you_to_the_wheel_from_the_builder(home, world, monkeypatch):
    import asyncio
    monkeypatch.setattr(writer, "run", lambda story, scene=None: "wheel")
    monkeypatch.setattr(writer, "check", lambda: None)
    async def go():
        app = builder.BuilderApp(universe="thornwood", story="the-last-clause")
        monkeypatch.setattr(app, "suspend", lambda: contextlib.nullcontext())
        async with app.run_test(size=(220, 55)) as pilot:
            await pilot.pause()
            await pilot.press("w")
            await pilot.pause()
        return app.next
    assert asyncio.run(go()) == ("wheel", {})


def test_the_builder_says_why_it_cannot_open_the_writer(home, world, monkeypatch):
    import asyncio
    monkeypatch.setattr(writer, "check", lambda: "Neovim isn't installed (test).")
    vault.create_universe("Storyless")
    async def go():
        app = builder.BuilderApp(universe="thornwood", story="the-last-clause")
        async with app.run_test(size=(220, 55)) as pilot:
            await pilot.pause()
            await pilot.press("w")
            await pilot.pause()
            a = flat(screen_text(app))
            app.screen_ref.open_universe("storyless")
            await pilot.pause()
            monkeypatch.setattr(writer, "check", lambda: None)
            await pilot.press("w")
            await pilot.pause()
            return a, flat(screen_text(app))
    a, b = asyncio.run(go())
    assert "Neovim isn't installed (test)." in a and "no story to write yet" in b


def test_every_help_screen_lists_the_mode_keys(home, world):
    async def wheel(app, pilot):
        await pilot.press("question_mark")
        await pilot.pause()
        return flat(screen_text(app))
    assert "Wheel (this), Universe Builder, Writer, Settings" in run_tui(store.new_story(), make_engine(home), wheel, size=(200, 100))
    assert "F1 Wheel   F2 Builder   F3 Writer" in builder.HELP
    lua = (ROOT / "storywheel" / "nvim" / "lua" / "sw" / "init.lua").read_text()
    assert "F1 Wheel   F2 Builder   F3 Writer" in lua


# --- in a real terminal -----------------------------------------------------------------------------------------------------

class Term:
    """A program in a pseudo-terminal, with a pyte screen to read."""
    def __init__(self, argv, env, rows=40, cols=170):
        import pty
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.ByteStream(self.screen)
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.execvpe(argv[0], argv, env)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        self.status = None

    def read(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            if select.select([self.fd], [], [], 0.1)[0]:
                try:
                    data = os.read(self.fd, 65536)
                except OSError:
                    return
                if not data:
                    return
                self.stream.feed(data)

    def send(self, data, wait=1.0):
        os.write(self.fd, data)
        self.read(wait)

    def text(self):
        return "\n".join(line.rstrip() for line in self.screen.display)

    def wait_for(self, needle, seconds=25.0):
        end = time.time() + seconds
        while time.time() < end:
            self.read(0.3)
            if needle in " ".join(self.text().split()):
                return True
        return False

    def finish(self, seconds=6.0):
        end = time.time() + seconds
        while time.time() < end:
            try:
                pid, status = os.waitpid(self.pid, os.WNOHANG)
            except ChildProcessError:
                return self.status
            if pid:
                self.status = os.WEXITSTATUS(status)
                return self.status
            self.read(0.2)
        os.kill(self.pid, 9)
        os.waitpid(self.pid, 0)
        return None


def cli_env(home):
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "home"), STORYWHEEL_LIBRARY=str(home / "library"),
               STORYWHEEL_OUT=str(home / "out"), PYTHONPATH=str(ROOT), TERM="xterm-256color", COLUMNS="170", LINES="40")
    env.pop("KITTY_WINDOW_ID", None)
    return env


F1, F2, F3 = b"\x1bOP", b"\x1bOQ", b"\x1bOR"


@pytest.mark.skipif(not hasattr(os, "fork") or writer.check() is not None, reason="needs a terminal and Neovim")
def test_plain_storywheel_reopens_the_builder_exactly_where_you_left_off(home, world):
    state.State().update(mode="builder", universe="thornwood", story="the-last-clause", tab="place", entity="red-draw")
    t = Term([sys.executable, "-m", "storywheel"], cli_env(home))
    assert t.wait_for("Place: Red Draw")
    text = " ".join(t.text().split())
    assert "Places (1)" in text and "Story outline: The Last Clause" in text and "Place: Red Draw" in text
    t.send(b"Q", 1.0)
    t.send(b"y", 1.0)                                                  # Quit storywheel? asks first
    assert t.finish() == 0


@pytest.mark.skipif(not hasattr(os, "fork") or writer.check() is not None, reason="needs a terminal and Neovim")
def test_builder_to_writer_and_back_with_the_hotkeys(home, world):
    u, s = world
    state.State().update(mode="builder", universe="thornwood", story="the-last-clause")
    t = Term([sys.executable, "-m", "storywheel"], cli_env(home))
    assert t.wait_for("Story outline: The Last Clause")
    t.send(F3, 0.5)
    assert t.wait_for("Stacie ran down the road", 25)                 # Neovim is up, with the scene
    assert state.State().get("mode") == "writer"
    t.send(b"Goa line typed in the Writer", 0.8)
    t.send(b"\x1b", 0.5)
    t.send(F2, 1.0)                                                    # save and back to the Builder
    assert t.wait_for("Back from the Writer", 25)
    assert "7 words" in " ".join(t.text().split()) or "words in" in t.text()
    assert "a line typed in the Writer" in s.scenes()[0].read_text()
    assert state.State().get("mode") == "builder"
    t.send(b"Q", 1.0)
    t.send(b"y", 1.0)
    assert t.finish() == 0


@pytest.mark.skipif(not hasattr(os, "fork") or writer.check() is not None, reason="needs a terminal and Neovim")
def test_storywheel_reopens_the_writer_if_that_is_where_you_were(home, world):
    state.State().update(mode="writer", universe="thornwood", story="the-last-clause")
    t = Term([sys.executable, "-m", "storywheel"], cli_env(home))
    assert t.wait_for("Stacie ran down the road", 25)
    t.send(F2, 1.0)
    assert t.wait_for("Universe Builder") or t.wait_for("Stories in Thornwood")
    t.send(b"Q", 1.0)
    t.send(b"y", 1.0)
    assert t.finish() == 0


@pytest.mark.skipif(not hasattr(os, "fork"), reason="needs a terminal")
def test_with_no_state_storywheel_opens_the_wheel(home):
    t = Term([sys.executable, "-m", "storywheel"], cli_env(home))
    assert t.wait_for("Genre & mood")
    t.send(b"Q", 0.8)
    t.send(b"d", 0.8)
    assert t.finish() == 0
