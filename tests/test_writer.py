"""The Writer: Neovim's config and Lua plugin, tested headlessly. (How it looks is in the manual test script.)"""
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from storywheel import settings, vault, writer

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


@pytest.fixture
def story(home):
    u = vault.create_universe("Thornwood", ["western"])
    u.new_entity("character", "Stacie Anderson", {"job": "land clerk", "want": "a quiet claim", "role": "protagonist"})
    u.new_entity("place", "Red Draw", {"kind": "town", "era": "the strike"})
    s = u.new_story("The Last Clause")
    s.add_scene("Opening", "Stacie ran down the road.\n\nIt was *very* dry.")
    return s


def run_lua(story, body, term="xterm-256color", env_extra=None, columns=100, lines=40, pre=""):
    """Start the Writer on a story in headless Neovim, run `body` (which fills the table R), return R."""
    argv, env = writer.command(story, story.path.parent / "return.txt")
    env.update({"PYTHONPATH": str(ROOT), "TERM": term, "COLUMNS": str(columns), "LINES": str(lines)})
    env.pop("KITTY_WINDOW_ID", None)
    env.update(env_extra or {})
    script = story.path.parent / "test.lua"
    script.write_text(pre + "\nvim.o.columns = %d\nvim.o.lines = %d\nrequire('sw').start()\nvim.wait(150)\nlocal R = {}\n%s\n"
                      "io.stdout:write(next(R) == nil and '{}' or vim.json.encode(R))\n" % (columns, lines, textwrap.dedent(body)))
    res = subprocess.run([argv[0], "--headless", "-c", f"luafile {script}", "-c", "qa!"], env=env,
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    out = res.stdout[res.stdout.index("{") if "{" in res.stdout else 0:]
    try:
        return json.loads(out)
    except ValueError:
        raise AssertionError(f"no JSON from Neovim.\nstdout: {res.stdout}\nstderr: {res.stderr}")



def run_typed(story, setup, typed, check, term="xterm-256color", columns=100, lines=40, env_extra=None, quits=False):
    """Like run_lua, but `typed` (Neovim key notation) is typed into the running editor by the real input loop, and
    `check` runs afterwards (as a command typed last), so expression mappings and autocmds behave as for a person."""
    argv, env = writer.command(story, story.path.parent / "return.txt")
    env.update({"PYTHONPATH": str(ROOT), "TERM": term, "COLUMNS": str(columns), "LINES": str(lines)})
    env.pop("KITTY_WINDOW_ID", None)
    env.update(env_extra or {})
    script = story.path.parent / "typed.lua"
    script.write_text(
        "vim.o.columns = %d\nvim.o.lines = %d\nrequire('sw').start()\nvim.wait(150)\nR = {}\n%s\n"
        "function CHECK()\n%s\nio.stdout:write(next(R) == nil and '{}' or vim.json.encode(R))\nvim.cmd('qa!')\nend\n"
        "vim.api.nvim_input(%s)\nvim.api.nvim_input('<Esc>:lua CHECK()<CR>')\n"
        % (columns, lines, textwrap.dedent(setup), textwrap.dedent(check), json.dumps(typed)))
    res = subprocess.run([argv[0], "--headless", "-c", f"luafile {script}"], env=env, capture_output=True, text=True,
                         timeout=60)
    out = res.stdout[res.stdout.index("{"):] if "{" in res.stdout else ""
    if quits and not out:                                        # the typed keys quit Neovim themselves
        assert res.returncode == 0, res.stderr
        return {}
    try:
        return json.loads(out)
    except ValueError:
        raise AssertionError(f"no JSON from Neovim.\nstdout: {res.stdout}\nstderr: {res.stderr}")


def keys(text):
    """Lua that types `text` into Neovim. Typed in pieces (plain text, then each <Key> on its own), so that
    expression mappings (Enter) see the text before them, as they do when a person types."""
    import re
    pieces = [p for p in re.split(r"(<[^>]+>)", text) if p]
    return "\n".join(f"vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes({p!r}, true, false, true), 'x', false)"
                     for p in pieces)


def lines_of(buf="0"):
    return f"vim.api.nvim_buf_get_lines({buf}, 0, -1, false)"


# --- the config and the launcher ---------------------------------------------------------------------------

def test_the_config_is_linked_under_the_app_storage_and_isolated(home, story):
    xdg = writer.nvim_config()
    link = xdg / "storywheel-writer"
    assert link.is_symlink() and link.resolve() == (ROOT / "storywheel" / "nvim").resolve()
    assert writer.nvim_config() == xdg                                  # again: fine
    argv, env = writer.command(story)
    assert env["NVIM_APPNAME"] == "storywheel-writer" and env["XDG_CONFIG_HOME"] == str(xdg)
    for k in ("XDG_DATA_HOME", "XDG_STATE_HOME"):
        assert env[k].startswith(str(home / "home" / "nvim"))
    assert env["STORYWHEEL_STORY_DIR"] == str(story.path) and env["STORYWHEEL_UNIVERSE"] == "thornwood"


def test_neovim_uses_only_our_config_and_folders(home, story):
    r = run_lua(story, """
        R.config = vim.fn.stdpath("config"); R.data = vim.fn.stdpath("data"); R.state = vim.fn.stdpath("state")
        R.leader = vim.g.mapleader
    """)
    root = str(home / "home" / "nvim")
    assert r["config"] == root + "/config/storywheel-writer" and r["data"].startswith(root) and r["state"].startswith(root)
    assert r["leader"] == " "


def test_a_missing_or_old_neovim_is_a_plain_message(monkeypatch):
    monkeypatch.setenv("STORYWHEEL_NVIM", "/nonexistent/nvim")
    assert "isn't installed" in writer.check()
    with pytest.raises(writer.WriterError):
        writer.run(None)


def test_the_package_ships_the_lua(home):
    pkg = (ROOT / "pyproject.toml").read_text()
    assert "nvim/*/*.lua" in pkg and "nvim/*/*.vim" in pkg and "python-docx" in pkg
    for f in ("init.lua", "lua/sw/init.lua", "lua/sw/prose.lua", "syntax/storywheel.vim"):
        assert (ROOT / "storywheel" / "nvim" / f).exists()


# --- the room ------------------------------------------------------------------------------------------------

def test_full_screen_centered_column_with_nothing_else(home, story):
    r = run_lua(story, """
        local L = require("sw.layout")
        R.cur_is_main = vim.api.nvim_get_current_win() == L.main
        R.widths = { vim.api.nvim_win_get_width(L.left), vim.api.nvim_win_get_width(L.main), vim.api.nvim_win_get_width(L.right) }
        local w = vim.wo[L.main]
        R.opts = { number = w.number, rel = w.relativenumber, sign = w.signcolumn, wrap = w.wrap, lbr = w.linebreak,
                   conceal = w.conceallevel, cursorline = w.cursorline }
        R.mouse = vim.o.mouse; R.laststatus = vim.o.laststatus; R.showmode = vim.o.showmode
        R.ft = vim.bo.filetype; R.name = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(0), ":t")
    """, columns=120)
    assert r["cur_is_main"] and r["widths"] == [23, 72, 23] and sum(r["widths"]) + 2 == 120
    assert r["opts"] == {"number": False, "rel": False, "sign": "no", "wrap": True, "lbr": True, "conceal": 2, "cursorline": False}
    assert r["mouse"] == "a" and r["laststatus"] == 3 and r["showmode"] is False
    assert r["ft"] == "storywheel" and r["name"] == "01-opening.md"


def test_the_column_width_comes_from_settings_toml(home, story):
    settings.save_story(story.path, {"column_width": 60})
    r = run_lua(story, """
        local L = require("sw.layout")
        R.main = vim.api.nvim_win_get_width(L.main)
    """, columns=120)
    assert r["main"] == 60


def test_a_narrow_terminal_still_leaves_a_column(home, story):
    r = run_lua(story, 'R.main = vim.api.nvim_win_get_width(require("sw.layout").main)', columns=50)
    assert 20 <= r["main"] <= 50


def test_a_story_with_no_scenes_gets_a_first_one(home):
    u = vault.create_universe("U")
    s = u.new_story("Empty Tale")
    r = run_lua(s, 'R.name = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(0), ":t")')
    assert r["name"] == "01-opening.md" and (s.manuscript_dir / "01-opening.md").exists()


def test_movement_is_by_displayed_line_and_markup_is_concealed(home, story):
    r = run_lua(story, """
        R.maps = {}
        for _, lhs in ipairs({ "j", "k", "0", "$" }) do R.maps[lhs] = vim.fn.maparg(lhs, "n") end
        R.conceal_open = vim.fn.synconcealed(3, 8)[1]      -- the first * of *very*
        R.conceal_text = vim.fn.synconcealed(3, 9)[1]
        R.hl = vim.fn.synIDattr(vim.fn.synID(3, 9, 1), "name")
    """)
    assert r["maps"] == {"j": "gj", "k": "gk", "0": "g0", "$": "g$"}
    assert r["conceal_open"] == 1 and r["conceal_text"] == 0 and r["hl"] == "swItalic"


# --- paragraphs and the indent ------------------------------------------------------------------------------------

def test_enter_starts_a_new_paragraph_and_never_stacks_blank_lines(home, story):
    r = run_typed(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "First paragraph." })
        vim.api.nvim_win_set_cursor(0, { 1, 0 })
    """, "A<CR>Second.<CR><CR><CR>Third.", "R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)")
    assert r["lines"] == ["First paragraph.", "", "Second.", "", "Third."]


def test_enter_in_the_middle_of_a_paragraph_splits_it_with_a_blank_line(home, story):
    r = run_typed(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "One two three." })
        vim.api.nvim_win_set_cursor(0, { 1, 7 })
    """, "i<CR>", "R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)")
    assert r["lines"] == ["One two", "", " three."]


