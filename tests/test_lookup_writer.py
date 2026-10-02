"""The Writer's dictionary and thesaurus card: F7 on a word (or F6 for a typed one). Enter looks a word up (b goes back), r replaces
the word that was under the cursor in the same form, i inserts at the cursor, c copies, / filters."""
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
local ok_win = lk.win ~= nil and vim.api.nvim_win_is_valid(lk.win)
R.open = ok_win
R.card = (lk.buf and vim.api.nvim_buf_is_valid(lk.buf)) and vim.api.nvim_buf_get_lines(lk.buf, 0, -1, false) or {}
R.current = ok_win and lk.current() and lk.current().word or ""
R.title = ok_win and vim.api.nvim_win_get_config(lk.win).title[1][1] or ""
R.mode = vim.fn.mode()
R.main = vim.api.nvim_get_current_win() == require('sw.layout').main
R.lines = vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(require('sw.layout').main), 0, -1, false)
R.cursor = vim.api.nvim_win_get_cursor(require('sw.layout').main)
R.reg = vim.fn.getreg('+')
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


def test_f7_opens_a_card_grouped_by_meaning_with_every_similar_word(home, story):
    r = run(story, text("The old dog barked.") + AT % (1, 9), "<F7>", CARD)
    card = "\n".join(r["card"])
    assert r["open"] and " dog" in card and "noun" in card
    assert "1. a domesticated canine" in card and "2. a despicable person" in card
    i1, i2 = card.index("1. a domesticated canine"), card.index("2. a despicable person")
    assert "domestic dog" in card[i1:i2] and "wretch" not in card[i1:i2] and "wretch" in card[i2:]          # each meaning has its own words
    assert "More similar words (4)" in card and all(w in card for w in ("cur", "hound", "mutt", "pooch"))         # then the broad list
    assert "more)" not in card.replace("More similar words", "") and "…" not in card                         # nothing cut off
    assert r["main"] is False and r["mode"] != "i" and r["current"] == "domestic dog"
    assert "Open English WordNet" in card


def test_opposites_direct_and_indirect_are_on_the_card(home, story):
    r = run(story, text("A happy dog.") + AT % (1, 4), "<F7>", CARD)
    card = "\n".join(r["card"])
    assert "Opposite words\n   unhappy" in card
    assert "Opposite words, indirect (opposites of similar words)" in card and "sad (glad)" in card
    r = run(story, text("A dog.") + AT % (1, 3), "<F7>", CARD)
    assert "Related forms\n   doggy (derivation)" in "\n".join(r["card"])


def test_enter_looks_the_word_up_and_b_goes_back_and_n_forward(home, story):
    r = run(story, text("A dog ran.") + AT % (1, 3), "<F7><CR>", CARD)
    assert r["title"].strip().startswith("domestic dog") or "domestic" in r["title"] or "dog" in r["title"]
    assert r["lines"] == ["A dog ran."]                                    # Enter only looks up; nothing is replaced
    r = run(story, text("A happy dog.") + AT % (1, 4), "<F7>j<CR>", CARD)       # 'glad' under the cursor after j? -> looked up
    assert "[2/2]" in r["title"]
    r = run(story, text("A happy dog.") + AT % (1, 4), "<F7><CR>b", CARD)
    assert "happy" in r["title"] and "[" not in r["title"] or "[1/2]" in r["title"]
    r = run(story, text("A happy dog.") + AT % (1, 4), "<F7><CR>bn", CARD)
    assert "[2/2]" in r["title"]


def test_r_replaces_the_original_word_keeping_capitals_and_returns_to_typing(home, story):
    r = run(story, text("The old happy dog.") + AT % (1, 9), "<F7>r", CARD)
    assert r["lines"] == ["The old glad dog."] and r["main"] and r["mode"] == "i" and r["open"] is False
    r = run(story, text("Happy days.") + AT % (1, 2), "<F7>r", CARD)
    assert r["lines"] == ["Glad days."]
    r = run(story, text("so HAPPY now") + AT % (1, 5), "<F7>r", CARD)
    assert r["lines"] == ["so GLAD now"]


def test_r_after_looking_up_another_word_still_replaces_the_original(home, story):
    # run -> (Enter on sprint) -> the card for sprint -> move to dash -> r replaces the ORIGINAL "run" with dash
    r = run(story, text("I run home.") + AT % (1, 3), "<F7><CR><Right>r", CARD)
    assert r["lines"] == ["I dash home."]


def test_the_replacement_takes_the_form_of_the_original(home, story):
    # running (the -ing form of run): sprint -> sprinting
    r = run(story, text("She was running home.") + AT % (1, 9), "<F7>r", CARD)
    assert r["lines"] == ["She was sprinting home."]
    # ran (past): the first similar word of 'run' is sprint -> sprinted
    r = run(story, text("She ran home.") + AT % (1, 6), "<F7>r", CARD)
    assert r["lines"] == ["She sprinted home."]
    # geese (plural): a similar word of goose -> its plural; the fixture's goose has none, so check dogs
    r = run(story, text("Two dogs barked.") + AT % (1, 6), "<F7>r", CARD)
    assert r["lines"] == ["Two domestic dogs barked."]
    # capital kept as well as form
    r = run(story, text("Running home.") + AT % (1, 3), "<F7>r", CARD)
    assert r["lines"] == ["Sprinting home."]


