"""One manuscript file per story with scene markers inside it (a novel: one file per chapter)."""
import json
from pathlib import Path

import pytest

from storywheel import export, settings, vault, writer
from test_writer import run_lua, run_typed  # noqa: F401  (the same headless helpers)

pytestmark_nvim = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


# --- markers and scenes ------------------------------------------------------------------------------------------

def test_marker_lines():
    f = vault.marker_label
    assert f("* * *") == "" and f("* * * The Letter") == "The Letter" and f("* * *   spaced out  ") == "spaced out"
    assert f("*  * *") is None and f("* * ") is None and f(" * * *") is None and f("text * * *") is None
    assert f("* * *x") is None
    assert f("***") == "" and f("#") == "" and f("***  ") == "" and f("*** The Letter") == "The Letter"
    assert f("***bold italic***") is None and f("***bold italic*** and more") is None and f("# Heading") is None


def test_words_ignore_marker_lines_only():
    assert vault.count_words("* * *") == 0 and vault.count_words("* * * Two Words\n\none two") == 2
    assert vault.count_words("one * * * two") == 2                      # (not a marker: the line has other text)
    assert vault.count_words("a\n* * * Title\nb c") == 3


def scenes(text):
    return [(s["start"], s["end"], s["label"], s["marked"], s["first_line"], s["words"]) for s in vault.parse_scenes(text)]


def test_parsing_scenes():
    assert scenes("") == []
    assert scenes("\n\n") == []
    assert scenes("Plain text.\nMore.") == [(1, 2, "", False, "Plain text.", 3)]
    assert scenes("* * * Opening\n\nText here.\n\n* * *\n\nNext one.") == [
        (1, 4, "Opening", True, "Text here.", 2), (5, 7, "", True, "Next one.", 2)]
    assert scenes("\n\n* * * Named\ntext") == [(1, 4, "Named", True, "text", 1)]          # blank lines first: still the first scene
    assert scenes("Before.\n\n* * * After\n\nBody.") == [(1, 2, "", False, "Before.", 1), (3, 5, "After", True, "Body.", 1)]
    assert scenes("* * *\n* * *") == [(1, 1, "", True, "", 0), (2, 2, "", True, "", 0)]


def test_scene_list_runs_across_chapter_files(home):
    u = vault.create_universe("U")
    s = u.new_story("Novel")
    settings.save_story(s.path, {"format": "novel"})
    s.add_scene("One", "* * * First\n\nAlpha beta.\n\n* * * Second\n\nGamma.")
    s.add_scene("Two", "Delta epsilon zeta.\n\n* * * Fourth\n\neta")
    out = s.scene_list()
    assert [(e["n"], e["title"], e["file"], e["words"]) for e in out] == [
        (1, "First", "01-one.md", 2), (2, "Second", "01-one.md", 1), (3, "Scene 3", "02-two.md", 3), (4, "Fourth", "02-two.md", 1)]
    assert [e["line"] for e in out] == [1, 5, 1, 3]
    assert s.migrate_manuscript() is None and len(s.files()) == 2                       # a novel keeps its chapter files


def test_append_scene(home):
    u = vault.create_universe("U")
    s = u.new_story("Tale")
    a = s.append_scene("Opening", "First words.")
    assert Path(a["path"]).name == "manuscript.md" and a["line"] == 1
    b = s.append_scene("The Letter", "Second words.")
    c = s.append_scene("")
    text = (s.manuscript_dir / "manuscript.md").read_text()
    assert text.startswith("* * * Opening\n\nFirst words.\n\n* * * The Letter\n\nSecond words.\n\n* * *\n")
    assert b["line"] == 5 and c["line"] == 9
    assert [e["title"] for e in s.scene_list()] == ["Opening", "The Letter", "Scene 3"]
    assert len(s.files()) == 1


# --- migration ----------------------------------------------------------------------------------------------------------

def legacy(home, n=3):
    u = vault.create_universe("U")
    s = u.new_story("Tale")
    texts = {"Opening": "Stacie ran down the road.\n\nIt was *very* dry.", "The Letter": "A letter came on Tuesday.",
             "Ending": "* * *\n\nBy Friday it was gone."}
    for title in list(texts)[:n]:
        s.add_scene(title, texts[title])
    return s, texts


def test_old_scene_files_are_merged_in_order_into_one_file_with_a_backup(home):
    s, texts = legacy(home)
    before_words = s.word_count()
    before_text = [p.read_text() for p in s.files()]
    message = s.migrate_manuscript()
    assert message and "Merged 3 scene files into manuscript.md" in message
    assert [p.name for p in s.files()] == ["manuscript.md"]
    merged = (s.manuscript_dir / "manuscript.md").read_text()
    assert merged.startswith("* * * Opening\n\nStacie ran down the road.")
    assert "\n\n* * * The letter\n\nA letter came on Tuesday.\n\n* * * Ending\n\nBy Friday it was gone.\n" in merged
    assert s.word_count() == before_words                                              # no words lost, none added
    assert [e["title"] for e in s.scene_list()] == ["Opening", "The letter", "Ending"]
    backups = [d for d in (s.path / ".backups").iterdir() if d.name.startswith("migrated-")]
    assert len(backups) == 1 and sorted(p.name for p in backups[0].iterdir()) == ["01-opening.md", "02-the-letter.md", "03-ending.md"]
    assert [(backups[0] / n).read_text() for n in ("01-opening.md", "02-the-letter.md", "03-ending.md")] == before_text


