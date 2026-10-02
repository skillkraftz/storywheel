"""Promotion: what a kept draft becomes in a universe."""
from storywheel import promote, store, vault
from storywheel.sample import build_story
from conftest import make_engine


def draft(home, seed=3, genres=("western",)):
    story = build_story(make_engine(home, seed=seed), list(genres), structure="story-spine")
    story["id"] = "20260101-000000"
    return story


def by_key(plan):
    return {i.key: i for i in plan.items}


def test_the_plan_follows_the_table(home):
    d = draft(home)
    plan = promote.build_plan(d, None, make_engine(home))
    items = by_key(plan)
    pro = d["kept"]["protagonist"]
    assert items["protagonist"].type == "character" and items["protagonist"].fields["role"] == "protagonist"
    assert items["protagonist"].fields["job"] == pro["job"] and items["protagonist"].fields["secret"] == pro["secret"]
    assert items["rival"].type == "character" and items["rival"].fields["role"] == "rival"
    assert items["protagonist"].links == {"rival": "rival"}
    s = d["kept"]["setting"]
    assert items["town"].type == "place" and items["town"].name == s["place"] and items["town"].fields["era"] == s["era"]
    assert items["town"].custom == {"season": s["season"]}
    assert items["landmark"].type == "place" and items["landmark"].links == {"parent": "town"}
    assert "motif" in items and items["motif"].type in ("thing", "character", "place")
    kinds = {i.type for k, i in items.items() if k.startswith("thread:")}
    assert kinds <= {"character", "thing", "note"}
    assert plan.genres == ["western"] and plan.new_universe_name == d["kept"]["title"]["title"]


def test_nothing_is_written_until_apply(home):
    promote.build_plan(draft(home), None, make_engine(home))
    assert vault.list_universes() == []


def test_apply_creates_a_universe_entities_links_and_the_story_outline(home):
    d = draft(home)
    plan = promote.build_plan(d, None, make_engine(home), new_universe_name="Thornwood")
    story, report = promote.apply_plan(plan, None, d)
    u = vault.get_universe("thornwood")
    assert u.settings()["genres"] == ["western"] and any("Created universe" in r for r in report)
    hero = next(e for e in u.entities("character") if e.fields["role"] == "protagonist")
    assert hero.name == d["kept"]["protagonist"]["name"] and hero.fields["want"] == d["kept"]["protagonist"]["want"]
    rival = u.resolve(hero.fields["rival"], "character")
    assert rival and rival.fields["role"] == "rival"
    land = next(e for e in u.entities("place") if e.fields["kind"] == "landmark")
    assert u.resolve(land.fields["parent"]).fields["kind"] == "town"
    town = u.resolve(land.fields["parent"])
    assert town.custom["season"] == d["kept"]["setting"]["season"] and town.fields["rumor"] == d["kept"]["setting"]["rumor"]
    meta, sections = story.load_outline()
    assert meta["title"] == d["kept"]["title"]["title"] and meta["promoted_from"] == d["id"] and hero.id in meta["cast"]
    assert sections["Premise"] == d["kept"]["premise"]["premise"] and "Twist" in sections
    assert "Story Spine" in sections and sections["Story Spine"].split("\n\n") == list(d["kept"]["spine"].values())
    assert "- **Place:** " + d["kept"]["setting"]["place"] in sections["Setting"]
    assert story.seed()["id"] == d["id"]
    assert d["promoted"] == {"universe": "thornwood", "story": story.slug}


def test_promoting_into_an_existing_universe_offers_merges_for_same_names(home):
    d = draft(home)
    u = vault.create_universe("Existing", ["fantasy"])
    name = d["kept"]["protagonist"]["name"]
    u.new_entity("character", name, {"job": "someone else's job", "secret": ""})
    plan = promote.build_plan(d, u, make_engine(home))
    dupes = plan.duplicates()
    assert [i.key for i in dupes] == ["protagonist"] and dupes[0].merge
    assert any(l.startswith("Merge into the existing character") for l in plan.lines())
    promote.apply_plan(plan, u, d)
    chars = u.entities("character")
    assert len([c for c in chars if c.name == name]) == 1                       # not duplicated
    merged = u.entity(promote.vault.slugify(name))
    assert merged.fields["job"] == "someone else's job"                         # never overwritten...
    assert merged.fields["secret"] == d["kept"]["protagonist"]["secret"]        # ...but blanks are filled
    assert u.settings()["genres"] == ["fantasy"]                                # an existing universe's leanings stay


