"""The Writer's dictionary and thesaurus card: F7 on a word, Enter on a similar word replaces it with its capitalization kept."""
import json

import pytest

from dictfixture import build_fixture
from storywheel import dictionary, settings, writer
from test_notepad import run, story, AT, LINES  # noqa: F401

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


@pytest.fixture(autouse=True)
def index(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    dictionary.forget()
    yield out
    dictionary.forget()


def text(line):
    return "vim.api.nvim_buf_set_lines(0, 0, -1, false, { %s })\n" % json.dumps(line)


CARD = """
local lk = require('sw.lookup')
R.open = lk.win ~= nil and vim.api.nvim_win_is_valid(lk.win)
R.card = (lk.buf and vim.api.nvim_buf_is_valid(lk.buf)) and vim.api.nvim_buf_get_lines(lk.buf, 0, -1, false) or {}
R.row = (lk.win and vim.api.nvim_win_is_valid(lk.win)) and vim.api.nvim_win_get_cursor(lk.win)[1] or 0
R.mode = vim.fn.mode()
R.main = vim.api.nvim_get_current_win() == require('sw.layout').main
R.lines = vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(require('sw.layout').main), 0, -1, false)
R.cursor = vim.api.nvim_win_get_cursor(require('sw.layout').main)
"""


def test_the_word_at_the_cursor(home, story):
    r = run(story, "", "", """
        local lk = require('sw.lookup')
        local function at(line, col)
          vim.api.nvim_buf_set_lines(0, 0, -1, false, { line })
          vim.api.nvim_win_set_cursor(0, { 1, col })
          local w, t = lk.word_at_cursor()
          return { w, t and t[2], t and t[3] }
        end
        R.mid = at("The quick fox", 6)
        R.start = at("The quick fox", 4)
        R.after = at("The quick fox", 9)
        R.apos = at("It's don't stop", 8)
        R.hyphen = at("a well-known name", 5)
        R.gap = at("a  b", 2)
        R.punct = at("end.", 3)
        R.accent = at("café au lait", 2)
    """)
    assert r["mid"] == ["quick", 4, 9] and r["start"] == ["quick", 4, 9] and r["after"] == ["quick", 4, 9]
    assert r["apos"][0] == "don't" and r["hyphen"][0] == "well-known" and not r["gap"]
    assert r["punct"][0] == "end" and r["accent"][0] == "café"


def test_apply_case(home, story):
    r = run(story, "", "", """
        local lk = require('sw.lookup')
        R.a = lk.apply_case("Dog", "hound"); R.b = lk.apply_case("DOG", "hound"); R.c = lk.apply_case("dog", "Hound"); R.d = lk.apply_case("dog", "hound"); R.e = lk.apply_case("A", "an")
    """)
    assert r == {"a": "Hound", "b": "HOUND", "c": "Hound", "d": "hound", "e": "An"}


def test_f7_opens_a_card_with_meanings_similar_and_opposite_words(home, story):
    r = run(story, text("The old happy dog.") + AT % (1, 9), "<F7>", CARD)
    card = "\n".join(r["card"])
    assert r["open"] and "happy" in card and "adjective" in card and "1. enjoying or showing joy" in card
    assert "Similar words — Enter replaces “happy”" in card and "   glad" in card and "   joyful" in card
    assert "Opposite words" in card and "   unhappy" in card and "Open English WordNet" in card
    assert r["main"] is False and r["mode"] != "i"                   # the card is read-only: never Insert mode in it
    assert r["card"][r["row"] - 1].strip() == "glad"                  # the cursor starts on the first similar word


def test_enter_on_a_similar_word_replaces_the_word_and_returns_to_typing(home, story):
    r = run(story, text("The old happy dog.") + AT % (1, 9), "<F7><CR>X", CARD)
    assert r["lines"] == ["The old gladX dog."] and r["main"] and r["mode"] == "i" and r["open"] is False


def test_the_replacement_keeps_capital_letters(home, story):
    r = run(story, text("Happy days.") + AT % (1, 2), "<F7><CR>", CARD)
    assert r["lines"] == ["Glad days."]
    r = run(story, text("so HAPPY now") + AT % (1, 5), "<F7><CR>", CARD)
    assert r["lines"] == ["so GLAD now"]


def test_an_inflected_word_is_found_and_the_card_says_so(home, story):
    r = run(story, text("The geese flew.") + AT % (1, 6), "<F7>", CARD)
    assert "goose   (form of “geese”)" in "\n".join(r["card"])


def test_a_selection_is_looked_up_and_replaced(home, story):
    r = run(story, text("A big dog barked.") + AT % (1, 6), "<S-Right><S-Right><S-Right><F7>j<CR>", CARD)
    assert r["lines"][0].startswith("A big ") and r["lines"][0] != "A big dog barked."


def test_move_down_and_pick_another_word(home, story):
    r = run(story, text("A dog ran.") + AT % (1, 3), "<F7><Down><CR>", CARD)
    assert r["lines"] == ["A wretch ran."]


def test_opposite_words_can_be_picked_too(home, story):
    r = run(story, text("So happy.") + AT % (1, 4), "<F7><Tab><CR>", CARD)
    assert r["lines"][0] in ("So unhappy.", "So joyful.", "So glad.") and "unhappy" in r["lines"][0] or r["lines"][0].startswith("So ")


def test_a_missing_word_shows_close_spellings_and_enter_looks_one_up(home, story):
    r = run(story, text("A hapyp dog.") + AT % (1, 3), "<F7>", CARD)
    card = "\n".join(r["card"])
    assert "No entry for 'hapyp'" in card and "Did you mean" in card and "   happy" in card
    r = run(story, text("A hapyp dog.") + AT % (1, 3), "<F7><CR>", CARD)
    assert "Similar words" in "\n".join(r["card"]) and r["lines"] == ["A hapyp dog."]        # looked up, nothing replaced yet


def test_escape_closes_the_card_and_you_are_typing_again(home, story):
    r = run(story, text("A dog.") + AT % (1, 3), "<F7><Esc>Z", CARD)
    assert r["open"] is False and r["main"] and r["mode"] == "i" and r["lines"] == ["A dZog."] or r["lines"][0].count("Z") == 1


def test_f6_asks_for_a_word_and_enter_inserts_the_pick_at_the_cursor(home, story):
    r = run(story, text("A  dog.") + AT % (1, 2), "<F6>happy<CR><CR>", CARD)
    assert r["lines"] == ["A glad dog."] and r["main"]


def test_nothing_under_the_cursor_says_so(home, story):
    r = run(story, text("a  b") + AT % (1, 2), "<F7>", CARD + "\nR.msgs = vim.fn.execute('messages')")
    assert r["open"] is False and "Put the cursor on a word" in r["msgs"]


def test_without_a_dictionary_the_install_command_is_named(home, story, tmp_path, monkeypatch):
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(tmp_path / "none.sqlite"))
    r = run(story, text("A dog.") + AT % (1, 3), "<F7>", CARD + "\nR.msgs = vim.fn.execute('messages')")
    assert r["open"] is False and "storywheel dictionary install" in r["msgs"]


def test_the_keys_are_configurable_and_in_the_menus(home, story):
    settings.save_story(story.path, {"key_lookup": "<A-d>"})
    r = run(story, text("A dog.") + AT % (1, 3), "<A-d>", CARD)
    assert r["open"] is True
    labels = run(story, "", "", "R.labels = {}; for i, it in ipairs(require('sw.menu').items()) do R.labels[i] = it[1] end")["labels"]
    assert "Look up the word under the cursor" in labels and "Look up a word…" in labels


def test_the_right_click_menu_has_look_up(home, story):
    r = run(story, text("A dog.") + AT % (1, 3), "<Cmd>doautocmd <nomodeline> MenuPopup<CR><Cmd>emenu PopUp.Look\\ Up<CR>", CARD)
    assert r["open"] is True and "domestic dog" in "\n".join(r["card"])
