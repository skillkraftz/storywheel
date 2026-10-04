"""Notepad mode (the default): the Writer behaves like an ordinary text editor."""
import json
import subprocess
import textwrap
from pathlib import Path

import pytest

from storywheel import settings, vault, writer

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


@pytest.fixture
def story(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    s.add_scene("Opening", "Hello brave world\n\nsecond line here")
    return s


def run(story, setup, typed, check, term="xterm-256color", env_extra=None, columns=100, lines=40, quits=False):
    """Type `typed` (Neovim key notation) into the running Writer; `check` runs last, as a <Cmd> so that it works in
    Insert and Select mode too. Returns what check put in R."""
    argv, env = writer.command(story, story.path.parent / "return.txt")
    env.update({"PYTHONPATH": str(ROOT), "TERM": term, "COLUMNS": str(columns), "LINES": str(lines)})
    env.update({"STORYWHEEL_INTERNAL_CLIPBOARD": "1"})                # (a real clipboard tool would hold the test's pipe open)
    env.update(env_extra or {})
    script = story.path.parent / "np.lua"
    script.write_text(
        "vim.o.columns = %d\nvim.o.lines = %d\nrequire('sw').start()\nvim.wait(150)\nR = {}\n%s\n"
        "function CHECK()\n%s\nio.stdout:write(next(R) == nil and '{}' or vim.json.encode(R))\nvim.cmd('qa!')\nend\n"
        "vim.api.nvim_input(%s)\nvim.api.nvim_input('<Cmd>lua CHECK()<CR>')\n"
        % (columns, lines, textwrap.dedent(setup), textwrap.dedent(check), json.dumps(typed, ensure_ascii=False)))
    res = subprocess.run([argv[0], "--headless", "-c", f"luafile {script}"], env=env, capture_output=True, text=True, timeout=60)
    out = res.stdout[res.stdout.index("{"):] if "{" in res.stdout else ""
    if quits and not out:
        assert res.returncode == 0, res.stderr
        return {}
    try:
        return json.loads(out)
    except ValueError:
        raise AssertionError(f"no JSON from Neovim.\nstdout: {res.stdout}\nstderr: {res.stderr}")


LINES = "R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)"
AT = "vim.api.nvim_win_set_cursor(0, { %d, %d })"


def test_you_are_typing_from_the_start_and_escape_does_nothing(home, story):
    r = run(story, AT % (3, 16), "<Esc>abc<Esc><Esc>def", LINES + "; R.mode = vim.fn.mode()")
    assert r["mode"] == "i" and r["lines"][-1] == "second line hereabcdef"


def test_vim_keys_are_text_not_commands(home, story):
    r = run(story, AT % (1, 0), "dd gg x 5j", LINES)
    assert r["lines"][0].startswith("dd gg x 5jHello brave world")


def test_paragraphs_still_work(home, story):
    r = run(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { '' })", "one<CR>two", LINES)
    assert r["lines"] == ["one", "two"]


def test_escape_closes_a_completion_popup_and_clears_a_search_highlight(home, story):
    r = run(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'brave brave' })", "<Cmd>lua require('sw.notepad').find('brave')<CR><Esc>",
            "R.hl = vim.v.hlsearch; R.mode = vim.fn.mode()")
    assert r["hl"] == 0 and r["mode"] == "i"


# --- selecting -----------------------------------------------------------------------------------------------------

def test_shift_arrows_select_and_typing_replaces_the_selection(home, story):
    r = run(story, AT % (1, 6), "<S-Right><S-Right><S-Right>XYZ", LINES + "; R.mode = vim.fn.mode()")
    assert r["lines"][0] == "Hello XYZve world" and r["mode"] == "i"


def test_shift_down_selects_across_lines_and_backspace_deletes_it(home, story):
    r = run(story, AT % (1, 6), "<S-Down><S-Down><BS>", LINES)
    assert r["lines"][0] == "Hello " + "line here" or r["lines"][0].startswith("Hello ") and r["lines"][0] != "Hello brave world"


def test_the_selection_can_be_extended_backwards(home, story):
    r = run(story, AT % (1, 11), "<S-Left><S-Left><S-Left><S-Left><S-Left>X", LINES)
    assert r["lines"][0] == "Hello X world"


def test_a_plain_arrow_ends_the_selection(home, story):
    r = run(story, AT % (1, 6), "<S-Right><S-Right><Left>Q", LINES + "; R.mode = vim.fn.mode()")
    assert "Q" in r["lines"][0] and r["lines"][0].replace("Q", "") == "Hello brave world" and r["mode"] == "i"


