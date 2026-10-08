"""The menus driven by real key sequences, the way a person uses them: right-click > More… > Down > Enter, F12 > a number.
Each item must work after exactly the keys a person presses (no extra Enter), without any error message."""
import os
from pathlib import Path

import pytest

from storywheel import writer
from test_menus import problems, writer_menu_labels, RECORD  # noqa: F401
from test_notepad import run, story, ROOT  # noqa: F401

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")

POPUP_THEN_MENU = "<Cmd>lua require('sw.context').open({4, 4})<CR>" + "<Down>" * 7 + "<CR>"          # right-click, then More… (the last item)
SETUP = ("vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello brave world' })\n"
         "local p = require('sw.prose'); p.set_invisibles(false); p.set_typewriter(false); p.set_spell(false)\n")     # (the last run's toggles are remembered)
STATE = """
local m = require('sw.menu').last
R.menu_open = m ~= nil and vim.api.nvim_win_is_valid(m.win)
R.mode = vim.fn.mode()
R.in_main = vim.api.nvim_get_current_win() == require('sw.layout').main
R.invisibles = require('sw.prose').invisibles
R.typewriter = require('sw.prose').typewriter
R.spell = require('sw.prose').spell
R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
"""
LEAVES = {"Settings (F4)": "settings", "Back to the Builder (F2)": "builder", "To the Wheel (F1)": "wheel"}


def route_keys(how, i):
    if how == "f12":
        return "<F12>" + "<Down>" * i + "<CR>"
    if how == "number":
        return "<F12>" + str(i + 1)
    return POPUP_THEN_MENU + "<Down>" * i + "<CR>"         # right-click, More…, then Down and one Enter


def routes(i):
    return ("f12", "rightclick") + (("number",) if i < 9 else ())


def effect_ok(label, R, story):
    if label == "Typewriter mode":
        return R["typewriter"] is True
    if label == "Show invisibles":
        return R["invisibles"] is True
    if label == "Spellcheck":
        return R["spell"] is True
    if label == "New scene":
        return any(l.startswith("* * *") or l == "***" for l in R["lines"])
    return True


def test_every_item_of_the_writer_menu_works_with_one_enter_by_every_route(home, story):
    labels = writer_menu_labels(story)
    failures = []
    for i, label in enumerate(labels):
        for how in routes(i):
            typed = route_keys(how, i)
            if label == "Find…":
                typed += "brave<CR>"
            if label == "New scene":
                typed += "Second<CR>"
            errmsg, bad = problems(story, SETUP, typed, STATE)
            R = problems.last["R"]
            leaves = LEAVES.get(label)
            if leaves:
                got = (story.path.parent / "return.txt").read_text() if (story.path.parent / "return.txt").exists() else ""
                (story.path.parent / "return.txt").write_text("")
                if got != leaves:
                    failures.append((label, how, "did not leave for", leaves, got))
            elif R and R.get("menu_open"):
                failures.append((label, how, "menu still open after one Enter"))
            elif R and not effect_ok(label, R, story):
                failures.append((label, how, "no effect after one Enter", R))
            elif not label.startswith("List of grammar problems") and label not in ("Help", "Scenes sidebar", "Find and replace…", "Restore from a backup…") and not label.startswith("Story outline") and R and not R.get("in_main") and not label.startswith("This story's"):
                failures.append((label, how, "not back in the writing window", R.get("in_main")))
            if errmsg or bad:
                failures.append((label, how, errmsg, bad))
    assert failures == [], "\n".join(map(str, failures))


def test_right_click_writer_menu_enter_on_export_exports_with_the_first_enter(home, story):
    labels = writer_menu_labels(story)
    i = labels.index("Export manuscript (.docx)")
    errmsg, bad = problems(story, SETUP, route_keys("rightclick", i), STATE + "\nvim.wait(300)")
    assert errmsg == "" and bad == []
    made = list(Path(os.environ["STORYWHEEL_MANUSCRIPTS"]).glob("*/*.docx"))
    assert len(made) == 1


def test_after_right_click_writer_menu_enter_you_can_keep_typing_at_once(home, story):
    labels = writer_menu_labels(story)
    i = labels.index("Typewriter mode")
    errmsg, bad = problems(story, SETUP, route_keys("rightclick", i) + "xyz", STATE)
    R = problems.last["R"]
    assert errmsg == "" and bad == [] and R["typewriter"] is True
    assert R["lines"] == ["Hello brave worldxyz"] or R["lines"][0].endswith("xyz") or "xyz" in R["lines"][0]
    assert R["mode"] == "i" and R["in_main"] is True


def test_the_menu_never_puts_insert_mode_into_a_read_only_window(home, story):
    # right-click > More…: the menu is open, and we are NOT in Insert mode there
    errmsg, bad = problems(story, SETUP, POPUP_THEN_MENU, STATE)
    R = problems.last["R"]
    assert R["menu_open"] is True and R["mode"] != "i" and R["in_main"] is False and errmsg == "" and bad == []


def test_can_type_is_false_in_read_only_and_other_windows(home, story):
    r = run(story, "", "<F12>", "R.can = require('sw.notepad').can_type(); R.mod = vim.bo.modifiable")
    assert r["can"] is False and r["mod"] is False
    r = run(story, "", "", "R.can = require('sw.notepad').can_type()")
    assert r["can"] is True