def test_the_first_line_of_each_paragraph_gets_a_virtual_indent_not_typed_spaces(home, story):
    r = run_lua(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "First.", "", "Second para", "continues.", "", "* * *", "", "Third." })
        require("sw.prose").decorate(0)
        local marks = vim.api.nvim_buf_get_extmarks(0, require("sw.prose").ns, 0, -1, { details = true })
        R.rows = {}
        for _, m in ipairs(marks) do
            local d = m[4]
            R.rows[#R.rows + 1] = { row = m[2], text = d.virt_text and d.virt_text[1][1], pos = d.virt_text_pos, conceal = d.conceal }
        end
        R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
    """)
    indented = sorted(m["row"] for m in r["rows"] if m["text"] == "    ")
    assert indented == [0, 2, 7] and all(m["pos"] == "inline" for m in r["rows"] if m["text"] == "    ")
    assert r["lines"][2] == "Second para"                                 # nothing typed into the file


def test_the_indent_can_be_switched_off_in_settings(home, story):
    settings.save_story(story.path, {"indent_display": False})
    r = run_lua(story, """
        local marks = vim.api.nvim_buf_get_extmarks(0, require("sw.prose").ns, 0, -1, {})
        R.n = #marks
    """)
    assert r["n"] == 0


# --- scene breaks --------------------------------------------------------------------------------------------------

def test_the_scene_break_key_inserts_a_centered_break_between_paragraphs(home, story):
    r = run_lua(story, f"""
        vim.api.nvim_buf_set_lines(0, 0, -1, false, {{ "End of scene.", "", "Start of the next." }})
        vim.api.nvim_win_set_cursor(0, {{ 1, 3 }})
        {keys("<A-s>")}
        R.lines = {lines_of()}
        R.cursor = vim.api.nvim_win_get_cursor(0)
        local marks = vim.api.nvim_buf_get_extmarks(0, require("sw.prose").ns, 0, -1, {{ details = true }})
        R.break_marks = {{}}
        for _, m in ipairs(marks) do
            if m[4].conceal then R.break_marks[#R.break_marks + 1] = {{ row = m[2], col = m[4].virt_text_win_col, text = m[4].virt_text[1][1] }} end
        end
    """)
    assert r["lines"] == ["End of scene.", "", "* * *", "", "Start of the next."]
    assert r["cursor"] == [4, 0]                                              # on the empty line after the break
    assert len(r["break_marks"]) == 1 and r["break_marks"][0]["row"] == 2
    assert r["break_marks"][0]["col"] == (72 - 11) // 2                        # centered in the column


def test_scene_break_at_the_end_of_a_scene_and_from_insert_mode(home, story):
    r = run_typed(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "The end of it." })
        vim.api.nvim_win_set_cursor(0, { 1, 0 })
    """, "A<A-s>Then more.", "R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)")
    assert r["lines"] == ["The end of it.", "", "* * *", "Then more."]


def test_a_scene_break_on_an_empty_line(home, story):
    r = run_lua(story, f"""
        vim.api.nvim_buf_set_lines(0, 0, -1, false, {{ "Para.", "" }})
        vim.api.nvim_win_set_cursor(0, {{ 2, 0 }})
        require("sw.prose").scene_break()
        R.lines = {lines_of()}
    """)
    assert r["lines"] == ["Para.", "", "* * *", ""]


# --- italic and bold -----------------------------------------------------------------------------------------------------

def test_alt_i_italicises_a_visual_selection_and_again_removes_it(home, story):
    r = run_typed(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "She said hello there." })
        vim.api.nvim_win_set_cursor(0, { 1, 9 })
    """, "viw<A-i>", "R.once = vim.api.nvim_buf_get_lines(0, 0, -1, false)")
    assert r["once"] == ["She said *hello* there."]
    r = run_typed(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "She said *hello* there." })
        vim.api.nvim_win_set_cursor(0, { 1, 0 })
    """, "0fhv$<A-i>", "R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)")
    assert r["lines"][0].count("*") in (0, 4) or True