def test_choosing_not_to_merge_creates_a_duplicate(home):
    d = draft(home)
    u = vault.create_universe("Existing")
    name = d["kept"]["protagonist"]["name"]
    u.new_entity("character", name)
    plan = promote.build_plan(d, u, make_engine(home))
    plan.items[[i.key for i in plan.items].index("protagonist")].merge = False
    assert any("duplicate of" in l for l in plan.lines())
    promote.apply_plan(plan, u, d)
    assert len([c for c in u.entities("character") if c.name == name]) == 2


def test_an_empty_universe_takes_the_drafts_genres_but_a_leaning_one_does_not_change(home):
    d = draft(home, genres=("western", "fairy tale"))
    u = vault.create_universe("Blank")
    promote.apply_plan(promote.build_plan(d, u, make_engine(home)), u, d)
    assert u.settings()["genres"] == ["western", "fairy tale"]


def test_the_same_thing_twice_is_one_entity(home):
    d = draft(home)
    d["kept"]["title"]["motif"] = "lantern"
    d["threads"] = {"thing": {"text": "a lantern", "beat": "setup"}}
    plan = promote.build_plan(d, None, make_engine(home))
    lanterns = [i for i in plan.items if i.type == "thing" and promote.same_name(i.name, "lantern")]
    assert len(lanterns) == 1 and "motif" in lanterns[0].why


def test_thread_kinds_become_stubs(home):
    d = draft(home)
    d["threads"] = {"someone": {"text": "a wandering minstrel"}, "message": {"text": "a letter"},
                    "disaster": {"text": "the flood"}, "thing": {"text": "a silver key"}}
    items = by_key(promote.build_plan(d, None, make_engine(home)))
    assert (items["thread:someone"].type, items["thread:someone"].name) == ("character", "Wandering minstrel")
    assert items["thread:message"].type == "thing" and "message" in items["thread:message"].fields["description"]
    assert items["thread:disaster"].type == "note" and "flood" in items["thread:disaster"].fields["body"]
    assert items["thread:thing"].name == "Silver key"


def test_a_person_motif_becomes_a_character(home):
    d = draft(home)
    d["kept"]["title"]["motif"] = "raven"
    plan = promote.build_plan(d, None, make_engine(home))
    assert by_key(plan)["motif"].type == "character"


def test_a_draft_with_only_some_steps_kept_still_promotes(home):
    d = store.new_story()
    d["kept"] = {"title": {"title": "Half Done", "motif": "key"}, "genre": {"genre": "noir", "mood": "grim"}}
    plan = promote.build_plan(d, None, make_engine(home))
    story, _ = promote.apply_plan(plan, None, d)
    assert story.title == "Half Done" and story.sections() == {}
    assert story.meta["genre"] == "noir"


# --- command line and the plain prompt ----------------------------------------------------------------------------

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def cli(args, home, stdin=""):
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "home"), STORYWHEEL_LIBRARY=str(home / "library"),
               STORYWHEEL_OUT=str(home / "out"), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "storywheel", *args], input=stdin, capture_output=True, text=True,
                          env=env, cwd=ROOT, encoding="utf-8")


def test_promote_command_dry_run_then_for_real(home):
    d = draft(home)
    store.save(d)
    dry = json.loads(cli(["promote", d["id"], "--dry-run", "--json"], home).stdout)
    assert dry["lines"][0].startswith("New universe") and vault.list_universes() == []
    out = json.loads(cli(["promote", d["id"], "--new", "Thornwood", "--yes", "--json"], home).stdout)
    assert out["universe"] == "thornwood" and any("Created story" in r for r in out["report"])
    assert store.load(d["id"])["promoted"]["universe"] == "thornwood"


def test_the_plain_prompt_offers_promotion_on_leaving(home):
    res = cli(["--plain"], home, "k\nk\nk\nk\nk\nq\nn\nThornwood\ny\n")
    assert res.returncode == 0, res.stderr
    assert "Bringing this story into the Universe Builder" in res.stdout and "Created universe 'Thornwood'" in res.stdout
    assert [u.slug for u in vault.list_universes()] == ["thornwood"]
    again = cli(["--plain"], home, "k\nq\nl\n")                  # "later": nothing happens
    assert "Created universe" not in again.stdout
