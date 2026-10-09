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


# --- 4. F3 from the Wheel, and the Writer always shows the story's title ------------------------------------------------

import contextlib  # noqa: E402

from storywheel import hub as hubmod, modes, promote, store  # noqa: E402
from storywheel.engine import Engine  # noqa: E402
from storywheel.ratings import Ratings  # noqa: E402
from conftest import screen_text  # noqa: E402


def _hub_run(script, start, size=(190, 50)):
    async def go():
        app = hubmod.Hub(start, lambda: Engine(seed=3), lambda: Ratings())
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


def _record_writer(monkeypatch):
    calls = []

    def fake_run(story, scene=None, replace=None):
        calls.append((story.universe.slug, story.slug))
        fake_run.handover = None
        writer.run.handover = None
        return "builder"
    monkeypatch.setattr(writer, "run", fake_run)
    monkeypatch.setattr(writer, "check", lambda: None)
    monkeypatch.setattr(hubmod, "quiet_suspend", lambda app: contextlib.nullcontext())
    return calls


def _draft_promoted_into_its_own_universe(home):
    """The audit's case: the last Builder story is in Thornwood; the draft was promoted into a universe of its own and has Thornwood ticked."""
    from storywheel.sample import build_story
    thorn = vault.create_universe("Thornwood", ["western"])
    legacy = thorn.new_story("Legacy Labels", {"genre": "western"}, {"Premise": "Labels."})
    legacy.add_scene("Opening", "Old labels.")
    draft = build_story(Engine(seed=5), ["western"])
    draft["universes"] = ["thornwood"]
    store.save(draft)
    return thorn, legacy, draft, None


def test_4_f3_in_the_wheel_opens_the_drafts_own_story_not_the_last_builder_story(home, monkeypatch):
    modes.TRAIL.clear()
    thorn, legacy, draft, plan = _draft_promoted_into_its_own_universe(home)
    own = vault.create_universe("A Curfew for Xavi", ["western"])
    mine = own.new_story("A Curfew for Xavi", {"genre": "western"}, {"Premise": "Curfew."})
    mine.add_scene("Opening", "Xavi.")
    draft["promoted"] = {"universe": own.slug, "story": mine.slug}
    store.save(draft)
    state_mod = __import__("storywheel.state", fromlist=["State"])
    state_mod.State().update(universe="thornwood", story="legacy-labels", mode="wheel")      # (where the Builder was last)
    calls = _record_writer(monkeypatch)

    async def script(app, pilot):
        await pilot.press("f3")
        await pilot.pause()
        await pilot.pause()
        return calls[:]
    got = _hub_run(script, ("wheel", {"story_id": draft["id"]}))
    assert got == [(own.slug, mine.slug)]


def test_4_f3_on_a_draft_that_was_never_sent_says_so_and_opens_nothing(home, monkeypatch):
    modes.TRAIL.clear()
    thorn, legacy, draft, plan = _draft_promoted_into_its_own_universe(home)
    calls = _record_writer(monkeypatch)

    async def script(app, pilot):
        await pilot.press("f3")
        await pilot.pause()
        await pilot.pause()
        return calls[:], " ".join(screen_text(app).split()), app.mode_name
    got, text, mode = _hub_run(script, ("wheel", {"story_id": draft["id"]}))
    assert got == [] and mode == "wheel" and "This draft has no manuscript yet" in text


@pytest.mark.skipif(not hasattr(os, "fork"), reason="needs a pseudo-terminal")
def test_4_real_terminal_the_writer_shows_the_title_in_the_status_line(home, term_story):
    t = Term(term_story)
    try:
        status = [l for l in t.lines() if "in this scene" in l]
        assert status and "The Last Clause" in status[0]
        title = t.screen.title if hasattr(t.screen, "title") else ""
        assert "The Last Clause" in title            # the terminal window title too
    finally:
        t.close()


