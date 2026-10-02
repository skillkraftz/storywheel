"""The Lookup dialog (F5) in the Wheel, the Builder and Settings."""
import asyncio

import pytest
from textual.widgets import Input

from dictfixture import build_fixture
from storywheel import builder, dictionary, fill, settings_app, store, tui, vault
from storywheel.lookup_screen import LookupScreen
from conftest import make_engine, screen_text


@pytest.fixture
def index(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    dictionary.forget()
    yield out
    dictionary.forget()


def flat(t):
    return " ".join(t.split())


async def drive(app, word):
    async with app.run_test(size=(180, 50)) as pilot:
        await pilot.pause()
        await pilot.press("f5")
        await pilot.pause()
        opened = isinstance(app.screen, LookupScreen)
        box = app.screen.query_one("#word", Input)
        focused = app.screen.focused is box
        box.value = word
        await pilot.press("enter")
        await pilot.pause()
        text = flat(screen_text(app))
        await pilot.press("escape")
        await pilot.pause()
        return opened, focused, text, isinstance(app.screen, LookupScreen)


def check(result, needles):
    opened, focused, text, still = result
    assert opened and focused and not still
    for n in needles:
        assert n in text, (n, text[:400])


def test_wheel_lookup(home, index):
    check(asyncio.run(drive(tui.StorywheelApp(store.new_story(), make_engine(home)), "geese")), ["goose", "(from 'geese')", "web-footed long-necked birds", "Open English WordNet"])


def test_builder_lookup(home, index):
    vault.create_universe("U").new_story("S")
    app = builder.BuilderApp(engine_factory=lambda u: fill.make_engine(u, seed=1), universe="u")
    check(asyncio.run(drive(app, "running")), ["run", "move fast by using legs", "Similar:", "sprint"])


def test_settings_lookup(home, index):
    check(asyncio.run(drive(settings_app.SettingsApp(None, "builder"), "Happy")), ["adjective", "enjoying or showing joy", "Opposite:", "unhappy"])


def test_a_missing_word_shows_close_spellings(home, index):
    check(asyncio.run(drive(tui.StorywheelApp(store.new_story(), make_engine(home)), "hapyp")), ["No entry for 'hapyp'", "Did you mean: happy"])


def test_without_a_dictionary_the_dialog_says_how_to_install_it(home, tmp_path, monkeypatch):
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(tmp_path / "none.sqlite"))
    dictionary.forget()
    check(asyncio.run(drive(tui.StorywheelApp(store.new_story(), make_engine(home)), "dog")), ["storywheel dictionary install"])


def test_f5_is_in_the_help_of_every_mode_and_the_footer(home):
    assert "F5" in tui.HELP and "F5" in builder.HELP
