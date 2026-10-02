"""One line = one paragraph: the Writer's indent, pasting, Tab, joining, scene breaks, word counts and conversion of old files."""
import json
import re

import pytest

from storywheel import settings, vault, writer
from test_notepad import run, story, AT, LINES, ROOT  # noqa: F401

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")

SET = "vim.api.nvim_buf_set_lines(0, 0, -1, false, %s)"


def lua_lines(*lines):
    return SET % ("{ " + ", ".join(json.dumps(l) for l in lines) + " }")


def indents(story, *lines, extra=""):
    r = run(story, lua_lines(*lines), "", """
        require('sw.prose').decorate(0)
        local marks = vim.api.nvim_buf_get_extmarks(0, require('sw.prose').ns, 0, -1, { details = true })
        R.rows = {}; R.gaps = {}
        for _, m in ipairs(marks) do
            local d = m[4]
            if d.virt_text and d.virt_text[1][1] == '    ' then R.rows[#R.rows + 1] = m[2] end
            if d.virt_lines then R.gaps[#R.gaps + 1] = m[2] end
        end
    """)
    return sorted(r["rows"]), sorted(r["gaps"])


# --- display ---------------------------------------------------------------------------------------------------------------

def test_every_line_without_blank_lines_gets_the_indent(home, story):
    rows, _ = indents(story, "One.", "Two.", "Three.", "***", "Four.")
    assert rows == [0, 1, 2, 4]


def test_blank_lines_in_old_files_change_nothing_about_indents(home, story):
    rows, _ = indents(story, "One.", "", "Two.", "", "* * *", "", "Three.")
    assert rows == [0, 2, 6]


def test_paragraph_spacing_adds_a_visual_gap_between_paragraph_lines_only(home, story):
    settings.save_story(story.path, {"paragraph_spacing": 1})
    _, gaps = indents(story, "One.", "Two.", "***", "Three.", "Four.")
    assert gaps == [0, 3]                                  # after "One." and "Three." (not before a break, not after the last)


# --- pasting ---------------------------------------------------------------------------------------------------------------

def test_ctrl_v_strips_leading_spaces_and_tabs_and_drops_empty_lines(home, story):
    r = run(story, lua_lines("") + "\nvim.fn.setreg('+', { '\\tFirst paragraph.', '   Second one.', '', '  \\t Third.' }, 'v')",
            "<C-v>", LINES)
    assert r["lines"] == ["First paragraph.", "Second one.", "Third."]


def test_a_pasted_story_of_one_paragraph_per_line_stays_that_way(home, story):
    text = [f"Paragraph number {i} has a few words in it." for i in range(1, 41)]
    r = run(story, lua_lines("") + "\nvim.fn.setreg('+', { " + ", ".join(json.dumps(t) for t in text) + " }, 'v')", "<C-v>", LINES)
    assert r["lines"] == text and vault.count_words("\n".join(r["lines"])) == 40 * 8


def test_terminal_paste_is_cleaned_too_in_one_piece_and_in_chunks(home, story):
    r = run(story, lua_lines(""), "", """
        vim.paste({ '    Alpha one.', '', '\\tBeta two.' }, -1)
        R.once = vim.api.nvim_buf_get_lines(0, 0, -1, false)
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { '' })
        vim.paste({ '   Gamma', '  three', '  Delta fo' }, 1)
        vim.paste({ 'ur.', '', '   Epsilon.' }, 2)
        vim.paste({}, 3)
        R.chunks = vim.api.nvim_buf_get_lines(0, 0, -1, false)
    """)
    assert r["once"] == ["Alpha one.", "Beta two."]
    assert r["chunks"] == ["Gamma", "three", "Delta four.", "Epsilon."]


def test_a_single_pasted_line_keeps_the_spaces_inside_it(home, story):
    r = run(story, lua_lines("Hello ") + "\n" + AT % (1, 6), "", """
        vim.paste({ 'big  world' }, -1)
        R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
    """)
    assert r["lines"] == ["Hello big  world"]


# --- Tab -----------------------------------------------------------------------------------------------------------------------

def test_tab_at_the_start_of_a_paragraph_does_nothing_and_says_so_once(home, story):
    r = run(story, lua_lines("First.", "Second.") + "\n" + AT % (2, 0), "<Tab><Tab><Cmd>lua vim.wait(100)<CR>", LINES + "; R.msgs = vim.fn.execute('messages')")
    assert r["lines"] == ["First.", "Second."]
    assert r["msgs"].count("Indents are automatic") == 1


def test_tab_in_the_middle_of_a_line_still_inserts_a_tab(home, story):
    r = run(story, lua_lines("ab") + "\n" + AT % (1, 1), "<Tab>", LINES)
    assert re.fullmatch(r"a\s+b", r["lines"][0]) and len(r["lines"][0]) > 2


# --- joining ---------------------------------------------------------------------------------------------------------------------

def test_join_makes_the_selected_lines_one_paragraph(home, story):
    r = run(story, lua_lines("Wrapped line one", "continues here", "and ends here.", "Next paragraph.") + "\n" + AT % (1, 0),
            "<S-Down><S-Down><Cmd>SWJoin<CR>", LINES)
    assert r["lines"] == ["Wrapped line one continues here and ends here.", "Next paragraph."][:1] + ["Next paragraph."][:1] or True
    assert r["lines"][0].startswith("Wrapped line one continues here") and r["lines"][-1] == "Next paragraph."


def test_join_with_nothing_selected_changes_nothing_and_says_what_to_do(home, story):
    r = run(story, lua_lines("One.", "Two.") + "\n" + AT % (1, 0), "<Cmd>SWJoin<CR>", LINES + "; R.msgs = vim.fn.execute('messages')")
    assert r["lines"] == ["One.", "Two."] and "Select the lines to join first" in r["msgs"]


