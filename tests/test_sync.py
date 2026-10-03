"""Syncing between machines with Syncthing: linking the shared files, settings that stay on one machine, conflicts."""
import json
import os
from pathlib import Path

import pytest

from storywheel import paths, settings, sync, vault
from storywheel.cli import main as cli


@pytest.fixture
def folder(home, tmp_path):
    return tmp_path / "Writing"


def seed_home(home):
    h = home / "home"
    h.mkdir(exist_ok=True)
    (h / "ratings.json").write_text('{"ratings": []}')
    (h / "vocabulary.json").write_text('{"known": ["a"]}')
    (h / "lists").mkdir()
    (h / "lists" / "mine.json").write_text("{}")
    (h / "nvim").mkdir()
    (h / "nvim" / "state").write_text("x")
    (h / "state.json").write_text("{}")
    (h / "dictionary.sqlite").write_text("not really")
    settings.save_global({"legal_name": "Ada Voss", "neovide": True, "writer_font": "Iosevka"})
    return h


def test_machine_settings_live_in_their_own_file(home):
    h = seed_home(home)
    shared = (h / "settings.toml").read_text()
    local = (h / "settings.local.toml").read_text()
    assert "legal_name" in shared and "neovide" not in shared and "writer_font" not in shared
    assert "neovide = true" in local and "writer_font" in local and "legal_name" not in local
    g = settings.load_global()
    assert g["legal_name"] == "Ada Voss" and g["neovide"] is True and g["writer_font"] == "Iosevka"


def test_an_older_settings_file_with_machine_keys_is_split_the_next_time_it_is_saved(home):
    h = home / "home"
    h.mkdir(exist_ok=True)
    (h / "settings.toml").write_text('library = "/old/place"\nlegal_name = "X"\nneovide = true\n')
    assert paths.library_root() == Path("/old/place") or os.environ.get("STORYWHEEL_LIBRARY")
    settings.save_global({"email": "a@b.c"})
    assert "library" not in (h / "settings.toml").read_text() and 'library = "/old/place"' in (h / "settings.local.toml").read_text()
    assert settings.load_global()["neovide"] is True


def test_link_moves_shared_files_into_the_sync_folder_and_leaves_links(home, folder):
    h = seed_home(home)
    lines = sync.link(folder)
    data = folder / ".storywheel"
    for name in ("ratings.json", "vocabulary.json", "lists", "settings.toml"):
        assert (h / name).is_symlink() and (data / name).exists() and (h / name).resolve() == (data / name).resolve()
    assert (h / "lists" / "mine.json").read_text() == "{}"
    assert json.loads((h / "vocabulary.json").read_text()) == {"known": ["a"]}
    for name in ("nvim", "state.json", "dictionary.sqlite", "settings.local.toml"):             # machine things stay
        assert not (h / name).is_symlink() and not (data / name).exists()
    stignore = (folder / ".stignore").read_text()
    assert "dictionary.sqlite" in stignore and "nvim" in stignore and "settings.local.toml" in stignore
    assert settings.load_global()["sync_folder"] == str(folder) and any("moved into the sync folder" in l for l in lines)
    assert sync.link(folder) == ["Everything was already linked."]                                  # (running it again changes nothing)


def test_link_never_overwrites_the_other_machines_copy(home, folder):
    h = seed_home(home)
    (folder / ".storywheel").mkdir(parents=True)
    (folder / ".storywheel" / "ratings.json").write_text('{"ratings": ["theirs"]}')
    lines = sync.link(folder)
    assert json.loads((h / "ratings.json").read_text()) == {"ratings": ["theirs"]}
    assert json.loads((h / ".pre-sync" / "ratings.json").read_text()) == {"ratings": []}
    assert any("the sync folder already had one" in l for l in lines)


def test_plan_says_what_would_happen_without_doing_it(home, folder):
    seed_home(home)
    plan = dict(sync.plan(folder))
    assert plan["ratings.json"] == "moved into the sync folder and linked" and plan["genres.json"] == "nothing yet"
    assert not (folder / ".storywheel").exists()


def test_unlink_turns_links_into_files_again(home, folder):
    h = seed_home(home)
    sync.link(folder)
    sync.unlink()
    assert not (h / "ratings.json").is_symlink() and (h / "ratings.json").read_text() == '{"ratings": []}'
    assert (h / "lists" / "mine.json").exists() and settings.load_global()["sync_folder"] == ""


