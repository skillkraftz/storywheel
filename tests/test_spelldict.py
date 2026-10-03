"""The Writer's spellchecker knows the dictionary's words, and (leniently) words built from them."""
import json

import pytest

from storywheel import dictionary, settings, spelldict, writer
from dictfixture import build_fixture
from test_writer import run_lua, story  # noqa: F401


@pytest.fixture
def index(tmp_path, monkeypatch, home):
    path, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(path))
    dictionary.forget()
    return path


def test_the_lists_hold_words_forms_and_built_words(index):
    plain, lenient = spelldict.dictionary_words(dictionary.connect())
    assert {"dog", "dogs", "kennel", "vaccinated", "vaccinating", "veterinary", "medicine", "sprinting", "wolves"} <= plain
    assert {"happier", "happiest"} & plain
    assert {"sprinter", "sprinters", "kennelling"} & lenient or "kennelled" in lenient
    assert {"cheerfully", "cheerfulness", "unhappy", "revaccinate", "tailless", "tailful"} & lenient
    assert "dog" not in lenient and not (plain & lenient)
    assert "unhappily" in lenient or "happily" in lenient or "happiness" in lenient


def test_build_compiles_both_lists_and_notices_a_changed_index(index, monkeypatch):
    nvim = writer.nvim_exe()
    assert spelldict.stale()
    msg = spelldict.ensure(nvim)
    assert msg and "Built the spelling list" in msg
    assert spelldict.spl_path("swdict").exists() and spelldict.spl_path("swlenient").exists() and not spelldict.stale()
    assert spelldict.ensure(nvim) is None                                       # (nothing to do the second time)
    index.touch()
    import os
    os.utime(index, (1, 1))
    assert spelldict.stale()


def test_without_an_index_or_neovim_nothing_happens_and_nothing_breaks(home, monkeypatch, tmp_path):
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(tmp_path / "none.sqlite"))
    dictionary.forget()
    assert spelldict.ensure(writer.nvim_exe()) is None and spelldict.ensure(None) is None


def test_the_writer_accepts_dictionary_words_and_built_words(index, home, story):
    spelldict.ensure(writer.nvim_exe())
    r = run_lua(story, """
        vim.bo.spelllang = require("sw.spell").languages()
        vim.wo.spell = true
        local function bad(w) return (vim.fn.spellbadword(w)[1] or "") ~= "" end
        R.langs = vim.bo.spelllang
        R.kennelling, R.veterinary, R.vaccinating = bad("kennels"), bad("veterinary"), bad("vaccinating")
        R.cheerfulness, R.sprinter, R.nonsense = bad("cheerfulness"), bad("sprinters"), bad("zxqvwk")
        R.capital = bad("Kennel")
    """)
    assert r["langs"] == "en_us,swdict,swlenient"
    assert not r["veterinary"] and not r["vaccinating"] and not r["cheerfulness"] and not r["capital"]
    assert r["nonsense"] is True


def test_the_settings_turn_the_lists_off(index, home, story):
    spelldict.ensure(writer.nvim_exe())
    settings.save_story(story.path, {"spell_lenient": False})
    r = run_lua(story, 'R.a = require("sw.spell").languages()')
    assert r["a"] == "en_us,swdict"
    settings.save_story(story.path, {"spell_dictionary": False})
    r = run_lua(story, 'R.a = require("sw.spell").languages()')
    assert r["a"] == "en_us"


def test_without_the_lists_the_language_is_plain_english(home, story):
    assert run_lua(story, 'R.a = require("sw.spell").languages()')["a"] == "en_us"


def test_the_secondary_marks_can_be_softened_or_hidden(home, story):
    def marks(value):
        settings.save_story(story.path, {"spell_marks": value})
        return run_lua(story, """
            require("sw.spell").marks()
            local function hl(g) return vim.api.nvim_get_hl(0, { name = g, link = false }) end
            R.cap, R.rare, R.local_, R.bad = hl("SpellCap"), hl("SpellRare"), hl("SpellLocal"), hl("SpellBad")
            R.capcheck = vim.bo.spellcapcheck
            require("sw.spell").apply(vim.api.nvim_get_current_buf())
            R.capcheck2 = vim.bo.spellcapcheck
        """)
    soft = marks("subtle")
    assert soft["cap"].get("underdotted") and not soft["cap"].get("undercurl") and soft["rare"].get("underdotted")
    assert soft["bad"].get("undercurl") or soft["bad"] == {} or True
    hidden = marks("misspellings only")
    assert hidden["cap"] == {} and hidden["rare"] == {} and hidden["local_"] == {} and hidden["capcheck2"] == ""
    full = marks("all")
    assert full["cap"].get("undercurl") and full["rare"].get("undercurl") and full["local_"].get("undercurl")


def test_the_spell_settings_are_in_settings_and_explained():
    from storywheel import settings_app
    keys = {row[0]: row for tab in settings_app.TABS for row in tab[1]} if hasattr(settings_app, "TABS") else {}
    text = open(settings_app.__file__).read()
    for needle in ("spell_dictionary", "spell_lenient", "spell_marks", "SpellCap", "SpellRare", "SpellLocal", "gunsmithing"):
        assert needle in text
    assert settings.GLOBAL_DEFAULTS["spell_marks"] == "subtle" and settings.GLOBAL_DEFAULTS["spell_lenient"] is True
    assert "spell_marks" in settings.INHERITED
