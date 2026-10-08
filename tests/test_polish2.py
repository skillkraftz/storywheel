"""Polish 2 (ISSUES #19-36): what a writer does, and what they see."""
import pytest

from test_polish1 import ann, builder_run  # noqa: F401  (the fixture and helper of polish 1)


def status(s):
    w = s.query_one("#status")
    for name in ("content", "renderable"):
        if hasattr(w, name):
            return str(getattr(w, name))
    return str(w.render())


# --- 19. messages name the key that works -----------------------------------------------------------------------------------

def test_19_the_structure_row_points_to_m(home, ann):
    async def script(app, pilot):
        s = app.screen_ref
        await pilot.click("#outline", offset=(5, 2))
        await pilot.pause()
        for _ in range(40):
            if s.top_rows()[s.outline.highlighted or 0][0] == "meta:structure":
                break
            await pilot.press("down")
        await pilot.press("e")
        await pilot.pause()
        return status(s)
    msg = builder_run(script)
    assert "with m" in msg and "Wheel" not in msg, msg


def test_19_p_on_a_prose_story_points_to_m(home, ann):
    async def script(app, pilot):
        s = app.screen_ref
        await pilot.press("P")
        await pilot.pause()
        return status(s)
    msg = builder_run(script)
    assert "not a screenplay" in msg and "with m" in msg and "(S, story settings)" not in msg, msg



# --- 20. story settings (S) and your details (G) -----------------------------------------------------------------------------

from storywheel import settings, vault  # noqa: E402
from textual.widgets import Input, Select, Tabs  # noqa: E402
from test_polish1 import _hub_run  # noqa: E402


def test_20_story_settings_are_choices_and_say_what_follows_your_default(home, ann):
    settings.save_global({**settings.load_global(), "daily_goal": 800})

    async def script(app, pilot):
        s = app.screen_ref
        await pilot.press("S")
        await pilot.pause()
        dlg = app.screen
        notes = {k: str(dlg.query_one(f"#note-{k}").content) for k in ("daily_goal", "typewriter", "font")}
        goal = dlg.query_one("#f-daily_goal", Input)
        shown = goal.placeholder
        goal.focus()
        await pilot.pause()
        for ch in "1200":
            await pilot.press(ch)
        sel = dlg.query_one("#f-typewriter", Select)
        sel.focus()
        await pilot.pause()
        await pilot.press("enter", "down", "enter")                   # your default -> on
        await pilot.pause()
        typed = (sel.value, str(dlg.query_one("#note-typewriter").content), str(dlg.query_one("#note-daily_goal").content))
        await pilot.click("#save")
        await pilot.pause()
        return notes, shown, typed, type(app.screen).__name__
    notes, shown, typed, after = builder_run(script)
    assert "follows your default: 800" in notes["daily_goal"] and "follows your default: off" in notes["typewriter"]
    assert shown == "your default (800)"
    assert typed[0] == "on" and "this story's own" in typed[1] and "this story's own" in typed[2]
    assert after != "StorySettingsScreen"
    own = settings.story_own(vault.get_universe("thornwood").story("the-last-clause").path)
    assert own == {"daily_goal": 1200, "typewriter": True}               # only what was chosen is stored; the font and the rest still follow


def test_20_clearing_a_story_setting_goes_back_to_your_default(home, ann):
    story = ann.story("the-last-clause")
    settings.save_story(story.path, {"daily_goal": 1200, "typewriter": True, "font": "Courier New"})

    async def script(app, pilot):
        await pilot.press("S")
        await pilot.pause()
        dlg = app.screen
        assert dlg.query_one("#f-daily_goal", Input).value == "1200" and dlg.query_one("#f-typewriter", Select).value == "on"
        dlg.query_one("#f-daily_goal", Input).focus()
        await pilot.pause()
        for _ in range(4):
            await pilot.press("backspace")
        sel = dlg.query_one("#f-typewriter", Select)
        sel.focus()
        await pilot.pause()
        await pilot.press("enter", "up", "enter")                      # on -> your default
        await pilot.pause()
        await pilot.click("#save")
        await pilot.pause()
    builder_run(script)
    assert settings.story_own(story.path) == {"font": "Courier New"}
    assert settings.load_story(story.path)["daily_goal"] == 500 and settings.load_story(story.path)["typewriter"] is False


def test_20_escape_changes_nothing(home, ann):
    story = ann.story("the-last-clause")

    async def script(app, pilot):
        await pilot.press("S")
        await pilot.pause()
        app.screen.query_one("#f-daily_goal", Input).focus()
        await pilot.pause()
        await pilot.press("9", "escape")
        await pilot.pause()
    builder_run(script)
    assert not (story.path / "settings.toml").exists() or settings.story_own(story.path) == {}


