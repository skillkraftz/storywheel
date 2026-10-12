"""Batch 24 B5: the Writer's page count comes from the PDF's own pagination (keep-together, (MORE)/(CONT'D)), so the two agree."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from storywheel import fountain, screenplay_pdf as sp, vault, writer
from test_notepad import run  # noqa: F401  (the headless Writer driver)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "screenplay" / "the-lamp.fountain"
needs_nvim = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")

LONG_SPEECH = " ".join(f"Sentence {i} goes on for a while and then it stops." for i in range(1, 9))


def long_script(scenes=30):
    """Scenes whose headings, long speeches and action fall on page feet in all sorts of places."""
    parts = ["Title: Long", "Credit: Written by", "", "FADE IN:", ""]
    for i in range(scenes):
        parts += [f"INT. ROOM {i} - DAY", "", "She waits by the window. " * (1 + i % 5), "", "MARA", f"(beat {i})", LONG_SPEECH[: 120 + (i * 37) % 300], "",
                  "BRAM", "Yes.", "", "MARA", "No. " + LONG_SPEECH, "", "CUT TO:", ""]
    return "\n".join(parts)


SCRIPTS = {"fixture": FIXTURE.read_text(encoding="utf-8"), "long": long_script(), "short": "INT. ROOM - DAY\n\nShe waits.\n\nMARA\nHello.\n",
           "empty": ""}


@pytest.mark.parametrize("name", list(SCRIPTS))
def test_the_estimate_is_the_pdfs_own_page_count(tmp_path, name):
    text = SCRIPTS[name]
    pdf = tmp_path / "s.pdf"
    real = sp.render(text, pdf, {"title": ["T"]} if name != "empty" else None, contd=True)
    assert sp.page_count(text, True) == (real if name != "empty" else 0)                          # (an empty script is 0 pages; the PDF still has its blank one)
    est = sp.estimate_pages(text, True)
    assert (est == 0 and real == 1) or (real - 1 < est <= real)                                   # (the last page as a fraction of a page)
    data = pdf.read_bytes()
    assert len(re.findall(rb"/Type\s*/Page[^s]", data)) == real + (1 if name != "empty" else 0)  # (a title page, then the script pages)


def test_a_heading_is_never_the_last_thing_on_a_page_and_speeches_break_with_more_and_contd():
    pages = sp.paginate(SCRIPTS["long"], True)
    assert len(pages) > 5
    text = "\n".join(ln.text for pg in pages for ln in pg.lines if ln is not None)
    assert "(MORE)" in text and "(CONT'D)" in text
    for pg in pages:
        printed = [ln for ln in pg.lines if ln is not None]
        assert printed and printed[-1].kind != "heading"


def test_the_command_line_counts_from_stdin_the_way_the_pdf_does():
    text = SCRIPTS["long"]
    out = subprocess.run([sys.executable, "-m", "storywheel", "script", "pages", "-", "--json", "--contd"], input=text, capture_output=True, text=True, cwd=ROOT)
    data = json.loads(out.stdout)
    assert out.returncode == 0 and data["count"] == sp.page_count(text, True) and data["pages"] == sp.estimate_pages(text, True)
    plain = subprocess.run([sys.executable, "-m", "storywheel", "script", "pages", "-"], input=text, capture_output=True, text=True, cwd=ROOT)
    assert float(plain.stdout) == sp.estimate_pages(text, False)


@pytest.fixture
def script_story(home):
    u = vault.create_universe("Thornwood", ["horror"])
    s = u.new_story("Long", {"structure": "Short Film"})
    s.script_path.parent.mkdir(parents=True, exist_ok=True)
    s.script_path.write_text(SCRIPTS["long"], encoding="utf-8")
    return s


@needs_nvim
def test_the_writers_status_line_agrees_with_the_pdf(home, script_story, tmp_path):
    real = sp.render(SCRIPTS["long"], tmp_path / "x.pdf", None, contd=True)
    r = run(script_story, "", "", """
        local script = require('sw.script')
        local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
        R.quick = math.ceil(script.estimate_pages(lines))
        R.now = script.pages_now(lines)
        R.status = script.status(0)
    """, env_extra={"PYTHONPATH": str(ROOT), "STORYWHEEL_PY": sys.executable})
    assert r["now"]["count"] == real and f"p. {real}" in r["status"]
    assert r["quick"] != real or real > 0                                                          # (the flat 4% estimate is only the fallback now)


@needs_nvim
def test_the_status_line_asks_in_the_background_and_shows_the_real_count_when_it_arrives(home, script_story, tmp_path):
    real = sp.render(SCRIPTS["long"], tmp_path / "x.pdf", None, contd=True)
    r = run(script_story, "", "", """
        local script = require('sw.script')
        script.delay_ms = 20
        script.cli_pages = nil
        script.requested = nil
        R.first = script.status(0)                                   -- (the quick estimate while the paginator works)
        vim.wait(10000, function() return script.cli_pages ~= nil end, 50)
        R.count = script.cli_pages and script.cli_pages.count
        R.after = script.status(0)
    """, env_extra={"PYTHONPATH": str(ROOT), "STORYWHEEL_PY": sys.executable})
    assert r["count"] == real and r["after"].startswith(f"p. {real}")