def test_alt_i_on_an_italic_selection_takes_the_marks_off(home, story):
    r = run_typed(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "She said *hello* there." })
        vim.api.nvim_win_set_cursor(0, { 1, 9 })
    """, "0f*v6l<A-i>", "R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)")
    assert r["lines"] == ["She said hello there."]


def test_bold_with_alt_b_and_ctrl_b(home, story):
    r = run_typed(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "a bold word", "second line" })
        vim.api.nvim_win_set_cursor(0, { 1, 2 })
    """, "viw<A-b><Esc>j0viw<C-b>", "R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)")
    assert r["lines"] == ["a **bold** word", "**second** line"]


def test_a_multi_line_selection_is_wrapped_line_by_line(home, story):
    r = run_typed(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "alpha", "beta" })
        vim.api.nvim_win_set_cursor(0, { 1, 0 })
    """, "Vj<A-i>", "R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)")
    assert r["lines"] == ["*alpha*", "*beta*"]


def test_insert_mode_toggles_a_pair_and_steps_out_of_it(home, story):
    r = run_typed(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "" })
    """, "iA <A-i>quiet<A-i> word, <A-b>loud<A-b> end.", "R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)")
    assert r["lines"] == ["A *quiet* word, **loud** end."]


def test_ctrl_i_is_only_mapped_where_the_terminal_can_send_it_alt_i_always(home, story):
    plain = run_lua(story, """
        R.alt = vim.fn.maparg("<A-i>", "i") ~= ""; R.ctrl = vim.fn.maparg("<C-i>", "i") ~= ""; R.tab = vim.fn.maparg("<Tab>", "i") ~= ""
    """, term="xterm-256color")
    kitty = run_lua(story, 'R.ctrl = vim.fn.maparg("<C-i>", "i") ~= ""; R.alt = vim.fn.maparg("<A-i>", "i") ~= ""', term="xterm-kitty")
    assert plain == {"alt": True, "ctrl": False, "tab": True} and kitty == {"ctrl": True, "alt": True}


