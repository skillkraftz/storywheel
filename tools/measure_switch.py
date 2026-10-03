"""Measure how long switching between the Textual modes takes (milliseconds), on a small made-up library.

    python tools/measure_switch.py            old design: each mode is its own app (build, mount, first paint)
    python tools/measure_switch.py hub        new design: one app, modes kept alive (first visit, then repeat visits)

Run on the machine you care about (a Raspberry Pi's numbers are what matters there). Uses a temporary library and home.
"""
import asyncio
import pathlib
import os
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
tmp = tempfile.mkdtemp()
os.environ["STORYWHEEL_HOME"] = os.path.join(tmp, "home")
os.environ["STORYWHEEL_LIBRARY"] = os.path.join(tmp, "library")
os.environ["STORYWHEEL_MANUSCRIPTS"] = os.path.join(tmp, "out")
os.makedirs(os.environ["STORYWHEEL_HOME"])

from storywheel import fill, vault  # noqa: E402
from storywheel.ratings import Ratings  # noqa: E402

SIZE = (190, 50)


def make_library():
    u = vault.create_universe("Thornwood", ["western"])
    for i in range(40):
        u.new_entity("character", f"Person Number{i}", {"job": "clerk", "want": "a quiet claim"})
        u.new_entity("place", f"Place {i}", {"kind": "town"})
    s = u.new_story("The Last Clause")
    s.add_scene("Opening", "Stacie ran down the road.\n\nIt was dry.")
    return u, s


async def timed(label, coro_factory, results):
    t = time.perf_counter()
    await coro_factory()
    results.append((label, (time.perf_counter() - t) * 1000))


def old():
    from storywheel import builder, settings_app, tui, words_app, store
    from storywheel.engine import Engine
    u, s = make_library()
    results = []

    async def run_one(label, make):
        app = make()
        t = time.perf_counter()
        async with app.run_test(size=SIZE) as pilot:
            await pilot.pause()
            results.append((label, (time.perf_counter() - t) * 1000))

    async def go():
        await run_one("builder", lambda: builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), ratings=Ratings(), universe=u.slug))
        await run_one("settings", lambda: settings_app.SettingsApp(None, "builder"))
        await run_one("words", lambda: words_app.WordsApp(None, "builder", {"universe": u.slug}))
        engine = Engine(seed=1)
        await run_one("wheel", lambda: tui.StorywheelApp(store.new_story(), engine))
    asyncio.run(go())
    return results


def hub():
    from storywheel import hub as hubmod
    u, s = make_library()
    results = []

    async def go():
        app = hubmod.Hub(start=("builder", {"universe": u.slug}), get_engine=lambda: __import__("storywheel.engine", fromlist=["Engine"]).Engine(seed=1),
                         get_ratings=lambda: Ratings())
        async with app.run_test(size=SIZE) as pilot:
            await pilot.pause()
            for round_ in ("first visit", "repeat visit", "repeat visit"):
                for mode in ("settings", "words", "wheel", "builder"):
                    t = time.perf_counter()
                    app.go(mode, {"universe": u.slug})
                    await pilot.pause()
                    results.append((f"{mode} ({round_})", (time.perf_counter() - t) * 1000))
                    if round_ != "first visit":
                        results.append((f"   of which our code", app.timings[-1][1]))
    asyncio.run(go())
    return results


if __name__ == "__main__":
    rows = hub() if (len(sys.argv) > 1 and sys.argv[1] == "hub") else old()
    for label, ms in rows:
        print(f"  {label:<28} {ms:7.0f} ms")
