"""Batch 24 B2: a screenplay's scenes in the sidebar: synopses shown dimmed under their headings, and scenes moved up or down with their
whole block in one undo step (headless Neovim)."""
import pytest

from storywheel import fountain, vault, writer
from test_notepad import AT, LINES, run

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")

SCRIPT = """Title: Rooms
Credit: Written by

FADE IN:

# Act One

= The act in a line.

INT. ATTIC - NIGHT

= Mara finds the lamp.

Dust hangs in the lamplight.

MARA
(whispering)
Hello?

INT. CELLAR - DAY

Damp walls.

BRAM
Who's there?

# Act Two

= Act two begins.

EXT. LANE - DAY

= Rain on the lane.

Rain.
"""

ATTIC = ["INT. ATTIC - NIGHT", "", "= Mara finds the lamp.", "", "Dust hangs in the lamplight.", "", "MARA", "(whispering)", "Hello?", ""]
CELLAR = ["INT. CELLAR - DAY", "", "Damp walls.", "", "BRAM", "Who's there?", ""]
LANE = ["EXT. LANE - DAY", "", "= Rain on the lane.", "", "Rain."]


@pytest.fixture
def script_story(home):
    u = vault.create_universe("Thornwood", ["horror"])
    s = u.new_story("Rooms", {"structure": "Short Film"})
    s.script_path.parent.mkdir(parents=True, exist_ok=True)
    s.script_path.write_text(SCRIPT, encoding="utf-8")
    return s


def heading_rows(lines):
    return [l for l in lines if l.startswith(("INT.", "EXT."))]


def test_the_python_reader_gives_a_synopsis_to_its_scene_not_to_the_section():
    scenes = fountain.scenes(SCRIPT)
    assert [(s["title"], s["synopsis"]) for s in scenes] == [("INT. ATTIC - NIGHT", "Mara finds the lamp."), ("INT. CELLAR - DAY", ""),
                                                             ("EXT. LANE - DAY", "Rain on the lane.")]


def test_the_sidebar_shows_each_synopsis_dimmed_under_its_heading(home, script_story):
    r = run(script_story, "", "", """
      local sb = require('sw.sidebar'); sb.open()
      R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
      R.dim = {}
      for i in pairs(sb.dim) do R.dim[#R.dim + 1] = i end
      table.sort(R.dim)
      local marks = vim.api.nvim_buf_get_extmarks(0, sb.ns, 0, -1, { details = true })
      R.groups = {}
      for _, m in ipairs(marks) do R.groups[#R.groups + 1] = m[4].hl_group end
      sb.jump(sb.entries[R.dim[1]])
      R.row = vim.api.nvim_win_get_cursor(0)[1]
    """)
    lines = r["lines"]
    at = next(i for i, l in enumerate(lines) if "INT. ATTIC" in l)
    assert lines[at + 1].strip() == "= Mara finds the lamp." and not any("The act in a line" in l or "Act two begins" in l for l in lines)
    assert len(r["dim"]) == 2 and r["dim"][0] == at + 2 and set(r["groups"]) == {"Comment"}
    assert r["row"] == SCRIPT.split("\n").index("INT. ATTIC - NIGHT") + 1 + 2          # (a synopsis line opens its scene, like the heading)


def test_a_scene_moves_down_with_its_whole_block_and_the_sections_stay_put(home, script_story):
    r = run(script_story, "", "", """
      local sb = require('sw.sidebar'); sb.open()
      local sc = require('sw.story').scene_list()[1]
      R.ok = sb.move(sc, 1)
      R.lines = vim.api.nvim_buf_get_lines(vim.fn.bufnr(require('sw.story').files()[1].path), 0, -1, false)
    """)
    assert r["ok"]
    lines = r["lines"]
    assert heading_rows(lines) == ["INT. CELLAR - DAY", "INT. ATTIC - NIGHT", "EXT. LANE - DAY"]
    assert lines.index("# Act One") < lines.index("INT. CELLAR - DAY") < lines.index("INT. ATTIC - NIGHT") < lines.index("# Act Two") < lines.index("EXT. LANE - DAY")
    assert lines[lines.index("INT. CELLAR - DAY"):lines.index("# Act Two")] == CELLAR + ATTIC
    saved = script_story.script_path.read_text(encoding="utf-8").split("\n")
    assert [l for l in saved if l.strip()] == [l for l in lines if l.strip()]
    assert sorted(l for l in saved if l.strip()) == sorted(l for l in SCRIPT.split("\n") if l.strip())


def test_a_scene_moves_up_over_a_section_and_the_last_scene_keeps_the_end_of_the_file(home, script_story):
    r = run(script_story, "", "", """
      local sb = require('sw.sidebar'); sb.open()
      local sc = require('sw.story').scene_list()[3]
      R.ok = sb.move(sc, -1)
      R.lines = vim.api.nvim_buf_get_lines(vim.fn.bufnr(require('sw.story').files()[1].path), 0, -1, false)
    """)
    lines = r["lines"]
    assert r["ok"] and heading_rows(lines) == ["INT. ATTIC - NIGHT", "EXT. LANE - DAY", "INT. CELLAR - DAY"]
    assert lines.index("# Act One") < lines.index("INT. ATTIC - NIGHT") < lines.index("EXT. LANE - DAY") < lines.index("# Act Two")
    assert lines.index("# Act Two") < lines.index("INT. CELLAR - DAY")
    assert lines[-2:] == ["BRAM", "Who's there?"] or lines[-3:-1] == ["BRAM", "Who's there?"]


def test_one_undo_puts_the_scenes_back_and_the_cursor_follows_its_text(home, script_story):
    r = run(script_story, "", "", """
      local sb = require('sw.sidebar')
      local story = require('sw.story')
      local path = story.files()[1].path
      local buf = vim.fn.bufnr(path)
      local before = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
      local row
      for i, l in ipairs(before) do if l == 'Damp walls.' then row = i end end
      vim.api.nvim_win_set_cursor(0, { row, 2 })
      R.ok = sb.move_here(-1)
      R.text = vim.api.nvim_get_current_line()
      R.cursor = vim.api.nvim_win_get_cursor(0)
      R.moved = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
      vim.api.nvim_buf_call(buf, function() vim.cmd('silent undo') end)
      R.same = vim.deep_equal(before, vim.api.nvim_buf_get_lines(buf, 0, -1, false))
    """)
    assert r["ok"] and r["text"] == "Damp walls." and r["cursor"][0] == r["moved"].index("Damp walls.") + 1 and r["cursor"][1] == 2
    assert heading_rows(r["moved"])[:2] == ["INT. CELLAR - DAY", "INT. ATTIC - NIGHT"]
    assert r["same"] is True


def test_the_first_and_last_scene_cannot_go_further_and_nothing_changes(home, script_story):
    r = run(script_story, "", "", """
      local sb = require('sw.sidebar')
      local scenes = require('sw.story').scene_list()
      R.up = sb.move(scenes[1], -1)
      R.down = sb.move(scenes[3], 1)
      R.msg = vim.fn.execute('messages')
    """)
    assert r["up"] is False and r["down"] is False and "first scene" in r["msg"] and "last scene" in r["msg"]
    assert script_story.script_path.read_text(encoding="utf-8") == SCRIPT


def test_the_menu_has_the_move_items_for_a_script_only(home, script_story):
    r = run(script_story, "", "", "local t = {} for _, it in ipairs(require('sw.menu').items()) do t[#t + 1] = it[1] end R.menu = table.concat(t, '|')")
    assert "Move this scene up" in r["menu"] and "Move this scene down" in r["menu"]
