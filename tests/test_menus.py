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


POPUP_ITEMS = ["Cut", "Copy", "Paste", "Select All", "Italic", "Bold", "Scene Break", "Find", "Look Up", "Join Lines", "Writer Menu"]


def test_the_right_click_menu_opens_without_errors(home, story):
    """Opening is what Neovim's own MenuPopup handler reacts to (it once raised E329: No menu 'Go to definition')."""
    errmsg, bad = problems(story, "", "", "vim.cmd('doautocmd <nomodeline> MenuPopup'); vim.cmd('doautocmd <nomodeline> MenuPopup')")
    assert errmsg == "" and bad == []


def test_no_default_popup_handler_is_left_to_fight_our_menu(home, story):
    from test_notepad import run as r
    out = r(story, "", "", "R.groups = vim.api.nvim_get_autocmds({ event = 'MenuPopup' }); R.n = #R.groups")
    assert out["n"] == 0, out["groups"]


def choose(name):
    """What a right-click does in Neovim: MenuPopup fires, then the chosen item runs (typed, as input, so prompts can be answered)."""
    return "<Cmd>doautocmd <nomodeline> MenuPopup<CR><Cmd>emenu PopUp." + name.replace(" ", "\\ ") + "<CR>" + ("brave<CR>" if name == "Find" else "")


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
