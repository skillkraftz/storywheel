"""Print what each mode looks like at a given terminal size (default 190x50), from a small made-up library, to look for wrapping and cut-off text.

    python tools/screens.py [COLUMNSxROWS] [mode ...]      modes: wheel builder builder-thing builder-story settings words
"""
import asyncio
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
tmp = tempfile.mkdtemp()
os.environ["STORYWHEEL_HOME"] = os.path.join(tmp, "home")
os.environ["STORYWHEEL_LIBRARY"] = os.path.join(tmp, "library")
os.environ["STORYWHEEL_MANUSCRIPTS"] = os.path.join(tmp, "out")
os.makedirs(os.environ["STORYWHEEL_HOME"])

from storywheel import hub as hubmod, vault  # noqa: E402
from storywheel.engine import Engine  # noqa: E402
from storywheel.ratings import Ratings  # noqa: E402


def text_of(app):
    return "\n".join(line.rstrip() for line in (app.export_screenshot and __import__("textual.pilot", fromlist=["x"]) and _lines(app)))


def _lines(app):
    from rich.console import Console
    import io
    from textual._compositor import Compositor  # noqa: F401
    width, height = app.size
    return ["".join(seg.text for seg in strip) for strip in app.screen._compositor.render_strips()][:height]


def build_library():
    u = vault.create_universe("The Unbelievably Long Named Universe Of Dry Country", ["western"])
    for n in ("Stacie Anderson", "Wade Hollis", "Maeve O'Brien"):
        u.new_entity("character", n, {"job": "land clerk", "want": "a quiet claim", "trait": "stubborn", "secret": "she forged the deed to the north pasture years ago",
                                       "flaw": "cannot leave a grudge alone", "need": "to trust somebody with the truth"})
    u.new_entity("place", "Red Draw", {"kind": "town", "era": "the strike", "rumor": "the well was poisoned by the land office before anyone moved in"})
    t = u.new_entity("thing", "bottle of moonlight", {"description": "a corked bottle that glows faintly at night and hums when someone near it is lying to themselves"})
    t.proper = False
    u.save_entity(t)
    u.new_entity("group", "The Land Office", {"goal": "to own every acre between the river and the pass before the railroad arrives"})
    s = u.new_story("The Last Clause", {"genre": "western"}, {"Premise": "A clerk finds a clause."})
    s.add_scene("Opening", "Stacie ran down the road.")
    u.new_story("A Second Story With A Rather Long Title Indeed", {"genre": "western"}, {"Premise": "x"})
    return u, s, t


async def main(size, modes):
    u, s, t = build_library()
    app = hubmod.Hub(("builder", {"universe": u.slug, "story": s.slug}), lambda: Engine(seed=3), lambda: Ratings())
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        for mode in modes:
            if mode == "builder-thing":
                b = app.screens_built["builder"]
                await pilot.press("3")
                await pilot.pause()
                b.entity = u.entity(t.id)
                b.refresh_all()
                await pilot.pause()
                app.go("builder", {})
            elif mode == "builder-story":
                app.go("builder", {"universe": u.slug, "story": s.slug})
            else:
                app.go(mode, {"universe": u.slug})
            await pilot.pause()
            await pilot.pause()
            print(f"===== {mode} ({size[0]}x{size[1]}) " + "=" * 40)
            print("\n".join(line.rstrip() for line in _lines(app)))


if __name__ == "__main__":
    args = sys.argv[1:]
    size = (190, 50)
    if args and "x" in args[0] and args[0][0].isdigit():
        w, h = args.pop(0).split("x")
        size = (int(w), int(h))
    asyncio.run(main(size, args or ["wheel", "builder", "builder-thing", "settings", "words"]))