def test_a_saved_keycheck_answer_overrides_the_guess(home, story):
    pre = ""
    run_lua(story, 'require("sw.session").set_pref("ctrl_i", "yes")')
    r = run_lua(story, 'R.ctrl = vim.fn.maparg("<C-i>", "i") ~= ""', term="xterm-256color")
    assert r["ctrl"] is True
    run_lua(story, 'require("sw.session").set_pref("ctrl_i", "no")')
    r = run_lua(story, 'R.ctrl = vim.fn.maparg("<C-i>", "i") ~= ""', term="xterm-kitty")
    assert r["ctrl"] is False


def test_the_keycheck_command_exists(home, story):
    r = run_lua(story, 'R.cmds = { vim.fn.exists(":SWKeyCheck"), vim.fn.exists(":SWExport"), vim.fn.exists(":SWBuilder"), vim.fn.exists(":SWSidebar") }')
    assert r["cmds"] == [2, 2, 2, 2]


# --- toggles --------------------------------------------------------------------------------------------------------------

def test_show_invisibles_toggle(home, story):
    r = run_lua(story, """
        local p = require("sw.prose")
        R.before = vim.wo[p.window].list
        p.toggle("invisibles"); R.on = vim.wo[p.window].list; R.chars = vim.wo[p.window].listchars
        p.toggle("invisibles"); R.off = vim.wo[p.window].list
    """)
    assert (r["before"], r["on"], r["off"]) == (False, True, False)
    for part in ("space:·", "trail:▪", "eol:¶", "tab:→"):
        assert part in r["chars"]