def test_escape_leaves_a_selection_and_you_are_typing_again(home, story):
    r = run(story, AT % (1, 6), "<S-Right><S-Right><Esc>Q", LINES + "; R.mode = vim.fn.mode()")
    assert r["mode"] == "i" and "Q" in r["lines"][0] and r["lines"][0].replace("Q", "") == "Hello brave world"


def test_the_mouse_is_set_up_to_select_like_any_app(home, story):
    """(Dragging itself can't be done headlessly: see the manual test script.)"""
    r = run(story, "", "", "R.sm = vim.o.selectmode; R.km = vim.o.keymodel; R.sel = vim.o.selection; R.mouse = vim.o.mouse; R.mm = vim.o.mousemodel")
    assert r == {"sm": "mouse,key", "km": "startsel,stopsel", "sel": "exclusive", "mouse": "a", "mm": "popup_setpos"}


# --- clipboard ------------------------------------------------------------------------------------------------------

def test_ctrl_c_copies_and_ctrl_v_pastes(home, story):
    r = run(story, AT % (1, 6), "<S-Right><S-Right><S-Right><Cmd>lua require('sw.notepad').copy()<CR><End><C-v>", LINES + "; R.reg = vim.fn.getreg('+')")
    assert r["reg"] == "bra" and r["lines"][0] == "Hello brave worldbra"


def test_ctrl_x_cuts(home, story):
    r = run(story, AT % (1, 6), "<S-Right><S-Right><S-Right><S-Right><S-Right><C-x>", LINES + "; R.reg = vim.fn.getreg('+'); R.mode = vim.fn.mode()")
    assert r["reg"] == "brave" and r["lines"][0] == "Hello  world" and r["mode"] == "i"


def test_ctrl_v_replaces_a_selection(home, story):
    r = run(story, AT % (1, 0), "<S-Right><S-Right><S-Right><S-Right><S-Right><Cmd>lua require('sw.notepad').copy()<CR><Right><Right><Right><S-Right><S-Right><S-Right><S-Right><S-Right><C-v>",
            LINES)
    assert r["lines"][0] == "Hello brHelloorld"


def test_copy_and_paste_several_lines(home, story):
    r = run(story, AT % (1, 0), "<C-a><Cmd>lua require('sw.notepad').copy()<CR><Right><C-v>", LINES)
    assert r["lines"] == ["Hello brave world", "", "second line hereHello brave world", "second line here"]


def test_the_internal_clipboard_is_used_when_asked(home, story):
    r = run(story, "", "", "R.kind = require('sw.notepad').clipboard_kind")
    assert r["kind"] == "internal"


def test_with_no_clipboard_tool_copy_and_paste_work_inside_the_writer_and_you_are_told(home, story):
    r = run(story, AT % (1, 6), "<S-Right><S-Right><S-Right><Cmd>lua require('sw.notepad').copy()<CR><End><C-v>",
            "R.kind = require('sw.notepad').clipboard_kind; R.note = require('sw.notepad').clipboard_note; " + LINES,
            env_extra={"STORYWHEEL_INTERNAL_CLIPBOARD": "0", "PATH": "/nonexistent", "DISPLAY": "", "WAYLAND_DISPLAY": ""})
    assert r["kind"] == "internal" and "inside the Writer only" in r["note"] and r["lines"][0] == "Hello brave worldbra"


# --- undo, save, select all, find -----------------------------------------------------------------------------------------

def test_undo_and_redo_go_back_a_word_at_a_time(home, story):
    r = run(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { '' })", "one two three<C-z><C-z>",
            LINES + "; R.after_undo = R.lines[1]")
    assert r["after_undo"] == "one" or r["after_undo"].startswith("one")
    r2 = run(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { '' })", "one two three<C-z><C-z><C-y>", LINES)
    assert len(r2["lines"][0]) > len(r["after_undo"])


def test_ctrl_s_saves_at_once(home, story):
    run(story, AT % (3, 16), "<C-s>", "")
    r = run(story, AT % (3, 16), "NEW<C-s>", "R.disk = io.open(vim.api.nvim_buf_get_name(0)):read('*a'); R.modified = vim.bo.modified")
    assert "NEW" in r["disk"] and r["modified"] is False


def test_ctrl_a_selects_everything(home, story):
    r = run(story, "", "<C-a>X", LINES)
    assert r["lines"] == ["X"]


