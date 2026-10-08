"""Every item of the right-click menu and of the Writer menu, run the way a user runs them (the menu opens, an item is
chosen), must finish without an error message. Errors show up in v:errmsg and :messages."""
import json
import re

import pytest

from storywheel import writer
from test_notepad import run, story, ROOT  # noqa: F401  (the fixtures and the headless driver)

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")

RECORD = """
vim.api.nvim_create_autocmd("VimLeavePre", { callback = function()
  local f = io.open(%r, "w")
  f:write(vim.json.encode({ errmsg = vim.v.errmsg, messages = vim.fn.execute("messages"), R = R or {} }))
  f:close()
end })
"""


def problems(story, setup, typed, check=""):
    out = story.path.parent / "errs.json"
    out.unlink(missing_ok=True)
    run(story, RECORD % str(out) + setup, typed, check, quits=True)
    data = json.loads(out.read_text())
    bad = [l for l in data["messages"].splitlines() if re.match(r"(E\d+:|Error)", l) or "E5108" in l or "stack traceback" in l or "Error " in l]
    problems.last = data
    return data["errmsg"], bad


POPUP_ITEMS = ["Undo", "Redo", "Cut", "Copy", "Paste", "Add to Dictionary", "Look Up", "More…"]


def test_the_right_click_menu_opens_without_errors(home, story):
    """Opening is what Neovim's own MenuPopup handler reacts to (it once raised E329: No menu 'Go to definition')."""
    errmsg, bad = problems(story, "", "", "require('sw.context').open({4, 4}); require('sw.context').open({4, 4})")
    assert errmsg == "" and bad == []


def test_neovims_own_popup_menu_is_gone(home, story):
    from test_notepad import run as r
    out = r(story, "", "", "local ok, m = pcall(vim.fn.menu_get, 'PopUp'); R.n = ok and #m or 0; R.mm = vim.o.mousemodel")
    assert out["mm"] == "extend" and out["n"] == 0


def choose(name):
    """What a right-click does: our menu opens and the chosen item runs by Down and Enter (typed, as input, so prompts can be answered)."""
    from nvdrive import context_keys
    return context_keys(name)


@pytest.mark.parametrize("name", POPUP_ITEMS)
def test_every_right_click_item_runs_without_errors(home, story, name):
    errmsg, bad = problems(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello brave world' })\nvim.api.nvim_win_set_cursor(0, { 1, 6 })",
                           choose(name), "vim.wait(100)")
    assert errmsg == "" and bad == [], name


@pytest.mark.parametrize("name", POPUP_ITEMS)
def test_every_right_click_item_runs_with_a_selection(home, story, name):
    errmsg, bad = problems(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello brave world' })",
                           "<S-Right><S-Right><S-Right>" + choose(name), "vim.wait(100)")
    assert errmsg == "" and bad == [], name


def writer_menu_labels(story):
    return run(story, "", "", "R.labels = {}; for i, it in ipairs(require('sw.menu').items()) do R.labels[i] = it[1] end")["labels"]


