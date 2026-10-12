"""Batch 23 B3: the Writer completes the words added to the universe's dictionary, alongside character names."""
import pytest

from storywheel import writer
from test_writer import story, run_lua, run_typed  # noqa: F401  (the fixture and the headless drivers)

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


def add_file(story, text):
    d = story.universe.path / "spell"
    d.mkdir(exist_ok=True)
    (d / "en.utf-8.add").write_text(text, encoding="utf-8")


def test_added_words_complete_after_the_names_and_keep_a_typed_capital(home, story):
    add_file(story, "lamplighter\nStaciana\nzephyrine/\n# a comment\nbadword/!\nab\n")
    r = run_lua(story, """
        local w = require("sw.world")
        local function words(p) return vim.tbl_map(function(i) return i.word end, w.matches(p)) end
        R.lam, R.Lam, R.sta, R.bad, R.short, R.zeph, R.added = words("lam"), words("Lam"), words("sta"), words("bad"), words("la"), words("zep"), w.added_words()
    """)
    assert r["lam"] == ["lamplighter"] and r["Lam"] == ["Lamplighter"]
    assert r["sta"][:2] == ["Stacie", "Stacie Anderson"] and "Staciana" in r["sta"]          # (names first, then the added words)
    assert r["bad"] == [] and r["short"] == [] and r["zeph"] == ["zephyrine"]
    assert r["added"] == ["lamplighter", "Staciana", "zephyrine"]


def test_they_complete_while_typing_with_the_same_menu(home, story):
    add_file(story, "lamplighter\n")
    r = run_typed(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "" })
    """, "iThe lamp<Cmd>lua require('sw.world').complete(); R.items = vim.fn.complete_info({'items'}).items<CR>", "")
    assert [i["word"] for i in r["items"]] == ["lamplighter"] and r["items"][0]["menu"] == "[added]"


def test_a_word_added_a_moment_ago_is_offered_at_once_and_a_universe_without_names_still_completes(home, story):
    for e in story.universe.entities():
        e.path.unlink()
    r = run_lua(story, """
        local w = require("sw.world")
        w.load()
        R.none = #w.matches("nov")
        local f = io.open(require("sw.spell").mine, "a"); f:write("novelette\\n"); f:close()
        R.after = vim.tbl_map(function(i) return i.word end, w.matches("nov"))
        R.entities = #w.entities
    """)
    assert r["entities"] == 0 and r["none"] == 0 and r["after"] == ["novelette"]


def test_add_to_dictionary_then_complete(home, story):
    r = run_lua(story, """
        require("sw.spell").add_word("gloaming")
        local w = require("sw.world")
        R.words = vim.tbl_map(function(i) return i.word end, w.matches("gloa"))
    """)
    assert r["words"] == ["gloaming"]
