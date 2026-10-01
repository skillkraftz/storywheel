import json

import pytest

from storywheel import store
from storywheel.engine import Engine
from storywheel.library import Library, WordList, Entry
from storywheel.mix import Mix, new_mix

PROFILES = {
    "western": {"western": 3, "historical": 2, "general": 1},
    "fantasy": {"fantasy": 3, "mythological": 2, "general": 1},
    "horror": {"horror": 3, "general": 1},
}


def wl(list_id, tags, entries=("x",), slot=None):
    slot = slot or list_id.split("/")[0]
    return WordList(list_id, slot, tags, [e if isinstance(e, Entry) else Entry(e) for e in entries])


def make_library(lists, floor=0.12):
    return Library({l.id: l for l in lists}, PROFILES, {"general": 1.0}, floor)


@pytest.fixture
def library():
    return make_library([])


@pytest.fixture
def engine():
    return Engine(seed=7)


def mix_for(library, *genres, **changes):
    data = new_mix(genres)
    data.update(changes)
    return Mix(data, library)


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Point the store at a throwaway home and output folder."""
    monkeypatch.setattr(store, "HOME", tmp_path / "home")
    monkeypatch.setattr(store, "OUT", tmp_path / "out")
    monkeypatch.setattr(store, "STORIES", tmp_path / "home" / "stories")
    monkeypatch.setattr(store, "UNIVERSE", tmp_path / "home" / "universe.json")
    return tmp_path


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc))
    return path


# --- helpers for the full-screen app ----------------------------------------------------------------------

import asyncio  # noqa: E402
import re  # noqa: E402


def screen_text(app):
    """The text on the app's screen right now, line by line (read from a screenshot)."""
    svg = app.export_screenshot()
    lines = {}
    for y, t in re.findall(r'<text class="[^"]*" x="[\d.]+" y="([\d.]+)"[^>]*>([^<]*)</text>', svg):
        t = t.replace("&#160;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#x27;", "'")
        lines.setdefault(float(y), []).append(t)
    return "\n".join("".join(v).rstrip() for _y, v in sorted(lines.items()))


def make_engine(home, seed=3, ratings=True):
    from storywheel.engine import Engine
    from storywheel.ratings import Ratings
    return Engine(seed=seed, user_dir=home / "home",
                  ratings=Ratings(home / "home" / "ratings.json") if ratings else None)


def run_tui(story, engine, script, size=(120, 40)):
    """Start the app on a story, run `script(app, pilot)`, and return what it returns."""
    from storywheel.tui import StorywheelApp

    async def go():
        app = StorywheelApp(story, engine)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())
