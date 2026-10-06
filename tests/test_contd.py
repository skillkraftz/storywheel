"""Automatic (CONT'D) (batch 18): a character who speaks again after action in the same scene gets (CONT'D) in the PDF and, dimmed, on screen
in the Writer, when the `script_contd` setting is on (the default, as in Final Draft and Fade In). Across a page break it is always added."""
import pytest

from storywheel import export, fountain, screenplay_pdf as sp, settings, vault, writer

pdfplumber = pytest.importorskip("pdfplumber")


def marked(text):
    return [(e.name, e.line) for e in fountain.auto_contd(fountain.parse(text).elements)]


SCENE = """INT. KITCHEN - NIGHT

MARA
Is anyone there?

She listens. Nothing.

MARA
Hello?

BRAM (O.S.)
Only me.

MARA
Bram.

She sits.

MARA (V.O.)
I should have known.

EXT. YARD - NIGHT

MARA
Cold out here.
"""


def test_the_same_speaker_after_action_in_the_same_scene():
    assert marked(SCENE) == [("MARA", 8), ("MARA", 19)]
    # (line 14: Bram spoke in between; line 23: a new scene; line 19 keeps its V.O. and gets CONT'D after it)


def test_a_cue_that_already_says_contd_and_dual_dialogue_are_left_alone():
    assert marked("INT. A - DAY\n\nMARA\nOne.\n\nRain.\n\nMARA (CONT'D)\nTwo.\n") == []
    assert marked("INT. A - DAY\n\nMARA\nOne.\n\nRain.\n\nMARA\nTwo.\n\nBRAM ^\nThree.\n") == [("MARA", 8)]
    assert marked("INT. A - DAY\n\nMARA\nOne.\n\nBRAM ^\nX.\n\nRain.\n\nMARA\nTwo.\n") == []      # (after a dual pair: not a continuation)
    assert marked("INT. A - DAY\n\nMARA\nOne.\n\nCUT TO:\n\nMARA\nTwo.\n") == []                   # (a transition starts afresh)


def cues(text, contd, tmp_path):
    path = tmp_path / f"c{int(contd)}.pdf"
    sp.render(text, path, None, contd=contd)
    with pdfplumber.open(path) as pdf:
        words = [w for p in pdf.pages for w in p.extract_words(keep_blank_chars=True)]
    return [w["text"].strip() for w in words if 3.6 * 72 < w["x0"] < 3.8 * 72]


def test_the_pdf_adds_it_only_when_the_setting_is_on(tmp_path):
    on, off = cues(SCENE, True, tmp_path), cues(SCENE, False, tmp_path)
    assert on == ["MARA", "MARA (CONT'D)", "BRAM (O.S.)", "MARA", "MARA (V.O.) (CONT'D)", "MARA"]
    assert off == ["MARA", "MARA", "BRAM (O.S.)", "MARA", "MARA (V.O.)", "MARA"]


def test_a_page_break_never_doubles_it(tmp_path):
    fill = "\n".join([" ".join(["word"] * 11)] * 42)
    speech = " ".join(["Talking on and on about the house."] * 40)
    text = f"INT. ROOM - DAY\n\nMARA\nFirst.\n\n{fill}\n\nMARA\n{speech}\n"
    found = cues(text, True, tmp_path)
    assert found == ["MARA", "MARA (CONT'D)", "(MORE)", "MARA (CONT'D)"]                    # (the top of page 2: once, not twice)


@pytest.fixture
def script_story(home):
    settings.save_global({"author_name": "Andy Example"})
    u = vault.create_universe("Kitchen", ["noir"])
    s = u.new_story("Late", {"format": "short-film"})
    s.script_path.parent.mkdir(parents=True, exist_ok=True)
    s.script_path.write_text("Title: Late\n\n" + SCENE, encoding="utf-8")
    return s


def exported_cues(story):
    path = export.export(story, "pdf")["path"]
    with pdfplumber.open(path) as pdf:
        return [w["text"].strip() for p in pdf.pages[1:] for w in p.extract_words(keep_blank_chars=True) if 3.6 * 72 < w["x0"] < 3.8 * 72]


def test_the_export_follows_the_setting(script_story):
    assert "MARA (CONT'D)" in exported_cues(script_story)
    settings.save_story(script_story.path, {"script_contd": False})
    assert "MARA (CONT'D)" not in exported_cues(script_story)
    assert "(CONT'D)" not in script_story.script_path.read_text()                       # (the file keeps only the names)


def test_the_setting_is_a_switch_in_settings():
    from storywheel import settings_app
    fields = {key: kind for _title, rows in settings_app.SECTIONS for key, _label, kind, *_ in rows}
    assert fields["script_contd"] == "bool" and settings.GLOBAL_DEFAULTS["script_contd"] is True


VIRT = """
    local marks = vim.api.nvim_buf_get_extmarks(0, require('sw.script').ns, 0, -1, { details = true })
    R.rows = {}
    for _, m in ipairs(marks) do
      local vt = m[4].virt_text
      if vt and vt[1][1]:find("CONT'D", 1, true) then R.rows[#R.rows + 1] = m[2] + 1 end
    end
"""


@pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")
def test_the_writer_shows_it_dimmed_and_the_file_stays_plain(script_story):
    from test_notepad import run
    r = run(script_story, "", "", VIRT)
    assert r["rows"] == [10, 21]                                                       # (the two continuing cues: lines 8 and 19, after the title page)
    settings.save_story(script_story.path, {"script_contd": False})
    assert run(script_story, "", "", VIRT).get("rows", []) in ([], {})
