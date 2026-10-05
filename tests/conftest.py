import json

import pytest

from storywheel import store
from storywheel.engine import Engine
from storywheel.library import Library, WordList, Entry
from storywheel.mix import Mix, new_mix

@pytest.fixture(autouse=True)
def _own_grammar_port(monkeypatch):
    """Never talk to a real LanguageTool server on the usual port (the owner may be running one): every test gets a free port of its own."""
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    monkeypatch.setenv("STORYWHEEL_GRAMMAR_PORT", str(port))


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
    monkeypatch.setenv("STORYWHEEL_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("STORYWHEEL_LIBRARY", str(tmp_path / "library"))
    monkeypatch.setenv("STORYWHEEL_MANUSCRIPTS", str(tmp_path / "manuscripts"))
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


def run_tui(story, engine, script, size=(200, 50)):
    """Start the app on a story, run `script(app, pilot)`, and return what it returns."""
    from storywheel.tui import StorywheelApp

    async def go():
        app = StorywheelApp(story, engine)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


# --- the testing policy (CLAUDE.md, batch 14): markers are assigned here, in one place -------------------------------------
#
# serial: cannot run beside other tests (a real terminal on a pty, the hub, shared ports); the full run runs these in a second pass without xdist.
# slow:   left out while working (`-m "not slow"`): real terminals, performance, and the 200-story fidelity / repetition checks.

SERIAL_FILES = {"test_appearance.py", "test_hub.py", "test_kitty_keys.py", "test_switching.py", "test_performance.py", "test_grammar_server.py"}
# tests that start LibreOffice: two at once share its profile and one of them fails, so they run in the serial pass
SERIAL_TESTS = ("test_export.py::test_the_docx_opens_in_libreoffice", "test_export.py::test_odt_is_made_with_libreoffice")
SLOW_FILES = SERIAL_FILES | {"test_menu_keys.py", "test_menus.py", "test_dropdowns.py", "test_setup_update.py", "test_builder_ratings.py", "test_layout_batch6.py"}
SLOW_TESTS = (                                   # (parts of node ids) each takes more than about five seconds on its own
    "test_genre_content.py::test_no_genres_frames_are_even_close",
    "test_batch15.py::test_no_rendered_text_has_an_empty_fill",
    "test_batch15.py::test_a_period_era_never_gets",
    "test_batch15.py::test_builder_beat_rolls_never_leave_a_blank",
    "test_genre_content.py::test_romance_blends_with_every_other",
    "test_genre_content.py::test_blends_read_like_both",
    "test_genre_content.py::test_no_repeats_and_nothing_far_above",
    "test_genre_content.py::test_a_single_genre_draws_about_four_fifths",
    "test_genre_content.py::test_the_voice_follows_in_verbs",
    "test_genre_content.py::test_mystery_clues_come_back",
    "test_ratings.py::test_a_disliked_frame_is_drawn_less",
    "test_sentence_polish.py::test_a_comedy_is_rarely_eerie",
    "test_sentence_lint.py::test_samples_of_the_new_genres",
    "test_leaks.py::test_no_frame_doubles_its_verb",
    "test_leaks.py::test_every_structure_is_free_of_leaks",
    "test_era_and_places.py::test_noir_",
    "test_era_and_places.py::test_the_new_genres_story_shapes",
    "test_coherence.py::test_ten_reframes",
    "test_coherence.py::test_future_eras_do_show_up",
    "test_coherence.py::test_templates_the_story_cannot_satisfy",
    "test_coherence.py::test_stories_never_say_the_stockyards",
    "test_coherence.py::test_modern_and_future_eras_do_not_leak",
    "test_atoms.py::test_every_sentence_starts_with_a_capital",
    "test_atoms.py::test_assembled_stories_do_not_repeat",
    "test_kinds_floors.py::test_a_western_story_rarely_has",
    "test_kinds_floors.py::test_verb_and_abstract_atoms_follow",
    "test_fidelity.py::test_the_rest_is_general_modern",
    "test_fidelity.py::test_excluding_a_tag_removes_it_even",
    "test_layout_stability.py::test_focusing_any",
    "test_settings_mode.py::test_the_mode_keys_leave_settings",
    "test_words.py::test_the_part_of_speech",
)


def pytest_collection_modifyitems(config, items):
    import inspect
    for item in items:
        name = item.nodeid.rsplit("/", 1)[-1]
        fname = name.split("::")[0]
        try:
            source = inspect.getsource(item.function)
        except (OSError, TypeError, AttributeError):
            source = ""
        real_terminal = "pty.fork" in source or "real_terminal" in item.name
        if fname in SERIAL_FILES or real_terminal or any(part in name for part in SERIAL_TESTS):
            item.add_marker(pytest.mark.serial)
        if fname in SLOW_FILES or real_terminal or any(part in name for part in SLOW_TESTS):
            item.add_marker(pytest.mark.slow)
