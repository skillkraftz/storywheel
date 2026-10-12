"""Batch 24 B1: versions in the Writer: a key and an F12 menu item list the story's versions and open one (headless Neovim)."""
import json

import pytest

from storywheel import settings, vault, versions, writer, modes, keys
from test_writer import story, run_lua, run_typed  # noqa: F401  (the fixture and the headless drivers)

nvim = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


@pytest.fixture
def two(story):
    new, _notes = versions.new_version(story, "feature-film", "The Last Clause (script)")
    return story, new


@nvim
def test_with_no_other_version_the_key_only_says_so(story):
    r = run_lua(story, """
        R.win = require("sw.versions").open() == false
        R.msg = vim.fn.execute("messages")
        R.floats = 0
        for _, w in ipairs(vim.api.nvim_list_wins()) do if vim.api.nvim_win_get_config(w).relative ~= "" then R.floats = R.floats + 1 end end
    """)
    assert r["win"] and "no other versions" in r["msg"] and r["floats"] == 0


@nvim
def test_the_list_shows_title_format_and_status_and_marks_this_one(two):
    a, b = two
    r = run_lua(a, """
        local v = require("sw.versions")
        local win = v.open()
        R.lines = vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(win), 0, -1, false)
        R.cursor = vim.api.nvim_win_get_cursor(win)[1]
    """)
    assert len(r["lines"]) == 2
    assert "The Last Clause" in r["lines"][0] and "short story" in r["lines"][0] and "(this one)" in r["lines"][0] and r["cursor"] == 1
    assert "script" in r["lines"][1] and "feature film" in r["lines"][1] and "(this one)" not in r["lines"][1]


@nvim
def test_choosing_another_version_saves_and_asks_the_program_to_open_it(two):
    a, b = two
    rf = a.path.parent / "return.txt"
    typed = "<Cmd>lua require('sw.versions').open()<CR>j<CR>"
    run_typed(a, "", typed, "", quits=True)
    assert rf.read_text() == "writer"
    assert json.loads((a.path.parent / "return.txt.data").read_text()) == {"universe": "thornwood", "story": b.slug}


@nvim
def test_choosing_this_version_stays_put_and_the_menu_and_key_are_there(two):
    a, b = two
    r = run_lua(a, """
        local v = require("sw.versions")
        local win = v.open()
        R.stayed = v.switch(v.rows[1]) == false
        R.msg = vim.fn.execute("messages")
        local labels = {}
        for _, it in ipairs(require("sw.menu").items()) do labels[#labels + 1] = it[1] end
        R.menu = table.concat(labels, "|")
        R.key = vim.fn.maparg("<A-o>", "n", false, true).desc
    """)
    assert r["stayed"] and "already in this version" in r["msg"] and "Versions of this story…" in r["menu"]
    assert r["key"] == "Writer: key_versions"


def test_the_versions_key_is_configurable_in_settings_keys():
    assert keys.WRITER_KEYS["key_versions"][1] == "<A-o>"
    assert settings.STORY_DEFAULTS["key_versions"] == "<A-o>" and "key_versions" in settings.INHERITED


def test_the_program_reopens_the_writer_on_the_chosen_version(two, monkeypatch):
    a, b = two
    calls = []

    def fake_run(story, scene=None, replace=None):
        calls.append(story.slug)
        fake_run.handover = {"universe": "thornwood", "story": b.slug} if len(calls) == 1 else None
        return "writer" if len(calls) == 1 else "builder"
    monkeypatch.setattr(writer, "run", fake_run)
    monkeypatch.setattr(writer, "check", lambda: None)
    st = modes.state_mod.State()
    nxt = modes.run_writer(st, {"universe": "thornwood", "story": a.slug})
    assert nxt == ("writer", {"universe": "thornwood", "story": b.slug})
    nxt = modes.run_writer(st, nxt[1])
    assert calls == [a.slug, b.slug] and nxt[0] == "builder"