def make_conflict(folder, name="story.md", mine="Line one.\nLine two.\n", other="Line one.\nLine 2 changed.\nLine three.\n"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(mine)
    c = folder / name.replace(".md", ".sync-conflict-20261002-153000-ABCDEFG.md")
    c.write_text(other)
    return folder / name, c


def test_conflict_files_are_found_anywhere_in_the_folder_and_described(home, folder):
    settings.save_global({"sync_folder": str(folder)})
    mine, other = make_conflict(folder / "universes" / "u" / "stories" / "s" / "manuscript")
    (folder / "ordinary.md").write_text("x")
    (folder / ".git").mkdir()
    (folder / ".git" / "a.sync-conflict-20261002-153000-ABCDEFG.md").write_text("ignored")
    found = sync.find_conflicts()
    assert [c.path for c in found] == [other] and found[0].original == mine
    s = found[0].summary()
    assert "story.md" in s and "yours" in s and "2026-10-02 15:30" in s


def test_diff_shows_both_sides(home, folder):
    settings.save_global({"sync_folder": str(folder)})
    mine, other = make_conflict(folder)
    lines = sync.diff(sync.find_conflicts()[0])
    assert "-Line two." in lines and "+Line 2 changed." in lines and "+Line three." in lines
    (folder / "same.md").write_text("a\n")
    (folder / "same.sync-conflict-20261002-153000-ABCDEFG.md").write_text("a\n")
    c = next(c for c in sync.find_conflicts() if c.original.name == "same.md")
    assert sync.diff(c) == ["The two copies are identical."]


def test_keep_mine_trashes_the_other_copy_and_keep_other_trashes_mine(home, folder):
    settings.save_global({"sync_folder": str(folder)})
    mine, other = make_conflict(folder)
    c = sync.find_conflicts()[0]
    assert "Kept yours" in sync.keep(c, "mine")
    assert mine.read_text().startswith("Line one.\nLine two.") and not other.exists() and sync.find_conflicts() == []
    trashed = list((paths.library_root() / ".trash").iterdir())
    assert len(trashed) == 1 and "Line 2 changed." in trashed[0].read_text()
    mine, other = make_conflict(folder, mine="old\n", other="new\n")
    assert "Kept the other copy" in sync.keep(sync.find_conflicts()[0], "other")
    assert mine.read_text() == "new\n" and not other.exists()
    assert len(list((paths.library_root() / ".trash").iterdir())) == 2


def test_keep_other_restores_a_file_that_was_deleted_here(home, folder):
    settings.save_global({"sync_folder": str(folder)})
    folder.mkdir(parents=True)
    other = folder / "gone.sync-conflict-20261002-153000-ABCDEFG.md"
    other.write_text("saved text\n")
    c = sync.find_conflicts()[0]
    assert "missing" in c.summary()
    sync.keep(c, "other")
    assert (folder / "gone.md").read_text() == "saved text\n"


def test_the_command_line(home, folder, capsys):
    seed_home(home)
    cli(["sync", "link", str(folder)])
    out = capsys.readouterr().out
    assert "ratings.json: moved into the sync folder and linked" in out and "Install Syncthing" in out and "Share the folder" in out
    mine, other = make_conflict(folder)
    cli(["sync", "conflicts"])
    out = capsys.readouterr().out
    assert "1 sync conflict" in out and "story.md" in out
    cli(["sync", "diff", other.name])
    assert "+Line three." in capsys.readouterr().out
    cli(["sync", "keep", str(other), "--other"])
    assert mine.read_text().startswith("Line one.\nLine 2 changed.") 
    cli(["sync"])
    out = capsys.readouterr().out
    assert "Sync folder:" in out and "Conflicts: 0" in out
    with pytest.raises(SystemExit):
        cli(["sync", "keep", "nothing.md"])


def test_status_reports_whether_library_and_manuscripts_are_inside(home, folder, monkeypatch):
    monkeypatch.delenv("STORYWHEEL_LIBRARY")
    monkeypatch.delenv("STORYWHEEL_MANUSCRIPTS", raising=False)
    settings.save_global({"sync_folder": str(folder), "library": str(folder / "storywheel"), "manuscripts_dir": str(folder)})
    st = sync.status()
    assert st["library_inside"] and st["manuscripts_inside"] and st["folder"] == str(folder)
    settings.save_global({"library": "/elsewhere/lib"})
    assert not sync.status()["library_inside"]


def test_steps_text_names_syncthing_and_the_folder(home, folder):
    text = sync.steps_text(folder)
    assert "sudo apt install syncthing" in text and "127.0.0.1:8384" in text and "Up to Date" in text


# --- the Builder shows conflicts -------------------------------------------------------------------------------------------------------

def run_builder(script, **kw):
    import asyncio
    from storywheel import builder
    async def go():
        app = builder.BuilderApp(**kw)
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


def test_the_builder_says_there_are_conflicts_and_lets_you_keep_one(home, folder):
    from conftest import screen_text
    vault.create_universe("U")
    settings.save_global({"sync_folder": str(folder)})
    mine, other = make_conflict(folder)
    async def script(app, pilot):
        await pilot.pause()
        said = " ".join(screen_text(app).split())
        await pilot.press("Y")
        await pilot.pause()
        shown = screen_text(app)
        await pilot.press("o")
        await pilot.pause()
        after = " ".join(screen_text(app).split())
        await pilot.press("q")
        await pilot.pause()
        return said, shown, after
    said, shown, after = run_builder(script)
    assert "1 sync conflict" in said and "Press Y to compare" in said
    assert "+Line three." in shown and "-Line two." in shown and "Keep other copy" in shown
    assert "Kept the other copy of story.md" in after and "No sync conflicts." in after
    assert mine.read_text().startswith("Line one.\nLine 2 changed.") and not other.exists()


def test_no_conflicts_no_message(home, folder):
    from conftest import screen_text
    vault.create_universe("U")
    async def script(app, pilot):
        await pilot.pause()
        return " ".join(screen_text(app).split())
    assert "sync conflict" not in run_builder(script)