def test_20_g_opens_settings_on_the_you_tab_with_the_tab_bar_focused(home, ann):
    async def script(app, pilot):
        await pilot.press("G")
        await pilot.pause()
        await pilot.pause()
        scr = app.screen
        return app.mode_name, scr.query_one("#tabs").active, isinstance(scr.focused, Tabs)
    assert _hub_run(script, ("builder", {"universe": "thornwood", "story": "the-last-clause"})) == ("settings", "t-you", True)


# --- 21. the help screen's layout ---------------------------------------------------------------------------------------------

def _help_keys_text(start, mode, size=(200, 50)):
    from conftest import screen_text
    from textual.widgets import Static

    async def script(app, pilot):
        await pilot.press("question_mark")
        await pilot.pause()
        await pilot.pause()
        head = " ".join(screen_text(app).split())
        await pilot.press("2")                                           # the Keys tab
        await pilot.pause()
        await pilot.pause()
        return head, str(app.screen.query_one("#help-text", Static).content)
    return _hub_run(script, start, size)


def test_21_the_help_hint_line_is_whole_and_says_how_to_close(home, ann):
    head, _keys = _help_keys_text(("builder", {"universe": "thornwood", "story": "the-last-clause"}), "builder", size=(200, 50))
    assert "Esc or q closes" in head


def test_21_a_key_shown_in_another_rows_label_is_not_listed_again(home, ann):
    _head, text = _help_keys_text(("wheel", {}), "wheel")
    rows = [l.split("  ")[1].strip() if l.startswith("  ") and "  " in l[2:] else None for l in text.splitlines()]
    assert "+/-" in rows and "-" not in rows                   # one row for liking and disliking
    assert "u/U" not in rows and "u" in rows and "U" in rows   # u and U do different things: two rows, each under its own key
    _head, text = _help_keys_text(("builder", {"universe": "thornwood", "story": "the-last-clause"}), "builder")
    rows = [l.split("  ")[1].strip() if l.startswith("  ") and "  " in l[2:] else None for l in text.splitlines()]
    assert "+/-" in rows and "-" not in rows


@pytest.mark.parametrize("start", [("wheel", {}), ("builder", {"universe": "thornwood", "story": "the-last-clause"})])
def test_21_a_long_description_hangs_under_its_own_column(home, ann, start):
    from storywheel import helpdoc
    _head, text = _help_keys_text(start, start[0], size=(130, 50))
    titles = {t for t, _items in helpdoc.binding_rows(start[0])}
    body = text.split("\nMouse\n")
    keys_part = [l for l in body[0].splitlines()[2:]]                   # (after the 'Keys' heading and its underline)
    stray = [l for l in keys_part if l.strip() and not l.startswith(" ") and l not in titles]
    assert not stray, stray                                   # every wrapped line starts under the descriptions, none at the left edge
    if len(body) > 1:
        mouse = [l for l in body[1].splitlines()[1:] if l.strip()]
        assert all(l.startswith(("- ", " ")) for l in mouse), mouse    # a wrapped bullet hangs under its text
    longest = max(text.splitlines(), key=len)
    assert len(longest) <= 130 - 8


# --- 23. a new card has a highlighted row ---------------------------------------------------------------------------------------

def test_23_a_new_card_starts_on_its_first_row_and_down_moves_to_the_second(home, ann):
    async def script(app, pilot):
        s = app.screen_ref
        await pilot.click("#card", offset=(5, 1))
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        first = (s.card.highlighted, s.field_key())
        await pilot.press("down")
        await pilot.pause()
        return first, (s.card.highlighted, s.field_key())
    first, second = builder_run(script)
    assert first == (0, "name") and second[0] == 1 and second[1] != "name"


# --- 24. the Wheel card: a near miss on ▲ ▼ does not reroll ------------------------------------------------------------------------