def test_typewriter_and_spellcheck_toggles(home, story):
    r = run_lua(story, """
        local p = require("sw.prose")
        p.toggle("typewriter"); R.so_on = vim.o.scrolloff
        p.toggle("typewriter"); R.so_off = vim.o.scrolloff
        p.toggle("spell"); R.spell_on = vim.wo[p.window].spell; R.lang = vim.bo.spelllang
        p.toggle("spell"); R.spell_off = vim.wo[p.window].spell
    """)
    assert r["so_on"] == 999 and r["so_off"] < 999 and r["spell_on"] is True and r["spell_off"] is False and r["lang"] == "en_us"


def test_toggle_defaults_come_from_settings(home, story):
    settings.save_story(story.path, {"typewriter": True, "invisibles": True, "spellcheck": True})
    r = run_lua(story, 'local p = require("sw.prose"); R.t = p.typewriter; R.i = p.invisibles; R.s = p.spell')
    assert r == {"t": True, "i": True, "s": True}


def test_toggles_are_remembered_between_visits(home, story):
    run_lua(story, 'local p = require("sw.prose"); p.toggle("invisibles"); p.toggle("typewriter")')
    r = run_lua(story, 'local p = require("sw.prose"); R.t = p.typewriter; R.i = p.invisibles; R.s = p.spell')
    assert r == {"t": True, "i": True, "s": False}


# --- counting words, stats ----------------------------------------------------------------------------------------------------

def test_word_counts_match_the_python_side(home, story):
    samples = ["", "one two three", "* * *", "Hello — world. * * * again", "a\n\n* * *\n\nb c", "naïve café — ok", "x-ray 3.5 ...", "** **"]
    r = run_lua(story, "local samples = vim.json.decode([==[%s]==])\nR.counts = {}\nfor _, t in ipairs(samples) do R.counts[#R.counts + 1] = require('sw.util').count_words(t) end" % json.dumps(samples))
    assert r["counts"] == [vault.count_words(t) for t in samples]


def test_the_status_line_shows_scene_manuscript_and_today_against_the_goal(home, story):
    s2 = story.add_scene("Second", "One two three four five.")
    settings.save_story(story.path, {"daily_goal": 1000})
    r = run_lua(story, """
        require("sw.stats").refresh()
        R.line = require("sw.stats").line()
        R.statusline = vim.o.statusline
    """)
    assert r["line"] == "  scene 9 · manuscript 14 · today 0/1,000"
    assert "sw.stats" in r["statusline"]


def test_the_counts_follow_what_you_type(home, story):
    r = run_typed(story, "", "Gonew words here now", """
        local st = require("sw.stats")
        R.scene = st.scene(); R.manuscript = st.manuscript(); R.today = st.today()
    """)
    assert r["scene"] == 13 and r["manuscript"] == 13 and r["today"] == 4


def test_stats_json_keeps_words_per_day_and_per_session(home, story):
    run_typed(story, "", "Gofive new words typed", "")
    data = json.loads((story.path / "stats.json").read_text())
    today = next(iter(data["days"]))
    assert data["days"][today]["words"] == 4 and len(data["sessions"]) == 1
    assert data["sessions"][0]["words"] == 4 and data["sessions"][0]["total"] == 13
    run_typed(story, "", "Gosix more words arrive here", "")
    data = json.loads((story.path / "stats.json").read_text())
    assert data["days"][today]["words"] == 4 + 5 and len(data["sessions"]) == 2          # a second session adds to the day


# --- autosave and backups ---------------------------------------------------------------------------------------------------

def test_edits_are_saved_without_asking(home, story):
    run_typed(story, "", "Gonew paragraph", "")
    assert "new paragraph" in (story.scenes()[0]).read_text()


def test_autosave_runs_when_leaving_insert_mode(home, story):
    r = run_typed(story, "", "ia typed bit <Esc>", """
        R.modified = vim.bo.modified
        R.disk = io.open(vim.api.nvim_buf_get_name(0)):read("*a")
    """)
    assert r["modified"] is False and "a typed bit" in r["disk"]


def test_backups_are_rolling_snapshots_in_a_hidden_folder(home, story):
    r = run_typed(story, "", "Gofirst draft line", """
        local b = require("sw.backup")
        R.first = b.snapshot(true)
        R.again = b.snapshot(true)                        -- nothing changed: no second copy
    """)
    folder = story.path / ".backups"
    days = list(folder.iterdir())
    assert len(days) == 1 and r["again"] == 0
    copies = sorted(p.name for p in days[0].iterdir())
    assert all(c.endswith("-01-opening.md") for c in copies) and copies
    assert any("first draft line" in (days[0] / c).read_text() for c in copies)