def test_every_writer_menu_item_runs_by_number_and_by_enter(home, story):
    labels = writer_menu_labels(story)
    assert len(labels) >= 15
    failures = []
    for i, label in enumerate(labels):
        for how in ("number", "enter"):
            if how == "number" and i >= 9:
                continue
            typed = f"<F12>{i + 1}" if how == "number" else "<F12>" + "<Down>" * i + "<CR>"
            errmsg, bad = problems(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello brave world' })", typed, "vim.wait(100)")
            if errmsg or bad:
                failures.append((label, how, errmsg, bad))
    assert failures == [], "\n".join(map(str, failures))


def test_every_writer_menu_item_runs_by_mouse_click(home, story):
    labels = writer_menu_labels(story)
    failures = []
    for i, label in enumerate(labels):
        errmsg, bad = problems(story, "", "<F12>", f"""
            local m = require('sw.menu').last
            local pos = vim.api.nvim_win_get_position(m.win)
            vim.api.nvim_input_mouse('left', 'press', '', 0, pos[1] + {i} + 1, pos[2] + 3)
            vim.api.nvim_input_mouse('left', 'release', '', 0, pos[1] + {i} + 1, pos[2] + 3)
            vim.wait(200)""")
        if errmsg or bad:
            failures.append((label, errmsg, bad))
    assert failures == []



def test_help_from_the_menu_closes_with_q_and_you_are_typing_again(home, story):
    labels = writer_menu_labels(story)
    downs = labels.index("Help")
    r = run(story, "", "<F12>" + "<Down>" * downs + "<CR>q", "R.mode = vim.fn.mode(); R.win_is_main = vim.api.nvim_get_current_win() == require('sw.layout').main")
    assert r["win_is_main"] is True and r["mode"] == "i"


# --- batch 11: a right-click menu that fits -------------------------------------------------------------------------------------------

def popup_rows(story, setup="", lines=40):
    """The names in the right-click menu as it opens (MenuPopup fires first, as for a real click)."""
    r = run(story, setup, "", """
        R.items = {}
        for _, it in ipairs(require('sw.context').items(require('sw.spell').bad_word())) do R.items[#R.items + 1] = it[1] end
    """, lines=lines)
    return r["items"]


def test_the_right_click_menu_is_only_the_everyday_items(home, story):
    items = popup_rows(story)
    assert items == ["Undo", "Redo", "-", "Cut", "Copy", "Paste", "-", "Look Up", "Add to Dictionary", "-", "More…"]
    assert len(items) <= 11                                              # (the old menu had 21 rows)


def test_fix_spelling_is_there_only_on_a_misspelled_word(home, story):
    plain = popup_rows(story)
    marked = popup_rows(story, "require('sw.spell').bad_word = function() return 'wrold' end")
    assert "Fix Spelling…" not in plain and "Fix Spelling…" in marked
    assert marked.index("Fix Spelling…") < marked.index("Look Up")
    assert [i for i in marked if i != "Fix Spelling…"] == plain


def test_fix_spelling_offers_suggestions_and_replaces_the_word(home, story):
    r = run(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello brave wrold' })
        vim.api.nvim_win_set_cursor(0, { 1, 14 })
        require('sw.spell').bad_word = function() return 'wrold' end
        vim.fn.spellsuggest = function() return { 'world', 'wild' } end
    """, "<Cmd>lua require('sw.spell').suggest()<CR>2", "R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false); R.mode = vim.fn.mode()")
    assert r["lines"][0] == "Hello brave wild" and r["mode"] == "i"


def test_more_opens_the_full_writer_menu(home, story):
    errmsg, bad = problems(story, "", choose("More…"), "vim.wait(100)")
    assert errmsg == "" and bad == []
    r = run(story, "", choose("More…"), "R.float = vim.api.nvim_win_get_config(0).relative; R.first = vim.api.nvim_buf_get_lines(0, 0, 2, false)[1]")
    assert r["float"] == "editor" and "Edit" in r["first"]


@pytest.mark.parametrize("lines", [12, 16, 24])
def test_the_full_menu_fits_a_short_window_and_scrolls_to_every_item(home, story, lines):
    """Tall lines in kitty (180% line height) leave few rows: the menu must fit the window and still reach its last item."""
    r = run(story, "", "<F12>", """
        local m = require('sw.menu').last
        local cfg = vim.api.nvim_win_get_config(m.win)
        R.top, R.height, R.lines = cfg.row, cfg.height, vim.o.lines
        R.total = vim.api.nvim_buf_line_count(m.buf)
        vim.api.nvim_set_current_win(m.win)
        vim.api.nvim_win_set_cursor(m.win, { R.total, 0 })
        vim.cmd('redraw')
        R.last_visible = vim.fn.line('w$', m.win) == R.total
        R.cursor = vim.api.nvim_win_get_cursor(m.win)[1]
    """, lines=lines)
    assert r["top"] + r["height"] + 2 <= r["lines"], r                      # (inside the window, borders included)
    assert r["last_visible"] and r["cursor"] == r["total"]
    assert r["height"] <= r["total"]
