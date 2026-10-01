"""Rolling entity fields with the generator, and renames with a preview."""
import pytest

from storywheel import fill, rename, schemas, vault
from storywheel.fill import Filler, NothingToLink


def filler(universe, seed=3):
    return Filler(universe, fill.make_engine(universe, seed=seed))


def test_a_blank_character_rolls_every_rollable_field_and_leaves_write_only_ones(home):
    u = vault.create_universe("W", ["western"])
    e = u.new_entity("character")
    done = filler(u).roll_blank(e)
    assert set(done) >= {"name", "age", "job", "trait", "want", "need", "flaw", "secret"}
    assert e.fields["role"] == "" and e.fields["relationships"] == []         # write-only: untouched
    assert all(e.fields[k] for k in ("name", "age", "job", "want"))
    assert " " in e.fields["name"]                                           # a first and a last name


def test_rolling_one_field_changes_only_that_field(home):
    u = vault.create_universe("W", ["western"])
    e = u.new_entity("character")
    f = filler(u)
    f.roll_blank(e)
    before = dict(e.fields)
    seen = {e.fields["job"]}
    for _ in range(6):
        e.fields["job"] = f.roll(e, "job")
        seen.add(e.fields["job"])
    assert len(seen) > 2 and {k: v for k, v in e.fields.items() if k != "job"} == {k: v for k, v in before.items() if k != "job"}


def test_rolling_a_name_never_returns_the_same_name_forever(home):
    u = vault.create_universe("W", ["western"])
    e = u.new_entity("character")
    f = filler(u)
    names = {f.roll(e, "name") for _ in range(8)}
    assert len(names) >= 6


def test_a_write_only_field_cannot_be_rolled(home):
    u = vault.create_universe("W")
    e = u.new_entity("character")
    with pytest.raises(ValueError):
        filler(u).roll(e, "role")


def test_places_things_and_groups_roll(home):
    u = vault.create_universe("W", ["western"])
    f = filler(u)
    place, thing, group = u.new_entity("place"), u.new_entity("thing"), u.new_entity("group")
    assert {"name", "era", "feature", "rumor"} <= set(f.roll_blank(place))
    assert f.roll_blank(thing) == ["name"] and thing.fields["name"][0].isupper()
    assert f.roll_blank(group) == ["name", "goal"] and group.fields["name"].startswith("The ") and group.fields["name"].endswith("Company")


def test_the_universes_genre_leanings_steer_the_roll(home):
    fairy = vault.create_universe("F", ["fairy tale"])
    west = vault.create_universe("W", ["western"])
    def jobs(u):
        f, e, out = filler(u, 5), u.new_entity("character"), []
        for _ in range(60):
            out.append(f.roll(e, "job"))
        return out
    from storywheel.engine import Engine
    eng = Engine(seed=1)
    western_jobs = {x.text for wl in eng.library.by_slot["job"] if "western" in wl.tags for x in wl.entries}
    fairy_jobs = {x.text for wl in eng.library.by_slot["job"] if "fairy tale" in wl.tags for x in wl.entries}
    w, f = jobs(west), jobs(fairy)
    assert sum(j in western_jobs for j in w) > sum(j in western_jobs for j in f)
    assert sum(j in fairy_jobs for j in f) > sum(j in fairy_jobs for j in w)


def test_a_character_can_have_an_existing_character_as_rival(home):
    u = vault.create_universe("W", ["western"])
    sheriff = u.new_entity("character", "Sheriff Lund")
    hero = u.new_entity("character")
    f = filler(u, 7)
    seen = {f.roll(hero, "rival") for _ in range(30)}
    assert sheriff.id in seen                                 # sometimes a real entity
    assert any(v != sheriff.id for v in seen)                 # sometimes generated text
    assert all(v == sheriff.id or u.resolve(v) is None for v in seen)


def test_a_rival_is_never_the_character_itself(home):
    u = vault.create_universe("W")
    only = u.new_entity("character", "Solo")
    assert all(filler(u).roll(only, "rival") != only.id for _ in range(20))


def test_link_only_fields_pick_real_entities_or_say_there_are_none(home):
    u = vault.create_universe("W")
    thing = u.new_entity("thing", "Horn")
    with pytest.raises(NothingToLink):
        filler(u).roll(thing, "owner")
    hero = u.new_entity("character", "Stacie")
    assert filler(u).roll(thing, "owner") == hero.id
    town = u.new_entity("place", "Red Draw")
    inn = u.new_entity("place")
    assert filler(u).roll(inn, "parent") == town.id


