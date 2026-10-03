"""q is "back" everywhere; Q quits storywheel (and asks); F1-F5 are labelled as the modes in every footer and help screen."""
import asyncio

import pytest

from dictfixture import build_fixture
from storywheel import builder, dictionary, fill, modes, navigation, settings_app, store, tui, vault, words_app
from conftest import make_engine, screen_text


@pytest.fixture(autouse=True)
def clean_trail():
    modes.TRAIL.clear()
    yield
    modes.TRAIL.clear()


@pytest.fixture
def world(home):
    u = vault.create_universe("Thornwood", ["western"])
    u.new_story("The Last Clause")
    return u


def flat(t):
    return " ".join(t.split())


def make(kind, home):
    if kind == "wheel":
        return tui.StorywheelApp(store.new_story(), make_engine(home))
    if kind == "builder":
        return builder.BuilderApp(engine_factory=lambda u: fill.make_engine(u, seed=1), universe="thornwood")
    if kind == "settings":
        return settings_app.SettingsApp(None, "builder")
    return words_app.WordsApp(None, "builder", {"universe": "thornwood"})


KINDS = ["wheel", "builder", "settings", "words"]


@pytest.mark.parametrize("kind", KINDS)
def test_every_footer_says_q_is_back_and_Q_quits_storywheel_and_labels_the_modes(world, kind):
    async def go():
        app = make(kind, world.path.parent)
        async with app.run_test(size=(240, 55)) as pilot:
            await pilot.pause()
            if kind == "words":
                app.screen.query("OptionList").first().focus()          # (with the cursor in a text box, q and Q are letters: the footer hides them)
                await pilot.pause()
            return flat(screen_text(app))
    text = asyncio.run(go())
    assert "q Back" in text and "Q Quit storywheel" in text and "F1-F5 Modes: Wheel · Builder · Writer · Settings · Words" in text


@pytest.mark.parametrize("kind", KINDS)
def test_q_goes_back_along_the_trail(world, kind):
    modes.TRAIL.append("settings" if kind != "settings" else "builder")
    async def go():
        app = make(kind, world.path.parent)
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            app.screen.query("OptionList").first().focus() if kind == "words" else None
            await pilot.pause()
            await pilot.press("q")
            await pilot.pause()
            return app.next
    nxt = asyncio.run(go())
    assert nxt is not None and nxt[0] == "back"


@pytest.mark.parametrize("kind", ["wheel", "builder"])
def test_q_with_nowhere_to_go_back_says_so_and_stays(world, kind):
    async def go():
        app = make(kind, world.path.parent)
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            await pilot.press("q")
            await pilot.pause()
            return app.next, flat(screen_text(app))
    nxt, text = asyncio.run(go())
    assert nxt is None and "nothing to go back to" in text and "Q to quit storywheel" in text


@pytest.mark.parametrize("kind", ["builder", "settings", "words"])
def test_Q_asks_first_and_yes_quits_and_no_stays(world, kind):
    async def go(answer):
        app = make(kind, world.path.parent)
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            if kind == "words":
                app.screen.query("OptionList").first().focus()
            await pilot.press("Q")
            await pilot.pause()
            asked = type(app.screen).__name__ == "ConfirmScreen" and "Quit storywheel" in flat(screen_text(app))
            await pilot.press(answer)
            await pilot.pause()
            return asked, app.next
    asked, nxt = asyncio.run(go("n"))
    assert asked and nxt is None
    asked, nxt = asyncio.run(go("y"))
    assert asked and nxt == ("quit", {})


def test_Q_in_the_wheel_is_the_keep_or_delete_question(world):
    async def go():
        app = make("wheel", world.path.parent)
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            await pilot.press("Q")
            await pilot.pause()
            return type(app.screen).__name__, flat(screen_text(app))
    screen, text = asyncio.run(go())
    assert screen == "QuitScreen" and "Keep this story or delete it" in text


def test_the_done_dialog_closes_with_q_and_quits_with_capital_Q():
    assert "Q" in tui.DoneScreen.BINDINGS[0].key and "q" in tui.DoneScreen.BINDINGS[1].key


# --- the trail ---------------------------------------------------------------------------------------------------------------------

def test_moves_build_the_trail_and_a_visited_mode_cuts_it_back(home):
    modes._arrive("wheel", "builder")
    modes._arrive("builder", "words")
    modes._arrive("words", "settings")
    assert modes.TRAIL == ["wheel", "builder", "words"]
    modes._arrive("settings", "builder")                # back at a mode already on the trail: cut back to before it
    assert modes.TRAIL == ["wheel"]
    modes._arrive("builder", "builder")
    assert modes.TRAIL == ["wheel"]
    assert modes.can_go_back()


def test_the_loop_resolves_back_to_the_mode_you_came_from(home, monkeypatch):
    seen = []
    script = {"builder": [("words", {})], "words": [("back", {"fallback": "builder"})], "wheel": []}
    def make_runner(name):
        def run(*a, **k):
            seen.append(name)
            nxt = script[name].pop(0) if script[name] else None
            return nxt
        return run
    monkeypatch.setattr(modes, "run_builder", lambda st, p, r: make_runner("builder")())
    monkeypatch.setattr(modes, "run_words", lambda st, p: make_runner("words")())
    monkeypatch.setattr(modes, "run_wheel", lambda st, p, e, plain=False: make_runner("wheel")())
    script["builder"].append(None)
    modes.run_classic(("builder", {}), None, None)
    assert seen == ["builder", "words", "builder"]


def test_back_with_an_empty_trail_uses_the_fallback(home, monkeypatch):
    seen = []
    monkeypatch.setattr(modes, "run_settings", lambda st, p: seen.append("settings") or ("back", {"fallback": "words"}) if len(seen) == 0 else None)
    monkeypatch.setattr(modes, "run_words", lambda st, p: seen.append("words") or None)
    modes.run_classic(("settings", {}), None, None)
    assert seen == ["settings", "words"]


# --- the help screens ------------------------------------------------------------------------------------------------------------------

def test_every_help_screen_says_what_q_and_Q_do():
    for text in (tui.HELP, builder.HELP, settings_app.HELP, words_app.HELP):
        assert "[b]q[/b]" in text and "[b]Q[/b]" in text and "uit storywheel" in text.replace("Quit storywheel", "Quit storywheel")
    assert "F1-F5" in tui.HELP and "F1-F5" in settings_app.HELP and "F1 Wheel" in builder.HELP and "F5 Words" in builder.HELP
