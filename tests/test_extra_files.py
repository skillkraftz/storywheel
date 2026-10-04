"""Files in a manuscript folder that storywheel did not make are never merged, counted, exported or read: the Builder shows them."""
import asyncio
import json

import pytest

from storywheel import builder, export, migrate, vault

COPY = "01-opening (xps copy 2026-10-04).md"


@pytest.fixture
def story(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    return s


def old_story_with_copy(story, same_text=True):
    """exactly the reported case: 01-opening.md plus a sync tool's copy next to it, in an old one-file-per-scene story"""
    d = story.manuscript_dir
    d.mkdir(parents=True, exist_ok=True)
    (d / "01-opening.md").write_text("The rain came early.\nShe waited.\n")
    (d / COPY).write_text("The rain came early.\nShe waited.\n" if same_text else "Another version.\n")
    return d


def test_the_copy_is_not_merged_into_the_manuscript(story):
    d = old_story_with_copy(story)
    assert story.migrate_manuscript() is None                               # one scene file: nothing to merge
    assert [p.name for p in story.files()] == ["01-opening.md"]
    assert (d / COPY).read_text() == "The rain came early.\nShe waited.\n"   # untouched
    assert (d / "01-opening.md").exists() and not (d / "manuscript.md").exists()
    assert "The rain came early." in story.manuscript_text() and story.manuscript_text().count("The rain came early.") == 1
    assert story.word_count() == 6 and [e["title"] for e in story.scene_list()] == ["Opening"]


def test_the_copy_is_listed_as_an_extra_file(story):
    old_story_with_copy(story)
    assert [p.name for p in story.extra_files()] == [COPY]


def test_the_migration_runs_once_per_story(story):
    d = story.manuscript_dir
    d.mkdir(parents=True)
    (d / "01-opening.md").write_text("One.\n")
    (d / "02-the-letter.md").write_text("Two.\n")
    msg = story.migrate_manuscript()
    assert "Merged 2 scene files" in msg and [p.name for p in story.files()] == ["manuscript.md"]
    assert (story.path / ".one-file-manuscript").exists()
    # a sync tool brings the old file back, and a copy of the merged file: neither is merged again
    (d / "01-opening.md").write_text("One again.\n")
    (d / "manuscript (xps copy).md").write_text("whatever\n")
    assert story.migrate_manuscript() is None
    assert [p.name for p in story.files()] == ["manuscript.md"]
    assert "One again" not in story.manuscript_text()
    assert {p.name for p in story.extra_files()} == {"01-opening.md", "manuscript (xps copy).md"}      # (old name next to manuscript.md: extra)


def test_only_known_names_are_scene_files(story):
    d = story.manuscript_dir
    d.mkdir(parents=True)
    for name in ("01-opening.md", "02-the-letter.md", "notes.md", "01-opening.sync-conflict-20261004.md", "03-x (copy).md", ".hidden.md", "x.txt"):
        (d / name).write_text("text\n")
    assert [p.name for p in story.files()] == ["01-opening.md", "02-the-letter.md"]
    assert {p.name for p in story.extra_files()} == {"notes.md", "01-opening.sync-conflict-20261004.md", "03-x (copy).md", "x.txt"}


def test_migrate_all_stories_leaves_the_copy_alone(story):
    d = old_story_with_copy(story)
    lines = migrate.migrate_manuscripts()
    assert not any("Merged" in l for l in lines)
    assert (d / COPY).exists() and (d / "01-opening.md").exists()


def test_the_copy_is_not_exported_or_counted(story):
    old_story_with_copy(story, same_text=False)
    assert "Another version" not in export.compile_text(story)
    assert story.word_count() == 6


def test_ignore_and_delete(story):
    d = old_story_with_copy(story)
    story.ignore_file(COPY)
    assert story.extra_files() == [] and (d / COPY).exists()
    assert json.loads((story.path / ".ignored-manuscript-files.json").read_text()) == [COPY]
    where = story.delete_extra_file(COPY)
    assert not (d / COPY).exists() and where.exists() and ".trash" in str(where)
    with pytest.raises(ValueError):
        story.delete_extra_file("01-opening.md")                           # (a real manuscript file is never deleted this way)


def test_a_novel_never_merges(story):
    from storywheel import settings
    settings.save_story(story.path, {"format": "novel"})
    d = story.manuscript_dir
    d.mkdir(parents=True)
    (d / "01-one.md").write_text("A.\n")
    (d / "02-two.md").write_text("B.\n")
    assert story.migrate_manuscript() is None and [p.name for p in story.files()] == ["01-one.md", "02-two.md"]


def run_builder(story, fn):
    async def go():
        app = builder.BuilderApp(universe=story.universe.slug if hasattr(story, "universe") else "thornwood", story=story.slug)
        async with app.run_test(size=(200, 55)) as pilot:
            await pilot.pause()
            return await fn(app, pilot)
    return asyncio.run(go())


def test_the_builder_shows_the_extra_file_with_open_delete_ignore(story):
    old_story_with_copy(story)
    async def fn(app, pilot):
        scr = app.screen_ref
        status = str(scr.query_one("#status").content)
        note = str(scr.query_one("#extras").content)
        shown = scr.query_one("#extras").display and scr.query_one("#extras-btns").display
        return status, note, shown
    status, note, shown = run_builder(story, fn)
    assert "Extra file in the manuscript folder:" in status and COPY in status and "looks like a copy from another tool" in status
    assert COPY in note and shown


def test_ignore_hides_it_and_delete_asks_first(story):
    d = old_story_with_copy(story)
    async def fn(app, pilot):
        scr = app.screen_ref
        scr.extra_act("delete")
        await pilot.pause()
        top = type(app.screen).__name__
        await pilot.press("n")                                              # answer no
        await pilot.pause()
        still = (d / COPY).exists()
        scr.extra_act("ignore")
        await pilot.pause()
        return top, still, scr.query_one("#extras").display
    top, still, shown = run_builder(story, fn)
    assert top == "ConfirmScreen" and still and shown is False
    assert (d / COPY).exists()


def test_open_shows_the_file_read_only(story):
    old_story_with_copy(story, same_text=False)
    async def fn(app, pilot):
        app.screen_ref.extra_act("open")
        await pilot.pause()
        return type(app.screen).__name__, app.screen.query_one("#fv-text").text, app.screen.query_one("#fv-text").read_only
    name, text, ro = run_builder(story, fn)
    assert name == "FileViewScreen" and "Another version." in text and ro is True


@pytest.mark.skipif(__import__("storywheel.writer", fromlist=["x"]).check() is not None, reason="Neovim 0.10+ is not installed")
def test_the_writer_ignores_the_copy_too(story):
    from test_notepad import run as nrun
    old_story_with_copy(story, same_text=False)
    r = nrun(story, "", "", "local names = {}; for _, f in ipairs(require('sw.story').files()) do names[#names + 1] = f.name end; R.names = names")
    assert r["names"] == ["01-opening.md"]