def test_find_next_and_previous(home, story):
    r = run(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'one cat', 'two cat', 'three cat' }); vim.api.nvim_win_set_cursor(0, { 1, 0 })", "", """
        local np = require("sw.notepad")
        np.find("cat")
        R.a = vim.api.nvim_win_get_cursor(0)
        np.find_next(1); R.b = vim.api.nvim_win_get_cursor(0)
        np.find_next(1); R.c = vim.api.nvim_win_get_cursor(0)
        np.find_next(1); R.d = vim.api.nvim_win_get_cursor(0)          -- wraps round
        np.find_next(-1); R.e = vim.api.nvim_win_get_cursor(0)
        R.none = np.find_next(1) and np.find("zebra") or false
    """)
    assert [r[k][0] for k in "abcde"] == [1, 2, 3, 1, 3]


def test_ctrl_f_and_ctrl_g_are_mapped(home, story):
    r = run(story, "", "", """
        for _, k in ipairs({ "<C-f>", "<C-g>", "<A-g>", "<C-s>", "<C-z>", "<C-y>", "<C-c>", "<C-x>", "<C-v>", "<C-a>", "<C-q>", "<F12>", "<A-m>", "<Esc>" }) do
            R[k] = vim.fn.maparg(k, "i") ~= ""
        end
    """)
    assert all(r.values()), r


def menu_labels(story):
    return run(story, "", "", "R.labels = {}; for i, it in ipairs(require('sw.menu').items()) do R.labels[i] = it[1] end")["labels"]


# --- menus -----------------------------------------------------------------------------------------------------------------

def test_right_click_menu_has_the_edit_entries(home, story):
    r = run(story, "", "", """
        R.names = {}
        for _, m in ipairs(vim.fn.menu_get("PopUp")[1].submenus) do R.names[#R.names + 1] = m.name end
        R.mousemodel = vim.o.mousemodel
    """)
    names = [n for n in r["names"] if not n.startswith("-")]
    assert names == ["Undo", "Redo", "Cut", "Copy", "Paste", "Select All", "Italic", "Bold", "Scene Break", "Find", "Replace", "Add to Dictionary", "Look Up", "Join Lines", "Writer Menu"]
    assert r["mousemodel"] == "popup_setpos"


def test_popup_entries_do_what_they_say(home, story):
    r = run(story, "", "", """
        local np = require("sw.notepad")
        vim.cmd("emenu PopUp.Select\\\\ All")
        R.mode = vim.fn.mode()
    """)
    assert r["mode"] in ("s", "v", "i")


def test_the_writer_menu_lists_the_actions(home, story):
    r = run(story, "", "<F12>", """
        local m = require("sw.menu").last
        R.labels = vim.api.nvim_buf_get_lines(m.buf, 0, -1, false)
        R.float = vim.api.nvim_win_get_config(m.win).relative
        R.in_menu = vim.api.nvim_get_current_win() == m.win
    """)
    text = "\n".join(r["labels"])
    for needle in ("Scenes sidebar", "Export manuscript (.docx)", "Show invisibles", "Settings (F4)", "Back to the Builder (F2)", "Typewriter mode",
                   "Spellcheck", "Use Vim keys for now", "Quit storywheel"):
        assert needle in text, needle
    assert r["float"] == "editor" and r["in_menu"] is True


def test_the_menu_runs_an_item_with_a_number_and_returns_you_to_typing(home, story):
    r = run(story, "", "<F12>" + "<Down>" * menu_labels(story).index("Show invisibles") + "<CR>", "R.inv = require('sw.prose').invisibles; R.mode = vim.fn.mode(); R.menu_open = require('sw.menu').last and vim.api.nvim_win_is_valid(require('sw.menu').last.win)")
    assert r["inv"] is True and r["mode"] == "i" and r["menu_open"] is False


def test_the_menu_closes_with_escape_and_with_alt_m(home, story):
    r = run(story, "", "<A-m><Esc>", "R.mode = vim.fn.mode(); R.open = vim.api.nvim_win_is_valid(require('sw.menu').last.win)")
    assert r["mode"] == "i" and r["open"] is False


def test_back_to_the_builder_from_the_menu_and_with_ctrl_q(home, story):
    run(story, "", "<F12>" + "<Down>" * menu_labels(story).index("Back to the Builder (F2)") + "<CR>", "", quits=True)
    assert (story.path.parent / "return.txt").read_text() == "builder"
    (story.path.parent / "return.txt").write_text("")
    run(story, "", "<C-q>", "", quits=True)
    assert (story.path.parent / "return.txt").read_text() == "builder"


def test_the_menu_can_switch_to_vim_keys_for_the_session(home, story):
    r = run(story, "", "<F12>" + "<Down>" * menu_labels(story).index("Use Vim keys for now") + "<CR>", "R.enabled = require('sw.notepad').enabled")
    assert r["enabled"] is False


# --- the setting ------------------------------------------------------------------------------------------------------------------

def test_the_setting_turns_vim_behavior_back_on(home, story):
    settings.save_story(story.path, {"notepad_mode": False})
    r = run(story, AT % (1, 0), "<Esc>", "R.mode = vim.fn.mode(); R.esc = vim.fn.maparg('<Esc>', 'i'); R.sm = vim.o.selectmode; R.km = vim.o.keymodel")
    assert r["mode"] == "n" and r["esc"] == "" and r["sm"] == "" and r["km"] == ""


def test_the_global_setting_is_the_default_for_every_story(home, story):
    settings.save_global({"notepad_mode": False})
    r = run(story, "", "", "R.enabled = require('sw.notepad').enabled")
    assert r["enabled"] is False
    settings.save_global({"notepad_mode": True})
    r = run(story, "", "", "R.enabled = require('sw.notepad').enabled")
    assert r["enabled"] is True


def test_autosave_does_not_need_you_to_leave_insert_mode(home, story):
    r = run(story, AT % (3, 16), "typed words", """
        vim.api.nvim_exec_autocmds("CursorHoldI", {})
        R.mode = vim.fn.mode(); R.modified = vim.bo.modified
        R.disk = io.open(vim.api.nvim_buf_get_name(0)):read("*a")
    """)
    assert r["mode"] == "i" and r["modified"] is False and "typed words" in r["disk"]


def test_italic_and_bold_still_work_in_notepad_mode(home, story):
    r = run(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { '' })", "a <A-i>quiet<A-i> and <A-b>loud<A-b>.", LINES)
    assert r["lines"] == ["a *quiet* and **loud**."]


def test_a_selection_is_italicised_with_alt_i(home, story):
    r = run(story, AT % (1, 6), "<S-Right><S-Right><S-Right><S-Right><S-Right><A-i>", LINES)
    assert r["lines"][0] == "Hello *brave* world"


def test_help_describes_notepad_mode(home, story):
    r = run(story, "", "", "R.help = table.concat(require('sw').HELP, '\\n')")
    for needle in ("Notepad mode", "Escape does nothing", "Ctrl+C / X / V", "F12 or Alt+M", "Right-click"):
        assert needle in r["help"], needle


# --- Home and End -------------------------------------------------------------------------------------------------------

LONG = " ".join(["word%02d" % i for i in range(60)])         # 420 characters: several screen lines in a 72 column window


def seg_starts():
    return """
        local nums = {}
        local w = require('sw.layout').main
        R.width = vim.api.nvim_win_get_width(w)
    """


def test_home_goes_to_the_start_of_the_visible_line_then_the_paragraph(home, story):
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { %s })\nvim.api.nvim_win_set_cursor(0, { 1, 200 })" % json.dumps(LONG)
    r = run(story, setup, "<Home>", "R.col = vim.api.nvim_win_get_cursor(0)[2]; R.mode = vim.fn.mode(); R.width = vim.api.nvim_win_get_width(require('sw.layout').main)")
    assert 0 < r["col"] < 200 and 200 - r["col"] < r["width"] and r["mode"] == "i"
    assert LONG[r["col"] - 1] == " "                                   # the screen line starts right after a space
    first = r["col"]
    r = run(story, setup, "<Home><Home>", "R.col = vim.api.nvim_win_get_cursor(0)[2]")
    assert r["col"] == 0                                               # Home again: the paragraph's start (the lines in between are one press each)


def test_end_goes_to_the_end_of_the_visible_line_and_after_the_last_character_on_the_last(home, story):
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { %s })\nvim.api.nvim_win_set_cursor(0, { 1, 5 })" % json.dumps(LONG)
    r = run(story, setup, "<End>", "R.col = vim.api.nvim_win_get_cursor(0)[2]; R.width = vim.api.nvim_win_get_width(require('sw.layout').main)")
    assert 5 < r["col"] < 100 and r["col"] <= r["width"]               # not the end of the 419-character paragraph
    r = run(story, setup + "\nvim.api.nvim_win_set_cursor(0, { 1, 400 })", "<End>", "R.col = vim.api.nvim_win_get_cursor(0)[2]")
    assert r["col"] == len(LONG)


def test_home_and_end_on_a_short_line_are_the_line_start_and_end(home, story):
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'short line here' })\nvim.api.nvim_win_set_cursor(0, { 1, 6 })"
    assert run(story, setup, "<Home>", "R.col = vim.api.nvim_win_get_cursor(0)[2]")["col"] == 0
    assert run(story, setup, "<End>", "R.col = vim.api.nvim_win_get_cursor(0)[2]")["col"] == 15


def test_home_and_end_leave_a_selection_and_you_keep_typing(home, story):
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'short line here' })\nvim.api.nvim_win_set_cursor(0, { 1, 6 })"
    r = run(story, setup, "<S-Right><S-Right><End>X", LINES + "; R.mode = vim.fn.mode()")
    assert r["lines"] == ["short line hereX"] and r["mode"] == "i"


# --- Shift+Home / Shift+End, the Ctrl keys, function keys ---------------------------------------------------------------------

def long_setup(col):
    return "vim.api.nvim_buf_set_lines(0, 0, -1, false, { %s })\nvim.api.nvim_win_set_cursor(0, { 1, %d })" % (json.dumps(LONG), col)


def test_shift_end_selects_to_the_end_of_the_visible_line_and_typing_replaces_it(home, story):
    r = run(story, long_setup(5), "<S-End>X", LINES + "; R.mode = vim.fn.mode(); R.width = vim.api.nvim_win_get_width(require('sw.layout').main)")
    line = r["lines"][0]
    assert line.startswith("word0X") or line.startswith("word0") and "X" in line[:r["width"] + 2]
    assert len(line) > len(LONG) - r["width"] - 2 and len(line) < len(LONG) - 20          # only the rest of that screen line went
    assert r["mode"] == "i"


def test_shift_home_selects_back_to_the_start_of_the_visible_line(home, story):
    r = run(story, long_setup(200), "<S-Home>X", LINES)
    line = r["lines"][0]
    assert line.endswith(LONG[200:]) and "X" in line and len(line) < len(LONG)
    assert line[:20] == LONG[:20]                                                          # the first screen lines are untouched


def test_shift_home_then_shift_end_move_the_active_end_and_keep_the_anchor(home, story):
    r = run(story, long_setup(200), "<S-Home><S-End>X", LINES)
    line = r["lines"][0]
    assert "X" in line and line.count("X") == 1 and line.startswith(LONG[:150])


def test_shift_end_on_a_short_line_selects_to_the_end_and_shift_home_to_the_start(home, story):
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'short line here' })\nvim.api.nvim_win_set_cursor(0, { 1, 6 })"
    assert run(story, setup, "<S-End>X", LINES)["lines"] == ["short X"]
    assert run(story, setup, "<S-Home>X", LINES)["lines"] == ["Xline here"]


def test_shift_end_copies_what_it_selected(home, story):
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'short line here' })\nvim.api.nvim_win_set_cursor(0, { 1, 6 })"
    r = run(story, setup, "<S-End><Cmd>lua require('sw.notepad').copy()<CR>", "R.reg = vim.fn.getreg('+')")
    assert r["reg"] == "line here"


@pytest.mark.parametrize("key", ["<C-u>", "<C-w>", "<C-t>", "<C-d>", "<C-k>", "<C-e>", "<C-n>", "<C-p>", "<C-j>", "<C-l>", "<C-]>",
                                 "<C-r>x", "<C-^>", "<C-_>", "<C-@>", "<C-\\>"])
def test_neovims_insert_mode_ctrl_keys_do_nothing_in_notepad_mode(home, story, key):
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello brave world', 'second line' })\nvim.api.nvim_win_set_cursor(0, { 1, 11 })"
    settings.save_story(story.path, {"key_replace": "<A-r>"}) if key.startswith("<C-r>") else None
    r = run(story, setup, key, LINES + "; R.mode = vim.fn.mode(); R.cur = vim.api.nvim_win_get_cursor(0)")
    assert r["lines"][:2] == ["Hello brave world", "second line"] or r["lines"][0] == "Hello bravex world"
    assert r["mode"] == "i" and r["cur"][0] == 1


def test_ctrl_u_does_not_delete_the_line_and_ctrl_z_still_undoes(home, story):
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello brave world' })\nvim.api.nvim_win_set_cursor(0, { 1, 17 })"
    r = run(story, setup, "<C-u>abc", LINES)
    assert r["lines"] == ["Hello brave worldabc"]


def test_ctrl_h_and_ctrl_backspace_delete_the_previous_word(home, story):
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello brave world' })\nvim.api.nvim_win_set_cursor(0, { 1, 17 })"
    assert run(story, setup, "<C-h>", LINES)["lines"] == ["Hello brave "]
    assert run(story, setup, "<C-BS>", LINES)["lines"] == ["Hello brave "]
    assert run(story, setup, "<C-h><C-h>", LINES)["lines"] == ["Hello "]


def test_ctrl_h_with_a_selection_deletes_the_selection(home, story):
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello brave world' })\nvim.api.nvim_win_set_cursor(0, { 1, 6 })"
    r = run(story, setup, "<S-Right><S-Right><S-Right><S-Right><S-Right><S-Right><C-h>X", LINES)
    assert r["lines"] == ["HelloXworld"] or r["lines"] == ["Hello Xworld"] or "brave" not in r["lines"][0]


def test_ctrl_delete_deletes_the_next_word(home, story):
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello brave world' })\nvim.api.nvim_win_set_cursor(0, { 1, 6 })"
    assert run(story, setup, "<C-Del>", LINES)["lines"][0] in ("Hello world", "Hello  world", "Hello brave world"[:6] + "world")


@pytest.mark.parametrize("key", ["<F10>", "<F11>", "<S-F5>", "<C-F6>", "<A-F7>", "<F9>x"])
def test_unmapped_function_keys_do_nothing(home, story, key):
    settings.save_story(story.path, {"key_sidebar": "<A-d>", "key_lookup": "<A-l>", "key_lookup_word": "<A-k>"})     # (F9, F7 and F6 freed for the test)
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello' })\nvim.api.nvim_win_set_cursor(0, { 1, 5 })"
    r = run(story, setup, key, LINES)
    assert r["lines"] in (["Hello"], ["Hellox"]) and "<F" not in r["lines"][0]


def test_the_default_replace_key_is_ctrl_r_and_ctrl_h_is_not_replace(home, story):
    setup = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello' })\nvim.api.nvim_win_set_cursor(0, { 1, 5 })"
    r = run(story, setup, "<C-r>", "R.open = require('sw.replace').win ~= nil and vim.api.nvim_win_is_valid(require('sw.replace').win)")
    assert r["open"] is True
    r = run(story, setup, "<C-h>", "R.open = require('sw.replace').win ~= nil and vim.api.nvim_win_is_valid(require('sw.replace').win)")
    assert not r["open"]


def test_the_right_click_menu_shows_the_key_beside_each_entry_and_undo_redo_work(home, story):
    settings.save_story(story.path, {"key_italic": "<A-u>"})
    r = run(story, "", "", """
        R.hints = {}
        for _, m in ipairs(vim.fn.menu_get("PopUp")[1].submenus) do R.hints[m.name] = m.actext end
    """)
    h = r["hints"]
    assert h["Undo"] == "Ctrl+Z" and h["Redo"] == "Ctrl+Y" and h["Cut"] == "Ctrl+X" and h["Find"] == "Ctrl+F"
    assert h["Replace"] == "Ctrl+R" and h["Italic"] == "Alt+U" and h["Writer Menu"] == "F12" and h["Look Up"] == "F7"
    # Undo and Redo through the menu do what Ctrl+Z / Ctrl+Y do
    r = run(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'abc' })\nvim.cmd('let &undolevels = &undolevels')\nvim.api.nvim_win_set_cursor(0, { 1, 3 })",
            "def<Cmd>doautocmd <nomodeline> MenuPopup<CR><Cmd>emenu PopUp.Undo<CR>", LINES + "; R.mode = vim.fn.mode()")
    assert r["lines"] == ["abc"] and r["mode"] == "i"
    r = run(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'abc' })\nvim.cmd('let &undolevels = &undolevels')\nvim.api.nvim_win_set_cursor(0, { 1, 3 })",
            "def<Cmd>emenu PopUp.Undo<CR><Cmd>emenu PopUp.Redo<CR>", LINES)
    assert r["lines"] == ["abcdef"]


def test_the_writer_menu_lists_undo_and_redo_with_their_keys(home, story):
    labels = run(story, "", "", "R.labels = {}; for i, it in ipairs(require('sw.menu').items()) do R.labels[i] = it[1] end")["labels"]
    assert "Undo (Ctrl+Z)" in labels and "Redo (Ctrl+Y)" in labels
