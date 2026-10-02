"""Restore from a backup, from the Writer's menu: the list, the preview, and the restore (with the confirmation)."""
import json

import pytest

from storywheel import backups, settings, vault, writer
from test_notepad import run, story, AT, LINES  # noqa: F401

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


@pytest.fixture
def with_backups(story):
    manu = story.files()[0]
    b = story.path / ".backups" / "2026-10-01"
    b.mkdir(parents=True)
    (b / f"0930-{manu.name}").write_text("The old text of the scene.\nSecond line of the old text.\n", encoding="utf-8")
    c = story.path / ".backups" / "quotes-20260920-120000"
    c.mkdir()
    (c / manu.name).write_text("Before the quotes were made straight.\n", encoding="utf-8")
    return story, manu


STATE = """
local r = require('sw.restore')
R.open = r.win ~= nil and vim.api.nvim_win_is_valid(r.win)
R.list = (r.win and vim.api.nvim_win_is_valid(r.win)) and vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(r.win), 0, -1, false) or {}
R.preview = (r.pwin and vim.api.nvim_win_is_valid(r.pwin)) and vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(r.pwin), 0, -1, false) or {}
R.lines = vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(require('sw.layout').main), 0, -1, false)
R.mode = vim.fn.mode()
R.main = vim.api.nvim_get_current_win() == require('sw.layout').main
"""


def test_the_list_shows_date_kind_file_and_words_with_a_preview(home, with_backups):
    s, manu = with_backups
    r = run(s, "", "<Cmd>lua require('sw.restore').open()<CR>", STATE)
    assert r["open"] and len(r["list"]) >= 2                              # (the Writer makes a copy of its own when it starts)
    old = next(l for l in r["list"] if "2026-10-01 09:30" in l)
    assert "while writing" in old and manu.name in old and "12 words" in old
    quotes_row = next(l for l in r["list"] if "before quotes were made straight" in l)
    assert quotes_row.strip().startswith("2026-09-20")


def test_moving_changes_the_preview(home, with_backups):
    s, manu = with_backups
    r = run(s, "", "<Cmd>lua require('sw.restore').open()<CR>j", STATE)
    assert r["preview"] == ["The old text of the scene.", "Second line of the old text."]


def test_enter_asks_and_yes_restores_keeping_the_current_version(home, with_backups):
    s, manu = with_backups
    manu.write_text("What is in the file now.\n", encoding="utf-8")
    r = run(s, "require('sw.util').auto_answer = true", "<Cmd>lua require('sw.restore').open()<CR>j<CR>", STATE + "\nvim.wait(300)")
    assert r["open"] is False and r["main"] and r["mode"] == "i"
    assert r["lines"][0] == "The old text of the scene."
    assert manu.read_text().startswith("The old text of the scene.")
    kept = [row for row in backups.list_backups(s) if row["kind"] == "restore"]
    assert len(kept) == 1 and kept[0]["words"] >= 5


def test_no_leaves_everything_as_it_is(home, with_backups):
    s, manu = with_backups
    manu.write_text("What is in the file now.\n", encoding="utf-8")
    r = run(s, "require('sw.util').auto_answer = false", "<Cmd>lua require('sw.restore').open()<CR>j<CR>", STATE)
    assert manu.read_text() == "What is in the file now.\n" and r["open"] is True
    assert not [row for row in backups.list_backups(s) if row["kind"] == "restore"]


def test_unsaved_typing_is_saved_before_the_list_so_nothing_is_lost(home, with_backups):
    s, manu = with_backups
    r = run(s, "require('sw.util').auto_answer = true\nvim.api.nvim_buf_set_lines(0, 0, -1, false, { 'typed but not saved yet' })", "<Cmd>lua require('sw.restore').open()<CR>j<CR>", STATE + "\nvim.wait(300)")
    kept = [row for row in backups.list_backups(s) if row["kind"] == "restore"]
    assert kept and "typed but not saved yet" in open(kept[0]["path"]).read()
    assert r["lines"][0] == "The old text of the scene."


def test_escape_closes_the_list_and_you_are_typing_again(home, with_backups):
    s, manu = with_backups
    r = run(s, "", "<Cmd>lua require('sw.restore').open()<CR><Esc>", STATE)
    assert r["open"] is False and r["main"] and r["mode"] == "i"


def test_no_backups_says_so(home, story):
    r = run(story, "require('sw.restore').fetch = function() return {} end", "<Cmd>lua require('sw.restore').open()<CR>", STATE + "\nR.msgs = vim.fn.execute('messages')")
    assert r["open"] is False and "no backups of this story yet" in r["msgs"]


def test_the_menu_has_the_entry_and_the_leave_group(home, story):
    r = run(story, "", "", "R.labels = {}; for i, it in ipairs(require('sw.menu').items()) do R.labels[i] = it[1] end; R.groups = {}; for _, g in ipairs(require('sw.menu').groups()) do R.groups[#R.groups + 1] = g[1] end")
    assert "Restore from a backup…" in r["labels"] and r["groups"] == ["Edit", "Look up", "Story", "Leave", "More"]
    assert not any("settings.toml" in l for l in r["labels"]) and "Use Vim keys for now" in r["labels"]
    assert any(l.startswith("Quit storywheel") for l in r["labels"])