def test_4_the_status_line_shows_the_whole_title_when_it_fits_and_shortens_only_in_a_narrow_window(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause of the Dry Years")           # 32 characters: over the old fixed limit of 30
    s.add_scene("Opening", "The gate was shut.")
    r = drive(s, [keys("<Cmd>set columns=140<CR>")], "R.wide = require('sw.stats').line()")
    assert "The Last Clause of the Dry Years (short story)  ·  words:" in r["wide"]
    r = drive(s, [keys("<Cmd>set columns=70<CR>")], "R.narrow = require('sw.stats').line()")
    assert "…  ·  words:" in r["narrow"].replace(" (short story)", "") and "The Last Clause of the Dry Years" not in r["narrow"]


# --- 5. no paragraph indent in the Writer's floats ----------------------------------------------------------------------

FLOAT_MARKS = """
R.floats = {}
R.main_marks = 0
for _, w in ipairs(vim.api.nvim_list_wins()) do
  local b = vim.api.nvim_win_get_buf(w)
  local n = #vim.api.nvim_buf_get_extmarks(b, require('sw.prose').ns, 0, -1, {})
  if w == require('sw.layout').main then R.main_marks = n
  elseif vim.api.nvim_win_get_config(w).relative ~= '' then R.floats[#R.floats + 1] = { n = n, lines = #vim.api.nvim_buf_get_lines(b, 0, -1, false) } end
end
"""


@pytest.mark.parametrize("key", ["<F3>", "<C-o>", "<F12>", "<C-r>", "<F8>"])
def test_5_floats_get_no_paragraph_indent(home, two, key):
    steps = [keys(key), keys("<Cmd>lua vim.wait(250)<CR>")]
    r = drive(two, steps, FLOAT_MARKS)
    if key != "<F8>":                                    # (peek needs a name under the cursor)
        assert r["floats"], r
    assert all(f["n"] == 0 for f in r["floats"]), r
    assert r["main_marks"] > 0                           # while the manuscript still has its indent


def test_5_the_help_float_has_no_indent_even_after_it_is_changed(home, two):
    steps = [keys("<F3>"), keys("<Tab>"), keys("2"), keys("<Cmd>lua vim.wait(250)<CR>")]
    r = drive(two, steps, FLOAT_MARKS)
    assert r["floats"] and all(f["n"] == 0 for f in r["floats"]), r


# --- 6. the outline overlay and older Story Spine outlines (labels stored with the sentence) ----------------------------------

def test_6_ctrl_o_does_not_repeat_the_story_spine_openers(home):
    u = vault.create_universe("Thornwood", ["western"])
    legacy = ("**Once upon a time.** Once upon a time, Ann lived in Redwater.\n\n**Every day.** Every day, Ann swept the porch.\n\n"
              "**One day.** One day, a stranger came.")
    s = u.new_story("The Last Clause", {"genre": "western", "mood": "cozy", "structure": "Story Spine"}, {"Story Spine": legacy})
    s.add_scene("Opening", "Hello")
    r = drive(s, [keys("<C-o>")], "local ov = require('sw.overview'); R.lines = vim.api.nvim_buf_get_lines(ov.buf, 0, -1, false)")
    text = "\n".join(r["lines"])
    assert "1. Once upon a time, Ann lived in Redwater." in text
    assert "2. Every day, Ann swept the porch." in text and "3. One day, a stranger came." in text
    assert "Once upon a time. Once" not in text and "Every day. Every" not in text and "**" not in text


def test_6_a_label_that_is_not_in_the_sentence_is_kept(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("Act Story", {"genre": "western", "structure": "Three-Act Outline"},
                    {"Three-Act Outline": "**Act One.** Ann lived in Redwater.\n\n**Act Two.** She ran."})
    s.add_scene("Opening", "Hello")
    r = drive(s, [keys("<C-o>")], "local ov = require('sw.overview'); R.lines = vim.api.nvim_buf_get_lines(ov.buf, 0, -1, false)")
    text = "\n".join(r["lines"])
    assert "1. Act One. Ann lived in Redwater." in text and "2. Act Two. She ran." in text


# --- 7. the help's tab bar and the outline overlay ----------------------------------------------------------------------------

LONG_SPINE = ("Once upon a time, Ann lived in Redwater, a town that had never once been in a hurry to be anywhere, and had never been "
              "asked to be, either, by anyone who mattered to the people who lived there.\n\n"
              "Every day, Ann swept the porch of the land office before anyone arrived, and every day somebody left a muddy print on it.\n\n"
              "One day, a stranger came with a locked box and a story nobody in the town believed for a moment.")


@pytest.fixture
def long_story(home):
    u = vault.create_universe("Thornwood", ["western"])
    u.new_entity("character", "Ann Lowell", {"role": "protagonist", "job": "teacher", "want": "the deed", "need": "to trust",
                                             "secret": "she forged her own father's signature on the deed in the year of the drought"})
    s = u.new_story("The Last Clause", {"genre": "western", "mood": "cozy", "structure": "Story Spine"},
                    {"Premise": "When a stranger brings a locked box to Redwater, Ann must open it before the posse arrives, and before anyone learns "
                                "what her father put inside it.",
                     "Setting": "- **Place:** Redwater\n- **Era:** the 1880s\n- **Rumor:** a pistol lies buried at the livery",
                     "Story Spine": LONG_SPINE, "Twist": "The stranger was Ann's brother."})
    s.add_scene("Opening", "Hello")
    settings.save_story(s.path, {"spellcheck": False})
    return s


@pty_only
def test_7_real_terminal_the_help_tab_bar_fits_and_the_hints_are_on_the_border(home, long_story):
    t = Term(long_story, rows=36, cols=120)
    try:
        t.key("F3")
        text = t.text()
        bar = next(l for l in t.lines() if "Writing prose" in l or "Writing basics" in l)
        assert "Writing prose" in bar and "Writing basics" in bar and "Keys" in bar and "Export" in bar     # every tab name, the open one included
        assert "Tab / Shift+Tab" in text and "F3, Esc, q close" in text
        assert "-----" not in text                                          # headings are coloured, not underlined with dashes
        assert "<se" not in text
    finally:
        t.close()


@pty_only
def test_7_real_terminal_a_narrow_help_keeps_the_open_tabs_name(home, long_story):
    t = Term(long_story, rows=30, cols=70)
    try:
        t.key("F3")
        bar = next(l for l in t.lines() if " 1 " in l and "2" in l)
        assert "1" in bar and ("Writing prose" in bar or "Writing p…" in bar or "Writing" in bar)
        assert "2" in bar and "3" in bar and "4" in bar
    finally:
        t.close()


@pty_only
def test_7_real_terminal_the_outline_fits_and_wrapped_beats_hang_under_their_text(home, long_story):
    t = Term(long_story, rows=44, cols=100)
    try:
        t.key("Ctrl+O")
        lines = t.lines()
        r1 = next(i for i, l in enumerate(lines) if "1. Once upon a time" in l)
        first, nxt = lines[r1], lines[r1 + 1]
        inner = nxt[nxt.index("│") + 1:] if "│" in nxt else nxt
        left = inner[:len(inner) - len(inner.lstrip())]
        assert len(left) >= 3, nxt                                           # hangs under its text, not back at the left edge
        assert "A pistol lies buried at the livery" in t.text()              # the last section is on screen without scrolling
        assert "Rumor" in t.text()
    finally:
        t.close()


# --- 8. deleting a Wheel draft goes to the trash, and the quit box asks first -------------------------------------------------

from conftest import make_engine, run_tui  # noqa: E402
from storywheel.sample import build_story  # noqa: E402


def _two_drafts(home):
    mine = build_story(make_engine(home), ["western"])
    other = build_story(make_engine(home, seed=9), ["western"])
    mine["id"], other["id"] = "20260101-000001-mine", "20260101-000002-other"           # (ids are made from the clock: two in one second would clash)
    store.save(mine)
    store.save(other)
    return mine, other


def test_8_deleting_a_past_story_moves_it_to_the_trash_and_says_where(home):
    mine, other = _two_drafts(home)

    async def script(app, pilot):
        lst = app.main.query_one("#stories")
        lst.focus()
        await pilot.pause()
        row = next(i for i in range(lst.option_count) if lst.get_option_at_index(i).id == other["id"] or other["id"] in str(lst.get_option_at_index(i).id))
        lst.highlighted = row
        await pilot.press("d")
        await pilot.pause()
        asked = " ".join(screen_text(app).split())
        await pilot.press("y")
        await pilot.pause()
        return asked, " ".join(screen_text(app).split())
    asked, after = run_tui(store.load(mine["id"]), make_engine(home), script)
    trash = home / "home" / ".trash"
    assert "Delete the story" in asked and "This can't be undone" not in asked and ".trash" in asked
    assert not (home / "home" / "stories" / f"{other['id']}.json").exists() and (trash / f"{other['id']}.json").exists()
    assert "Deleted" in after and ".trash" in after
    assert (home / "home" / "stories" / f"{mine['id']}.json").exists()


def test_8_the_quit_boxs_delete_asks_first_and_no_keeps_the_story(home):
    mine, _other = _two_drafts(home)

    async def script(app, pilot):
        await pilot.press("Q")
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        screen = type(app.screen).__name__
        asked = " ".join(screen_text(app).split())
        still_there = (home / "home" / "stories" / f"{mine['id']}.json").exists()
        await pilot.press("n")
        await pilot.pause()
        back = type(app.screen).__name__
        return screen, asked, still_there, (home / "home" / "stories" / f"{mine['id']}.json").exists(), back
    screen, asked, there1, there2, back = run_tui(store.load(mine["id"]), make_engine(home), script)
    assert screen == "ConfirmScreen" and ".trash" in asked and there1 and there2 and back == "QuitScreen"


def test_8_confirming_the_quit_boxs_delete_moves_the_draft_to_the_trash(home):
    mine, _other = _two_drafts(home)

    async def script(app, pilot):
        await pilot.press("Q")
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        return app.return_value
    message = run_tui(store.load(mine["id"]), make_engine(home), script)
    trash = home / "home" / ".trash"
    assert not (home / "home" / "stories" / f"{mine['id']}.json").exists() and (trash / f"{mine['id']}.json").exists()
    assert message and "Deleted" in message and ".trash" in message


# --- 9. the status line counts the writing window, not the float you are in ----------------------------------------------------

import re  # noqa: E402


def _scene_words(t):
    row = next(l for l in t.lines() if "in this scene" in l)
    return int(re.search(r"in this scene (\d+)", row).group(1))


@pty_only
def test_9_real_terminal_floats_do_not_change_the_words_in_this_scene(home, term_story):
    t = Term(term_story)
    try:
        base = _scene_words(t)
        assert base == 4                                              # "The gate was shut."
        for open_key, close_key in (("F3", "F3"), ("Ctrl+O", "Esc"), ("Ctrl+R", "Esc"), ("F12", "Esc")):
            t.key(open_key, wait=0.8)
            assert _scene_words(t) == base, open_key
            t.key(close_key, wait=0.5)
        t.send("x y z ")                                            # and it still counts what you type
        assert _scene_words(t) == base + 3
    finally:
        t.close()


def test_9_the_count_is_the_writing_windows_even_when_a_float_is_current(home, two):
    r = drive(two, [keys("<F3>"), keys("<Cmd>lua vim.wait(300)<CR>")],
              "R.line = require('sw.stats').line(); R.float_current = vim.api.nvim_win_get_config(0).relative ~= ''")
    assert r["float_current"] is True and "in this scene 4 " in r["line"]


# --- 10. Alt with a letter that does nothing types nothing -----------------------------------------------------------------------

def test_10_alt_f_in_a_prose_story_types_nothing_and_says_why(home, two):
    r = drive(two, [keys("<A-f>")], LINES + "; R.msg = vim.fn.execute('messages'); R.mode = vim.fn.mode()")
    assert r["mode"] == "i" and r["lines"] == ["* * * Opening", "", "The gate was shut.", "", "* * * The hall", "", "The guild hall was dark. Priya went in anyway."]
    assert "The flip test is for screenplays." in r["msg"]


def test_10_other_unmapped_alt_letters_type_nothing(home, two):
    # (not a, which is... free; q quits and has its own test; these have no job)
    unused = "".join(f"<A-{c}>" for c in "dhkoprxzDFGHJ")
    r = drive(two, [keys(unused)], LINES)
    assert r["lines"][0] == "* * * Opening" and r["lines"][2] == "The gate was shut."


def test_10_alt_letters_that_have_a_job_still_work(home, two):
    # Alt+I italic: typing around it wraps in marks; Alt+M opens the menu; Alt+N asks for a scene title (cancelled)
    r = drive(two, [keys("<C-Home><A-i>word<A-i>")], LINES)
    assert r["lines"][0].startswith("*word*")
    r = drive(two, [keys("<A-m>")], "R.menu = require('sw.menu').last ~= nil and vim.api.nvim_win_is_valid(require('sw.menu').last.win)")
    assert r["menu"] is True


def test_10_a_screenplay_still_flips(home):
    u = vault.create_universe("Films", ["western"])
    s = u.new_story("Short", {"format": "screenplay"})
    settings.save_story(s.path, {"format": "screenplay", "script_kind": "short-film", "spellcheck": False})
    (s.manuscript_dir).mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "script.fountain").write_text("INT. KITCHEN - DAY\n\nAnn pours coffee.\n")
    r = drive(s, [keys("<A-f>"), keys("<Cmd>lua vim.wait(300)<CR>")], "R.msg = vim.fn.execute('messages'); R.lines = vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(require('sw.layout').main), 0, -1, false)")
    assert "The flip test is for screenplays" not in r["msg"] and r["lines"][0] == "INT. KITCHEN - DAY"       # (it ran the flip test; no stray f typed)


# --- 11. the cursor stays off scene-marker lines -------------------------------------------------------------------------------

@pytest.fixture
def marked(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    (s.manuscript_dir).mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "manuscript.md").write_text("* * * Opening\n\nThe gate was shut.\n\n* * * The Hall\n\nThe guild hall was dark.\n")
    settings.save_story(s.path, {"spellcheck": False})
    return s


CURSOR = "R.row = vim.api.nvim_win_get_cursor(0)[1]; R.mode = vim.fn.mode()"


def _saved_text(story):
    return story.manuscript_path.read_text() if hasattr(story, "manuscript_path") else (story.manuscript_dir / "manuscript.md").read_text()


def _leave_and_read(t, story):
    t.key("F2", wait=2.0)
    return (story.manuscript_dir / "manuscript.md").read_text()


@pty_only
def test_11_real_terminal_arrowing_down_onto_a_marker_moves_on_and_typing_leaves_it_alone(home, marked):
    t = Term(marked)
    try:
        t.key("Ctrl+Home")
        for _ in range(3):
            t.key("Down", wait=0.25)                       # row 2 (blank), 3, 4 (blank); the next Down would land on the marker at row 5
        t.key("Down", wait=0.25)
        t.send("xyz")
        text = _leave_and_read(t, marked)
    finally:
        t.close()
    lines = text.splitlines()
    assert "* * * The Hall" in lines and "* * * Opening" in lines
    assert "xyz" in text and not any("xyz" in l and "* *" in l for l in lines)


@pty_only
def test_11_real_terminal_arrowing_up_onto_a_marker_moves_off_it(home, marked):
    t = Term(marked)
    try:
        t.key("Ctrl+Home")
        for _ in range(6):
            t.key("Down", wait=0.2)
        for _ in range(3):
            t.key("Up", wait=0.25)
        t.send("abc")
        text = _leave_and_read(t, marked)
    finally:
        t.close()
    lines = text.splitlines()
    assert "* * * The Hall" in lines and "* * * Opening" in lines and not any("abc" in l and "* *" in l for l in lines)


@pty_only
def test_11_real_terminal_a_click_on_a_marker_line_moves_off_it(home, marked):
    t = Term(marked)
    try:
        row, col = t.find("The Hall")
        t.click("left", row, col + 2)
        t.send("zz")
        text = _leave_and_read(t, marked)
    finally:
        t.close()
    assert "* * * The Hall" in text.splitlines() and not any("zz" in l and "* *" in l for l in text.splitlines())


def test_11_typing_a_scene_break_still_works(home, marked):
    r = drive(marked, [keys("<C-End>"), keys("<CR>***<CR>Next scene")], LINES)
    assert "***" in r["lines"] and r["lines"][-1].endswith("Next scene")


@pty_only
def test_11_real_terminal_a_marker_at_the_very_end_gets_an_empty_line_to_type_on(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    (s.manuscript_dir).mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "manuscript.md").write_text("The gate was shut.\n\n* * * The End")
    settings.save_story(s.path, {"spellcheck": False})
    t = Term(s)
    try:
        t.key("Ctrl+Home")
        for _ in range(3):
            t.key("Down", wait=0.25)
        t.send("ok")
        text = _leave_and_read(t, s)
    finally:
        t.close()
    lines = text.splitlines()
    assert "* * * The End" in lines and any(l.endswith("ok") for l in lines) and not any("ok" in l and "* *" in l for l in lines)


# --- 12. peek (F8): the schema's field order, nothing cut off, and F8 again to scroll ------------------------------------------

@pytest.fixture
def peek_story(home):
    u = vault.create_universe("Thornwood", ["western"])
    u.new_entity("character", "Ann Lowell", {
        "role": "protagonist", "age": "52", "job": "teacher", "trait": "stubborn", "want": "the deed to the schoolhouse",
        "need": "to trust her neighbours", "flaw": "pride",
        "secret": "she forged her own father's signature on the deed in the year of the drought, and has kept the pen ever since in a drawer "
                  "under the stove where nobody would ever think to look for it",
        "rival": "the sheriff"})
    s = u.new_story("The Last Clause")
    s.add_scene("Opening", "Ann Lowell")
    settings.save_story(s.path, {"spellcheck": False})
    return s


def _field_rows(t):
    lines = t.lines()
    out = {}
    for label in ("Role", "Age", "Job", "Trait", "Want", "Need", "Flaw", "Secret", "Rival"):
        for i, l in enumerate(lines):
            if f"{label}:" in l and "Ann Lowell" not in l:
                out[label] = i
                break
    return out


def test_12_entity_list_json_carries_the_schema_order(home, peek_story):
    import json
    import subprocess
    import sys
    out = subprocess.run([sys.executable, "-m", "storywheel", "entity", "list", "thornwood", "--json"], capture_output=True, text=True,
                         env={**os.environ, "PYTHONPATH": str(ROOT)}).stdout
    ann = json.loads(out)[0]
    assert ann["order"][:5] == ["name", "role", "age", "job", "trait"]


@pty_only
def test_12_real_terminal_peek_lists_fields_in_the_schema_order_and_shows_want(home, peek_story):
    t = Term(peek_story, rows=40, cols=100)
    try:
        t.key("Ctrl+Home")
        t.key("Down", wait=0.3)
        t.key("Down", wait=0.3)
        t.key("Right", wait=0.3)
        t.key("F8", wait=0.8)
        rows = _field_rows(t)
        assert list(rows) == ["Role", "Age", "Job", "Trait", "Want", "Need", "Flaw", "Secret", "Rival"], rows       # all there, none cut off
        assert list(rows.values()) == sorted(rows.values())                                                          # in the schema's order
    finally:
        t.close()


@pty_only
def test_12_real_terminal_a_card_taller_than_the_window_scrolls_after_a_second_f8(home, peek_story):
    t = Term(peek_story, rows=16, cols=60)
    try:
        t.key("Ctrl+Home")
        t.key("Down", wait=0.3)
        t.key("Down", wait=0.3)
        t.key("Right", wait=0.3)
        t.key("F8", wait=0.8)
        assert "Role:" in t.text() and "Rival:" not in t.text()          # too tall for the window: the end is cut off...
        t.key("F8", wait=0.6)                                              # ...so F8 again takes the focus
        for _ in range(12):
            t.key("Down", wait=0.15)
        assert "Rival:" in t.text()                                        # and scrolling reaches it
        t.key("Esc", wait=0.5)
        assert "Rival:" not in t.text()
        t.send("x")
        line = next(l for l in t.lines() if "Lowell" in l)
        assert "x" in line and len(line.strip()) == len("Ann Lowell") + 1                                # typing goes on: x was typed, not a delete
    finally:
        t.close()


@pty_only
@pytest.mark.parametrize("reply", [
    b"\x1bP1+r4D73=" + b"\x1b]52;%p1%s;%p2%s\x07".hex().upper().encode() + b"\x1b\\",                  # XTGETTCAP "Ms" (the clipboard query), answered
    b"\x1bP0+r4D73\x1b\\",                                           # ...and refused
    b"\x1b[?62;22c", b"\x1b]11;rgb:0000/0000/0000\x07", b"\x1b[?2026;2$y", b"\x1b[?1;2R",     # DA1, background colour, DECRPM, cursor report
])
def test_12b_real_terminal_a_late_terminal_reply_is_never_typed_into_the_text(home, term_story, reply):
    """The terminal may answer Neovim's start-up questions late, while the Writer sits in insert mode (found on Neovim 0.11)."""
    t = Term(term_story)
    try:
        t.send("abc ")
        t.send(reply, wait=0.8)                                        # a reply arriving long after Neovim started
        t.send("def")
        t.key("Esc", wait=0.5)
        t.send(reply, wait=0.8)
        t.send("!")
        text = t.text()
        assert "abc def!" in text, [l for l in t.lines() if "abc" in l or "+r" in l or "52" in l]
    finally:
        t.close()


# --- 13. Past stories: the protagonist and setting buttons say they go to a universe -------------------------------------------------

def test_13_the_past_stories_buttons_offer_the_piece_to_this_draft_or_to_a_universe(home):
    """(Polish 2 made "Use protagonist" a real use of the piece in this draft; sending it to a universe is the second choice.)"""
    mine, other = _two_drafts(home)
    thorn = vault.create_universe("Thornwood", ["western"])

    async def script(app, pilot):
        s = app.main
        labels = [str(s.query_one("#st-protagonist").label), str(s.query_one("#st-setting").label)]
        lst = s.stories_list
        lst.focus()
        await pilot.pause()
        lst.highlighted = [lst.get_option_at_index(i).id for i in range(lst.option_count)].index(other["id"])
        await pilot.click("#st-protagonist")
        await pilot.pause()
        offered = [str(o.prompt) for o in app.screen.query_one("#choices").options] if type(app.screen).__name__ == "ChoiceScreen" else []
        await pilot.press("down", "enter")                                   # the second choice: send it to a universe
        await pilot.pause()
        asked = app.screen.title_text if type(app.screen).__name__ == "ChoiceScreen" else "(no choice box)"
        await pilot.press("enter")
        await pilot.pause()
        return labels, offered, asked
    labels, offered, asked = run_tui(store.load(mine["id"]), make_engine(home), script)
    assert labels == ["Use protagonist", "Use setting"]
    assert len(offered) == 2 and offered[0].startswith("Use it in this draft") and offered[1].startswith("Send it to a universe")
    assert "to which universe" in asked
    assert vault.get_universe("thornwood").find_by_name(other["kept"]["protagonist"]["name"], "character")


def test_13_the_wheel_help_says_use_in_this_draft_or_send_to_a_universe(home):
    from storywheel import helpdoc
    text = " ".join(helpdoc.text("wheel", 120).split())
    assert "Use its protagonist in the current story" not in text and "to the current story" not in text
    assert "Use its protagonist in the draft you are on" in text and "send it to a universe you choose" in text


# --- 14. Words: a and k work on the word you are on, on every tab ------------------------------------------------------------------

from test_words import index, fit, world, run as words_run, open_genre, select_word, type_word, show_tab  # noqa: E402,F401
from storywheel import learn  # noqa: E402
from textual.widgets import TabbedContent  # noqa: E402,F401
from storywheel.virtuallist import VirtualList  # noqa: E402


def test_14_k_in_lookup_marks_the_word_you_are_on_known(index, world):
    u, s = world

    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        select_word(app, "w:puppy|")
        await pilot.press("k")
        await pilot.pause()
        return flat_text(app), learn.MyWords().known
    text, known = words_run(script, {"universe": "thornwood", "story": s.slug})
    assert "puppy" in known and "Known" in text


def flat_text(app):
    return " ".join(screen_text(app).split())


def test_14_a_in_genre_words_learns_the_genre_word_not_the_one_left_in_lookup(index, fit, world):
    u, s = world

    async def script(app, pilot):
        await type_word(app, pilot, "dog")                        # a word is left highlighted in the (now hidden) Lookup tab
        select_word(app, "w:puppy|")
        await open_genre(app, pilot)
        v = app.screen.query_one("#gwvlist", VirtualList)
        v.focus()
        await pilot.pause()
        word = v.current()["word"]
        await pilot.press("a")
        await pilot.pause()
        return word, learn.MyWords().learning_words(), flat_text(app)
    word, learning, text = words_run(script, {"universe": "thornwood", "story": s.slug})
    assert word in learning and "puppy" not in learning                          # (the word you are on, not the one left in Lookup)
    assert f"“{word}” is ★ Learning" in text


def test_14_k_in_genre_words_marks_that_word_known(index, fit, world):
    u, s = world

    async def script(app, pilot):
        await open_genre(app, pilot)
        v = app.screen.query_one("#gwvlist", VirtualList)
        v.focus()
        await pilot.pause()
        word = v.current()["word"]
        await pilot.press("k")
        await pilot.pause()
        return word, learn.MyWords().known, flat_text(app)
    word, known, text = words_run(script, {"universe": "thornwood", "story": s.slug})
    assert word.lower() in known and "Known" in text


def test_14_a_and_l_agree_in_lookup(index, world):
    u, s = world

    async def script(app, pilot):
        out = []
        for key, word in (("a", "puppy"), ("l", "tail")):
            await type_word(app, pilot, "dog")
            select_word(app, f"w:{word}|")
            await pilot.press(key)
            await pilot.pause()
        return learn.MyWords().learning_words()
    got = words_run(script, {"universe": "thornwood", "story": s.slug})
    assert "puppy" in got and "tail" in got


# --- 15. Builder: Write, Export and Copy never quietly take the first story -----------------------------------------------------

def _two_stories(home):
    u = vault.create_universe("Thornwood", ["western"])
    a = u.new_story("Alpha Story")
    a.add_scene("Opening", "Alpha words here.")
    b = u.new_story("Beta Story")
    b.add_scene("Opening", "Beta words are different.")
    return u, a, b


def _overview_run(script):
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="thornwood", story=None)
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            s = app.screen_ref
            await pilot.press("o")                                     # the universe overview: no story is open
            await pilot.pause()
            assert s.story is None
            return await script(app, pilot)
    return asyncio.run(go())