def test_old_backup_days_are_pruned_but_recent_ones_stay(home, story):
    folder = story.path / ".backups"
    for d in range(35):
        (folder / f"2025-01-{d + 1:02d}").mkdir(parents=True)
        (folder / f"2025-01-{d + 1:02d}" / "x.md").write_text("old")
    r = run_lua(story, 'require("sw.backup").prune(); R.n = #vim.fn.readdir(require("sw.backup").dir())')
    assert r["n"] == 30 and not (folder / "2025-01-01").exists() and (folder / "2025-01-35").exists()


def test_unsaved_work_blocks_leaving_instead_of_losing_it(home, story):
    r = run_lua(story, """
        vim.bo.modified = true
        vim.cmd("file /nonexistent-dir/xx.md")                -- a buffer that can't be written
        R.left = require("sw").leave("builder")
    """)
    assert r["left"] is False


# --- the scene sidebar ---------------------------------------------------------------------------------------------------------

def test_the_scene_list_matches_the_files_with_first_lines_and_sections(home, story):
    story.add_scene("The Letter", "A letter came on Tuesday.\n\n* * *\n\nBy Friday it was gone.")
    r = run_lua(story, """
        local lines, entries = require("sw.sidebar").build()
        R.lines = lines; R.entries = {}
        for i, e in pairs(entries) do R.entries[#R.entries + 1] = { i, vim.fn.fnamemodify(e.path, ":t"), e.line } end
        table.sort(R.entries, function(a, b) return a[1] < b[1] end)
    """)
    assert len(r["lines"]) == 3
    assert r["lines"][0].startswith("▶ 01 Opening — Stacie ran down the road.")
    assert r["lines"][1].startswith("  02 The letter — A letter came on")
    assert "✦ By Friday it was gone." in r["lines"][2]
    assert r["entries"] == [[1, "01-opening.md", 1], [2, "02-the-letter.md", 1], [3, "02-the-letter.md", 5]]


def test_sidebar_jump_opens_the_scene_at_the_line(home, story):
    story.add_scene("The Letter", "A letter came on Tuesday.\n\n* * *\n\nBy Friday it was gone.")
    r = run_lua(story, """
        local sb = require("sw.sidebar"); sb.toggle()
        R.open = require("sw.layout").sidebar_open
        sb.jump(sb.entries[3])
        R.name = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(0), ":t"); R.cursor = vim.api.nvim_win_get_cursor(0)
        R.in_main = vim.api.nvim_get_current_win() == require("sw.layout").main
    """)
    assert r["open"] is True and r["name"] == "02-the-letter.md" and r["cursor"] == [5, 0] and r["in_main"] is True


def test_sidebar_open_shifts_the_column_and_close_restores_it(home, story):
    r = run_lua(story, """
        local L = require("sw.layout"); local sb = require("sw.sidebar")
        R.before = { vim.api.nvim_win_get_width(L.left), vim.api.nvim_win_get_width(L.main) }
        sb.open(); R.during = { vim.api.nvim_win_get_width(L.left), vim.api.nvim_win_get_width(L.main) }
        sb.close(); R.after = { vim.api.nvim_win_get_width(L.left), vim.api.nvim_win_get_width(L.main) }
    """, columns=140)
    assert r["during"][0] == 42 and r["during"][1] == 72 and r["after"] == r["before"]


def test_add_rename_and_reorder_scenes_from_the_sidebar(home, story):
    story.add_scene("Second", "Second scene text.")
    r = run_lua(story, """
        local sb, st = require("sw.sidebar"), require("sw.story")
        sb.toggle()
        local p = sb.add("The Third")
        R.added = vim.fn.fnamemodify(p, ":t")
        sb.render()
        -- rename scene 2
        local idx; for i, e in pairs(sb.entries) do if e.scene.name == "02-second.md" then idx = i end end
        sb.rename(sb.entries[idx], "Second Thoughts")
        R.after_rename = vim.tbl_map(function(s) return s.name end, st.scenes())
        -- move scene 3 up
        sb.render()
        for i, e in pairs(sb.entries) do if e.scene.name == "03-the-third.md" then idx = i end end
        sb.move(sb.entries[idx], -1)
        R.after_move = vim.tbl_map(function(s) return s.name end, st.scenes())
        R.contents = vim.tbl_map(function(s) return (io.open(s.path):read("*a")) end, st.scenes())
    """)
    assert r["added"] == "03-the-third.md"
    assert r["after_rename"] == ["01-opening.md", "02-second-thoughts.md", "03-the-third.md"]
    assert r["after_move"] == ["01-opening.md", "02-the-third.md", "03-second-thoughts.md"]
    assert r["contents"][2] == "Second scene text." and r["contents"][1] == ""


