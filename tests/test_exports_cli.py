"""Every export records what it was made from; `exports status` and `exports make` (for homesync and scripts)."""
import json

import pytest

from storywheel import export, settings, vault
from storywheel.cli import main as cli


@pytest.fixture
def two(home):
    settings.save_global({"author_name": "Ada Voss", "legal_name": "Ada Voss", "export_format": "md"})
    u = vault.create_universe("Thornwood", ["western"])
    a, b = u.new_story("The Last Clause"), u.new_story("Dry Years")
    a.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (a.manuscript_dir / "manuscript.md").write_text("The rain came early.\nShe waited for the sheriff.\n")
    return u, a, b                                                          # b has no manuscript at all


def run(capsys, *args):
    cli(list(args))
    return capsys.readouterr().out


def test_an_export_records_what_it_was_made_from(two):
    _u, a, _b = two
    result = export.export(a, "md")
    folder = export.export_folder(a, create=False)
    doc = json.loads((folder / ".storywheel-exports.json").read_text())
    assert doc["story"] == "thornwood/the-last-clause" and len(doc["exports"]) == 1
    e = doc["exports"][0]
    assert e["file"] == result["path"].rsplit("/", 1)[1] and e["format"] == "md" and e["words"] == 9
    assert e["hash"] == export.content_hash(a) and len(e["hash"]) == 64 and e["date"][:4].isdigit() and e["anonymous"] is False
    export.export(a, "txt")
    assert [x["format"] for x in json.loads((folder / ".storywheel-exports.json").read_text())["exports"]] == ["md", "txt"]


def test_status_for_a_story_never_exported(two, capsys):
    rows = json.loads(run(capsys, "exports", "status", "--json"))
    by = {r["story"]: r for r in rows}
    a = by["thornwood/the-last-clause"]
    assert a["state"] == "never exported" and a["last_export"] is None and a["changed"] is None and a["words"] == 9
    assert a["default_format"] == "md" and a["folder"] == "" and len(a["hash"]) == 64
    assert by["thornwood/dry-years"]["words"] == 0 and by["thornwood/dry-years"]["state"] == "never exported"
    assert export.export_folder(two[1], create=False) is None                # (looking never makes a folder)


def test_status_after_an_export_and_after_a_one_word_change(two, capsys):
    _u, a, _b = two
    path = run(capsys, "exports", "make", "thornwood/the-last-clause").strip()
    assert path.endswith(".md")
    row = next(r for r in json.loads(run(capsys, "exports", "status", "--json")) if r["story"] == "thornwood/the-last-clause")
    assert row["state"] == "up to date" and row["changed"] is False and row["last_export"]["words"] == 9
    assert row["last_export"]["file"] == path.rsplit("/", 1)[1] and row["folder"] == str(export.export_folder(a, create=False))
    (a.manuscript_dir / "manuscript.md").write_text("The rain came late.\nShe waited for the sheriff.\n")          # one word swapped: same word count
    row = next(r for r in json.loads(run(capsys, "exports", "status", "--json")) if r["story"] == "thornwood/the-last-clause")
    assert row["words"] == 9 and row["last_export"]["words"] == 9 and row["state"] == "changed" and row["changed"] is True     # (by hash, not by count)
    run(capsys, "exports", "make", "thornwood/the-last-clause")
    row = next(r for r in json.loads(run(capsys, "exports", "status", "--json")) if r["story"] == "thornwood/the-last-clause")
    assert row["state"] == "up to date"


def test_status_text(two, capsys):
    run(capsys, "exports", "make", "thornwood/the-last-clause")
    out = run(capsys, "exports", "status")
    assert "thornwood/the-last-clause" in out and "state: up to date" in out and "default format: md" in out and "last export: 9 words" in out
    assert "state: never exported" in out and "(none yet)" in out


def test_make_uses_the_story_default_format_and_its_export_settings(two, capsys):
    _u, a, _b = two
    settings.save_story(a.path, {"export_format": "docx", "export_anonymous": True})
    path = run(capsys, "exports", "make", "thornwood/the-last-clause").strip()
    assert path.endswith(".docx")
    from docx import Document
    text = "\n".join(p.text for p in Document(path).paragraphs)
    assert "Ada Voss" not in text                                           # anonymous, as the story's settings say
    row = next(r for r in json.loads(run(capsys, "exports", "status", "--json")) if r["story"] == "thornwood/the-last-clause")
    assert row["default_format"] == "docx" and row["anonymous"] is True
    assert json.loads(open(export.export_folder(a, create=False) / ".storywheel-exports.json").read())["exports"][-1]["anonymous"] is True


def test_make_takes_a_format_a_story_slug_and_json(two, capsys):
    out = json.loads(run(capsys, "exports", "make", "the-last-clause", "--format", "txt", "--json"))
    assert out["format"] == "txt" and out["path"].endswith(".txt") and out["story"] == "thornwood/the-last-clause" and out["words"] >= 9
    assert out["hash"] == export.content_hash(two[1])


def test_make_says_plainly_when_it_cannot(two, capsys):
    with pytest.raises(SystemExit) as e:
        cli(["exports", "make", "thornwood/dry-years"])
    assert e.value.code == 1 and "manuscript is empty" in capsys.readouterr().out
    with pytest.raises(SystemExit) as e:
        cli(["exports", "make", "thornwood/dry-years", "--json"])
    assert "empty" in json.loads(capsys.readouterr().out)["error"]
    with pytest.raises(SystemExit) as e:
        cli(["exports", "make", "nope/none"])
    with pytest.raises(SystemExit) as e:
        cli(["exports", "make", "no-such-story"])
    assert "No story 'no-such-story'" in str(e.value)
    with pytest.raises(SystemExit) as e:
        cli(["exports", "make"])
    assert "needs a story" in str(e.value)


def test_a_slug_in_two_universes_must_be_qualified(two):
    vault.create_universe("Other").new_story("The Last Clause")
    with pytest.raises(SystemExit) as e:
        cli(["exports", "make", "the-last-clause"])
    assert "several universes" in str(e.value)