def test_15_c_with_no_story_open_asks_which_and_copies_that_one(home, monkeypatch):
    from storywheel import clipboard
    copied = []
    monkeypatch.setattr(clipboard, "copy", lambda text, app=None: copied.append(text) or "test clipboard")
    _two_stories(home)

    async def script(app, pilot):
        await pilot.press("C")
        await pilot.pause()
        asked = type(app.screen).__name__, app.screen.title_text if hasattr(app.screen, "title_text") else ""
        assert copied == []                                             # nothing was copied yet
        await pilot.press("down", "enter")                              # the second story
        await pilot.pause()
        return asked
    asked = _overview_run(script)
    assert asked[0] == "ChoiceScreen" and "Which story" in asked[1]
    assert len(copied) == 1 and "Beta words" in copied[0] and "Alpha words" not in copied[0]


def test_15_escape_on_the_question_does_nothing(home, monkeypatch):
    from storywheel import clipboard
    copied = []
    monkeypatch.setattr(clipboard, "copy", lambda text, app=None: copied.append(text) or "x")
    _two_stories(home)

    async def script(app, pilot):
        await pilot.press("C")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        return type(app.screen).__name__, app.screen_ref.story
    screen, story = _overview_run(script)
    assert copied == [] and story is None and screen != "ChoiceScreen"


