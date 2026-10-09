"""Batch 21, item 1: the Wheel asks a new draft its format first, always shows it on the card, and lets you change it any time (F)."""
import asyncio

from storywheel import formats, session, settings, store, structures
from storywheel.engine import Engine
from storywheel.tui import ChoiceScreen, StorywheelApp
from conftest import make_engine, screen_text


def run_ask(home, story, script, size=(200, 50)):
    async def go():
        app = StorywheelApp(story, make_engine(home), ask_format=True)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


def header(app):
    return app.main.query_one("#card-box").border_title


def test_a_new_draft_asks_its_format_first_starting_on_your_default(home):
    settings.save_global({"format": "short-story", "script_kind": "flash"})

    async def script(app, pilot):
        dlg = app.screen
        assert isinstance(dlg, ChoiceScreen) and [v for _l, v in dlg.options] == [f.key for f in formats.FORMATS]
        shown = dlg.query_one("#choices").highlighted
        await press(pilot, "enter")                                                   # (the highlighted row is the default)
        return shown, app.session.story.get("format"), header(app), type(app.screen).__name__
    shown, fmt, head, after = run_ask(home, store.new_story(), script)
    assert shown == 0 and fmt == "flash" and "Flash fiction" in head and "Genre & mood" in head and after == "MainScreen"


def test_picking_another_format_and_escape_for_the_default(home):
    async def pick(app, pilot):
        await press(pilot, "down", "enter")                                           # (starts on short story, the default; one down is the novel)
        return app.session.story["format"], header(app)
    fmt, head = run_ask(home, store.new_story(), pick)
    assert fmt == "novel" and "Novel" in head

    async def escape(app, pilot):
        assert isinstance(app.screen, ChoiceScreen)
        await press(pilot, "escape")
        return app.session.story["format"], header(app), isinstance(app.screen, ChoiceScreen)
    fmt, head, still = run_ask(home, store.new_story(), escape)
    assert fmt == "short-story" and "Short story" in head and not still


def test_the_highlight_starts_on_the_default_format(home):
    async def script(app, pilot):
        return app.screen.query_one("#choices").highlighted
    assert run_ask(home, store.new_story(), script) == 1                              # (short story is the second row)


def test_a_draft_that_has_been_asked_or_has_kept_something_is_not_asked(home):
    kept = store.new_story()
    kept["kept"]["genre"] = {"genre": "noir", "mood": "wry"}

    async def script(app, pilot):
        return type(app.screen).__name__
    assert run_ask(home, kept, script) == "MainScreen"
    asked = store.new_story()
    asked["format"] = "novel"
    assert run_ask(home, asked, script) == "MainScreen"


def test_f_changes_the_format_any_time_and_swaps_a_structure_that_no_longer_fits(home):
    story = store.new_story()
    story["format"] = "novel"
    story["kept"]["genre"] = {"genre": "noir", "mood": "wry"}
    story["kept"]["structure"] = {"format": "Novel", "structure": "Save the Cat"}
    story["kept"]["spine"] = {"stc_opening": "Something."}
    story["step"] = 3

    async def script(app, pilot):
        assert header(app).startswith("Protagonist") and "Novel" in header(app)
        await press(pilot, "F")
        dlg = app.screen
        assert isinstance(dlg, ChoiceScreen) and dlg.query_one("#choices").highlighted == 2          # (starts on the current format)
        dlg.query_one("#choices").highlighted = 1
        await press(pilot, "enter")                                                   # short story
        return (app.session.story["format"], dict(app.session.story["kept"]["structure"]), "spine" in app.session.story["kept"],
                header(app), " ".join(app.session.take_notes()) + " " + screen_text(app))
    fmt, kept, body, head, said = run_ask(home, story, script)
    assert fmt == "short-story" and "Short story" in head
    assert kept == {"format": "Short story", "structure": "Story Spine"} and not body
    assert "doesn't fit" in " ".join(said.split())


def test_changing_the_format_to_one_the_structure_fits_changes_nothing_else(home):
    s = session.Session(store.new_story(), Engine(seed=2))
    s.enter(0)
    s.keep()                                                                          # genre
    s.keep()                                                                          # structure
    s.set_format("short-story")
    s.set_format("novel")
    assert s.story["kept"]["structure"]["format"] == "Novel"
    s.set_format("flash")
    assert structures.find(s.story["kept"]["structure"]["structure"]) in formats.structures_for("flash")


def test_the_promote_screen_offers_every_other_format_including_flash(home):
    from storywheel.sample import build_story
    from storywheel import vault, promote
    from storywheel.tui import PromotePreviewScreen
    draft = build_story(Engine(seed=5), ["noir"], structure="story-spine")
    draft["format"] = "novel"
    u = vault.create_universe("Rain City", ["noir"])
    plan = promote.build_plan(draft, u, Engine(seed=5), None)

    async def go():
        app = StorywheelApp(draft, make_engine(home))
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            app.push_screen(PromotePreviewScreen(plan))
            await pilot.pause()
            await pilot.pause()
            return " ".join(screen_text(app).split())
    text = asyncio.run(go())
    for f in formats.FORMATS:
        assert f.label.lower() in text
    assert "flash fiction" in text and "(this story)" in text
