"""Find and replace in the Writer (Ctrl+H): matching rules, replacing one and all (one undo step), the form driven by real keys."""
import json

import pytest

from storywheel import settings, writer
from test_notepad import run, story, AT, LINES  # noqa: F401

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")

TEXT = ["The Cat sat. the cat ran; category catalog cat's tail.", "Concatenate: a CAT, a cat.", "No felines here."]
SET = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { %s })" % ", ".join(json.dumps(t) for t in TEXT)


MAIN = "R.lines = vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(require('sw.layout').main), 0, -1, false)"
TITLE = "R.title = vim.api.nvim_win_get_config(require('sw.replace').win).title[1][1]"


def lua(body):
    return SET + "\nvim.cmd('let &undolevels = &undolevels')\nlocal rp = require('sw.replace')\n" + body


def test_matches_ignore_case_by_default_and_count_every_occurrence(home, story):
    r = run(story, lua("R.n = #rp.matches(0, 'cat', { case = false, word = false })"), "", "")
    assert r["n"] == 8


def test_match_case_and_whole_word(home, story):
    r = run(story, lua("""
        R.case = #rp.matches(0, 'cat', { case = true, word = false })
        R.word = #rp.matches(0, 'cat', { case = false, word = true })
        R.both = #rp.matches(0, 'Cat', { case = true, word = true })
        R.none = #rp.matches(0, 'zebra', {})
        R.empty = #rp.matches(0, '', {})
    """), "", "")
    assert r["case"] == 6 and r["word"] == 5 and r["both"] == 1 and r["none"] == 0 and r["empty"] == 0


def test_special_characters_are_literal(home, story):
    r = run(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'a.b a*b [x] a\\\\b \"quoted\" ~ $ ^' })\nlocal rp = require('sw.replace')", "",
            "R.dot = #rp.matches(0, 'a.b', {}); R.star = #rp.matches(0, 'a*b', {}); R.br = #rp.matches(0, '[x]', {}); R.tilde = #rp.matches(0, '~', {}); R.caret = #rp.matches(0, '^', {})")
    assert r == {"dot": 1, "star": 1, "br": 1, "tilde": 1, "caret": 1}


def test_replace_all_counts_and_is_one_undo_step(home, story):
    r = run(story, lua("R.n = rp.replace_all(0, 'cat', 'dog', { case = false, word = true }); R.after = vim.api.nvim_buf_get_lines(0, 0, -1, false)"),
            "<C-z>", LINES)
    assert r["n"] == 5
    assert r["after"] == ["The dog sat. the dog ran; category catalog dog's tail.", "Concatenate: a dog, a dog.", "No felines here."]
    assert r["lines"] == TEXT                       # a single undo brings everything back


def test_replace_one_walks_through_the_text(home, story):
    r = run(story, lua("""
        R.a = { rp.replace_one(0, 'cat', 'X', 0, 0, { case = false, word = true }) }
        R.b = { rp.replace_one(0, 'cat', 'X', R.a[2], R.a[3], { case = false, word = true }) }
        R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
    """), "", "")
    assert r["a"][0] == 1 or r["a"][1] == 1
    assert r["lines"][0] == "The X sat. the X ran; category catalog cat's tail."


def test_the_form_opens_with_the_selection_and_shows_the_count(home, story):
    r = run(story, lua(AT % (1, 4)), "<S-Right><S-Right><S-Right><C-h>", """
        R.find = vim.api.nvim_buf_get_lines(require('sw.replace').buf, 0, 1, false)[1]
        R.title = vim.api.nvim_win_get_config(require('sw.replace').win).title[1][1]
        R.mode = vim.fn.mode()
        R.in_form = vim.api.nvim_get_current_win() == require('sw.replace').win
    """)
    assert r["find"] == "Cat" and "8 matches" in r["title"] and r["mode"] == "i" and r["in_form"]


def test_type_find_and_replace_then_alt_a_replaces_all_and_esc_returns_to_typing(home, story):
    r = run(story, lua(AT % (1, 0)), "<C-h>cat<Tab>dog<A-w><A-a><Esc>X",
            MAIN + "; R.mode = vim.fn.mode(); R.main = vim.api.nvim_get_current_win() == require('sw.layout').main")
    assert r["lines"][0] == "XThe dog sat. the dog ran; category catalog dog's tail."
    assert r["lines"][1] == "Concatenate: a dog, a dog." and r["main"] and r["mode"] == "i"


def test_enter_finds_next_and_alt_r_replaces_that_one(home, story):
    r = run(story, lua(AT % (1, 0)), "<C-h>cat<Tab>X<Up><A-w><CR><CR><A-r>",
            MAIN)
    assert sum(l.count("X") for l in r["lines"]) == 1 and r["lines"][0] != TEXT[0] or r["lines"][1] != TEXT[1]
    assert "".join(r["lines"]).count("X") == 1


def test_toggles_change_the_count(home, story):
    r = run(story, lua(AT % (1, 0)), "<C-h>cat", """
        local rp = require('sw.replace')
        rp.actions.refresh()
        R.t1 = vim.api.nvim_win_get_config(rp.win).title[1][1]
        rp.actions.toggle('case')
        R.t2 = vim.api.nvim_win_get_config(rp.win).title[1][1]
        rp.actions.toggle('word')
        R.t3 = vim.api.nvim_win_get_config(rp.win).title[1][1]
    """)
    assert "8 matches" in r["t1"] and "case: match" in r["t2"] and "6 matches" in r["t2"]
    assert "whole word" in r["t3"] and "3 matches" in r["t3"]


def test_not_found_says_so_and_changes_nothing(home, story):
    r = run(story, lua(AT % (1, 0)), "<C-h>zebra<Tab>x<A-a>", MAIN + "; " + TITLE)
    assert r["lines"] == TEXT and "nothing to replace" in r["title"]


def test_the_key_is_configurable_and_in_the_menu(home, story):
    settings.save_story(story.path, {"key_replace": "<A-h>"})
    r = run(story, lua(AT % (1, 0)), "<A-h>", "R.open = require('sw.replace').win ~= nil and vim.api.nvim_win_is_valid(require('sw.replace').win)")
    assert r["open"] is True
    labels = run(story, "", "", "R.labels = {}; for i, it in ipairs(require('sw.menu').items()) do R.labels[i] = it[1] end")["labels"]
    assert "Find and replace…" in labels
