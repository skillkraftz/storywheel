"""Polish 1: each fix is tested the way it is used, with real keys (and clicks) sent to Neovim's input, never by calling the Lua directly."""
import pytest

from storywheel import vault, writer
from test_notepad import run, LINES, ROOT  # noqa: F401

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


@pytest.fixture
def two(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    s.add_scene("Opening", "The gate was shut.")
    s.add_scene("The Hall", "The guild hall was dark. Priya went in anyway.")
    return s


# --- 1. the scene sidebar ------------------------------------------------------------------------------------------

def test_1_f9_down_enter_then_typing_types_in_scene_two(home, two):
    r = run(two, "", "<F9><Down><CR>dd", LINES + "; R.mode = vim.fn.mode(); R.name = vim.api.nvim_buf_get_name(0)")
    assert r["mode"] == "i"
    text = "\n".join(r["lines"])
    assert "dd" in text and "The guild hall was dark. Priya went in anyway." in text and "* * * The hall" in text


def test_1_f9_then_q_then_typing_types_text(home, two):
    r = run(two, "", "<F9>q" + "hello", LINES + "; R.mode = vim.fn.mode()")
    assert r["mode"] == "i" and any("hello" in l for l in r["lines"])
    assert any(l.startswith("* * * The hall") for l in r["lines"])         # the next scene's marker line is untouched


def test_1_f9_twice_returns_to_typing(home, two):
    r = run(two, "", "<F9><F9>xyz", LINES + "; R.mode = vim.fn.mode()")
    assert r["mode"] == "i" and any("xyz" in l for l in r["lines"])
    assert any(l.startswith("* * * The hall") for l in r["lines"])


def test_1_sidebar_keys_work_straight_after_f9(home, two):
    # no E21 and Down moves the sidebar cursor
    r = run(two, "", "<F9><Down>", "R.row = vim.api.nvim_win_get_cursor(0)[1]; R.win_left = vim.api.nvim_get_current_win() == require('sw.layout').left; R.msg = vim.fn.execute('messages')")
    assert r["win_left"] is True and r["row"] == 2 and "E21" not in r["msg"]


# --- 2. the right-click menu ----------------------------------------------------------------------------------------

from nvdrive import drive, keys, mouse, right_click_text  # noqa: E402

STATE = """
local ctx = require('sw.context').last
R.menu = ctx ~= nil and vim.api.nvim_win_is_valid(ctx.win)
R.f12 = require('sw.menu').last ~= nil and vim.api.nvim_win_is_valid(require('sw.menu').last.win)
R.lines = vim.api.nvim_buf_get_lines(require('sw.layout').main and vim.api.nvim_win_get_buf(require('sw.layout').main) or 0, 0, -1, false)
R.mode = vim.fn.mode()
R.in_main = vim.api.nvim_get_current_win() == require('sw.layout').main
"""
TYPED = [keys("abc ")]                                       # (so that Undo has something to undo)


def test_2_a_right_click_opens_our_own_menu_and_letting_go_runs_nothing(home, two):
    r = drive(two, TYPED + right_click_text(), STATE + "R.native = vim.o.mousemodel")
    assert r["menu"] is True and r["native"] == "extend"
    assert any(l.startswith("abc ") for l in r["lines"])           # Undo did not run, though the button was let go next to an item


def test_2_letting_go_of_the_right_button_over_an_item_runs_nothing(home, two):
    steps = TYPED + [mouse("right", "press", "text_row(1)", "text_col(3)"), mouse("right", "release", "item_row('Undo')", "item_col()")]
    r = drive(two, steps, STATE)
    assert r["menu"] is True and any(l.startswith("abc ") for l in r["lines"])


def test_2_a_second_right_click_closes_it_and_runs_nothing(home, two):
    steps = TYPED + right_click_text() + [mouse("right", "press", "item_row('Undo')", "item_col()"), mouse("right", "release", "item_row('Undo')", "item_col()")]
    r = drive(two, steps, STATE)
    assert r["menu"] is False and r["in_main"] is True and r["mode"] == "i"
    assert any(l.startswith("abc ") for l in r["lines"])


def test_2_escape_closes_it_and_runs_nothing(home, two):
    r = drive(two, TYPED + right_click_text() + [keys("<Esc>")], STATE)
    assert r["menu"] is False and r["in_main"] is True and r["mode"] == "i" and any(l.startswith("abc ") for l in r["lines"])


def test_2_a_left_click_on_an_item_runs_it(home, two):
    steps = TYPED + right_click_text() + [mouse("left", "press", "item_row('Undo')", "item_col()"), mouse("left", "release", "item_row('Undo')", "item_col()")]
    r = drive(two, steps, STATE)
    assert r["menu"] is False and not any(l.startswith("abc ") for l in r["lines"]) and r["mode"] == "i" and r["in_main"] is True


def test_2_enter_runs_the_highlighted_item(home, two):
    r = drive(two, TYPED + right_click_text() + [keys("<CR>")], STATE)          # (the first item is Undo)
    assert r["menu"] is False and not any(l.startswith("abc ") for l in r["lines"])


def test_2_a_left_click_outside_closes_it_without_running_anything(home, two):
    steps = TYPED + right_click_text() + [mouse("left", "press", "text_row(5)", "text_col(60)"), mouse("left", "release", "text_row(5)", "text_col(60)")]
    r = drive(two, steps, STATE)
    assert r["menu"] is False and any(l.startswith("abc ") for l in r["lines"]) and r["mode"] == "i"


def test_2_right_click_inside_the_f12_menu_opens_no_other_menu(home, two):
    steps = [keys("<F12>"), mouse("right", "press", "5", "math.floor(vim.o.columns / 2)"), mouse("right", "release", "5", "math.floor(vim.o.columns / 2)")]
    r = drive(two, steps, STATE)
    assert r["menu"] is False and r["f12"] is True


def test_2_right_click_in_the_help_opens_no_menu(home, two):
    steps = [keys("<F3>"), mouse("right", "press", "5", "math.floor(vim.o.columns / 2)"), mouse("right", "release", "5", "math.floor(vim.o.columns / 2)")]
    r = drive(two, steps, STATE)
    assert r["menu"] is False


def test_2_it_fits_a_short_window_and_scrolls_to_the_last_item(home, two):
    steps = right_click_text() + [keys("<Down><Down><Down><Down><Down><Down><Down><Down><Down>")]
    r = drive(two, steps, STATE + """
        local w = require('sw.context').last.win
        R.height = vim.api.nvim_win_get_height(w); local p = vim.fn.win_screenpos(w); R.bottom = p[1] + R.height
        R.cur = vim.api.nvim_get_current_line()""", lines=12)
    assert r["menu"] is True and r["height"] <= 8 and r["bottom"] <= 12 and "More" in r["cur"]


def test_2_cut_from_the_menu_works_on_a_selection(home, two):
    steps = [keys("<C-Home><S-Right><S-Right><S-Right>"),
             mouse("right", "press", "text_row(1)", "text_col(1)"), mouse("right", "release", "text_row(1)", "text_col(1)"),
             keys("<Down><Down><CR>")]                                              # Undo, Redo, [sep], Cut
    r = drive(two, steps, STATE + "R.reg = vim.fn.getreg('+')")
    assert r["reg"] == "* *" or r["reg"] != ""


# --- 2, in a real terminal (the mouse codes a terminal sends; the menu is drawn and hit-tested for real) ----------------

import os  # noqa: E402
from ptydrive import Term  # noqa: E402
from storywheel import settings  # noqa: E402

pty_only = pytest.mark.skipif(not hasattr(os, "fork"), reason="needs a pseudo-terminal")


@pytest.fixture
def term_story(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    s.add_scene("Opening", "The gate was shut.")
    settings.save_story(s.path, {"spellcheck": False})
    return s


@pty_only
def test_2_real_terminal_right_click_release_over_an_item_second_click_and_left_click(home, term_story):
    t = Term(term_story)
    try:
        t.send("abc ")
        assert "abc " in t.text()
        # press on the text, let go on the menu's first item: nothing runs, the menu stays
        row, col = t.find("abc")
        t.mouse("right", "press", row, col + 1, 0.3)
        t.mouse("right", "release", row, col + 1, 0.5)
        assert "Undo" in t.text() and "More…" in t.text()
        ur, uc = t.find("Undo")
        # a second right-click, on an item: closes the menu, runs nothing
        t.mouse("right", "press", ur, uc + 1, 0.3)
        t.mouse("right", "release", ur, uc + 1, 0.5)
        assert "Undo" not in t.text() and "abc" in t.text()
        # again, then a left click on Undo runs it
        t.click("right", row, col + 1)
        ur, uc = t.find("Undo")
        t.click("left", ur, uc + 1)
        assert "Undo" not in t.text()
        assert "abc " not in t.text()                      # (the space typed last was undone)
        t.send("Z")                                          # and typing still works
        assert "abcZ" in t.text()
    finally:
        t.close()


@pty_only
def test_2_real_terminal_right_click_inside_the_f12_menu_opens_no_second_menu(home, term_story):
    t = Term(term_story)
    try:
        t.key("F12")
        assert "Writer" in t.text()
        r, c = t.find("Spellcheck")
        t.click("right", r, c + 2)
        assert "Add to Dictionary" not in t.text() and "Spellcheck" in t.text()      # no second menu, and the F12 menu is still there
        t.key("Esc")
        t.send("q")
        assert "q" in t.text()
    finally:
        t.close()


@pty_only
def test_2_real_terminal_menu_fits_a_short_window_and_scrolls(home, term_story):
    t = Term(term_story, rows=10, cols=100)
    try:
        t.send("hello")
        r, c = t.find("hello")
        t.click("right", 1, c + 1)
        assert "Undo" in t.text()
        for _ in range(8):
            t.key("Down", wait=0.15)
        assert "More…" in t.text()                          # scrolled to the last item
        shown = [l for l in t.lines() if l.strip()]
        assert len(t.lines()) == 10
        t.key("Esc")
        assert "More…" not in t.text()
    finally:
        t.close()


# --- 3. the Builder: entity keys in the Outline ---------------------------------------------------------------------

import asyncio  # noqa: E402

from storywheel import builder, fill  # noqa: E402

SPINE = ["Once upon a time, Ann lived in Redwater.", "Every day, Ann swept the porch.", "One day, a stranger came.", "Because of that, Ann hid the key.",
         "Because of that, the stranger followed.", "Until finally, Ann ran.", "Ever since then, Ann sleeps lightly."]


def builder_run(script, size=(200, 50)):
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="thornwood", story="the-last-clause")
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


@pytest.fixture
def ann(home):
    u = vault.create_universe("Thornwood", ["western"])
    u.new_entity("character", "Ann Lowell", {"role": "protagonist", "job": "teacher", "trait": "stubborn"})
    u.new_story("The Last Clause", {"structure": "Story Spine", "genre": "western", "mood": "cozy"}, {"Story Spine": "\n\n".join(SPINE)})
    return u


def _entity_files(u):
    return {str(p): p.read_bytes() for p in sorted(u.path.rglob("*.md")) if "characters" in p.parts}


def test_3_entity_keys_in_the_outline_leave_the_entity_alone(home, ann):
    before = _entity_files(ann)

    async def script(app, pilot):
        s = app.screen_ref
        await pilot.click("#outline", offset=(5, 2))                    # focus the outline with a click
        await pilot.pause()
        assert s.focused is s.outline
        sent = {}
        for key in ("space", "R", "plus", "minus", "n", "d", "r", "c"):
            await pilot.press(key)
            await pilot.pause()
            sent[key] = (type(app.screen).__name__, s.query_one("#status").renderable.__str__() if hasattr(s.query_one("#status"), "renderable") else "")
        return sent, type(app.screen).__name__, len(s.universe.entities("character"))
    sent, screen_name, n = builder_run(script)
    assert screen_name != "ConfirmScreen" and not any(v[0] in ("ConfirmScreen", "EditScreen") for v in sent.values()), sent       # (no 'delete?' or 'rename' box)
    assert n == 1 and _entity_files(ann) == before


def test_3_f_in_the_outline_rolls_the_beat_not_the_character(home, ann):
    before = _entity_files(ann)

    async def script(app, pilot):
        s = app.screen_ref
        await pilot.click("#outline", offset=(5, 2))
        await pilot.pause()
        for _ in range(40):                                              # arrow down to the first beat
            if s.top_rows()[s.outline.highlighted or 0][0].startswith("beat:"):
                break
            await pilot.press("down")
        key = s.top_rows()[s.outline.highlighted][0]
        old = [t for k, _l, t in outline_rows(s.story) if k == key][0]
        await pilot.press("f")
        await pilot.pause()
        new = [t for k, _l, t in outline_rows(s.story) if k == key][0]
        return old, new, s.entity.name
    from storywheel.outline import rows as outline_rows
    old, new, name = builder_run(script)
    assert new != old and name == "Ann Lowell"
    assert _entity_files(ann) == before


def test_3_the_keys_still_work_on_the_card(home, ann):
    async def script(app, pilot):
        s = app.screen_ref
        await pilot.click("#card", offset=(5, 1))
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        return len(s.universe.entities("character"))
    assert builder_run(script) == 2
