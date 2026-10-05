"""Export the sample screenplays in tests/fixtures/screenplay as PDFs (and the-lamp as Final Draft too), next to them: the-lamp.fountain
(every Fountain element) and page-breaks.fountain (a speech broken with (MORE)/(CONT'D), a scene heading kept off the bottom of a page).

Everything happens in a temporary storywheel home and library with a made-up author, so your own files are never read or written:

    python tools/screenplay_sample.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "tests" / "fixtures" / "screenplay"


def main():
    tmp = Path(tempfile.mkdtemp(prefix="sw-sample-"))
    for var, sub in (("STORYWHEEL_HOME", "home"), ("STORYWHEEL_LIBRARY", "library"), ("STORYWHEEL_MANUSCRIPTS", "manuscripts")):
        os.environ[var] = str(tmp / sub)
    sys.path.insert(0, str(ROOT))
    from storywheel import export, settings, vault
    settings.save_global({"author_name": "Andy Example", "address": "12 Example Road\nExampletown EX1 2AB", "email": "andy@example.com",
                          "phone": "555 0100"})
    u = vault.create_universe("Holloway", ["ghost story"])
    story = u.new_story("The Lamp in the Attic", {"structure": "Short Film"})
    story.script_path.parent.mkdir(parents=True, exist_ok=True)
    story.script_path.write_text((HERE / "the-lamp.fountain").read_text(encoding="utf-8"), encoding="utf-8")
    for fmt in ("pdf", "fdx"):
        r = export.export(story, fmt)
        out = HERE / f"the-lamp.{fmt}"
        shutil.copy(r["path"], out)
        print(f"wrote {out.relative_to(ROOT)}" + "".join(f"\n  note: {w}" for w in r["warnings"]))
    r = export.export(story, "pdf", anonymous=True)
    shutil.copy(r["path"], HERE / "the-lamp-anonymous.pdf")
    print(f"wrote {(HERE / 'the-lamp-anonymous.pdf').relative_to(ROOT)}")
    other = u.new_story("Page Breaks", {"format": "screenplay"})
    other.script_path.parent.mkdir(parents=True, exist_ok=True)
    other.script_path.write_text((HERE / "page-breaks.fountain").read_text(encoding="utf-8"), encoding="utf-8")
    r = export.export(other, "pdf")
    shutil.copy(r["path"], HERE / "page-breaks.pdf")
    print(f"wrote {(HERE / 'page-breaks.pdf').relative_to(ROOT)}")
    shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