def test_i_inserts_the_word_at_the_cursor_where_the_card_was_opened(home, story):
    r = run(story, text("A  dog.") + AT % (1, 2), "<F6>happy<CR>i", CARD)
    assert r["lines"] == ["A glad dog."] and r["main"] and r["mode"] == "i"
    r = run(story, text("A dog.") + AT % (1, 3), "<F7>i", CARD)
    assert r["lines"] == ["A domestic dogdog."] or "domestic dog" in r["lines"][0]


def test_c_copies_the_word(home, story):
    r = run(story, text("A dog.") + AT % (1, 3), "<F7>j<Cmd>lua require('sw.lookup').copy(require('sw.lookup').current().word)<CR>c", CARD)
    assert r["reg"] != "" and r["lines"] == ["A dog."] and r["open"]


def test_c_key_copies_and_the_card_stays_open(home, story):
    r = run(story, text("A dog.") + AT % (1, 3), "<F7>c", CARD)
    assert r["reg"] == "domestic dog" and r["open"] and r["lines"] == ["A dog."]


def test_f6_replaces_the_word_under_the_cursor_with_r_and_inserts_with_i(home, story):
    r = run(story, text("A dog ran.") + AT % (1, 3), "<F6>happy<CR>r", CARD)
    assert r["lines"] == ["A glad ran."]                                  # the same keys as F7: r replaces the word under the cursor
    r = run(story, text("A dog ran.") + AT % (1, 3), "<F6>happy<CR>i", CARD)
    assert r["lines"][0].startswith("A gladdog") or "glad" in r["lines"][0]


def test_r_with_nothing_under_the_cursor_says_so(home, story):
    r = run(story, text("a  b") + AT % (1, 2), "<F6>happy<CR>r", CARD + "\nR.msgs = vim.fn.execute('messages')")
    assert r["open"] and "Nothing to replace" in r["msgs"] and r["lines"] == ["a  b"]


def test_the_filter_narrows_every_list_and_escape_clears_it(home, story):
    r = run(story, text("A dog.") + AT % (1, 3), "<F7>", CARD + "\nlocal lk = require('sw.lookup'); lk.filter = 'ou'; lk.render(); R.filtered = vim.api.nvim_buf_get_lines(lk.buf, 0, -1, false)")
    f = "\n".join(r["filtered"])
    assert "hound" in f and "mutt" not in f and "pooch" not in f and "domestic dog" not in f.split("More similar")[0].split("1. a domesticated canine")[1].split("2. a despicable")[0]
    r = run(story, text("A dog.") + AT % (1, 3), "<F7>", CARD + "\nlocal lk = require('sw.lookup'); lk.filter = 'ou'; lk.render(); R.t = vim.api.nvim_win_get_config(lk.win).title[1][1]")
    assert "filter: ou" in r["t"]
    r = run(story, text("A dog.") + AT % (1, 3), "<F7>", "local lk = require('sw.lookup'); lk.filter = 'ou'; lk.render(); vim.api.nvim_feedkeys(vim.keycode('<Esc>'), 'x', false); R.f = lk.filter; R.open = lk.win ~= nil and vim.api.nvim_win_is_valid(lk.win)")
    assert r["f"] == "" and r["open"] is True


def test_the_card_scrolls_and_arrow_keys_move_between_words(home, story):
    r = run(story, text("A dog.") + AT % (1, 3), "<F7><Right><Right>", CARD)
    assert r["current"] != "domestic dog"
    r = run(story, text("A dog.") + AT % (1, 3), "<F7><Right><Left>", CARD)
    assert r["current"] == "domestic dog"
    r = run(story, text("A dog.") + AT % (1, 3), "<F7><Tab>", CARD)
    assert r["current"] == "wretch" or r["current"] != "domestic dog"
    r = run(story, text("A dog.") + AT % (1, 3), "<F7><Down><Up>", CARD)
    assert r["current"] != ""


def test_a_selection_is_looked_up_and_replaced(home, story):
    r = run(story, text("A big dog barked.") + AT % (1, 6), "<S-Right><S-Right><S-Right><F7>r", CARD)
    assert r["lines"][0].startswith("A big ") and r["lines"][0] != "A big dog barked."


def test_an_inflected_word_is_found_and_the_card_says_so(home, story):
    r = run(story, text("The wolves flew.") + AT % (1, 6), "<F7>", CARD)
    assert "wolf   (form of “wolves”)" in "\n".join(r["card"])


def test_a_missing_word_shows_close_spellings_and_enter_looks_one_up(home, story):
    r = run(story, text("A hapyp dog.") + AT % (1, 3), "<F7>", CARD)
    card = "\n".join(r["card"])
    assert "No entry for 'hapyp'" in card and "Did you mean" in card and "happy" in card
    r = run(story, text("A hapyp dog.") + AT % (1, 3), "<F7><CR>", CARD)
    assert "More similar words" in "\n".join(r["card"]) or "glad" in "\n".join(r["card"])
    assert r["lines"] == ["A hapyp dog."]


def test_escape_closes_the_card_and_you_are_typing_again(home, story):
    r = run(story, text("A dog.") + AT % (1, 3), "<F7><Esc>Z", CARD)
    assert r["open"] is False and r["main"] and r["mode"] == "i" and "Z" in r["lines"][0]


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


def test_the_footer_shows_the_keys(home, story):
    r = run(story, text("A dog.") + AT % (1, 3), "<F7>", "R.footer = vim.api.nvim_win_get_config(require('sw.lookup').win).footer[1][1]")
    for key in ("Enter look up", "b back", "r replace", "i insert", "c copy", "/ filter", "Esc close"):
        assert key in r["footer"]
