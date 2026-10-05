"""The Writer in screenplay mode (batch 17): the prose rules are off, Tab cycles a line's element, Enter knows what comes next, headings and
cues are capitalized, names complete, the page is approximated with display-only indents, the sidebar lists scenes under their sections,
the status line shows pages, and the flip test lists what a reader would notice."""
import pytest

from storywheel import screenplay, settings, vault, writer
from test_notepad import AT, LINES, run

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")

SCRIPT = """Title: The Lamp
Credit: Written by

FADE IN:

# Act One

= Mara comes back.

INT. ATTIC - NIGHT

Dust hangs in the lamplight.

MARA
(whispering)
Hello?

BRAM
Who's there?

# Act Two

EXT. LANE - DAY

Rain.
"""


@pytest.fixture
def script_story(home):
    u = vault.create_universe("Thornwood", ["horror"])
    s = u.new_story("The Lamp", {"structure": "Short Film"})
    assert s.is_screenplay()
    s.script_path.parent.mkdir(parents=True, exist_ok=True)
    s.script_path.write_text(SCRIPT, encoding="utf-8")
    return s


def set_text(lines):
    return "vim.api.nvim_buf_set_lines(0, 0, -1, false, %s)\n" % ("{" + ", ".join('"%s"' % l.replace('"', '\\"') for l in lines) + "}")


def test_the_writer_opens_the_script_and_the_prose_rules_stay_off(home, script_story):
    r = run(script_story, "", "", LINES + "; R.name = vim.api.nvim_buf_get_name(0); R.marks = #vim.api.nvim_buf_get_extmarks(0, require('sw.prose').ns, 0, -1, {})")
    assert r["name"].endswith("script.fountain") and r["lines"][:2] == ["Title: The Lamp", "Credit: Written by"]
    assert r["marks"] == 0                                            # (no virtual paragraph indents from the prose rules)


def test_enter_after_action_leaves_a_blank_line_and_a_typed_break_is_not_rewritten(home, script_story):
    r = run(script_story, set_text(["Rain falls."]) + AT % (1, 11), "<CR>***<CR>Next", LINES)
    assert r["lines"] == ["Rain falls.", "", "***", "", "Next"]


def test_paste_keeps_blank_lines_and_indents(home, script_story):
    r = run(script_story, set_text([""]) + "vim.fn.setreg('+', {'MARA', '  Hello.', '', 'BRAM', 'Hi.'}, 'l')\n" + AT % (1, 0), "<C-v>", LINES)
    assert r["lines"][1:] == ["MARA", "  Hello.", "", "BRAM", "Hi."]


def test_tab_cycles_the_element_of_a_line(home, script_story):
    seen = []
    for presses in range(1, 6):
        r = run(script_story, set_text(["Rain.", "", "mara"]) + AT % (3, 4), "<Tab>" * presses, LINES)
        seen.append(r["lines"])
    assert seen[0] == ["Rain.", "", "MARA"]                                          # character
    assert seen[1] == ["Rain.", "", "(MARA)"]                                        # parenthetical
    assert seen[2] == ["Rain.", "", "MARA"]                                          # dialogue (on its own: reads as text)
    assert seen[3] == ["Rain.", "", "> MARA"]                                        # transition (forced)
    assert seen[4] == ["Rain.", "", "!MARA"]                                         # back to action (forced, so caps don't read as a cue)


def test_a_parenthetical_or_dialogue_joins_the_speech_above_it(home, script_story):
    r = run(script_story, set_text(["MARA", "Hello.", "", "whispering"]) + AT % (4, 10),
            "<Cmd>lua require('sw.script').set_element(0, 4, 'parenthetical')<CR>", LINES)
    assert r["lines"] == ["MARA", "Hello.", "(whispering)"]


def test_a_transition_gets_blank_lines_round_it(home, script_story):
    r = run(script_story, set_text(["Rain.", "cut to:", "INT. ROOM - DAY"]) + AT % (2, 7),
            "<Cmd>lua require('sw.script').set_element(0, 2, 'transition')<CR>", LINES)
    assert r["lines"] == ["Rain.", "", "CUT TO:", "", "INT. ROOM - DAY"]


def test_enter_after_a_cue_starts_dialogue_and_after_dialogue_returns_to_action(home, script_story):
    r = run(script_story, set_text(["Rain.", "", ""]) + AT % (3, 0), "MARA<CR>Hello.<CR>She leaves.", LINES)
    assert r["lines"] == ["Rain.", "", "MARA", "Hello.", "", "She leaves."]


def test_headings_and_known_cues_are_capitalized(home, script_story):
    r = run(script_story, set_text(["MARA", "Hi.", "", ""]) + AT % (4, 0), "int. attic - night<CR>Dust.<CR>mara<CR>Again.", LINES)
    assert r["lines"] == ["MARA", "Hi.", "", "INT. ATTIC - NIGHT", "", "Dust.", "", "MARA", "Again."]


