"""Every dropdown (Select) opens showing its options, not just the first one (a one-line row must not clip the list that opens from it)."""
import asyncio

import pytest
from textual.widgets import Select, TabbedContent
from textual.widgets._select import SelectOverlay

from storywheel import vault


async def open_every_dropdown(app, pilot, keys):
    seen = []
    for key in keys:
        await pilot.press(key)
        await pilot.pause()
        await pilot.pause()
        screen = app.screen
        tabs = screen.query_one(TabbedContent)
        for pane in list(tabs.query("TabPane")):
            tabs.active = pane.id
            await pilot.pause()
            await pilot.pause()
            for sel in list(screen.query(Select)):
                if not sel.display or not sel.region.width or not sel.region.height:
                    continue
                sel.expanded = True
                await pilot.pause()
                await pilot.pause()
                ov = sel.query_one(SelectOverlay)
                seen.append((key, pane.id, sel.id, ov.option_count, ov.region.height))
                sel.expanded = False
                await pilot.pause()
    return seen


def run(size, keys):
    from storywheel import hub as hubmod
    from storywheel.engine import Engine
    from storywheel.ratings import Ratings
    async def go():
        u = vault.create_universe("Thornwood", ["western"])
        u.new_story("The Last Clause")
        app = hubmod.Hub(("builder", {"universe": "thornwood"}), lambda: Engine(seed=3), lambda: Ratings())
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await open_every_dropdown(app, pilot, keys)
    return asyncio.run(go())


@pytest.mark.parametrize("size", [(190, 50), (150, 30), (120, 24)])
def test_every_dropdown_in_settings_and_words_shows_its_options(home, size):
    seen = run(size, ("f4", "f5"))
    assert len(seen) >= (15 if size[1] >= 30 else 6)                      # (in a 24-row window the Words boxes are scrolled off screen)
    for key, pane, sid, count, height in seen:
        assert count >= 1
        assert height >= min(count, 5), (key, pane, sid, count, height)       # (several rows, not the one the row has)
        assert height <= max(count, 1) + 2


def test_the_rhymes_boxes_dropdowns_open_inside_their_box(home):
    seen = run((190, 50), ("f5",))
    rows = {sid: (count, height) for _k, _p, sid, count, height in seen}
    assert rows["rhsyl"][1] >= 5 and rows["rhrare"][1] >= 2
