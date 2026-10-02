"""A world of the size that felt slow (160 entities, four ~20k-word stories): our own work for a click must stay small."""
import asyncio
import time

import pytest

from bigworld import make_big_universe
from storywheel import builder, fill, vault, writing_stats

LIMIT = 0.050                         # seconds of our own work, on a warm cache (the first look at the files may take longer)


@pytest.fixture
def big(home):
    return make_big_universe()


async def opened(big, size=(200, 50)):
    u, stories, made = big
    app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe=u.slug, story=stories[0].slug)
    return app, size


def best_of(fn, n=5):
    times = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t)
    return min(times), times


def test_selecting_an_entity_is_fast(big):
    u, stories, made = big
    chars = [e for e in made if e.type == "character"]
    async def go():
        app, size = await opened(big)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.type = "character"
            s.refresh_all()
            await pilot.pause()
            i = iter(range(1, 50))
            def select():
                s.entity = s.universe.entity(chars[next(i)].id)
                s.refresh_card()
                s.refresh_right()
            select()                                                   # (warm)
            return best_of(select)
    best, times = asyncio.run(go())
    assert best < LIMIT, [round(t * 1000) for t in times]


def test_rolling_one_field_is_fast(big):
    u, stories, made = big
    async def go():
        app, size = await opened(big)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.type = "character"
            s.refresh_all()
            s.entity = s.universe.entity(next(e for e in made if e.type == "character").id)
            s.refresh_card()
            await pilot.pause()
            s.card.highlighted = 3
            key = s.field_key()
            s.roll_field(key)                                          # (warm: the generator loads its lists once)
            return best_of(lambda: s.roll_field(key))
    best, times = asyncio.run(go())
    assert best < LIMIT, [round(t * 1000) for t in times]


def test_a_roll_reads_no_entity_file_twice_and_leaves_the_stats_alone(big, monkeypatch):
    u, stories, made = big
    reads = []
    real = vault.Entity.from_text
    monkeypatch.setattr(vault.Entity, "from_text", classmethod(lambda cls, text, path=None: reads.append(path) or real.__func__(cls, text, path)))
    async def go():
        app, size = await opened(big)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.type = "character"
            s.refresh_all()
            s.entity = s.universe.entity(next(e for e in made if e.type == "character").id)
            await pilot.pause()
            s.card.highlighted = 3
            key = s.field_key()
            s.roll_field(key)                                          # (the first roll may fill the cache)
            before = len(reads)
            stats_calls = []
            real_summary = writing_stats.summary
            monkeypatch.setattr(writing_stats, "summary", lambda *a, **k: stats_calls.append(1) or real_summary(*a, **k))
            s.roll_field(key)
            await pilot.pause()
            return len(reads) - before, len(stats_calls)
    extra_reads, stats_calls = asyncio.run(go())
    assert extra_reads <= 1                       # only the entity just written is read again
    assert stats_calls == 0                       # a field roll does not redraw the stats box


def test_changes_made_elsewhere_are_noticed(big):
    u, stories, made = big
    s0 = stories[0]
    before = s0.word_count()
    assert before > 15000 and s0.word_count() == before
    path = s0.manuscript_dir / "manuscript.md"
    time.sleep(0.01)
    path.write_text(path.read_text() + "\n\nOne more line of words.\n")      # (what the Writer does)
    assert s0.word_count() == before + 5
    e = next(x for x in u.entities() if x.type == "character")
    file = e.path
    time.sleep(0.01)
    file.write_text(file.read_text().replace(e.name, "Totally New Name"))    # (what Obsidian does)
    assert u.entity(e.id).name == "Totally New Name"


def test_entities_handed_out_are_copies(big):
    u, _, made = big
    e = u.entity(made[0].id)
    e.fields["name"] = "Changed in memory only"
    e.fields["tags"] = ["x"]
    assert u.entity(made[0].id).name != "Changed in memory only"


def test_appearances_and_outline_are_remembered_per_story(big):
    u, stories, made = big
    e = next(x for x in made if x.type == "character")
    first = [s.slug for s in u.appearances(e)]
    t = time.perf_counter()
    again = [s.slug for s in u.appearances(e)]
    assert again == first and time.perf_counter() - t < 0.02
    meta, sections = stories[0].load_outline()
    meta["title"] = "changed copy"
    assert stories[0].load_outline()[0]["title"] != "changed copy"


def test_the_stats_box_is_fast_once_the_files_are_known(big):
    u, stories, _ = big
    writing_stats.summary(u, stories[0])
    best, times = best_of(lambda: writing_stats.summary(u, stories[0]))
    assert best < LIMIT, [round(t * 1000) for t in times]


def test_the_wheel_with_a_big_universe_ticked_redraws_fast(big):
    from storywheel import store, tui
    from storywheel.engine import Engine
    u, _, _ = big
    async def go():
        st = store.new_story()
        st["universes"] = [u.slug]
        app = tui.StorywheelApp(st, Engine(seed=3))
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            m = app.main
            m.action_roll()
            return best_of(m.action_roll), best_of(m.refresh_all), best_of(m.refresh_universe)
    for best, times in asyncio.run(go()):
        assert best < LIMIT, [round(t * 1000) for t in times]


def test_the_settings_stats_tab_does_not_reread_the_manuscripts(big):
    from storywheel import settings_app
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            app.screen.query_one("#tabs").active = "t-stats"
            await pilot.pause()
            return best_of(lambda: app.screen.refresh_stats() if hasattr(app.screen, "refresh_stats") else writing_stats.per_story())
    best, times = asyncio.run(go())
    assert best < LIMIT, [round(t * 1000) for t in times]
