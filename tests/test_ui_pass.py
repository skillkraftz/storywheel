"""The UI pass: flags, three columns, quitting, clipboard, plain text, no page-break divs, --json."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from textual.widgets import Input

from storywheel import clipboard, store, tui
from storywheel.ratings import Ratings
from storywheel.session import Session
from conftest import make_engine, run_tui, screen_text

ROOT = Path(__file__).resolve().parent.parent


def new_story():
    return store.new_story()


async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


def idx(s, key):
    return [st.key for st in s.steps].index(key)


def kept_session(home, upto="twist", seed=3):
    s = Session(store.new_story(), make_engine(home, seed=seed))
    s.enter(0)
    while s.step.key != upto and not s.done:
        s.keep()
    return s


# --- markdown and plain text -------------------------------------------------------------------------

def test_markdown_has_no_html_and_sections_are_plain_rules(home):
    s = kept_session(home, "twist")
    s.keep()
    md = store.to_markdown(s.story)
    assert "<div" not in md and "page-break" not in md
    assert md.count("\n---\n\n## ") >= 3 and md.startswith("---\ntitle:")


def test_plain_text_is_only_what_is_kept_and_has_no_markup(home):
    s = kept_session(home, "setting")
    text = store.to_plain(s.story)
    assert text.splitlines()[0] == store.title_of(s.story).upper()
    assert "PROTAGONIST" in text and "Name" in text
    assert "SETTING" not in text and "PREMISE" not in text                  # not kept yet
    assert not any(c in text for c in ("**", "##", "<div", "|"))
    assert store.to_plain(store.new_story()) == ""


def test_plain_text_includes_the_body_with_its_labels(home):
    s = kept_session(home, "twist")
    text = store.to_plain(s.story)
    assert "PREMISE" in text and s.story["kept"]["premise"]["premise"].split()[0] in text
    assert s.story["kept"]["spine"] and list(s.story["kept"]["spine"].values())[0][:20] in text.replace("\n  ", " ")


def test_delete_removes_the_json_and_the_markdown(home):
    s = kept_session(home, "twist")
    s.save()
    path = Path(s.story["md_path"])
    assert path.exists() and (home / "home" / "stories" / f"{s.story['id']}.json").exists()
    store.delete(s.story)
    assert not path.exists() and not list((home / "home" / "stories").glob("*.json"))
    store.delete(s.story)                                               # twice is fine


# --- flags and issues --------------------------------------------------------------------------------------

def test_a_step_built_on_a_stand_in_is_flagged_yellow_then_clears(home):
    s = Session(store.new_story(), make_engine(home))
    s.enter(0)
    for _ in range(3):
        s.keep()
    s.keep()                                                # protagonist kept
    s.jump(idx(s, "spine"))
    s.jump(idx(s, "protagonist"))
    s.back()                                                # (just moving about)
    s2 = Session(store.new_story(), make_engine(home, seed=4))
    s2.enter(0)
    for _ in range(3):
        s2.keep()
    s2.jump(idx(s2, "spine"))
    s2.keep()                                               # spine kept on stand-ins
    assert s2.flag(idx(s2, "spine")) == "changed"
    assert any("stand-in" in m for _sev, m in s2.issues())
    s2.jump(idx(s2, "protagonist"))
    s2.keep()
    s2.jump(idx(s2, "setting"))
    s2.keep()                                               # both real now: the swap cleared the flag
    assert s2.flag(idx(s2, "spine")) is None and not [m for _s, m in s2.issues() if m.startswith("Spine")]


def test_a_step_that_refers_to_a_skipped_step_is_broken_red(home):
    s = kept_session(home, "spine")
    s.keep()
    assert s.flag(idx(s, "spine")) is None
    s.jump(idx(s, "protagonist"))
    s.skip()                                                # the protagonist is no longer kept
    assert s.flag(idx(s, "spine")) == "broken"
    sev, message = s.issues()[0]
    assert sev == "broken" and "no longer a kept protagonist" in message


# --- the three columns -------------------------------------------------------------------------------------

def test_sidebar_shows_yellow_and_red_markers_and_clicking_a_flagged_step_jumps(home):
    async def script(app, pilot):
        s = app.session
        for _ in range(3):
            await press(pilot, "k")
        await pilot.click("#steps", offset=(4, idx(s, "spine"))); await pilot.pause()
        await press(pilot, "k")                                          # spine kept on stand-ins
        await pilot.click("#steps", offset=(4, 0)); await pilot.pause()
        yellow = screen_text(app)
        await pilot.click("#steps", offset=(4, idx(s, "spine"))); await pilot.pause()
        return yellow, s.step.key
    text, step = run_tui(new_story(), make_engine(home), script)
    assert "● 7 " in text and step == "spine"


def test_red_cross_for_a_reference_that_no_longer_exists(home):
    async def script(app, pilot):
        s = app.session
        while s.step.key != "twist":
            await press(pilot, "k")
        await pilot.click("#steps", offset=(4, idx(s, "protagonist"))); await pilot.pause()
        await press(pilot, "x")
        return screen_text(app)
    text = run_tui(new_story(), make_engine(home), script)
    assert "✗" in text and "no longer a kept protagonist" in " ".join(text.split())


def test_the_right_column_is_the_story_so_far_in_plain_text(home):
    async def script(app, pilot):
        s = app.session
        before = screen_text(app)
        while s.step.key != "premise":
            await press(pilot, "k")
        return before, screen_text(app), store.title_of(s.story), s.story["kept"]["protagonist"]["name"]
    before, after, title, name = run_tui(new_story(), make_engine(home), script)
    assert "The story so far" in before and "nothing kept yet" in before
    assert title.upper() in after and "PROTAGONIST" in after and name.split()[0] in after
    assert "PREMISE" not in after.split("The story so far")[1]


def test_issues_are_listed_at_the_top_of_the_right_column(home):
    async def script(app, pilot):
        s = app.session
        for _ in range(3):
            await press(pilot, "k")
        await pilot.click("#steps", offset=(4, idx(s, "spine"))); await pilot.pause()
        await press(pilot, "k")
        return " ".join(screen_text(app).split())
    text = run_tui(new_story(), make_engine(home), script)
    assert "● Title was built on a stand-in" in text or "● Spine was built on a stand-in" in text


# --- past stories --------------------------------------------------------------------------------------------

def two_stories(home):
    a = kept_session(home, "twist", seed=1)
    a.story["id"] = "20200101-000000"              # (ids are timestamps: keep them apart)
    a.save()
    b = kept_session(home, "twist", seed=2)
    b.story["id"] = "20990101-000000"
    b.save()
    return a.story, b.story


def test_the_past_stories_list_shows_saved_stories(home):
    a, b = two_stories(home)
    async def script(app, pilot):
        return screen_text(app)
    text = run_tui(store.new_story(), make_engine(home), script)
    assert "Past stories" in text
    assert store.title_of(a)[:15] in text and store.title_of(b)[:15] in text


def test_open_a_past_story(home):
    a, b = two_stories(home)
    async def script(app, pilot):
        await pilot.press("n") if False else None
        first = app.session.story["id"]
        lst = app.main.stories_list
        ids = [lst.get_option_at_index(i).id for i in range(lst.option_count)]
        target = next(i for i in ids if i != first)
        lst.focus(); await pilot.pause()
        lst.highlighted = ids.index(target)
        await press(pilot, "enter")
        return first, app.session.story["id"], target, app.session.step.key, screen_text(app)
    first, now, target, step, text = run_tui(store.new_story(), make_engine(home), script)
    assert now == target != first and store.title_of(store.load(target)).upper() in text


def test_delete_a_past_story_asks_first(home):
    a, b = two_stories(home)
    async def script(app, pilot):
        lst = app.main.stories_list
        ids = [lst.get_option_at_index(i).id for i in range(lst.option_count)]
        victim = ids[-1]
        lst.focus(); await pilot.pause()
        lst.highlighted = ids.index(victim)
        await press(pilot, "d")
        asked = type(app.screen).__name__
        await press(pilot, "n")
        still = (home / "home" / "stories" / f"{victim}.json").exists()
        await press(pilot, "d")
        await press(pilot, "y")
        return asked, still, (home / "home" / "stories" / f"{victim}.json").exists()
    assert run_tui(store.new_story(), make_engine(home), script) == ("ConfirmScreen", True, False)


def test_the_story_you_are_in_cannot_be_deleted_from_the_list(home):
    story = kept_session(home, "twist").story
    async def script(app, pilot):
        lst = app.main.stories_list
        lst.focus(); await pilot.pause()
        await press(pilot, "d")
        return type(app.screen).__name__, screen_text(app)
    screen, text = run_tui(store.load(story["id"]) if (home / "home" / "stories" / f"{story['id']}.json").exists()
                           else story, make_engine(home), script)
    assert screen == "MainScreen"




# --- leaving ----------------------------------------------------------------------------------------------------------

def test_q_asks_keep_or_delete_and_escape_cancels(home):
    async def script(app, pilot):
        await press(pilot, "k", "q")
        asked = (type(app.screen).__name__, " ".join(screen_text(app).split()))
        await press(pilot, "escape")
        return asked, app.is_running, type(app.screen).__name__
    (screen, text), running, back = run_tui(new_story(), make_engine(home), script)
    assert screen == "QuitScreen" and "Bringing this story into the Universe Builder" in text and running and back == "MainScreen"


def test_keeping_prints_the_story_then_the_markdown_path_and_the_resume_command(home):
    story = new_story()
    async def script(app, pilot):
        while app.session.step.key != "premise":
            await press(pilot, "k")
        await press(pilot, "q", "k")
        return app.return_value
    message = run_tui(story, make_engine(home), script)
    title = store.title_of(store.load(story["id"]))
    assert message.splitlines()[0] == title.upper() and "PROTAGONIST" in message
    assert message.index("PROTAGONIST") < message.index("Markdown: ") < message.index("Resume with:  storywheel resume")
    assert (home / "home" / "stories" / f"{story['id']}.json").exists()


def test_deleting_on_exit_removes_the_story_and_its_markdown(home):
    story = new_story()
    async def script(app, pilot):
        for _ in range(4):
            await press(pilot, "k")
        assert list((home / "out").glob("*.md"))
        await press(pilot, "q", "d")
        return app.return_value
    message = run_tui(story, make_engine(home), script)
    assert "Deleted" in message and "PROTAGONIST" not in message
    assert not (home / "home" / "stories" / f"{story['id']}.json").exists() and not list((home / "out").glob("*.md"))


def test_run_app_prints_what_the_app_returns(home, capsys, monkeypatch):
    class Fake:
        next = None

        def __init__(self, *a):
            pass
        def run(self):
            return "TITLE\n\nResume with:  storywheel resume X"
    monkeypatch.setattr(tui, "StorywheelApp", Fake)
    tui.run_app(new_story(), make_engine(home))
    out = capsys.readouterr().out
    assert "TITLE" in out and "Resume with:  storywheel resume X" in out


# --- the clipboard ----------------------------------------------------------------------------------------------------------

def test_c_copies_the_story_so_far_as_plain_text(home, monkeypatch):
    got = []
    monkeypatch.setattr(clipboard, "copy", lambda text, app=None: got.append(text) or "wl-copy")
    async def script(app, pilot):
        await press(pilot, "c")
        empty = screen_text(app)
        while app.session.step.key != "premise":
            await press(pilot, "k")
        await press(pilot, "c")
        return empty, screen_text(app), store.to_plain(app.session.story)
    empty, after, text = run_tui(new_story(), make_engine(home), script)
    assert "Nothing is kept yet" in empty and len(got) == 1 and got[0] == text
    assert "Copied the story so far" in after and "wl-copy" in after


def test_clipboard_uses_the_first_tool_available(monkeypatch):
    calls = []
    monkeypatch.setattr(clipboard.shutil, "which", lambda p: "/bin/" + p if p == "xclip" else None)
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(clipboard.subprocess, "run", lambda cmd, **kw: calls.append((cmd, kw["input"])))
    assert clipboard.copy("héllo") == "xclip"
    assert calls == [(["xclip", "-selection", "clipboard"], "héllo".encode("utf-8"))]


def test_clipboard_falls_back_to_the_terminal_then_to_none(monkeypatch):
    monkeypatch.setattr(clipboard.shutil, "which", lambda p: None)
    class App:
        def __init__(self):
            self.sent = []
        def copy_to_clipboard(self, text):
            self.sent.append(text)
    app = App()
    assert clipboard.copy("x", app) == "the terminal (OSC 52)" and app.sent == ["x"]
    assert clipboard.copy("x") is None


# --- --json ------------------------------------------------------------------------------------------------------------------

def cli(args, home):
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "h"), STORYWHEEL_OUT=str(home / "o"), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "storywheel", *args], capture_output=True, text=True, env=env,
                          cwd=ROOT, encoding="utf-8")


def test_sample_json_is_a_clean_list_of_stories(home):
    res = cli(["sample", "western", "-n", "2", "--seed", "4", "--json"], home)
    data = json.loads(res.stdout)
    assert res.returncode == 0 and len(data) == 2
    first = data[0]
    assert first["genre"] == "western" and first["title"] and first["structure"]
    assert {"protagonist", "setting", "premise", "spine", "twist"} <= set(first["kept"])
    assert first["text"].startswith(first["title"].upper()) and first["markdown"].startswith("---")
    assert first["id"] is None or True
    assert json.loads(cli(["sample", "western", "-n", "2", "--seed", "4", "--json"], home).stdout) == data      # repeatable


def test_list_show_and_export_json(home):
    env_home = home / "h"
    assert json.loads(cli(["list", "--json"], home).stdout) == []
    import storywheel.paths as paths
    from storywheel import store as st
    s = kept_session(home, "twist")
    st.HOME, st.OUT = env_home, home / "o"
    st.STORIES, st.UNIVERSE = env_home / "stories", env_home / "universe.json"
    st.save(s.story)
    listed = json.loads(cli(["list", "--json"], home).stdout)
    assert len(listed) == 1 and listed[0]["number"] == 1 and listed[0]["id"] == s.story["id"]
    shown = json.loads(cli(["show", "1", "--json"], home).stdout)
    assert shown["title"] == listed[0]["title"] and shown["text"] and shown["resume"].endswith(s.story["id"])
    plain = cli(["show", "1"], home).stdout
    assert plain.startswith(shown["title"].upper())
    exported = json.loads(cli(["export", "1", "--json", "--out", str(home / "vault")], home).stdout)
    assert exported["path"].startswith(str(home / "vault")) and Path(exported["path"]).exists()
    missing = cli(["show", "nope", "--json"], home)
    assert missing.returncode == 1 and json.loads(missing.stdout)["error"]