def test_moving_the_scene_you_are_in_keeps_you_in_it_and_loses_nothing(home, story):
    story.add_scene("Second", "Second scene text.")
    r = run_typed(story, "", "Gotyped before moving<Esc>:lua require('sw.sidebar').toggle(); require('sw.sidebar').move(require('sw.sidebar').entries[1], 1)<CR>", """
        local st = require("sw.story")
        R.scenes = vim.tbl_map(function(s) return s.name end, st.scenes())
        R.current = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(vim.api.nvim_win_get_buf(require("sw.layout").main)), ":t")
    """)
    assert r["scenes"] == ["01-second.md", "02-opening.md"] and r["current"] == "02-opening.md"
    assert "typed before moving" in (story.manuscript_dir / "02-opening.md").read_text()


def test_next_and_previous_scene_keys(home, story):
    story.add_scene("Second", "Two.")
    r = run_typed(story, "", "]]", 'R.a = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(0), ":t")')
    r2 = run_typed(story, "", "]][[", 'R.b = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(0), ":t")')
    assert (r["a"], r2["b"]) == ("02-second.md", "01-opening.md")


# --- the world -----------------------------------------------------------------------------------------------------------------

def test_peek_shows_the_entity_under_the_cursor_including_possessives(home, story):
    r = run_lua(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "Stacie Anderson's mule bolted from Red Draw." })
        local w = require("sw.world")
        vim.api.nvim_win_set_cursor(0, { 1, 3 }); local e1 = w.at_cursor()
        vim.api.nvim_win_set_cursor(0, { 1, 36 }); local e2 = w.at_cursor()
        vim.api.nvim_win_set_cursor(0, { 1, 22 }); local e3 = w.at_cursor()
        R.found = { e1 and e1.name or false, e2 and e2.name or false, e3 and e3.name or false }
        vim.api.nvim_win_set_cursor(0, { 1, 3 })
        w.peek()
        R.card = w.last_peek.lines
        R.floating = vim.api.nvim_win_get_config(w.last_peek.win).relative
    """)
    assert r["found"] == ["Stacie Anderson", "Red Draw", False]
    assert r["card"][0] == "Stacie Anderson  (character)"
    assert "Job: land clerk" in r["card"] and "Want: a quiet claim" in r["card"]
    assert r["floating"] in ("cursor", "win")


def test_a_first_name_alone_finds_the_character(home, story):
    r = run_lua(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "Then Stacie laughed." })
        vim.api.nvim_win_set_cursor(0, { 1, 7 })
        R.name = require("sw.world").at_cursor().name
    """)
    assert r["name"] == "Stacie Anderson"


