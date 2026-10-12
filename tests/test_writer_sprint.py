"""Batch 23 B4: writing sprints in the Writer (headless Neovim; the visual side is in the manual script)."""
import json

import pytest

from storywheel import settings, vault, writer
from test_writer import story, run_lua, run_typed  # noqa: F401  (the fixture and the headless drivers)

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")

FAKE_CLOCK = """
    local sprint = require("sw.sprint")
    local now = 1000
    sprint.clock = function() return now end
    local function tick(n) now = now + n end
    local function add(text)
      local b = vim.api.nvim_get_current_buf()
      local n = vim.api.nvim_buf_line_count(b)
      vim.api.nvim_buf_set_lines(b, n, n, false, { "", text })
      require("sw.stats").refresh()
    end
"""


def test_a_sprint_counts_the_words_written_since_it_began_and_shows_in_the_status_line(home, story):
    r = run_lua(story, FAKE_CLOCK + """
        R.before = sprint.status_text()
        sprint.start(25, 30)
        R.start_line = sprint.status_text()
        add("one two three four five six seven eight nine ten")
        tick(60 * 10 + 5)
        R.mid = sprint.status_text()
        R.line = require("sw.stats").line()
        R.left = sprint.seconds_left()
    """)
    assert r["before"] == "" and r["start_line"] == "sprint 25:00 left · 0 / 30 words"
    assert r["mid"] == "sprint 14:55 left · 10 / 30 words" and "sprint 14:55 left" in r["line"] and "words: in this scene" in r["line"]
    assert r["left"] == 895


def test_the_end_gives_one_quiet_line_and_an_entry_in_the_stats(home, story):
    r = run_lua(story, FAKE_CLOCK + """
        sprint.start(10, 5)
        add("one two three four five six")
        tick(60 * 10)
        local rec = sprint.finish("done")
        R.rec = rec
        R.active = sprint.active == nil
        R.msg = vim.fn.execute("messages")
        R.after = sprint.status_text()
    """)
    rec = r["rec"]
    assert rec["words"] == 6 and rec["minutes"] == 10 and rec["actual_minutes"] == 10 and rec["wpm"] == 0.6
    assert rec["target"] == 5 and rec["hit"] is True and "early" not in rec
    assert r["active"] and r["after"] == ""
    assert "Sprint done: 6 words in 10 minutes (0.6 a minute)" in r["msg"] and "reached the 5-word target" in r["msg"]
    data = json.loads((story.path / "stats.json").read_text())
    assert len(data["sprints"]) == 1 and data["sprints"][0]["words"] == 6 and data["sprints"][0]["hit"] is True
    assert "days" in data and "sessions" in data                                   # (the rest of the file is as it was)


def test_stopping_early_is_fine_and_is_recorded_as_early(home, story):
    r = run_lua(story, FAKE_CLOCK + """
        sprint.start(25)
        add("alpha beta gamma delta")
        tick(120)
        sprint.ask()                                                                 -- the key again while it runs: stop
        R.msg = vim.fn.execute("messages")
        R.rec = sprint.last
        R.active = sprint.active == nil
    """)
    assert r["active"] and r["rec"]["early"] is True and r["rec"]["words"] == 4 and r["rec"]["actual_minutes"] == 2.0 and r["rec"]["wpm"] == 2.0
    assert "Sprint stopped: 4 words in 2.0 minutes (2.0 a minute)" in r["msg"]
    assert len(json.loads((story.path / "stats.json").read_text())["sprints"]) == 1


def test_an_instant_start_and_stop_is_just_cancelled(home, story):
    r = run_lua(story, FAKE_CLOCK + """
        sprint.start(5)
        sprint.finish("stopped")
        R.rec = sprint.last == nil
        R.msg = vim.fn.execute("messages")
    """)
    assert r["rec"] is True and "Sprint cancelled." in r["msg"]
    assert not (story.path / "stats.json").exists() or "sprints" not in json.loads((story.path / "stats.json").read_text())


def test_pasted_text_and_deleted_text_do_not_make_sprint_words(home, story):
    r = run_lua(story, FAKE_CLOCK + """
        sprint.start(25)
        require("sw.stats").skip_pasted({ "pasted words here that were not written" })
        add("pasted words here that were not written")           -- (what the paste put in the file)
        R.after_paste = sprint.words()
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "" })
        require("sw.stats").refresh()
        R.after_delete = sprint.words()
    """)
    assert r["after_paste"] == 0 and r["after_delete"] == 0


def test_the_time_running_out_ends_the_sprint_by_itself(home, story):
    r = run_lua(story, FAKE_CLOCK + """
        sprint.start(1)
        add("a few words typed here")
        tick(61)
        vim.wait(1500, function() return sprint.active == nil end, 50)     -- the real one-second timer fires and finds the time up
        R.ended = sprint.active == nil
        R.rec = sprint.last
    """)
    assert r["ended"] and r["rec"]["words"] == 5 and "early" not in r["rec"]


def test_the_menu_and_the_key_and_the_command(home, story):
    r = run_lua(story, FAKE_CLOCK + """
        R.label = sprint.menu_label()
        R.mapped = vim.fn.maparg(require("sw.story").setting("key_sprint", "<A-d>"), "i", false, true).desc
        vim.cmd("SWSprint 3 40")
        R.running = sprint.active and { sprint.active.minutes, sprint.active.target } or false
        R.label2 = sprint.menu_label()
        vim.cmd("SWSprint stop")
        R.stopped = sprint.active == nil
        R.items = vim.tbl_map(function(i) return i[1] end, require("sw.menu").items())
    """)
    assert r["label"] == "Start a writing sprint…" and r["mapped"] == "Writer: key_sprint"
    assert r["running"] == [3, 40] and r["label2"].startswith("Stop the writing sprint (sprint ")
    assert r["stopped"] and any("writing sprint" in i for i in r["items"])


def test_the_prompts_use_the_setting_for_the_default_length(home, story):
    settings.save_global({"sprint_minutes": 40})
    r = run_typed(story, "", "<Cmd>SWSprint<CR>15\r200\r", "R.s = require('sw.sprint').active and { require('sw.sprint').active.minutes, require('sw.sprint').active.target } or false")
    assert r["s"] == [15, 200]
    r = run_typed(story, "", "<Cmd>SWSprint<CR>\r\r", "R.s = require('sw.sprint').active and { require('sw.sprint').active.minutes, require('sw.sprint').active.target } or false")
    assert r["s"] == [40]                                                   # (Enter twice: the setting's length, no target)


def test_leaving_the_writer_ends_the_sprint_and_keeps_it(home, story):
    typed = ("<Cmd>lua require('sw.sprint').start(25)<CR>"
             "<Cmd>lua local b = vim.api.nvim_get_current_buf(); local n = vim.api.nvim_buf_line_count(b); "
             "vim.api.nvim_buf_set_lines(b, n, n, false, { '', 'six little words were written here' }); require('sw.stats').refresh(); "
             "TICK(180); require('sw').leave('builder')<CR>")
    run_typed(story, "local now = 1000; require('sw.sprint').clock = function() return now end; function TICK(n) now = now + n end", typed, "", quits=True)
    data = json.loads((story.path / "stats.json").read_text())
    assert len(data["sprints"]) == 1 and data["sprints"][0]["early"] is True and data["sprints"][0]["words"] == 6
