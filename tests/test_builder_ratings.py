"""Ratings in the Builder carry the same provenance as the Wheel's (frame and atoms) and change later rolls."""
import asyncio
import json
from collections import Counter

from storywheel import builder, fieldhistory, fill, vault
from storywheel.ratings import Ratings


def build(home, ratings, seed=3):
    return builder.BuilderApp(engine_factory=lambda u: fill.make_engine(u, seed=seed, ratings=ratings), ratings=ratings, universe="u")


def test_a_rated_roll_records_its_atoms_and_they_survive_a_restart(home):
    u = vault.create_universe("U", ["western"])
    t = u.new_entity("thing")
    path = home / "home" / "ratings.json"
    ratings = Ratings(path)
    async def go():
        app = build(home, ratings)
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.entity = s.universe.entity(t.id)
            s.roll_field("name")
            e = s.universe.entities("thing")[0]
            s.entity = e
            s._rate("name", -1)
            return e.fields["name"], e.id
    name, eid = asyncio.run(go())
    rec = json.loads(path.read_text())["ratings"][-1]
    assert rec["text"] == name and rec["rating"] == -1 and rec["atoms"] and rec["atoms"][0][0] == "thing"
    saved = fieldhistory.read_prov(u, eid)
    assert saved["name"][name]["atoms"][0][0] == "thing"
    h = fieldhistory.FieldHistory()
    h.use(u)
    assert h.provenance(eid, "name", name)[1][0][0] == "thing"                # (still known in a new session)


def test_a_value_written_by_hand_has_no_provenance_but_can_still_be_rated(home):
    u = vault.create_universe("U")
    t = u.new_entity("thing")
    ratings = Ratings(home / "home" / "ratings.json")
    async def go():
        app = build(home, ratings)
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.entity = s.universe.entity(t.id)
            s._set("description", "An old horn.", "Written.")
            s._rate("description", -1)
    asyncio.run(go())
    rec = ratings.records[-1]
    assert rec["text"] == "An old horn." and rec["frame"] is None and rec["atoms"] == []


def test_rating_an_atom_down_makes_it_come_up_less(home):
    u = vault.create_universe("U", ["western"])
    t = u.new_entity("thing")
    def tally(ratings):
        counts = Counter()
        for seed in range(400):
            f = fill.Filler(u, fill.make_engine(u, seed=seed, ratings=ratings))
            f.roll(t, "name")
            counts[f.last_atoms[0][1]] += 1
        return counts
    plain = tally(Ratings())
    victim = plain.most_common(1)[0][0]
    ratings = Ratings()
    for n in range(8):                                                       # eight different lines, all built on that atom
        ratings.rate(f"universe:{u.slug}", "thing", "name", f"line {n}", -1, None, [["thing", victim]], title="U")
    after = tally(ratings)
    assert after[victim] < plain[victim] * 0.8, (plain[victim], after[victim])


def test_a_step_field_rolled_in_the_builder_is_rated_with_the_wheels_provenance(home):
    u = vault.create_universe("U", ["western"])
    c = u.new_entity("character", "Ada Voss")
    ratings = Ratings(home / "home" / "ratings.json")
    async def go():
        app = build(home, ratings)
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.entity = s.universe.entity(c.id)
            s.roll_field("want")
            s._rate("want", -1)
    asyncio.run(go())
    rec = ratings.records[-1]
    assert rec["step"] == "character" and rec["field"] == "want" and (rec["frame"] or rec["atoms"])
