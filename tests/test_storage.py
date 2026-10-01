"""Storage: frontmatter, settings, schemas, universes, entities, links, migration."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from storywheel import frontmatter, migrate, paths, schemas, settings, store, vault

ROOT = Path(__file__).resolve().parent.parent


# --- frontmatter ------------------------------------------------------------------------------------------

def test_frontmatter_round_trips_text_lists_numbers_and_custom_fields():
    meta = {"id": "stacie", "name": 'Stacie "Stace" Anderson: the 3rd', "age": 34, "members": ["a", "b"],
            "empty": "", "flag": True, "custom": {"eye colour": "grey", "motto": "never again"}}
    text = frontmatter.dumps(meta, "Notes here.\n\nSecond paragraph.")
    assert text.startswith('---\nid: "stacie"\n') and "age: 34" in text
    back, body = frontmatter.loads(text)
    assert back == meta and body == "Notes here.\n\nSecond paragraph."


def test_frontmatter_reads_hand_written_plain_values():
    text = "---\nname: Stacie\nrole: rival\nage: 34\ntags: [a, b]\nquote: 'it''s'\n---\nBody"
    meta, body = frontmatter.loads(text)
    assert meta == {"name": "Stacie", "role": "rival", "age": 34, "tags": ["a", "b"], "quote": "it's"} and body == "Body"


def test_frontmatter_without_a_header_is_all_body():
    assert frontmatter.loads("just text") == ({}, "just text")
    assert frontmatter.loads("---\nno end") == ({}, "---\nno end")


# --- settings --------------------------------------------------------------------------------------------

def test_global_settings_round_trip_in_toml(home):
    assert settings.load_global()["font"] == "Times New Roman"
    path = settings.save_global({"author_name": "Andy Writer", "address": "1 Main St\nTown, ST 00000",
                                 "email": "a@example.com", "phone": "555-0100", "daily_goal": 750})
    text = path.read_text()
    assert 'author_name = "Andy Writer"' in text and "daily_goal = 750" in text
    got = settings.load_global()
    assert got["address"] == "1 Main St\nTown, ST 00000" and got["daily_goal"] == 750
    assert settings.surname(got) == "Writer"


def test_story_settings_fall_back_to_global_then_builtin(home, tmp_path):
    settings.save_global({"daily_goal": 900, "font": "Courier New"})
    s = settings.load_story(tmp_path / "story")
    assert s["daily_goal"] == 900 and s["font"] == "Courier New" and s["typewriter"] is False
    settings.save_story(tmp_path / "story", {"daily_goal": 300, "typewriter": True, "title_keyword": "Clause"})
    s = settings.load_story(tmp_path / "story")
    assert s["daily_goal"] == 300 and s["typewriter"] is True and s["title_keyword"] == "Clause"


def test_the_small_toml_reader_matches_the_real_one():
    text = '# c\nname = "A \\"q\\" b"  # trailing\nn = 3\nf = 1.5\nok = true\nlist = ["a", "b"]\n[sec]\nx = "y"\n'
    mini = settings._mini_parse(text)
    assert mini == {"name": 'A "q" b', "n": 3, "f": 1.5, "ok": True, "list": ["a", "b"], "sec": {"x": "y"}}
    try:
        import tomllib
    except ImportError:
        return
    assert tomllib.loads(text) == mini


# --- schemas ----------------------------------------------------------------------------------------------------

def test_schemas_are_data_for_the_five_types():
    assert set(schemas.load()) >= set(schemas.TYPES)
    assert schemas.field_keys("character")[:3] == ["name", "role", "age"]
    assert schemas.field_spec("character", "rival")["kind"] == "link"
    assert schemas.can_roll(schemas.field_spec("character", "job")) and not schemas.can_roll(schemas.field_spec("character", "role"))
    with pytest.raises(KeyError):
        schemas.get("spaceship")


def test_you_can_add_an_entity_type_with_a_json_file(home):
    (paths.home() / "entities").mkdir(parents=True)
    (paths.home() / "entities" / "spell.json").write_text(json.dumps(
        {"type": "spell", "label": "Spell", "plural": "Spells", "folder": "spells",
         "fields": [{"key": "name", "label": "Name", "kind": "short", "fill": {"write": True}}]}))
    assert "spell" in schemas.load()


# --- library layout -------------------------------------------------------------------------------------------------

def test_library_root_default_and_override(monkeypatch, tmp_path):
    monkeypatch.delenv("STORYWHEEL_LIBRARY", raising=False)
    assert paths.library_root() == Path.home() / "Writing" / "storywheel"
    monkeypatch.setenv("STORYWHEEL_LIBRARY", str(tmp_path / "x"))
    assert paths.library_root() == tmp_path / "x"


def test_create_universe_makes_folders_and_a_universe_file(home):
    u = vault.create_universe("The Thornwood", ["western", "fairy tale"], "Dry country.")
    assert u.slug == "the-thornwood" and u.path == home / "library" / "universes" / "the-thornwood"
    for sub in ("characters", "places", "things", "groups", "notes", "stories"):
        assert (u.path / sub).is_dir()
    s = u.settings()
    assert s["name"] == "The Thornwood" and s["genres"] == ["western", "fairy tale"] and s["notes"] == "Dry country."
    assert u.mix_dict() == {"base": ["western", "fairy tale"], "exclude_tags": [], "exclude_lists": [], "boost": {}}
    assert vault.create_universe("The Thornwood").slug == "the-thornwood-2"
    assert [x.slug for x in vault.list_universes()] == ["the-thornwood", "the-thornwood-2"]


def test_renaming_a_universe_keeps_its_folder(home):
    u = vault.create_universe("Old Name")
    vault.rename_universe(u, "New Name")
    assert vault.get_universe("old-name").name == "New Name"


def test_deleting_moves_to_the_trash(home):
    u = vault.create_universe("Doomed")
    e = u.new_entity("character", "Ghost")
    u.delete()
    assert vault.get_universe("doomed") is None
    trashed = list((home / "library" / ".trash").iterdir())
    assert len(trashed) == 1 and (trashed[0] / "characters" / "ghost.md").exists()


# --- entities --------------------------------------------------------------------------------------------------------

def test_an_entity_is_a_markdown_file_that_round_trips(home):
    u = vault.create_universe("U")
    e = u.new_entity("character", "Stacie Anderson", {"job": "land clerk", "want": "a quiet life", "age": "34"})
    e.custom["eye colour"] = "grey"
    e.body = "Grew up in the dry years.\n\nDistrusts bells."
    u.save_entity(e)
    text = (u.path / "characters" / "stacie-anderson.md").read_text()
    assert text.startswith('---\nid: "stacie-anderson"\ntype: "character"\nname: "Stacie Anderson"')
    assert "custom:\n  eye colour: \"grey\"" in text and text.rstrip().endswith("Distrusts bells.")
    again = u.entity("stacie-anderson")
    assert again.fields["job"] == "land clerk" and again.fields["age"] == "34" and again.custom == {"eye colour": "grey"}
    assert again.body == "Grew up in the dry years.\n\nDistrusts bells."


def test_a_note_keeps_its_body_in_the_body(home):
    u = vault.create_universe("U")
    n = u.new_entity("note", "The Dry Years", {"body": "It did not rain for six years."})
    text = n.path.read_text()
    assert text.rstrip().endswith("It did not rain for six years.") and "body:" not in text
    assert u.entity("the-dry-years").fields["body"] == "It did not rain for six years."


def test_new_blank_entities_get_placeholder_ids_then_a_real_one_when_named(home):
    u = vault.create_universe("U")
    a, b = u.new_entity("character"), u.new_entity("character")
    assert (a.id, b.id) == ("character-1", "character-2") and a.name == ""
    owner = u.new_entity("thing")
    owner.fields["owner"] = a.id
    u.save_entity(owner)
    a.fields["name"] = "Mark Lee"
    u.save_entity(a)
    assert a.id == "mark-lee" and (u.path / "characters" / "mark-lee.md").exists()
    assert not (u.path / "characters" / "character-1.md").exists()
    assert u.entity(owner.id).fields["owner"] == "mark-lee"            # the link followed the rename of the id


def test_a_real_id_never_changes_when_the_name_does(home):
    u = vault.create_universe("U")
    e = u.new_entity("character", "Mark Lee")
    e.fields["name"] = "Marcus Lee"
    u.save_entity(e)
    assert e.id == "mark-lee" and u.entity("mark-lee").name == "Marcus Lee"


def test_links_by_id_resolve_both_ways(home):
    u = vault.create_universe("U")
    hero = u.new_entity("character", "Stacie")
    sheriff = u.new_entity("character", "Sheriff Lund")
    hero.fields["rival"] = sheriff.id
    hero.fields["relationships"] = [sheriff.id, "nobody-here"]
    u.save_entity(hero)
    horn = u.new_entity("thing", "The Horn", {"owner": hero.id})
    labels = [(l, t.name if hasattr(t, "name") else t) for l, t in u.links_from(u.entity("stacie"))]
    assert ("Rival", "Sheriff Lund") in labels and ("Relationships", "Sheriff Lund") in labels
    assert ("Relationships", "nobody-here") in labels                       # a dangling link shows as text
    assert [(l, e.name) for l, e in u.links_to(hero)] == [("Owner", "The Horn")]
    assert u.resolve("stacie").name == "Stacie" and u.resolve("stacie", "place") is None and u.resolve("free text") is None


def test_deleting_an_entity_trashes_it_and_clears_links(home):
    u = vault.create_universe("U")
    a, b = u.new_entity("character", "A"), u.new_entity("character", "B")
    a.fields["rival"] = b.id
    a.fields["relationships"] = [b.id]
    u.save_entity(a)
    u.delete_entity(b)
    assert u.entity("b") is None and (home / "library" / ".trash").exists()
    again = u.entity("a")
    assert again.fields["rival"] == "" and again.fields["relationships"] == []


def test_find_by_name_is_case_insensitive(home):
    u = vault.create_universe("U")
    u.new_entity("character", "Stacie Anderson")
    u.new_entity("place", "Stacie Anderson")
    assert len(u.find_by_name("stacie anderson")) == 2 and len(u.find_by_name("STACIE ANDERSON", "place")) == 1
    assert u.find_by_name("") == []


def test_obsidian_can_read_it_the_frontmatter_is_valid_yaml_subset(home):
    u = vault.create_universe("U")
    e = u.new_entity("character", "Ann", {"want": "a: colon, and 'quotes'"})
    meta, _ = frontmatter.loads(e.path.read_text())
    assert meta["want"] == "a: colon, and 'quotes'"


# --- stories ---------------------------------------------------------------------------------------------------------------

def test_story_outline_sections_round_trip(home):
    u = vault.create_universe("U")
    s = u.new_story("The Last Clause", {"genre": "western", "structure": "Story Spine"},
                    {"Premise": "A clerk finds a clause.", "Twist": "It was hers."}, seed={"id": "draft"})
    assert s.slug == "the-last-clause" and s.title == "The Last Clause"
    assert s.sections() == {"Premise": "A clerk finds a clause.", "Twist": "It was hers."}
    s.set_section("Premise", "A clerk finds two clauses.")
    s.set_meta(genre="western / noir")
    assert s.sections()["Premise"] == "A clerk finds two clauses." and s.meta["genre"] == "western / noir"
    assert s.seed() == {"id": "draft"} and u.story("the-last-clause").title == "The Last Clause"
    assert s.outline_path.read_text().startswith("---\nid: ")


def test_scenes_are_files_in_order_and_words_are_counted(home):
    u = vault.create_universe("U")
    s = u.new_story("Tale")
    a = s.add_scene("Opening", "One two three.")
    b = s.add_scene("The Letter", "Four five.")
    assert [p.name for p in s.scenes()] == ["01-opening.md", "02-the-letter.md"]
    assert s.word_count() == 5 and s.manuscript_text() == "One two three.\n\nFour five."


# --- migration -----------------------------------------------------------------------------------------------------------------

def test_migrating_universe_json_into_loose_ends_with_a_backup(home):
    old = paths.home() / "universe.json"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text(json.dumps({
        "protagonist": [{"name": "Wade Hollis", "age": "34", "job": "drover", "trait": "stubborn"}],
        "setting": [{"place": "Dry Fork", "era": "the strike", "season": "autumn", "landmark": "the mesa", "rumor": "cursed"}],
        "spine": [{"setup": "Once upon a time, a drover rode in.", "turn": "One day it rained."}],
        "twist": [{"twist": "It was all a dream."}]}))
    report = migrate.migrate_universe_json()
    assert "1 character(s), 1 place(s), 2 note(s)" in report[0]
    u = vault.get_universe("loose-ends")
    wade = u.entity("wade-hollis")
    assert wade.fields["job"] == "drover" and wade.fields["role"] == "protagonist"
    fork = u.entity("dry-fork")
    assert fork.type == "place" and fork.fields["feature"] == "the mesa" and fork.fields["era"] == "the strike"
    notes = u.entities("note")
    assert len(notes) == 2 and any("Once upon a time" in n.fields["body"] for n in notes)
    assert not old.exists() and list(old.parent.glob("universe.json.migrated-*"))      # kept as a backup
    assert migrate.migrate_universe_json() == []                                      # nothing left to do


def test_migration_with_an_empty_or_missing_pool_does_nothing(home):
    assert migrate.migrate_universe_json() == []
    (paths.home()).mkdir(parents=True, exist_ok=True)
    (paths.home() / "universe.json").write_text('{"protagonist": []}')
    assert migrate.migrate_universe_json() == [] and vault.list_universes() == []


# --- command line ----------------------------------------------------------------------------------------------------------------------

def cli(args, home):
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "home"), STORYWHEEL_LIBRARY=str(home / "library"),
               STORYWHEEL_OUT=str(home / "out"), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "storywheel", *args], capture_output=True, text=True, env=env,
                          cwd=ROOT, encoding="utf-8")


def test_universe_entity_and_story_json_commands(home):
    u = vault.create_universe("Thornwood", ["western"])
    hero = u.new_entity("character", "Stacie", {"job": "clerk"})
    s = u.new_story("The Clause", {"genre": "western"}, {"Premise": "A clause."})
    s.add_scene("Opening", "Hello world.")
    unis = json.loads(cli(["universes", "--json"], home).stdout)
    assert unis[0]["slug"] == "thornwood" and unis[0]["counts"]["character"] == 1 and unis[0]["stories"] == ["the-clause"]
    ents = json.loads(cli(["entity", "list", "thornwood", "--type", "character", "--json"], home).stdout)
    assert ents[0]["id"] == "stacie" and ents[0]["fields"]["job"] == "clerk"
    one = json.loads(cli(["entity", "show", "thornwood", "stacie", "--json"], home).stdout)
    assert one["name"] == "Stacie"
    st = json.loads(cli(["story", "show", "thornwood/the-clause", "--json"], home).stdout)
    assert st["title"] == "The Clause" and st["scenes"] == ["01-opening.md"] and st["words"] == 2 and st["outline"]["Premise"] == "A clause."
    assert json.loads(cli(["story", "list", "--json"], home).stdout)[0]["id"] == "the-clause"
    assert cli(["entity", "list", "nope"], home).returncode != 0