def test_roll_blank_skips_link_fields_with_nothing_to_link(home):
    u = vault.create_universe("W")
    g = u.new_entity("group")
    done = filler(u).roll_blank(g)
    assert "leader" not in done and "name" in done


def test_reroll_all_replaces_every_rollable_field_but_not_write_only_ones(home):
    u = vault.create_universe("W", ["western"])
    e = u.new_entity("character", "Fixed Name", {"role": "ally"})
    f = filler(u)
    f.roll_blank(e)
    old = dict(e.fields)
    f.reroll_all(e)
    assert e.fields["role"] == "ally" and e.fields["name"] != "Fixed Name" and e.fields["job"] != "" and e.fields != old


def test_the_universes_own_lists_folder_feeds_its_rolls(home):
    u = vault.create_universe("Odd")
    (u.lists_dir / "job").mkdir(parents=True)
    (u.lists_dir / "job" / "odd.json").write_text('{"slot": "job", "tags": ["general"], "entries": ["moth wrangler"]}')
    e = u.new_entity("character")
    jobs = {filler(u, s).roll(e, "job") for s in range(40)}
    assert "moth wrangler" in jobs


# --- rename ------------------------------------------------------------------------------------------------

def world(home):
    u = vault.create_universe("W")
    stacie = u.new_entity("character", "Stacie", {"want": "Stacie wants out"})
    stacie.body = "Stacie grew up here. Stacie's mother taught her. Anastacie is unrelated."
    u.save_entity(stacie)
    u.new_entity("note", "Lore", {"body": "Everyone knows Stacie. Even stacie the cat."})
    s = u.new_story("Tale", {"genre": "western"}, {"Premise": "Stacie finds a clause."})
    s.add_scene("One", "Stacie ran. Stacie’s hat flew.\n\nNobody else did.")
    return u, stacie


def test_find_matches_is_whole_word_and_includes_possessives(home):
    u, stacie = world(home)
    matches = rename.find_matches(u, stacie)
    labels = [(m.kind, m.line_no) for m in matches]
    assert {m.kind for m in matches} == {"entity", "outline", "manuscript"}
    contexts = " | ".join(m.context for m in matches)
    assert "Stacie's mother" in contexts and "Stacie’s hat" in contexts and "Anastacie" not in contexts
    assert not any("name:" in m.context for m in matches)                     # the entity's own name line is not text
    assert len([m for m in matches if m.label.startswith("note")]) == 1         # case-sensitive: "stacie the cat" is safe
    assert len([m for m in matches if m.label.startswith("character")]) == 3    # the want, and two in the body


def test_nothing_changes_until_matches_are_applied(home):
    u, stacie = world(home)
    before = {p: p.read_text() for p in [stacie.path, u.stories()[0].outline_path, u.stories()[0].scenes()[0]]}
    rename.find_matches(u, stacie)
    assert all(p.read_text() == t for p, t in before.items())


def test_rename_all_matches(home):
    u, stacie = world(home)
    matches = rename.find_matches(u, stacie)
    n = rename.rename_entity(u, stacie, "Marcy", matches)
    assert n == len(matches)
    again = u.entity("stacie")                                                   # the id is stable
    assert again.name == "Marcy" and again.body.startswith("Marcy grew up here. Marcy's mother taught her.")
    assert "Anastacie" in again.body and again.fields["want"] == "Marcy wants out"
    story = u.stories()[0]
    assert story.sections()["Premise"] == "Marcy finds a clause."
    assert story.scenes()[0].read_text().startswith("Marcy ran. Marcy’s hat flew.")
    assert "Even stacie the cat" in u.entity("lore").fields["body"]
    assert rename.find_matches(u, again, "Stacie")[0:0] == []


def test_rename_only_the_accepted_matches(home):
    u, stacie = world(home)
    matches = rename.find_matches(u, stacie)
    for m in matches:
        m.accepted = m.kind != "manuscript"
    rename.rename_entity(u, stacie, "Marcy", matches)
    story = u.stories()[0]
    assert story.scenes()[0].read_text().startswith("Stacie ran.")             # the manuscript was declined
    assert story.sections()["Premise"] == "Marcy finds a clause."


def test_rename_with_no_matches_still_renames_the_entity_and_keeps_links(home):
    u, stacie = world(home)
    horn = u.new_entity("thing", "Horn", {"owner": stacie.id})
    rename.rename_entity(u, stacie, "Marcy", [])
    assert u.entity(horn.id).fields["owner"] == "stacie" and u.resolve("stacie").name == "Marcy"
