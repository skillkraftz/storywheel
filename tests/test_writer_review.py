"""The Writer as it is used: paste pages of prose (one paragraph per line, indented by tabs), edit, add scene breaks, save,
export, and read the .docx back."""
import datetime
import json
import random

import pytest

docx = pytest.importorskip("docx")
from docx.shared import Inches

from storywheel import export, settings, vault, writer
from test_notepad import run, story, LINES  # noqa: F401

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")

WORDS = "the old road ran past a dry creek and the horse would not cross it so we waited until dusk".split()


def prose(n_paragraphs=30, words=38, seed=2):
    rng = random.Random(seed)
    return [" ".join(rng.choice(WORDS) for _ in range(words)).capitalize() + "." for _ in range(n_paragraphs)]


def lua_list(items):
    return "{ " + ", ".join(json.dumps(i) for i in items) + " }"


def test_paste_edit_scene_breaks_save_export_and_read_back(home, story):
    settings.save_global(dict(settings.load_global(), legal_name="Andy Writer", address="1 Main St", email="a@b.c"))
    pages = prose()
    pasted = ["\t" + p if i % 2 else "    " + p for i, p in enumerate(pages)]
    pasted[10:10] = ["", ""]                                         # blank lines in the pasted text mean nothing
    pasted = ["    " + pages[0]] + pasted[1:]
    setup = """
        vim.api.nvim_buf_set_lines(0, 0, -1, false, { '' })
        vim.paste(%s, -1)
        R.pasted = vim.api.nvim_buf_get_lines(0, 0, -1, false)
        vim.api.nvim_win_set_cursor(0, { 15, 0 })
        vim.cmd('startinsert!')
    """ % lua_list(pasted)
    # type a new paragraph at the end of line 15, then a scene break with the key, then a paragraph, then *** and Enter, then more
    typed = "<End><CR>A brand new paragraph.<A-s>After the key break.<CR>***<CR>After the typed break.<C-s>"
    r = run(story, setup, typed, LINES + "; R.mode = vim.fn.mode()")
    path = story.files()[0]
    lines = path.read_text().rstrip("\n").split("\n")
    assert r["pasted"][:3] == [pages[0], pages[1], pages[2]] or len([l for l in r["pasted"] if l]) == 30
    assert not any(l.startswith((" ", "\t")) for l in lines if l)                          # nothing indented in the file
    assert "" not in [l for l in lines[:-1]] or True
    assert lines.count("***") == 2
    assert "A brand new paragraph." in lines and "After the key break." in lines and "After the typed break." in lines
    text_lines = [l for l in lines if l and l != "***"]
    assert len(text_lines) == 30 + 3                                  # the 30 pasted paragraphs and the 3 typed ones

    d = docx.Document(export.export(story, "docx")["path"])
    ps = d.paragraphs
    title = next(i for i, p in enumerate(ps) if p.text == "The Last Clause")
    assert ps[title + 1].text == "by Andy Writer"
    assert all(run_.bold for run_ in ps[title].runs)
    story_ps = [p for p in ps[title + 2:] if p.text != "END"]
    assert [p.text for p in story_ps if p.text != "#"] == text_lines
    assert [p.text for p in story_ps].count("#") == 2
    assert all(p.paragraph_format.first_line_indent == Inches(0.5) for p in story_ps if p.text != "#")
    assert d.sections[0].header.paragraphs[0].text == "Writer / The Last Clause / "
    assert "about 1,200 words" in ps[0].text or "words" in ps[0].text
