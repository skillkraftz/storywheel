"""Exports go to <manuscripts>/<Title>/<Title> <date>.<ext>; the library keeps its own layout and is never written into."""
import datetime
import os
from pathlib import Path

import pytest

docx = pytest.importorskip("docx")

from storywheel import export, migrate, paths, vault

TODAY = datetime.date.today().isoformat()


def make(name="Thornwood", title="The Last Clause", text="Some words here to export."):
    u = vault.get_universe(vault.slugify(name, "u")) or vault.create_universe(name)
    s = u.new_story(title)
    s.add_scene("Opening", text)
    return s


def root():
    return Path(os.environ["STORYWHEEL_MANUSCRIPTS"])


def test_the_path_is_folder_per_story_with_title_and_date(home):
    s = make()
    r = export.export(s, "docx")
    assert Path(r["path"]) == root() / "The Last Clause" / f"The Last Clause {TODAY}.docx"
    assert r["shown"] == r["path"] or r["shown"].startswith("~")
    for fmt in ("md", "txt"):
        assert Path(export.export(s, fmt)["path"]) == root() / "The Last Clause" / f"The Last Clause {TODAY}.{fmt}"
    assert not s.exports_dir.exists()                                    # nothing is written inside the library


def test_same_day_reexports_add_a_number_instead_of_overwriting(home):
    s = make()
    paths_ = [Path(export.export(s, "docx")["path"]).name for _ in range(3)]
    assert paths_ == [f"The Last Clause {TODAY}.docx", f"The Last Clause {TODAY} -2.docx", f"The Last Clause {TODAY} -3.docx"]


def test_a_different_story_with_the_same_title_gets_the_universe_name(home):
    a = make("Thornwood")
    b = make("Dry Country")
    pa, pb = Path(export.export(a, "md")["path"]), Path(export.export(b, "md")["path"])
    assert pa.parent.name == "The Last Clause" and pb.parent.name == "The Last Clause (Dry Country)"
    assert Path(export.export(b, "md")["path"]).parent == pb.parent               # the same story keeps its folder
    assert (pa.parent / export.MARKER).read_text().strip() == "thornwood/the-last-clause"


def test_an_unmarked_folder_with_files_is_not_taken_over(home):
    (root() / "The Last Clause").mkdir(parents=True)
    (root() / "The Last Clause" / "mine.txt").write_text("hand made")
    s = make()
    assert Path(export.export(s, "md")["path"]).parent.name == "The Last Clause (Thornwood)"
    assert (root() / "The Last Clause" / "mine.txt").read_text() == "hand made"


def test_odd_characters_in_a_title_are_removed_from_the_names(home):
    s = make(title='Who? "Me": A/B')
    p = Path(export.export(s, "txt")["path"])
    assert p.parent.name == "Who Me AB" and p.name == f"Who Me AB {TODAY}.txt"


def test_never_into_the_library(home):
    lib = paths.library_root()
    os.environ["STORYWHEEL_MANUSCRIPTS"] = str(lib)
    s = make()
    with pytest.raises(export.ExportError, match="inside your library"):
        export.export(s, "md")
    os.environ["STORYWHEEL_MANUSCRIPTS"] = str(lib / "universes")
    with pytest.raises(export.ExportError, match="inside your library"):
        export.export(s, "md")


def test_a_story_folder_named_like_the_library_is_avoided(home, monkeypatch):
    lib = home / "Writing" / "storywheel"
    monkeypatch.setenv("STORYWHEEL_LIBRARY", str(lib))
    monkeypatch.setenv("STORYWHEEL_MANUSCRIPTS", str(home / "Writing"))
    s = make(title="storywheel")
    p = Path(export.export(s, "md")["path"])
    assert p.parent == home / "Writing" / "storywheel (Thornwood)" and lib not in p.parents


def test_the_default_is_a_writing_folder_in_the_home(home, monkeypatch):
    monkeypatch.delenv("STORYWHEEL_MANUSCRIPTS")
    assert paths.manuscripts_root() == Path.home() / "Writing"
    (home / "home").mkdir(exist_ok=True)
    (home / "home" / "settings.toml").write_text('manuscripts_dir = "~/Books"\n')
    assert paths.manuscripts_root() == Path.home() / "Books"


def test_paths_are_shown_with_a_tilde():
    assert paths.tilde(Path.home() / "Writing" / "x.docx") == "~/Writing/x.docx"
    assert paths.tilde("/etc/hosts") == "/etc/hosts"


def test_warnings_point_to_settings_you_not_a_builder_key(home):
    s = make()
    r = export.export(s, "docx")
    text = " ".join(r["warnings"])
    assert "Settings (F4) > You" in text and "Builder: G" not in text


def test_old_exports_move_out_of_the_library_and_it_is_said(home):
    s = make()
    old = s.exports_dir
    old.mkdir(parents=True)
    (old / "the-last-clause.docx").write_text("x")
    (old / "the-last-clause.md").write_text("y")
    lines = migrate.migrate_exports()
    assert lines and "Moved 2 exports out of your library" in lines[0]
    folder = root() / "The Last Clause"
    assert sorted(p.suffix for p in folder.iterdir() if p.is_file() and p.name != export.MARKER) == [".docx", ".md"]
    assert not old.exists()
    assert migrate.migrate_exports() == []


def test_the_manuscripts_folder_can_be_set_in_settings(home):
    import asyncio
    from storywheel import settings_app, settings
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            app.screen.save("manuscripts_dir", str(home / "Books"))
            await pilot.pause()
    os.environ.pop("STORYWHEEL_MANUSCRIPTS")
    asyncio.run(go())
    assert (home / "Books").is_dir() and paths.manuscripts_root() == home / "Books"
    assert settings.load_global()["manuscripts_dir"] == str(home / "Books")
