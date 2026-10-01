"""The full-screen app, driven by key presses."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from textual.widgets import Input

from storywheel import store
from storywheel import tui
from storywheel.steps import public
from conftest import make_engine, run_tui, screen_text

ROOT = Path(__file__).resolve().parent.parent


def new_story():
    return store.new_story()


async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


async def go_to(app, pilot, step_key):
    s = app.session
    while s.step.key != step_key:
        await press(pilot, "k")


# --- the layout -----------------------------------------------------------------------------------------------

def test_the_screen_has_steps_a_card_a_history_and_a_footer_with_the_keys(home):
    async def script(app, pilot):
        return screen_text(app)
    text = run_tui(new_story(), make_engine(home), script)
    for step in ("Genre & mood", "Structure", "Title", "Protagonist", "Setting", "Premise", "Story Spine", "Twist"):
        assert step in text
    assert "▶ 1 Genre & mood" in text and "· 2 Structure" in text
    assert "History: every roll" in text and "#1 of 1" in text
    for needle in ("space Roll", "k Keep", "q Quit", "? Help", "f Field", "e Edit"):
        assert needle in text, needle


def test_the_sidebar_marks_kept_skipped_current_and_pending(home):
    async def script(app, pilot):
        await press(pilot, "k")             # keep genre
        await press(pilot, "x")             # skip structure
        await press(pilot, "k")             # keep title
        return screen_text(app)
    text = run_tui(new_story(), make_engine(home), script)
    assert "✓ 1 Genre & mood" in text and "– 2 Structure" in text
    assert "✓ 3 Title" in text or "● 3 Title" in text           # (● if the title invented a stand-in name)
    assert "▶ 4 Protagonist" in text and "· 5 Setting" in text


def test_space_rolls_and_k_keeps(home):
    async def script(app, pilot):
        s = app.session
        first = dict(s.fields)
        await press(pilot, "space")
        assert len(s.hist) == 2 and s.fields != first
        await press(pilot, "k")
        return s.step.key, dict(s.story["kept"]["genre"]), len(s.hist)
    step, kept, n = run_tui(new_story(), make_engine(home), script)
    assert step == "structure" and set(kept) == {"genre", "mood"}


def test_enter_on_the_card_also_rolls(home):
    async def script(app, pilot):
        await press(pilot, "enter")
        return len(app.session.hist)
    assert run_tui(new_story(), make_engine(home), script) == 2


def test_b_goes_back_and_x_skips(home):
    async def script(app, pilot):
        s = app.session
        await press(pilot, "k", "k")
        assert s.step.key == "title"
        await press(pilot, "b")
        assert s.step.key == "structure"
        await press(pilot, "x")
        return s.step.key, s.marker(1)
    assert run_tui(new_story(), make_engine(home), script) == ("title", "skipped")


def test_enter_on_a_step_in_the_sidebar_jumps_there(home):
    async def script(app, pilot):
        steps = app.main.steps_list
        steps.focus()
        await pilot.pause()
        await press(pilot, "down", "down", "down", "enter")
        return app.session.step.key, app.focused.id
    assert run_tui(new_story(), make_engine(home), script) == ("protagonist", "card")


# --- the card and fields --------------------------------------------------------------------------------------------

def test_arrow_keys_select_fields_and_f_rerolls_only_that_one(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "protagonist")
        before = dict(s.fields)
        await press(pilot, "down", "down")                    # name, age, job
        assert app.main.card_field() == "job"
        await press(pilot, "f")
        after = dict(s.fields)
        return before, after, app.main.card_field()
    before, after, field = run_tui(new_story(), make_engine(home), script)
    assert field == "job" and after["job"] != before["job"]
    assert after["name"] == before["name"] and after["age"] == before["age"] and after["trait"] == before["trait"]


def test_f_on_a_one_field_step_rolls_the_whole_thing(home):
    async def script(app, pilot):
        await go_to(app, pilot, "premise")
        n = len(app.session.hist)
        await press(pilot, "f")
        return len(app.session.hist) - n, screen_text(app)
    added, text = run_tui(new_story(), make_engine(home), script)
    assert added == 1 and "one field" in text


# --- history ------------------------------------------------------------------------------------------------------------

def test_the_history_panel_shows_what_changed_between_rolls(home):
    async def script(app, pilot):
        await go_to(app, pilot, "protagonist")
        await press(pilot, "down", "down", "f")
        return screen_text(app)
    text = run_tui(new_story(), make_engine(home), script)
    assert "#1" in text and "#2" in text and "job:" in text.split("History")[1]


def test_selecting_a_field_and_pressing_h_shows_that_fields_own_history(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "protagonist")
        await press(pilot, "down", "down", "f", "f")           # job three times
        await press(pilot, "h")
        return screen_text(app), app.main.hist_mode, s.field_values("job"), app.focused.id
    text, mode, jobs, focused = run_tui(new_story(), make_engine(home), script)
    assert mode == "field" and focused == "history" and len(jobs) == 3
    assert "History of: job" in text
    for job in jobs:
        assert job in text


def test_the_field_history_follows_the_selected_field(home):
    async def script(app, pilot):
        await go_to(app, pilot, "protagonist")
        await press(pilot, "down", "down", "f", "h")
        await press(pilot, "escape")                            # back to the card, still in field mode
        await press(pilot, "down")                              # trait
        return screen_text(app)
    assert "History of: trait" in run_tui(new_story(), make_engine(home), script)


def test_h_toggles_back_to_every_roll(home):
    async def script(app, pilot):
        await go_to(app, pilot, "protagonist")
        await press(pilot, "down", "h")
        await press(pilot, "h")
        return app.main.hist_mode
    assert run_tui(new_story(), make_engine(home), script) == "rolls"


def test_enter_on_a_history_row_picks_that_candidate(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "setting")
        await press(pilot, "space", "space")
        first = dict(s.hist[0])
        app.main.history.focus()                                # the history of every roll is showing by default
        await pilot.pause()
        await press(pilot, "home", "enter")
        return s.cur, public(s.cand) == public(first)
    assert run_tui(new_story(), make_engine(home), script) == (0, True)


def test_enter_on_a_field_history_row_brings_that_value_back_without_losing_the_rest(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "protagonist")
        await press(pilot, "down", "down", "f", "f")
        values = s.field_values("job")
        rest = {k: v for k, v in s.fields.items() if k != "job"}
        await press(pilot, "h")
        await press(pilot, "home", "enter")
        return s.fields["job"] == values[0], {k: v for k, v in s.fields.items() if k != "job"} == rest
    assert run_tui(new_story(), make_engine(home), script) == (True, True)


# --- editing ------------------------------------------------------------------------------------------------------------------

def test_e_opens_a_box_with_the_current_text_and_enter_applies_it(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "setting")
        await press(pilot, "down")                              # era (place is 0)
        field = app.main.card_field()
        current = s.fields[field]
        await press(pilot, "e")
        box = app.screen.query_one(Input)
        assert box.value == current
        box.value = "an age of glass"
        await press(pilot, "enter")
        return field, s.fields[field], s.cand["_src"], len(s.hist)
    field, value, src, n = run_tui(new_story(), make_engine(home), script)
    assert (value, src, n) == ("an age of glass", "edited", 2)


def test_escape_cancels_an_edit(home):
    async def script(app, pilot):
        await go_to(app, pilot, "setting")
        before = dict(app.session.fields)
        await press(pilot, "e")
        app.screen.query_one(Input).value = "changed my mind"
        await press(pilot, "escape")
        return dict(app.session.fields) == before, len(app.session.hist)
    assert run_tui(new_story(), make_engine(home), script) == (True, 1)


def test_w_writes_your_own_in_one_box_per_field(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "setting")
        await press(pilot, "w")
        boxes = list(app.screen.query(Input))
        assert len(boxes) == len(s.fields)
        boxes[0].value = "Oakhaven"
        for _ in boxes:
            await press(pilot, "enter")
        return s.fields["place"], s.fields["season"] == s.hist[0]["season"], s.cand["_src"]
    assert run_tui(new_story(), make_engine(home), script) == ("Oakhaven", True, "edited")


def test_capital_e_edits_in_the_external_editor(home, monkeypatch):
    from storywheel import cli
    monkeypatch.setattr(cli, "edit_in_editor", lambda fields: dict(fields, mood="a brand new mood"))
    from contextlib import contextmanager

    @contextmanager
    def no_suspend(*a, **k):
        yield
    async def script(app, pilot):
        monkeypatch.setattr(app, "suspend", no_suspend)
        await press(pilot, "E")
        return app.session.fields["mood"]
    assert run_tui(new_story(), make_engine(home), script) == "a brand new mood"


# --- ratings --------------------------------------------------------------------------------------------------------------------

def test_plus_and_minus_rate_the_selected_line_and_show_a_marker(home):
    async def script(app, pilot):
        await go_to(app, pilot, "setting")
        await press(pilot, "down", "down", "down", "down")       # rumor
        assert app.main.card_field() == "rumor"
        await press(pilot, "minus")
        marked = screen_text(app)
        rated = app.session.rating("rumor")
        await press(pilot, "minus")                              # again: cleared
        return marked, rated, app.session.rating("rumor"), app.session.fields["rumor"]
    marked, rated, cleared, rumor = run_tui(new_story(), make_engine(home), script)
    assert rated == -1 and cleared == 0 and "▼" in marked
    saved = json.loads((home / "home" / "ratings.json").read_text())["ratings"]
    assert [r["rating"] for r in saved] == [-1, 0] and saved[0]["text"] == rumor
    assert saved[0]["frame"]["slot"] == "rumor"


def test_plus_marks_a_line_liked(home):
    async def script(app, pilot):
        await go_to(app, pilot, "premise")
        await press(pilot, "plus")
        return screen_text(app), app.session.rating()
    text, rating = run_tui(new_story(), make_engine(home), script)
    assert rating == 1 and "▲" in text


def test_the_equals_key_works_as_plus(home):
    async def script(app, pilot):
        await go_to(app, pilot, "premise")
        await press(pilot, "equals_sign")
        return app.session.rating()
    assert run_tui(new_story(), make_engine(home), script) == 1


# --- the universe ----------------------------------------------------------------------------------------------------------------





# --- dialogs don't leak keys -------------------------------------------------------------------------------------------------------

def test_the_help_screen_opens_and_the_keys_underneath_do_nothing(home):
    async def script(app, pilot):
        s = app.session
        await press(pilot, "question_mark")
        text = screen_text(app)
        n, step = len(s.hist), s.step.key
        await press(pilot, "k", "space", "x")                   # none of these may act on the story
        unchanged = (len(s.hist), s.step.key) == (n, step)
        await press(pilot, "escape")
        await press(pilot, "k")
        return text, unchanged, s.step.key
    text, unchanged, step = run_tui(new_story(), make_engine(home), script)
    assert "Keys" in text and "mix editor" in text and unchanged and step == "structure"


def test_typing_in_the_edit_box_does_not_trigger_keys(home):
    async def script(app, pilot):
        await go_to(app, pilot, "setting")
        await press(pilot, "e")
        box = app.screen.query_one(Input)
        box.value = ""
        await press(pilot, "k", "q", "x", "f")                 # letters typed into the box
        return box.value, app.session.step.key, app.is_running
    value, step, running = run_tui(new_story(), make_engine(home), script)
    assert value == "kqxf" and step == "setting" and running


# --- the mix editor ------------------------------------------------------------------------------------------------------------------

def test_the_mix_editor_says_it_is_for_this_story_only(home):
    async def script(app, pilot):
        await press(pilot, "k", "m")
        return screen_text(app)
    text = " ".join(run_tui(new_story(), make_engine(home), script).split())      # (the banner wraps)
    assert "THIS STORY ONLY" in text and "never touch the genre profiles" in text and "nothing you have kept changes" in text
    assert "Tag" in text and "Default" in text and "Now" in text
    assert "Exclude" in text and "genre defaults" in text


def test_the_mix_editor_lists_every_tag_with_its_weight(home):
    async def script(app, pilot):
        s = app.session
        s.story["kept"]["genre"] = {"genre": "western / fairy tale", "mood": "cozy"}
        from storywheel.mix import sync_base
        sync_base(s.story)
        await press(pilot, "m")
        return [r for r in app.screen.tag_rows()]
    rows = {r[0]: r for r in run_tui(new_story(), make_engine(home), script)}
    assert {"western", "fairy tale", "historical", "fantasy", "general", "modern"} <= set(rows)
    assert rows["western"][3] == "1.5" and rows["general"][3] == "0.3"


def test_e_excludes_a_tag_for_this_story_and_plus_boosts_it(home):
    async def script(app, pilot):
        s = app.session
        s.story["kept"]["genre"] = {"genre": "western", "mood": "cozy"}
        from storywheel.mix import sync_base
        sync_base(s.story)
        await press(pilot, "m")
        first = app.screen.current_key()                        # the heaviest tag
        await press(pilot, "e")
        excluded = list(s.story["mix"]["exclude_tags"])
        text = screen_text(app)
        await press(pilot, "e")                                 # again: allowed
        await press(pilot, "plus", "plus")
        boost = dict(s.story["mix"]["boost"])
        await press(pilot, "minus")
        boost2 = dict(s.story["mix"]["boost"])
        await press(pilot, "0")
        return first, excluded, "excluded" in text, list(s.story["mix"]["exclude_tags"]), boost, boost2, dict(s.story["mix"]["boost"])
    first, excluded, shown, after, boost, boost2, cleared = run_tui(new_story(), make_engine(home), script)
    assert first == "western" and excluded == ["western"] and shown and after == []
    assert boost == {"western": 1.5} and boost2 == {"western": 1.25} and cleared == {}


def test_the_mix_editor_can_exclude_a_list_and_reset_to_defaults(home):
    async def script(app, pilot):
        s = app.session
        await press(pilot, "k", "m")
        await press(pilot, "tab")                                # the lists
        assert app.screen.view == "lists"
        key = app.screen.current_key()
        await press(pilot, "e")
        excluded_list = list(s.story["mix"]["exclude_lists"])
        await press(pilot, "tab", "e", "plus")                   # a tag excluded and boosted too
        dirty = (bool(s.story["mix"]["exclude_tags"]), bool(s.story["mix"]["boost"]))
        await press(pilot, "r")
        return key, excluded_list, dirty, dict(s.story["mix"])
    key, excluded, dirty, mix = run_tui(new_story(), make_engine(home), script)
    assert excluded == [key] and dirty[0] and dirty[1]
    assert mix["exclude_tags"] == [] and mix["exclude_lists"] == [] and mix["boost"] == {} and mix["base"]


def test_mix_changes_affect_future_rolls_and_never_what_is_kept(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "protagonist")
        kept_before = json.dumps(s.story["kept"], sort_keys=True)
        await press(pilot, "m", "e", "escape")
        kept_after = json.dumps(s.story["kept"], sort_keys=True)
        return kept_before == kept_after, bool(s.story["mix"]["exclude_tags"]), app.screen is app.main
    assert run_tui(new_story(), make_engine(home), script) == (True, True, True)


def test_leaving_the_mix_editor_saves_the_story(home):
    async def script(app, pilot):
        await press(pilot, "k", "m", "e", "escape")
        return app.session.story["id"]
    sid = run_tui(new_story(), make_engine(home), script)
    saved = json.loads((home / "home" / "stories" / f"{sid}.json").read_text())
    assert saved["mix"]["exclude_tags"] or saved["mix"]["exclude_lists"]


def test_the_mix_editor_never_changes_the_genre_profiles(home):
    from storywheel.library import Library
    before = json.dumps(Library.load().profiles, sort_keys=True)
    async def script(app, pilot):
        await press(pilot, "k", "m", "e", "plus", "plus", "r", "e", "escape")
    run_tui(new_story(), make_engine(home), script)
    assert json.dumps(Library.load().profiles, sort_keys=True) == before


# --- saving, finishing, quitting ------------------------------------------------------------------------------------------------------------

def test_q_saves_and_quits_with_a_resume_hint(home):
    story = new_story()
    async def script(app, pilot):
        await press(pilot, "k", "k")
        await pilot.press("q")
        await pilot.pause()
        await pilot.press("k")                      # "Keep this story or delete it?" -> keep
        await pilot.pause()
        return app.return_value
    message = run_tui(story, make_engine(home), script)
    assert f"storywheel resume {story['id']}" in message
    saved = json.loads((home / "home" / "stories" / f"{story['id']}.json").read_text())
    assert set(saved["kept"]) == {"genre", "structure"} and saved["step"] == 2


def test_keeping_the_last_step_shows_the_done_screen_and_writes_the_markdown(home):
    async def script(app, pilot):
        for _ in range(8):
            await press(pilot, "k")
        return screen_text(app), app.session.done
    text, done = run_tui(new_story(), make_engine(home), script)
    assert done and "Done:" in text and "Markdown:" in text
    assert list((home / "out").glob("*.md"))


def test_escape_on_the_done_screen_lets_you_keep_editing(home):
    async def script(app, pilot):
        for _ in range(8):
            await press(pilot, "k")
        await press(pilot, "escape")
        return app.session.step.key, app.session.done, app.screen is app.main
    assert run_tui(new_story(), make_engine(home), script) == ("twist", False, True)


def test_resuming_a_story_starts_on_the_step_it_stopped_at(home):
    story = new_story()
    async def first(app, pilot):
        await press(pilot, "k", "k", "k")
        await pilot.press("q")
        await pilot.pause()
        await pilot.press("k")                      # "Keep this story or delete it?" -> keep
        await pilot.pause()
    run_tui(story, make_engine(home), first)
    again = store.load(story["id"])
    async def second(app, pilot):
        return app.session.step.key, screen_text(app)
    step, text = run_tui(again, make_engine(home, seed=9), second)
    assert step == "protagonist" and ("✓ 3 Title" in text or "● 3 Title" in text)


# --- the launcher ------------------------------------------------------------------------------------------------------------------------------

def run_cli(args, stdin, home):
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "h"), STORYWHEEL_OUT=str(home / "o"), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "storywheel", *args], input=stdin, capture_output=True, text=True,
                          env=env, cwd=ROOT, encoding="utf-8")


def test_the_plain_prompt_is_still_there_with_dash_dash_plain(home):
    res = run_cli(["--plain"], "k\nk\nq\n", home)
    assert res.returncode == 0 and "GENRE & MOOD" in res.stdout and "STRUCTURE" in res.stdout and "Saved" in res.stdout
    res = run_cli(["--plain", "list"], "", home)
    assert res.returncode == 0
    res = run_cli(["new", "--plain"], "q\n", home)
    assert "GENRE & MOOD" in res.stdout


def test_without_a_terminal_the_plain_prompt_is_used_automatically(home):
    res = run_cli([], "q\n", home)                      # stdin is a pipe here
    assert "GENRE & MOOD" in res.stdout


def test_plain_plus_and_minus_rate_lines(home):
    script = "\n".join(["k", "k", "k", "+ 3", "- 3", "- 4", "x", "x", "+", "q"]) + "\n"
    res = run_cli(["--plain"], script, home)
    assert res.returncode == 0, res.stderr
    ratings = json.loads((home / "h" / "ratings.json").read_text())["ratings"]
    now = {}
    for r in ratings:
        now[(r["step"], r["field"])] = r["rating"]
    assert now == {("protagonist", "job"): -1, ("protagonist", "trait"): -1, ("premise", "premise"): 1}
    res = run_cli(["report"], "", home)
    assert "rated lines: 1 liked, 2 disliked" in res.stdout and "Worst-rated lines" in res.stdout


# --- in a real terminal ------------------------------------------------------------------------------------------------------------------

@pytest.mark.skipif(not hasattr(os, "fork"), reason="needs a pseudo-terminal")
def test_in_a_real_terminal_the_app_starts_and_q_saves_and_quits(home):
    import pty
    import select
    import time
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "h"), STORYWHEEL_OUT=str(home / "o"),
               TERM="xterm-256color", COLUMNS="110", LINES="34")
    pid, fd = pty.fork()
    if pid == 0:                                              # the child: run the real command
        os.chdir(ROOT)
        os.execvpe(sys.executable, [sys.executable, "-m", "storywheel"], env)
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
    os.write(fd, b"k")
    drain(1.0)
    os.write(fd, b"q")
    drain(1.0)
    os.write(fd, b"k")
    drain(3.0)
    _, status = os.waitpid(pid, 0)
    text = out.decode("utf-8", "replace")
    assert os.WEXITSTATUS(status) == 0
    assert "Genre" in text and "Resume with:  storywheel resume" in text
    assert list((home / "h" / "stories").glob("*.json"))


# --- stand-ins and stale candidates ---------------------------------------------------------------------------

def test_the_card_names_stand_ins_and_offers_update_when_they_go_stale(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "title")
        await press(pilot, "k")                                   # protagonist showing, unkept
        steps = s.steps
        await pilot.click("#steps", offset=(4, 6)); await pilot.pause()      # jump ahead to the spine
        assert s.step.key == "spine"
        notice = screen_text(app)
        stand_in = s.cand["_made"]["first"]
        await pilot.click("#steps", offset=(4, 3)); await pilot.pause()      # back to the protagonist
        s.edit_field("name", "Stacie Anderson"); app.main.after()
        await press(pilot, "k")
        await pilot.click("#steps", offset=(4, 6)); await pilot.pause()
        banner = " ".join(screen_text(app).split())
        await pilot.click("#ban-update"); await pilot.pause()
        return notice, stand_in, banner, s.is_stale(), " ".join(s.fields.values())
    notice, stand_in, banner, stale, text = run_tui(new_story(), make_engine(home), script, size=(200, 50))
    assert "Jumped ahead" in notice and "stand-ins" in notice
    assert f"Built for {stand_in}; your protagonist is now Stacie Anderson" in banner
    assert "Update" in banner and "Reroll" in banner and "Ignore" in banner and "Keep as is" not in banner
    assert not stale and "Stacie" in text and stand_in not in text