def test_15_x_with_no_story_open_asks_which_before_offering_formats(home):
    _two_stories(home)

    async def script(app, pilot):
        await pilot.press("x")
        await pilot.pause()
        first = app.screen.title_text
        await pilot.press("enter")                                      # the first story
        await pilot.pause()
        second = app.screen.title_text if hasattr(app.screen, "title_text") else ""
        return first, second, app.screen_ref.story.title
    first, second, title = _overview_run(script)
    assert "Which story" in first and "Export 'Alpha Story' as" in second and title == "Alpha Story"


def test_15_w_with_no_story_open_asks_which_and_writes_that_one(home, monkeypatch):
    _two_stories(home)
    calls = []
    monkeypatch.setattr(writer, "check", lambda: None)
    monkeypatch.setattr(builder.BuilderHooks, "run_writer", lambda self, screen, story, scene, note: calls.append(story.slug))

    async def script(app, pilot):
        await pilot.press("w")
        await pilot.pause()
        assert calls == [] and type(app.screen).__name__ == "ChoiceScreen"
        await pilot.press("down", "enter")
        await pilot.pause()
    _overview_run(script)
    assert calls == ["beta-story"]


def test_15_with_no_stories_at_all_it_says_so(home):
    vault.create_universe("Empty", ["western"])

    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="empty", story=None)
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            await pilot.press("C")
            await pilot.pause()
            return type(app.screen).__name__, " ".join(screen_text(app).split())
    screen, text = asyncio.run(go())
    assert screen != "ChoiceScreen" and "Open a story first" in text


def test_15_with_a_story_open_nothing_is_asked(home, monkeypatch):
    from storywheel import clipboard
    copied = []
    monkeypatch.setattr(clipboard, "copy", lambda text, app=None: copied.append(text) or "x")
    _two_stories(home)

    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="thornwood", story="alpha-story")
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            await pilot.press("C")
            await pilot.pause()
            return type(app.screen).__name__
    assert asyncio.run(go()) != "ChoiceScreen" and "Alpha words" in copied[0]
