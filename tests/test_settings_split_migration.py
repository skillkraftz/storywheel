"""Machine-only settings live in settings.local.toml; old links into a shared folder are turned back into real files."""
import os
from pathlib import Path

from storywheel import migrate, paths, settings
from storywheel.cli import main as cli


def test_machine_settings_live_in_their_own_file(home):
    h = home / "home"
    h.mkdir(exist_ok=True)
    settings.save_global({"legal_name": "Ada Voss", "neovide": True, "writer_font": "Iosevka", "update_remote": "xps:projects/storywheel"})
    shared, local = (h / "settings.toml").read_text(), (h / "settings.local.toml").read_text()
    assert "legal_name" in shared and "neovide" not in shared and "writer_font" not in shared and "update_remote" not in shared
    assert "neovide = true" in local and "update_remote" in local and "legal_name" not in local
    g = settings.load_global()
    assert g["legal_name"] == "Ada Voss" and g["neovide"] is True and g["update_remote"] == "xps:projects/storywheel"


def test_an_older_settings_file_with_machine_keys_is_split_when_saved(home):
    h = home / "home"
    h.mkdir(exist_ok=True)
    (h / "settings.toml").write_text('library = "/old/place"\nlegal_name = "X"\nneovide = true\n')
    settings.save_global({"email": "a@b.c"})
    assert "library" not in (h / "settings.toml").read_text() and 'library = "/old/place"' in (h / "settings.local.toml").read_text()
    assert settings.load_global()["neovide"] is True


def make_links(home, tmp_path):
    shared = tmp_path / "Writing" / ".storywheel"
    (shared / "lists").mkdir(parents=True)
    (shared / "lists" / "mine.json").write_text("{}")
    (shared / "ratings.json").write_text('{"ratings": []}')
    (shared / "vocabulary.json").write_text('{"known": ["a"]}')
    h = home / "home"
    h.mkdir(exist_ok=True)
    for name in ("lists", "ratings.json", "vocabulary.json"):
        os.symlink(shared / name, h / name)
    os.symlink(shared / "gone.json", h / "recent.json")                       # a link whose target no longer exists
    (h / "state.json").write_text("{}")
    return h, shared


def test_links_into_a_shared_folder_become_real_files_and_the_folder_is_untouched(home, tmp_path):
    h, shared = make_links(home, tmp_path)
    before = sorted(str(p.relative_to(shared)) for p in shared.rglob("*"))
    lines = migrate.migrate_sync_links()
    for name in ("lists", "ratings.json", "vocabulary.json"):
        assert not (h / name).is_symlink()
    assert (h / "lists" / "mine.json").read_text() == "{}" and (h / "ratings.json").read_text() == '{"ratings": []}'
    assert not (h / "recent.json").exists() and not (h / "recent.json").is_symlink()
    assert sorted(str(p.relative_to(shared)) for p in shared.rglob("*")) == before and (shared / "ratings.json").exists()
    text = "\n".join(lines)
    assert "ratings.json was a link into" in text and "real file" in text and "left as it was" in text and "recent.json was a link" in text and "gone" in text
    assert migrate.migrate_sync_links() == []                                  # (one time: nothing left to do)


def test_the_migration_runs_from_the_migrate_command(home, tmp_path, capsys):
    h, shared = make_links(home, tmp_path)
    cli(["migrate"])
    assert "was a link into" in capsys.readouterr().out and not (h / "ratings.json").is_symlink()


def test_no_sync_code_is_left():
    root = Path(__file__).resolve().parent.parent / "storywheel"
    assert not (root / "sync.py").exists()
    text = " ".join(p.read_text() for p in root.rglob("*.py") if p.name != "migrate.py")
    for needle in ("syncthing", "Syncthing", "sync-conflict", "stignore", "sync_folder", "storywheel sync"):
        assert needle not in text, needle
    r = __import__("subprocess").run(["python3", "-m", "storywheel", "sync"], capture_output=True, text=True, cwd=str(root.parent))
    assert r.returncode != 0 and "invalid choice" in r.stderr


def test_the_old_sync_folder_setting_is_dropped(home):
    h = home / "home"
    h.mkdir(exist_ok=True)
    (h / "settings.local.toml").write_text('sync_folder = "/x"\nneovide = true\n')
    assert any("sync_folder" in l for l in migrate.migrate_sync_links())
    assert "sync_folder" not in (h / "settings.local.toml").read_text() and settings.load_global()["neovide"] is True
