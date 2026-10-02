"""The Builder's field history is saved beside the entity, so the scroll wheel still works tomorrow."""
import asyncio
import json

import pytest

from storywheel import builder, fieldhistory, fill, vault
from conftest import screen_text


def make_app(universe="u"):
    return builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=4), universe=universe)


def test_rolled_values_are_remembered_on_disk(home):
    u = vault.create_universe("U", ["western"])
    c = u.new_entity("character", "Ada Voss")
    async def go():
        app = make_app()
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.entity = s.universe.entity(c.id)
            s.refresh_card()
            keys = [r[0] for r in s.rows()]
            s.card.highlighted = keys.index("job")
            for _ in range(3):
                s.roll_field("job")
            return list(s.hist[(c.id, "job")])
    seen = asyncio.run(go())
    assert len(seen) >= 2
    saved = json.loads((u.path / ".field-history" / f"{c.id}.json").read_text())
    assert saved["fields"]["job"] == seen and saved["entity"] == c.id


def test_history_comes_back_in_a_new_session_and_the_wheel_steps_through_it(home):
    u = vault.create_universe("U", ["western"])
    c = u.new_entity("character", "Ada Voss")
    async def first():
        app = make_app()
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.entity = s.universe.entity(c.id)
            for _ in range(3):
                s.roll_field("want")
            return list(s.hist[(c.id, "want")]), s.universe.entity(c.id).fields["want"]
    seen, current = asyncio.run(first())
    assert current == seen[-1]
    async def second():
        app = make_app()
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.entity = s.universe.entity(c.id)
            before = s.universe.entity(c.id).fields["want"]
            s.step_history("want", -1)                              # the scroll wheel: one value back
            return seen, before, s.universe.entity(c.id).fields["want"], list(s.hist[(c.id, "want")])
    seen, before, after, hist = asyncio.run(second())
    assert hist == seen and before == seen[-1] and after == seen[-2]


def test_written_values_are_remembered_too(home):
    u = vault.create_universe("U")
    c = u.new_entity("character", "Ada Voss")
    async def go():
        app = make_app()
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.entity = s.universe.entity(c.id)
            s._set("trait", "stubborn", "Written.")
            s._set("trait", "kind", "Written.")
    asyncio.run(go())
    assert fieldhistory.read(u, c.id)["trait"] == ["stubborn", "kind"]


def test_a_blank_entitys_history_moves_with_its_id_when_it_gets_a_name(home):
    u = vault.create_universe("U", ["western"])
    c = u.new_entity("character")
    assert c.id == "character-1"
    async def go():
        app = make_app()
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.entity = s.universe.entity(c.id)
            s._set("trait", "wary", "Written.")
            s._set("name", "Mara Quill", "Written.")
            return s.entity.id
    new_id = asyncio.run(go())
    assert new_id == "mara-quill"
    assert not (u.path / ".field-history" / "character-1.json").exists()
    assert fieldhistory.read(u, "mara-quill")["trait"] == ["wary"]


def test_deleting_an_entity_removes_its_history(home):
    u = vault.create_universe("U")
    c = u.new_entity("character", "Ada Voss")
    fieldhistory.write(u, c.id, {"trait": ["a", "b"]})
    async def go():
        app = make_app()
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.entity = s.universe.entity(c.id)
            s._deleted(s.entity, True)
    asyncio.run(go())
    assert not (u.path / ".field-history" / f"{c.id}.json").exists()


def test_a_damaged_file_is_ignored_and_history_is_per_universe(home):
    u = vault.create_universe("U")
    (u.path / ".field-history").mkdir()
    (u.path / ".field-history" / "x.json").write_text("{ broken")
    assert fieldhistory.read(u, "x") == {}
    v = vault.create_universe("V")
    fieldhistory.write(u, "a", {"f": [1]})
    assert fieldhistory.read(v, "a") == {} and fieldhistory.read(u, "a") == {"f": [1]}
    h = fieldhistory.FieldHistory()
    h.use(u)
    assert h.get(("a", "f")) == [1]
    h.use(v)
    assert h.get(("a", "f"), []) == []                                    # (a different universe: nothing carried over)


def test_it_is_not_listed_as_an_entity_or_a_story(home):
    u = vault.create_universe("U")
    c = u.new_entity("character", "Ada")
    fieldhistory.write(u, c.id, {"trait": ["a"]})
    assert [e.id for e in u.entities()] == [c.id] and u.stories() == []