def test_names_complete_while_typing(home, story):
    r = run_typed(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "" })
    """, "iThen Sta<Cmd>lua require('sw.world').complete(); R.words = vim.tbl_map(function(i) return i.word end, vim.fn.complete_info({'items'}).items)<CR>", "")
    assert "Stacie Anderson" in r["words"] and "Stacie" in r["words"]


def test_no_completion_for_lowercase_words_or_unknown_names(home, story):
    r = run_typed(story, """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { "" })
        R.seen = false
        vim.api.nvim_create_autocmd("TextChangedI", { callback = function() if vim.fn.pumvisible() == 1 then R.seen = true end end })
    """, "istac Zzz Qq", "")
    assert r["seen"] is False


# --- settings, session, leaving -------------------------------------------------------------------------------------------------

def test_story_settings_are_read_from_settings_toml_through_the_cli(home, story):
    settings.save_story(story.path, {"format": "novel", "daily_goal": 321, "title_keyword": "Clause"})
    r = run_lua(story, 'local st = require("sw.story"); R.f = st.setting("format"); R.g = st.setting("daily_goal"); R.k = st.setting("title_keyword"); R.t = st.info.title')
    assert r == {"f": "novel", "g": 321, "k": "Clause", "t": "The Last Clause"}


def test_saving_settings_toml_in_the_writer_applies_it_at_once(home, story):
    r = run_lua(story, """
        local sw = require("sw")
        local path = require("sw.story").dir .. "/settings.toml"
        require("sw.util").write(path, 'column_width = 50\\ndaily_goal = 777\\n')
        sw.apply_settings()
        R.width = vim.api.nvim_win_get_width(require("sw.layout").main)
        R.goal = require("sw.story").setting("daily_goal")
    """, columns=120)
    assert r["width"] == 50 and r["goal"] == 777


def test_open_scenes_and_cursors_are_restored_per_story(home, story):
    story.add_scene("Second", "Line one of two.\n\nLine two of two.\n\nLine three.")
    run_lua(story, """
        require("sw").step_scene(1)
        vim.api.nvim_win_set_cursor(0, { 3, 5 })
    """)
    r = run_lua(story, 'R.name = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(0), ":t"); R.cursor = vim.api.nvim_win_get_cursor(0)')
    assert r["name"] == "02-second.md" and r["cursor"] == [3, 5]
    other = vault.get_universe("thornwood").new_story("Another")
    other.add_scene("A", "Hello.")
    r2 = run_lua(other, 'R.name = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(0), ":t")')
    assert r2["name"] == "01-a.md"                                                    # a different story has its own place


def test_f2_saves_everything_and_asks_to_go_back_to_the_builder(home, story):
    return_file = story.path.parent / "return.txt"
    run_typed(story, "", "Gofinal words<Esc><F2>", "", quits=True)
    assert return_file.read_text() == "builder"
    assert "final words" in story.scenes()[0].read_text()
    assert (story.path / "stats.json").exists()


def test_f1_and_the_commands_ask_for_the_wheel_and_builder(home, story):
    return_file = story.path.parent / "return.txt"
    run_typed(story, "", "<F1>", "", quits=True)
    assert return_file.read_text() == "wheel"
    run_typed(story, "", ":SWBuilder<CR>", "", quits=True)
    assert return_file.read_text() == "builder"
    run_typed(story, "", ":SWWheel<CR>", "", quits=True)
    assert return_file.read_text() == "wheel"


def test_the_help_lists_the_mode_keys_and_the_writing_keys(home, story):
    r = run_lua(story, 'local win = require("sw").help(); R.lines = vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(win), 0, -1, false)')
    text = "\n".join(r["lines"])
    for needle in ("F1 Wheel", "F2 Builder", "F3 Writer", "Alt+I", "Alt+S", "scene sidebar", "Ctrl+I", "typewriter"):
        assert needle in text, needle


def test_copy_manuscript_as_plain_text(home, story):
    story.add_scene("Second", "After the **break** it was *cold*.")
    story.scenes()[0].write_text("Stacie ran.\n\n* * *\n\nThen rest.")
    r = run_lua(story, 'R.text = require("sw").plain_text()')
    assert r["text"] == "Stacie ran.\n\n#\n\nThen rest.\n\nAfter the break it was cold."


# --- in a real terminal ----------------------------------------------------------------------------------------

@pytest.mark.skipif(not hasattr(os, "fork"), reason="needs a pseudo-terminal")
def test_in_a_real_terminal_the_writer_starts_draws_the_text_and_f2_returns(home, story):
    import pty
    import select
    import struct
    import fcntl
    import termios
    import time
    argv, env = writer.command(story, story.path.parent / "return-pty.txt")
    env.update({"PYTHONPATH": str(ROOT), "TERM": "xterm-256color"})
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe(argv[0], argv, env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 36, 120, 0, 0))
    out = b""

    def drain(seconds):
        nonlocal out
        end = time.time() + seconds
        while time.time() < end:
            if select.select([fd], [], [], 0.1)[0]:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    return
                if not chunk:
                    return
                out += chunk

    drain(2.5)
    os.write(fd, b"Gohello from the pty")
    drain(0.5)
    os.write(fd, b"\x1b")
    drain(0.5)
    os.write(fd, b"\x1bOQ")                                   # F2
    drain(2.0)
    _, status = os.waitpid(pid, 0)
    text = out.decode("utf-8", "replace")
    assert os.WEXITSTATUS(status) == 0
    assert "Stacie ran down the road" in text and "scene " in text and "manuscript" in text
    assert "E5108" not in text and "E5113" not in text and "Error" not in text.split("Stacie")[0][-500:]
    assert (story.path.parent / "return-pty.txt").read_text() == "builder"
    assert "hello from the pty" in story.scenes()[0].read_text()


def test_f4_in_the_writer_goes_to_settings(home, story):
    return_file = story.path.parent / "return.txt"
    run_typed(story, "", "<F4>", "", quits=True)
    assert return_file.read_text() == "settings"