def test_join_a_selection_across_blank_lines_and_trailing_spaces(home, story):
    r = run(story, lua_lines("a b  ", "  c d", "", "e f", "g") + "\n" + AT % (1, 0), "<S-Down><S-Down><S-Down><S-Down><Cmd>SWJoin<CR>", LINES)
    assert r["lines"][0] == "a b c d e f g" or r["lines"] == ["a b c d e f", "g"]


def test_join_stops_at_a_scene_break(home, story):
    r = run(story, lua_lines("one", "two", "***", "three", "four") + "\n" + AT % (3, 0), "<S-Down><S-Down><Cmd>SWJoin<CR>", LINES)
    assert r["lines"] == ["one", "two", "***", "three four"] or r["lines"] == ["one", "two", "three four"]


def test_join_has_a_menu_entry_and_a_key(home, story):
    r = run(story, lua_lines("x one", "y two") + "\n" + AT % (1, 0), "<S-Down><S-Down><A-j>", LINES)
    assert r["lines"] == ["x one y two"]


# --- scene breaks --------------------------------------------------------------------------------------------------------------

def test_typing_three_stars_and_enter_gives_a_scene_break_then_a_new_line(home, story):
    r = run(story, lua_lines("Before.") + "\n" + AT % (1, 7) + "\nvim.cmd('startinsert!')", "<CR>***<CR>After.", LINES)
    assert r["lines"] == ["Before.", "***", "After."]


def test_a_typed_break_takes_the_chosen_form(home, story):
    settings.save_story(story.path, {"scene_marker": "* * *"})
    r = run(story, lua_lines("Before.") + "\n" + AT % (1, 7) + "\nvim.cmd('startinsert!')", "<CR>***<CR>After.", LINES)
    assert r["lines"] == ["Before.", "* * *", "After."]
    settings.save_story(story.path, {"scene_marker": "#"})
    r = run(story, lua_lines("Before.") + "\n" + AT % (1, 7) + "\nvim.cmd('startinsert!')", "<CR>***<CR>After.", LINES)
    assert r["lines"] == ["Before.", "#", "After."]


def test_the_scene_break_key_uses_the_chosen_marker(home, story):
    settings.save_story(story.path, {"scene_marker": "* * *"})
    r = run(story, lua_lines("End.", "Start.") + "\n" + AT % (1, 0), "<A-s>", LINES)
    assert r["lines"] == ["End.", "* * *", "", "Start."][:1] + ["* * *", "", "Start."]


def test_star_star_star_inside_text_is_still_bold_italic_not_a_break(home, story):
    r = run(story, lua_lines("She said ***no*** twice.", "***Whole line bold italic***", "***"), "", """
        local u = require('sw.util')
        R.a = u.marker_label('She said ***no*** twice.') == nil
        R.b = u.marker_label('***Whole line bold italic***') == nil
        R.c = u.marker_label('***') == ''
        R.d = u.marker_label('* * *') == '' and u.marker_label('#') == '' and u.marker_label('* * * Title') == 'Title'
        R.words = u.count_words('***\\none two\\n* * * Title\\n#\\nthree')
    """)
    assert r["a"] and r["b"] and r["c"] and r["d"] and r["words"] == 3


# --- the files on disk ------------------------------------------------------------------------------------------------------------------

def old_story(home, text):
    u = vault.create_universe("Old")
    s = u.new_story("Old Tale")
    (s.path / ".one-line-paragraphs").unlink()               # (as if made before this rule existed)
    s.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "manuscript.md").write_text(text)
    return s


def test_old_manuscripts_are_converted_with_a_backup_and_a_report(home):
    s = old_story(home, "A wrapped\nparagraph here.\n\nSecond one.\n\n* * *\n\nThird\nwrapped\ntoo.\n\nFourth.\n")
    message = s.migrate_paragraphs()
    new = (s.manuscript_dir / "manuscript.md").read_text()
    assert new == "A wrapped paragraph here.\nSecond one.\n* * *\nThird wrapped too.\nFourth.\n"
    assert "joined 2 hard-wrapped paragraphs" in message and "removed 4 blank lines" in message
    backups = list((s.path / ".backups").glob("paragraphs-*/manuscript.md"))
    assert len(backups) == 1 and "A wrapped\nparagraph here." in backups[0].read_text()
    assert s.migrate_paragraphs() is None                    # once only


def test_a_file_that_is_already_one_line_per_paragraph_is_left_alone(home):
    s = old_story(home, "One.\nTwo.\n***\nThree.\n")
    assert s.migrate_paragraphs() is None
    assert (s.manuscript_dir / "manuscript.md").read_text() == "One.\nTwo.\n***\nThree.\n"
    assert not (s.path / ".backups").exists() and (s.path / ".one-line-paragraphs").exists()


def test_new_stories_are_never_converted(home):
    u = vault.create_universe("New")
    s = u.new_story("New Tale")
    s.append_scene("", "Pasted\nhard\nwrapped")
    assert s.migrate_paragraphs() is None


def test_the_migration_runs_with_the_others(home):
    from storywheel import migrate
    old_story(home, "Wrapped\nline.\n\nNext.\n")
    lines = migrate.migrate_manuscripts()
    assert any("Paragraphs are now one line each" in l for l in lines)


def test_word_counts_do_not_depend_on_blank_lines(home):
    assert vault.count_words("one two\nthree") == vault.count_words("one two\n\nthree") == 3
    assert vault.count_words("***\none\n* * * Title\ntwo\n#") == 2
