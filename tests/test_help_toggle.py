"""The key of the mode you are in toggles its help; the key of another mode closes the help and goes there."""
import asyncio

import pytest

from storywheel import vault, writer
from test_help import run_hub, world  # noqa: F401  (the hub driver and the library fixture)

MODES = [("f1", "wheel", "MainScreen"), ("f2", "builder", "BuilderScreen"), ("f4", "settings", "SettingsScreen"), ("f5", "words", "WordsScreen")]


async def settle(pilot):
    for _ in range(4):
        await pilot.pause()


async def into(app, pilot, key, screen):
    """Be in the mode (its help closed)."""
    if type(app.screen).__name__ == "ChoiceScreen":                        # (a new draft asks its format first: Esc takes the default)
        await pilot.press("escape")
        await settle(pilot)
    if type(app.screen).__name__ != screen:
        await pilot.press(key)
        await settle(pilot)
        await settle(pilot)
        if type(app.screen).__name__ == "ChoiceScreen":                    # (a new draft asks its format first: Esc takes the default)
            await pilot.press("escape")
            await settle(pilot)
    assert type(app.screen).__name__ == screen, (key, type(app.screen).__name__)


@pytest.mark.parametrize("key,mode,screen", MODES)
def test_the_modes_key_opens_its_help_and_the_same_key_closes_it(world, key, mode, screen):
    async def script(app, pilot):
        await into(app, pilot, key, screen)
        await pilot.press(key)
        await settle(pilot)
        opened = type(app.screen).__name__
        await pilot.press(key)
        await settle(pilot)
        closed = type(app.screen).__name__
        await pilot.press(key)                                              # and it opens again: a toggle
        await settle(pilot)
        again = type(app.screen).__name__
        return opened, closed, again, app.mode_name
    assert run_hub(script) == ("HelpScreen", screen, "HelpScreen", mode)


@pytest.mark.parametrize("key,mode,screen", MODES)
def test_question_mark_closes_it_too(world, key, mode, screen):
    async def script(app, pilot):
        await into(app, pilot, key, screen)
        app.screen.set_focus(None)                                          # (in Words a text box has the focus and takes ? as a letter)
        await pilot.press("question_mark")
        await settle(pilot)
        opened = type(app.screen).__name__
        await pilot.press("question_mark")
        await settle(pilot)
        return opened, type(app.screen).__name__
    assert run_hub(script) == ("HelpScreen", screen)


@pytest.mark.parametrize("key,mode,screen", MODES)
@pytest.mark.parametrize("other,other_mode,other_screen", [m for m in MODES])
def test_another_modes_key_closes_the_help_and_goes_there(world, key, mode, screen, other, other_mode, other_screen):
    if other == key:
        pytest.skip("the same key is the toggle")
    async def script(app, pilot):
        await into(app, pilot, key, screen)
        await pilot.press(key)
        await settle(pilot)
        assert type(app.screen).__name__ == "HelpScreen"
        await pilot.press(other)
        await settle(pilot)
        await settle(pilot)
        if type(app.screen).__name__ == "ChoiceScreen":                    # (the Wheel's new draft asks its format first: Esc takes the default)
            await pilot.press("escape")
            await settle(pilot)
        return type(app.screen).__name__, app.mode_name, len([s for s in app.screen_stack if type(s).__name__ == "HelpScreen"])
    assert run_hub(script) == (other_screen, other_mode, 0)


def test_f3_in_the_help_goes_to_the_writer_or_says_why_it_cannot(world, monkeypatch):
    monkeypatch.setattr(writer, "check", lambda: "Neovim isn't installed (a test).")
    """From a mode's help, F3 closes the help and acts as F3 does in that mode (without a story or Neovim it says so, it does not stay in the help)."""
    async def script(app, pilot):
        await pilot.press("f4")
        await settle(pilot)
        await pilot.press("f4")
        await settle(pilot)
        await pilot.press("f3")
        await settle(pilot)
        return type(app.screen).__name__
    assert run_hub(script) != "HelpScreen"


# --- the Writer ---------------------------------------------------------------------------------------------------------------------------

SKIP_NVIM = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


@pytest.fixture
def story(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    s.add_scene("Opening", "Hello brave world")
    return s


@SKIP_NVIM
def test_f3_toggles_the_writers_help_float(home, story):
    from test_notepad import run as nrun
    check = "R.float = vim.api.nvim_win_get_config(0).relative; R.mode = vim.fn.mode()"
    assert nrun(story, "", "<F3>", check)["float"] == "editor"
    r = nrun(story, "", "<F3><F3>", check)
    assert r["float"] == "" and r["mode"] == "i"
    assert nrun(story, "", "<F3><F3><F3>", check)["float"] == "editor"
    assert nrun(story, "", "<F3><Esc>", check)["float"] == ""
    r = nrun(story, "", "<F12>" + "<Down>" * 12 + "<CR>", "R.labels = {}; for i, it in ipairs(require('sw.menu').items()) do R.labels[i] = it[1] end")


@SKIP_NVIM
@pytest.mark.parametrize("key,where", [("<F1>", "wheel"), ("<F2>", "builder"), ("<F4>", "settings")])
def test_other_mode_keys_in_the_writers_help_switch_as_usual(home, story, key, where):
    from test_notepad import run as nrun
    nrun(story, "", "<F3>" + key, "", quits=True)
    assert (story.path.parent / "return.txt").read_text() == where


@SKIP_NVIM
def test_f5_in_the_writers_help_goes_to_words(home, story):
    from test_notepad import run as nrun
    nrun(story, "", "<F3><F5>", "", quits=True)
    assert (story.path.parent / "return.txt").read_text() == "words"