def test_migrating_twice_does_nothing_more(home):
    s, _ = legacy(home)
    s.migrate_manuscript()
    text = (s.manuscript_dir / "manuscript.md").read_text()
    assert s.migrate_manuscript() is None and (s.manuscript_dir / "manuscript.md").read_text() == text
    assert len([d for d in (s.path / ".backups").iterdir()]) == 1


def test_a_single_file_and_a_novel_are_left_alone(home):
    s, _ = legacy(home, 1)
    assert s.migrate_manuscript() is None and [p.name for p in s.files()] == ["01-opening.md"]
    s2, _ = legacy(home)
    s2_story = vault.get_universe("u").new_story("Novel")
    settings.save_story(s2_story.path, {"format": "novel"})
    s2_story.add_scene("A", "One.")
    s2_story.add_scene("B", "Two.")
    assert s2_story.migrate_manuscript() is None and len(s2_story.files()) == 2


def test_a_file_that_already_names_its_scene_keeps_its_name(home):
    u = vault.create_universe("U")
    s = u.new_story("Tale")
    s.add_scene("One", "* * * Chosen Name\n\nText.")
    s.add_scene("Two", "More.")
    s.migrate_manuscript()
    assert (s.manuscript_dir / "manuscript.md").read_text().startswith("* * * Chosen Name\n\nText.\n\n* * * Two\n\nMore.")


def test_an_empty_scene_file_still_makes_a_scene(home):
    u = vault.create_universe("U")
    s = u.new_story("Tale")
    s.add_scene("Full", "Words here.")
    s.add_scene("Blank", "")
    s.migrate_manuscript()
    assert [e["title"] for e in s.scene_list()] == ["Full", "Blank"]


def test_starting_the_writer_migrates_first(home):
    s, _ = legacy(home)
    writer.command(s)
    assert [p.name for p in s.files()] == ["manuscript.md"]


def test_the_migrate_report_reaches_the_builder_and_the_json(home):
    import subprocess, os, sys
    s, _ = legacy(home)
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "home"), STORYWHEEL_LIBRARY=str(home / "library"), PYTHONIOENCODING="utf-8")
    root = Path(__file__).resolve().parent.parent
    run = lambda *a: subprocess.run([sys.executable, "-m", "storywheel", *a], capture_output=True, text=True, env=env, cwd=root).stdout
    before = json.loads(run("story", "show", "u/tale", "--json"))
    assert before["files"] == ["01-opening.md", "02-the-letter.md", "03-ending.md"]       # showing never changes anything
    said = run("migrate")
    assert "U / Tale: Merged 3 scene files into manuscript.md" in said
    data = json.loads(run("story", "show", "u/tale", "--json"))
    assert data["files"] == ["manuscript.md"] and data["scenes"] == ["Opening", "The letter", "Ending"]
    assert "Nothing to migrate" in run("migrate")


# --- export from markers ------------------------------------------------------------------------------------------------------

def test_markers_become_hash_breaks_and_a_leading_marker_is_dropped(home):
    docx = pytest.importorskip("docx")
    u = vault.create_universe("U")
    s = u.new_story("Tale")
    s.append_scene("Opening", "First scene words.\n\nMore of it.")
    s.append_scene("The Letter", "Second scene words.")
    s.append_scene("", "Third.")
    settings.save_global({"legal_name": "A. Writer"})
    result = export.export(s, "docx")
    d = docx.Document(result["path"])
    texts = [p.text for p in d.paragraphs]
    assert texts.count("#") == 2 and "Opening" not in " ".join(texts[5:]) and "The Letter" not in " ".join(texts[5:])
    body = texts[texts.index("by A. Writer") + 1:]
    assert [t for t in body if t] == ["First scene words.", "More of it.", "#", "Second scene words.", "#", "Third.", "END"]
    assert result["words"] == 10
    assert export.plain_text(s) == "First scene words.\n\nMore of it.\n\n#\n\nSecond scene words.\n\n#\n\nThird."


def test_markdown_export_has_plain_breaks(home):
    u = vault.create_universe("U")
    s = u.new_story("Tale")
    s.append_scene("Opening", "One.")
    s.append_scene("Next", "Two.")
    text = Path(export.export(s, "md")["path"]).read_text()
    assert "* * * Next" not in text and "\n\n* * *\n\nTwo." in text and "* * * Opening" not in text


def test_markers_next_to_text_without_blank_lines_still_break(home):
    assert export.paragraphs("One.\n* * * Two\nThree.") == [("text", "One."), ("scene_break", ""), ("text", "Three.")]


