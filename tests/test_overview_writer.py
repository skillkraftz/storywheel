"""Ctrl+O in the Writer: a floating, read-only overlay with the story's outline; Escape closes it."""
import pytest

from storywheel import settings, vault, writer
from test_notepad import run, LINES  # noqa: F401

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")

SECTIONS = {
    "Premise": "When a stranger brings a locked box to Redwater, Ann must open it before the posse arrives.",
    "Setting": "- **Place:** Redwater\n- **Era:** the 1880s\n- **Season:** autumn\n- **Landmark:** the livery\n- **Rumor:** a pistol lies buried at the livery",
    "Story Spine": "Once upon a time, Ann lived in Redwater.\n\nEvery day, Ann swept the porch.\n\nOne day, a stranger came.",
    "Twist": "The stranger was Ann's brother.",
}


@pytest.fixture
def story(home):
    u = vault.create_universe("Thornwood", ["western"])
    u.new_entity("character", "Ann Lowell", {"role": "protagonist", "job": "teacher", "want": "the deed", "need": "to trust"})
    u.new_entity("character", "Bob Rivers", {"role": "supporting", "job": "smith"})
    s = u.new_story("The Last Clause", {"genre": "western", "mood": "cozy", "structure": "Story Spine"}, SECTIONS)
    s.add_scene("Opening", "Hello brave world")
    return s


OPEN = """
local ov = require('sw.overview')
R.open = ov.is_open()
R.lines = ov.is_open() and vim.api.nvim_buf_get_lines(ov.buf, 0, -1, false) or {}
R.cfg = ov.is_open() and vim.api.nvim_win_get_config(ov.win) or {}
R.modifiable = ov.is_open() and vim.bo[ov.buf].modifiable or false
R.mode = vim.fn.mode()
R.in_main = vim.api.nvim_get_current_win() == require('sw.layout').main
"""


def test_ctrl_o_shows_the_outline_in_a_read_only_floating_window(home, story):
    r = run(story, "", "<C-o>", OPEN)
    text = "\n".join(r["lines"])
    assert r["open"] and not r["modifiable"] and r["cfg"]["relative"] == "editor"
    assert r["lines"][0] == "The Last Clause" and "western · cozy · Story Spine" in r["lines"][1]
    for needle in ("Premise", "locked box to Redwater", "Story Spine", "1. Once upon a time, Ann lived in Redwater.", "3. One day, a stranger came.",
                   "Twist", "The stranger was Ann's brother.", "Protagonist", "Ann Lowell", "Setting", "Place: Redwater",
                   "Era: the 1880s", "Rumor", "A pistol lies buried at the livery"):
        assert needle in text, needle
    import re
    assert re.search(r"Job:\s+teacher", text) and re.search(r"Want:\s+the deed", text)       # (the protagonist's values line up)
    assert "Bob Rivers" not in text and "Rumor: a pistol" not in text            # only the protagonist; the rumor has its own section


def test_escape_closes_it_and_typing_goes_on(home, story):
    r = run(story, "", "<C-o><Esc>xyz", OPEN + "; R.text = vim.api.nvim_buf_get_lines(0, 0, -1, false)")
    assert not r["open"] and r["in_main"] and r["mode"] == "i" and any("xyz" in l for l in r["text"])


def test_ctrl_o_again_closes_it_and_q_does_too(home, story):
    assert not run(story, "", "<C-o><C-o>", OPEN)["open"]
    assert not run(story, "", "<C-o>q", OPEN)["open"]


def test_the_manuscript_is_not_changed_by_the_overlay(home, story):
    r = run(story, "", "<C-o>jjj<Esc>", LINES)
    assert r["lines"][0].startswith("Hello brave world") and len(r["lines"]) <= 3


def test_the_key_can_be_changed_in_settings(home, story):
    settings.save_global({"key_overview": "<A-o>"})
    assert run(story, "", "<A-o>", OPEN)["open"]
    assert not run(story, "", "<C-o>", OPEN)["open"]


def test_a_story_without_an_outline_says_so(home):
    u = vault.create_universe("Plain", ["western"])
    s = u.new_story("Blank")
    s.add_scene("Opening", "Hello")
    r = run(s, "", "<C-o>", OPEN)
    assert "no outline yet" in "\n".join(r["lines"])


def test_the_menu_lists_it(home, story):
    r = run(story, "", "", "R.items = {}; for _, it in ipairs(require('sw.menu').items()) do R.items[#R.items + 1] = it[1] end")
    assert any(i.startswith("Story outline") and "Ctrl+O" in i for i in r["items"])
