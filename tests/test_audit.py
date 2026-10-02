"""Features the brief (CLAUDE.md) describes, checked end to end: universe-own atom lists and starting a Wheel draft from a universe."""
import asyncio
import json

from storywheel import builder, fill, modes, store, vault


def test_a_universes_own_lists_are_merged_and_used_when_rolling_in_it(home):
    u = vault.create_universe("Thornwood", ["western"])
    (u.lists_dir / "job").mkdir(parents=True)
    (u.lists_dir / "job" / "own.json").write_text(json.dumps(
        {"slot": "job", "tags": ["western"], "entries": ["thornwood bell-ringer"]}))
    eng = fill.make_engine(u, seed=1)
    own = [wl for wl in eng.library.lists.values() if "thornwood bell-ringer" in [e.text for e in wl.entries]]
    assert own and own[0].slot == "job"
    other = fill.make_engine(vault.create_universe("Other"), seed=1)
    assert not [wl for wl in other.library.lists.values() if "thornwood bell-ringer" in [e.text for e in wl.entries]]
    c = u.new_entity("character")
    seen = set()
    f = fill.Filler(u, eng)
    for _ in range(300):
        seen.add(f.roll(c, "job"))
    assert "thornwood bell-ringer" in seen                     # drawn, like any list of the universe's genre


def test_new_wheel_draft_from_inside_a_universe_starts_with_it_ticked(home):
    u = vault.create_universe("Thornwood", ["western"])
    u.new_entity("character", "Ada Voss")
    u.new_story("Tale")
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="thornwood", story="tale")
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            app.screen_ref.action_new_draft()
            await pilot.pause()
            return app.next
    nxt = asyncio.run(go())
    assert nxt == ("wheel", {"universe": "thornwood", "new": True})
    story = None

    class State(dict):
        def update(self, **kw):
            dict.update(self, **kw)
    seen = {}
    import storywheel.tui as tui
    real = tui.run_app
    tui.run_app = lambda story, engine, st, notice="": seen.update(story=story)
    try:
        modes.run_wheel(State(), nxt[1], lambda: fill.make_engine(u, seed=1))
    finally:
        tui.run_app = real
    assert seen["story"]["universes"] == ["thornwood"] and not seen["story"]["kept"]
