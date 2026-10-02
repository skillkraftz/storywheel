"""The title bar never grows when it is clicked, in any mode (the Wheel, the Builder, Settings, and their dialogs)."""
import asyncio

from storywheel import builder, fill, settings_app, store, tui, vault
from conftest import make_engine
from storywheel.header import QuietHeader


async def clicked(app, times=3):
    async with app.run_test(size=(180, 50)) as pilot:
        await pilot.pause()
        header = app.screen.query_one(QuietHeader)
        heights = [header.size.height]
        for x in (40, 10, 100)[:times]:
            await pilot.click(QuietHeader, offset=(x, 0))
            await pilot.pause()
            heights.append(header.size.height)
        return heights, header.has_class("-tall")


def test_wheel_header_ignores_clicks(home):
    heights, tall = asyncio.run(clicked(tui.StorywheelApp(store.new_story(), make_engine(home))))
    assert heights == [1, 1, 1, 1] and not tall


def test_builder_header_ignores_clicks(home):
    vault.create_universe("U").new_story("S")
    heights, tall = asyncio.run(clicked(builder.BuilderApp(engine_factory=lambda u: fill.make_engine(u, seed=1), universe="u")))
    assert heights == [1, 1, 1, 1] and not tall


def test_settings_header_ignores_clicks(home):
    heights, tall = asyncio.run(clicked(settings_app.SettingsApp(None, "builder")))
    assert heights == [1, 1, 1, 1] and not tall


def test_the_header_class_stops_the_base_handler(home):
    """The regression: with a plain override, Header._on_click still ran and the height went 1 -> 3."""
    from textual.widgets import Header
    assert QuietHeader._on_click is not Header._on_click

    class Plain(QuietHeader):
        pass
    heights, _ = asyncio.run(clicked(tui.StorywheelApp(store.new_story(), make_engine(home)), times=1))
    assert heights[-1] == 1