def test_24_clicks_next_to_the_arrows_change_nothing_and_the_arrows_still_rate(home):
    from conftest import make_engine, run_tui
    from test_mouse import arrow_at, click, go_to, new_story, row_of

    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "protagonist")
        row = row_of(app, "job")
        up_x, up_y = arrow_at(app, "job", 1)
        before = (dict(s.fields), len(s.hist))
        for dx in (-1, -2):                                           # just left of ▲ (the gap), and the cell before it
            await click(pilot, (up_x + dx, up_y))
        await click(pilot, (up_x + 6, up_y))                         # just right of ▼
        unchanged = (dict(s.fields), len(s.hist)) == before
        await click(pilot, (6, row))                                  # the value itself still rerolls
        rerolled = s.fields["job"] != before[0]["job"]
        up_x, up_y = arrow_at(app, "job", 1)
        await click(pilot, (up_x + 1, up_y))                          # and the middle of ▲ still rates
        return unchanged, rerolled, s.rating("job")
    unchanged, rerolled, rated = run_tui(new_story(), make_engine(home), script)
    assert unchanged and rerolled and rated == 1


# --- 25. Past stories: long titles, and copies that say so ------------------------------------------------------------------------

def test_25_past_stories_show_long_titles_and_mark_copies(home):
    import time
    from conftest import make_engine, run_tui, screen_text
    from storywheel import store
    first = store.new_story()
    first["kept"]["title"] = {"title": "Dry Summer of Ann Lowell"}
    store.save(first)
    time.sleep(1.1)
    copy = store.copy_as_new(first)
    store.save(copy)

    async def script(app, pilot):
        await pilot.pause()
        await pilot.pause()
        return screen_text(app)
    text = run_tui(copy, make_engine(home), script, size=(200, 50))
    rows = [l for l in text.splitlines() if "10-08" in l and "Dry Summer" in l]
    assert len(rows) == 2, rows
    original = next(l for l in rows if "(copy)" not in l)
    copied = next(l for l in rows if "(copy)" in l)
    assert "Dry Summer of Ann Lowell 10-08" in " ".join(original.split()) or "Dry Summer of Ann Lowell " in original      # not cut at 22 characters
    assert "(copy)" in copied and "…" in copied.split("(copy)")[0]                                                       # the copy keeps its mark when the title is cut


# --- 26. every entry of the F12 menu shows a key of its own ----------------------------------------------------------------------------

from test_notepad import run as nvrun  # noqa: E402
from test_polish1 import two  # noqa: E402,F401


def test_26_every_writer_menu_entry_has_a_distinct_key_shown_beside_it_and_it_runs_the_entry(home, two):
    r = nvrun(two, "", "<F12>", """
        local m = require('sw.menu').last
        R.keys = m.keys; R.n = #m.items
        R.lines = vim.api.nvim_buf_get_lines(m.buf, 0, -1, false)
        R.labels = {}; for i, it in ipairs(m.items) do R.labels[i] = it[1] end
        R.mapped = 0
        vim.api.nvim_buf_call(m.buf, function() for _, k in ipairs(m.keys) do if vim.fn.maparg(k, 'n', false, true).buffer == 1 then R.mapped = R.mapped + 1 end end end)""")
    assert r["mapped"] == r["n"]                                                   # every shown key is really a key of the menu
    assert len(r["keys"]) == r["n"] >= 30 and len(set(r["keys"])) == r["n"]
    assert not {"j", "k", "q"} & set(r["keys"])                                   # (those move and close)
    shown = {}
    for line in r["lines"]:
        parts = line.split()
        if parts and parts[0] in r["keys"] and " ".join(parts[1:]) in r["labels"]:
            shown[parts[0]] = " ".join(parts[1:])
    assert list(shown) == r["keys"], (shown, r["keys"])                          # every entry has its key printed beside it
    # a key past the ninth runs its entry: the last one, by its own key
    last = r["labels"][-1]
    r2 = nvrun(two, "", "<F12>" + r["keys"][-1], "R.closed = require('sw.menu').last == nil or not vim.api.nvim_win_is_valid(require('sw.menu').last.win)")
    assert r2["closed"] is True and last


# --- 27. find and replace: the key hints on the border are whole -------------------------------------------------------------------------

import os  # noqa: E402
from ptydrive import Term  # noqa: E402
from test_polish1 import term_story, pty_only  # noqa: E402,F401


@pty_only
@pytest.mark.parametrize("cols,hint", [(120, "Enter next · Alt+R replace · Alt+A all · Alt+C case · Alt+W word · Esc close"),
                                       (70, "Alt+A all · Alt+C case · Alt+W word · Esc")])
def test_27_real_terminal_the_replace_forms_hints_are_not_cut(home, term_story, cols, hint):
    t = Term(term_story, rows=30, cols=cols)
    try:
        t.key("Ctrl+R", wait=0.8)
        bottom = [l for l in t.lines() if "╰" in l and "╯" in l]
        assert bottom, t.text()
        assert hint in " ".join(bottom[0].split()), bottom
    finally:
        t.close()
