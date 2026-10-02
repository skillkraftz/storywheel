"""The title bar never grows when it is clicked, in any mode."""
import asyncio

from storywheel import builder, fill, settings_app, store, tui, vault
from conftest import make_engine
from storywheel.header import QuietHeader


async def clicked(app):
    async with app.run_test(size=(180, 50)) as pilot:
        await pilot.pause()
        header = app.screen.query_one(QuietHeader)
        h0 = header.size.height
        await pilot.click(QuietHeader, offset=(40, 0))
        await pilot.pause()
        await pilot.click(QuietHeader, offset=(40, 0))
        await pilot.pause()
        return h0, header.size.height, header.has_class("-tall")


def test_wheel_header_ignores_clicks(home):
    h0, h1, tall = asyncio.run(clicked(tui.StorywheelApp(store.new_story(), make_engine(home))))
    assert h0 == h1 == 1 and not tall


def test_builder_header_ignores_clicks(home):
    vault.create_universe("U").new_story("S")
    h0, h1, tall = asyncio.run(clicked(builder.BuilderApp(engine_factory=lambda u: fill.make_engine(u, seed=1), universe="u")))
    assert h0 == h1 == 1 and not tall


def test_settings_header_ignores_clicks(home):
    h0, h1, tall = asyncio.run(clicked(settings_app.SettingsApp(None, "builder")))
    assert h0 == h1 == 1 and not tall
