"""Saving stories, the universe, and the markdown export."""
import json

from storywheel import store


def sample_story():
    s = store.new_story()
    s["id"] = "20260101-120000"
    s["created"] = "2026-01-01T12:00"
    s["kept"] = {
        "genre": {"genre": "western / fairy tale", "mood": "cozy"},
        "title": {"title": "The Lantern of Dry Fork", "motif": "lantern"},
        "protagonist": {"name": "Wade Hollis", "job": "drover"},
        "premise": {"premise": "A drover finds a lantern."},
        "spine": {"once": "Once upon a time, Wade lived.", "every_day": "Every day, Wade worked."},
    }
    return s


def test_markdown_has_frontmatter_and_page_break_sections():
    md = store.to_markdown(sample_story())
    assert md.startswith('---\ntitle: "The Lantern of Dry Fork"\ngenre: "western / fairy tale"\n'
                         'mood: "cozy"\nmotif: "lantern"\ncreated: 2026-01-01\ntags: [storywheel]\n---\n')
    assert "# The Lantern of Dry Fork" in md
    assert "*western / fairy tale · cozy*" in md and "*Motif: lantern*" in md
    assert md.count(store.SECTION_BREAK) == 3            # head | protagonist | premise | spine
    assert '<div style="page-break-after: always;"></div>' in md
    assert "## Protagonist\n\n- **Name:** Wade Hollis\n- **Job:** drover" in md
    assert "## Premise\n\nA drover finds a lantern." in md
    assert "## Story Spine\n\nOnce upon a time, Wade lived.\n\nEvery day, Wade worked." in md


def test_skipped_steps_are_left_out():
    story = sample_story()
    del story["kept"]["premise"]
    assert "## Premise" not in store.to_markdown(story)


def test_save_writes_json_and_markdown(home):
    story = sample_story()
    path = store.save(story)
    assert path.read_text().startswith("---")
    assert path.parent == home / "out"
    saved = json.loads((home / "home" / "stories" / f"{story['id']}.json").read_text())
    assert saved["kept"]["title"]["title"] == "The Lantern of Dry Fork"


def test_changing_the_title_replaces_the_old_markdown_file(home):
    story = sample_story()
    old = store.save(story)
    story["kept"]["title"]["title"] = "The Lamp of Salt Fork"
    new = store.save(story)
    assert new != old and new.exists() and not old.exists()
    assert len(list((home / "out").glob("*.md"))) == 1


def test_export_to_another_folder_does_not_move_the_story(home):
    story = sample_story()
    kept_at = store.save(story)
    copy = store.export(story, home / "vault")
    assert copy.parent == home / "vault" and copy.exists() and kept_at.exists()


def test_mix_is_saved_with_the_story_and_follows_the_kept_genre(home):
    story = sample_story()
    story["mix"]["exclude_tags"].append("mythological")
    store.save(story)
    loaded = store.load(story["id"])
    assert loaded["mix"] == {"base": ["western", "fairy tale"], "exclude_tags": ["mythological"],
                             "exclude_lists": [], "boost": {}}


def test_v1_story_files_are_upgraded_on_load(home):
    story = sample_story()
    del story["mix"]
    (home / "home" / "stories").mkdir(parents=True)
    (home / "home" / "stories" / f"{story['id']}.json").write_text(json.dumps(story))
    assert store.load(story["id"])["mix"]["base"] == ["western", "fairy tale"]
    assert store.all_stories()[0]["mix"]["exclude_tags"] == []


def test_find_by_number_id_prefix_or_newest(home):
    a, b = sample_story(), sample_story()
    b["id"] = "20260202-120000"
    store.save(a)
    store.save(b)
    assert store.find()["id"] == b["id"]
    assert store.find("2")["id"] == a["id"]
    assert store.find("20260101")["id"] == a["id"]
    assert store.find("nope") is None


def test_universe_add_remove(home):
    fields = {"name": "Wade Hollis", "_src": "x"}
    assert store.add_to_universe("protagonist", fields) == (1, True)
    assert store.add_to_universe("protagonist", fields) == (1, False)
    assert store.load_universe() == {"protagonist": [{"name": "Wade Hollis"}]}
    assert store.remove_from_universe("protagonist", fields)
    assert store.load_universe() == {"protagonist": []}
    store.add_to_universe("setting", {"place": "Dry Fork"})
    assert store.remove_universe_entry("setting", 0) == {"place": "Dry Fork"}
    assert store.remove_universe_entry("setting", 5) is None