# --- the Writer ------------------------------------------------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


@pytest.fixture
def story(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    s.append_scene("Opening", "Stacie ran down the road.\n\nIt was *very* dry.")
    s.append_scene("The Letter", "A letter came on Tuesday.")
    s.append_scene("", "By Friday it was gone.")
    settings.save_story(s.path, {"notepad_mode": False})
    return s


def test_lua_and_python_find_the_same_scenes(home, story):
    samples = ["", "Plain text.", "* * * Opening\n\nText here.\n\n* * *\n\nNext one.", "Before.\n\n* * * After\n\nBody.",
               "\n\n* * * Named\ntext", "* * *\n* * *", "a\n* * * T\nb c\n\n\n* * *\nd"]
    r = run_lua(story, """
        local samples = vim.json.decode([==[%s]==])
        R.out = {}
        for _, t in ipairs(samples) do
            local row = {}
            for _, sc in ipairs(require("sw.util").parse_scenes(vim.split(t, "\\n", { plain = true }))) do
                row[#row + 1] = { sc.start, sc.finish, sc.label, sc.marked, sc.first_line, sc.words }
            end
            R.out[#R.out + 1] = row
        end
    """ % json.dumps(samples))
    expected = [[list(x) for x in scenes(t)] for t in samples]
    assert r["out"] == expected


def test_the_scene_list_in_lua_matches_python(home, story):
    r = run_lua(story, """
        R.scenes = {}
        for _, sc in ipairs(require("sw.story").scene_list()) do R.scenes[#R.scenes + 1] = { sc.n, sc.title, sc.start, sc.words, sc.first_line } end
    """)
    py = [[e["n"], e["title"], e["line"], e["words"], e["first_line"]] for e in story.scene_list()]
    assert r["scenes"] == py


def test_the_writer_opens_at_the_scene_the_builder_asked_for(home, story):
    entry = story.scene_list()[1]
    r = run_lua(story, 'R.name = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(0), ":t"); R.cursor = vim.api.nvim_win_get_cursor(0)',
                env_extra={"STORYWHEEL_SCENE": f"{entry['path']}:{entry['line']}"})
    assert r["name"] == "manuscript.md" and r["cursor"] == [9, 0]                    # the first line of text, not the marker line


def test_a_bad_scene_request_is_ignored(home, story):
    r = run_lua(story, 'R.cursor = vim.api.nvim_win_get_cursor(0)', env_extra={"STORYWHEEL_SCENE": "/nowhere/x.md:3"})
    assert r["cursor"][0] >= 1


def test_the_status_line_counts_the_scene_you_are_in(home, story):
    r = run_typed(story, "vim.api.nvim_win_set_cursor(0, { 9, 0 })", "", """
        local st = require("sw.stats")
        R.scene = st.scene(); R.total = st.manuscript()
    """)
    assert r["scene"] == 5 and r["total"] == vault.count_words((story.manuscript_dir / "manuscript.md").read_text()) == 19


def test_a_named_marker_is_drawn_centered_with_its_title(home, story):
    r = run_lua(story, """
        local ns = require("sw.prose").ns
        local marks = vim.api.nvim_buf_get_extmarks(0, ns, 0, -1, { details = true })
        R.rows = {}
        for _, m in ipairs(marks) do
            if m[4].conceal then
                local chunks = {}
                for _, c in ipairs(m[4].virt_text) do chunks[#chunks + 1] = c[1] end
                R.rows[#R.rows + 1] = { m[2], table.concat(chunks), m[4].virt_text_win_col }
            end
        end
    """)
    titles = {row[0]: row[1] for row in r["rows"]}
    assert titles[0] == "*     *     *   Opening" and titles[6] == "*     *     *   The Letter" and titles[10] == "*     *     *"


def test_the_first_line_after_a_marker_gets_the_paragraph_indent(home, story):
    r = run_lua(story, """
        local marks = vim.api.nvim_buf_get_extmarks(0, require("sw.prose").ns, 0, -1, { details = true })
        R.rows = {}
        for _, m in ipairs(marks) do if m[4].virt_text_pos == "inline" then R.rows[#R.rows + 1] = m[2] end end
    """)
    assert r["rows"] == [2, 4, 8, 12]                                 # Stacie, It was, A letter, By Friday


def test_adding_a_scene_in_the_writer_marks_it_and_opens_it(home, story):
    r = run_typed(story, "", ":lua require('sw.sidebar').toggle(); local p, l = require('sw.sidebar').add('The Epilogue'); require('sw').open_scene(p, { l + 1, 0 })<CR>iThe end.", """
        R.cursor = vim.api.nvim_win_get_cursor(0)
        R.titles = vim.tbl_map(function(s) return s.title end, require("sw.story").scene_list())
    """)
    assert r["titles"][-1] == "The Epilogue"
    text = (story.manuscript_dir / "manuscript.md").read_text()
    assert "* * * The Epilogue" in text and "The end." in text.split("* * * The Epilogue")[1]
