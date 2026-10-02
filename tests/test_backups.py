"""Restore from backups: list every kind with date, words and a preview; restoring first copies the current version aside."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from storywheel import backups, vault

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def story(home):
    u = vault.create_universe("Thornwood")
    s = u.new_story("The Last Clause")
    s.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "manuscript.md").write_text("Now it says this.\nThree words more.\n", encoding="utf-8")
    b = s.path / ".backups"
    (b / "2026-10-01").mkdir(parents=True)
    (b / "2026-10-01" / "0930-manuscript.md").write_text("Older version.\n", encoding="utf-8")
    (b / "2026-10-02").mkdir()
    (b / "2026-10-02" / "1415-manuscript.md").write_text("A longer version of the story.\nWith two lines.\n", encoding="utf-8")
    (b / "migrated-20260915-101010").mkdir()
    (b / "migrated-20260915-101010" / "01-opening.md").write_text("The old scene file.\n", encoding="utf-8")
    (b / "quotes-20260920-120000").mkdir()
    (b / "quotes-20260920-120000" / "manuscript.md").write_text("It’s curly.\n", encoding="utf-8")
    (b / "paragraphs-20260918-080000").mkdir()
    (b / "paragraphs-20260918-080000" / "manuscript.md").write_text("Wrapped\nline.\n\nNext.\n", encoding="utf-8")
    return s


def test_every_kind_is_listed_newest_first_with_date_file_and_words(story):
    rows = backups.list_backups(story)
    assert [r["id"] for r in rows] == ["2026-10-02/1415-manuscript.md", "2026-10-01/0930-manuscript.md", "quotes-20260920-120000/manuscript.md",
                                       "paragraphs-20260918-080000/manuscript.md", "migrated-20260915-101010/01-opening.md"]
    top = rows[0]
    assert top["kind"] == "rolling" and top["when"] == "2026-10-02 14:15" and top["file"] == "manuscript.md" and top["words"] == 9
    assert top["what"] == "while writing"
    kinds = {r["kind"]: r for r in rows}
    assert kinds["migrated"]["file"] == "01-opening.md" and kinds["migrated"]["when"] == "2026-09-15 10:10"
    assert kinds["quotes"]["what"] == "before quotes were made straight" and kinds["paragraphs"]["words"] == 3


def test_no_backups_is_an_empty_list(home):
    s = vault.create_universe("U").new_story("S")
    assert backups.list_backups(s) == []


def test_preview_shows_the_first_lines(story):
    e = backups.find(story, "2026-10-02/1415-manuscript.md")
    assert backups.preview(e).split("\n") == ["A longer version of the story.", "With two lines."]
    assert backups.find(story, "nope") is None
    long = story.path / ".backups" / "2026-10-02" / "1500-manuscript.md"
    long.write_text("\n".join(f"line {i}" for i in range(40)), encoding="utf-8")
    assert len(backups.preview(backups.find(story, "2026-10-02/1500-manuscript.md"), lines=5).split("\n")) == 5


def test_restore_puts_the_backup_back_and_keeps_what_was_there(story):
    result = backups.restore(story, "2026-10-01/0930-manuscript.md")
    assert (story.manuscript_dir / "manuscript.md").read_text() == "Older version.\n"
    assert result["restored"] == "manuscript.md" and result["words"] == 2
    kept = Path(result["kept"])
    assert kept.read_text() == "Now it says this.\nThree words more.\n" and "restore-" in kept.parent.name
    # the safety copy is itself a backup that can be restored: a restore can be undone
    rows = backups.list_backups(story)
    again = next(r for r in rows if r["kind"] == "restore")
    assert again["file"] == "manuscript.md" and again["what"] == "before a restore"
    backups.restore(story, again["id"])
    assert (story.manuscript_dir / "manuscript.md").read_text() == "Now it says this.\nThree words more.\n"


def test_restoring_an_old_scene_file_puts_it_back_next_to_the_manuscript(story):
    backups.restore(story, "migrated-20260915-101010/01-opening.md")
    assert (story.manuscript_dir / "01-opening.md").read_text() == "The old scene file.\n"
    assert (story.manuscript_dir / "manuscript.md").read_text().startswith("Now it says")


def test_restoring_with_no_current_file_has_nothing_to_keep(story):
    (story.manuscript_dir / "manuscript.md").unlink()
    result = backups.restore(story, "2026-10-01/0930-manuscript.md")
    assert result["kept"] is None and (story.manuscript_dir / "manuscript.md").read_text() == "Older version.\n"


def test_restoring_an_unknown_backup_is_an_error(story):
    with pytest.raises(ValueError, match="no backup"):
        backups.restore(story, "2020-01-01/0000-manuscript.md")


def test_the_cli_lists_shows_and_restores(story):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    def cli(*args):
        return subprocess.run([sys.executable, "-m", "storywheel", *args], capture_output=True, text=True, env=env, timeout=60)
    rows = json.loads(cli("backups", "list", "thornwood/the-last-clause", "--json").stdout)
    assert len(rows) == 5 and rows[0]["id"] == "2026-10-02/1415-manuscript.md"
    assert "A longer version" in cli("backups", "show", "thornwood/the-last-clause", "2026-10-02/1415-manuscript.md").stdout
    out = cli("backups", "restore", "thornwood/the-last-clause", "2026-10-01/0930-manuscript.md", "--json")
    assert json.loads(out.stdout)["restored"] == "manuscript.md"
    assert (story.manuscript_dir / "manuscript.md").read_text() == "Older version.\n"
    assert cli("backups", "restore", "thornwood/the-last-clause", "bogus").returncode != 0