def test_names_and_locations_complete_from_the_script(home, script_story):
    r = run(script_story, "vim.api.nvim_buf_set_lines(0, -1, -1, false, {'', ''})\nvim.api.nvim_win_set_cursor(0, {vim.api.nvim_buf_line_count(0), 0})",
            "BR<Cmd>lua require('sw.world').complete()<CR>", "R.pum = vim.fn.pumvisible(); R.items = vim.tbl_map(function(i) return i.word end, vim.fn.complete_info({'items'}).items)")
    assert r["pum"] == 1 and "BRAM" in r["items"]
    r = run(script_story, "vim.api.nvim_buf_set_lines(0, -1, -1, false, {'', ''})\nvim.api.nvim_win_set_cursor(0, {vim.api.nvim_buf_line_count(0), 0})",
            "EXT. AT<Cmd>lua require('sw.world').complete()<CR>", "R.items = vim.tbl_map(function(i) return i.word end, vim.fn.complete_info({'items'}).items)")
    assert "ATTIC" in r["items"]


def test_the_page_is_approximated_with_display_only_indents(home, script_story):
    check = """
    local ns = require('sw.script').ns
    R.pads = {}
    for _, m in ipairs(vim.api.nvim_buf_get_extmarks(0, ns, 0, -1, { details = true })) do
      local d = m[4]
      if d.virt_text and d.virt_text_pos == 'inline' then R.pads[tostring(m[2] + 1)] = #d.virt_text[1][1] end
    end
    """ + LINES
    r = run(script_story, "require('sw.script').decorate(0)", "", check)
    lines = r["lines"]
    pad = {lines[int(k) - 1]: v for k, v in r["pads"].items()}
    assert pad["MARA"] == 22 and pad["(whispering)"] == 16 and pad["Hello?"] == 10
    assert "INT. ATTIC - NIGHT" not in pad and "Dust hangs in the lamplight." not in pad


def test_the_file_stays_plain_fountain(home, script_story):
    run(script_story, "", "<C-s>", "")
    assert script_story.script_path.read_text(encoding="utf-8") == SCRIPT


def test_the_sidebar_lists_scenes_under_their_sections(home, script_story):
    r = run(script_story, "", "", "local sb = require('sw.sidebar'); sb.open(); R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)")
    text = "\n".join(r["lines"])
    assert "▸ Act One" in text and "INT. ATTIC - NIGHT" in text and "▸ Act Two" in text and "EXT. LANE - DAY" in text
    assert text.index("Act One") < text.index("INT. ATTIC") < text.index("Act Two") < text.index("EXT. LANE")


def test_the_sidebar_jumps_to_a_scene(home, script_story):
    r = run(script_story, "", "", """
      local sb = require('sw.sidebar'); sb.open()
      local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
      for i, l in ipairs(lines) do if l:find('EXT. LANE', 1, true) then vim.api.nvim_win_set_cursor(0, { i, 0 }) end end
      sb.jump()
      R.row = vim.api.nvim_win_get_cursor(0)[1]
      R.line = vim.api.nvim_get_current_line()
    """)
    lines = SCRIPT.split("\n")
    assert r["row"] >= lines.index("EXT. LANE - DAY") + 1


def test_the_status_line_shows_pages_against_the_target(home, script_story):
    r = run(script_story, "", "", "require('sw.stats').refresh(); R.line = require('sw.stats').line()")
    assert "p. 1 of ~12" in r["line"]


def test_the_flip_test_lists_problems_and_jumps_to_them(home, script_story):
    long_action = " ".join(["The rain keeps falling on the roof and the gutters overflow."] * 6)
    script_story.script_path.write_text(SCRIPT + "\n" + long_action + "\n\nWe see the lamp swing.\n", encoding="utf-8")
    r = run(script_story, "", "", """
      local found = require('sw.script').flip_test()
      R.kinds = vim.tbl_map(function(d) return d.kind end, found)
      R.float = vim.api.nvim_win_get_config(0).relative ~= ''
      vim.api.nvim_input('<CR>')
    """)
    assert "long-action" in r["kinds"] and "camera" in r["kinds"] and r["float"]


def test_lua_and_python_read_a_script_the_same_way(home, script_story):
    from storywheel import fountain
    text = open(__file__.replace("test_screenplay_writer.py", "fixtures/screenplay/the-lamp.fountain")).read()
    r = run(script_story, "", "", "local lines = vim.split(%r, '\\n', { plain = true }); R.types = require('sw.script').types(lines); R.pages = require('sw.script').estimate_pages(lines)"
            .replace("%r", "[==[" + text + "]==]"))
    py = fountain.line_types(text)
    lua = {i + 1: t for i, t in enumerate(r["types"]) if t not in ("blank",)}
    assert {k: v for k, v in py.items()} == lua
    from storywheel import screenplay_pdf
    est = screenplay_pdf.estimate_pages(text)
    assert abs(r["pages"] - est) <= max(0.6, 0.12 * est)


def test_the_menu_offers_script_exports(home, script_story):
    r = run(script_story, "", "", "R.labels = vim.tbl_map(function(i) return i[1] end, require('sw.menu').items())")
    labels = r["labels"]
    assert "Export script (.pdf)" in labels and "Export for Final Draft (.fdx)" in labels and "Export Fountain (.fountain)" in labels
    assert not any(".docx" in l for l in labels) and any(l.startswith("Flip test") for l in labels)
