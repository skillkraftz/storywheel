"""Nothing may move or resize when it gets the focus (every list, every mode), and the Builder's layout holds together."""
import asyncio

import pytest
from textual.widgets import DataTable, Input, OptionList, Select, TextArea, Tree

from storywheel import builder, fill, promote, settings_app, store, vault
from storywheel.sample import build_story
from conftest import make_engine, screen_text

KINDS = (OptionList, Tree, TextArea, DataTable, Input, Select)


def flat(text):
    return " ".join(text.split())


async def geometry_changes(app, pilot, screen=None):
    """Focus every focusable list-like widget in turn; report any whose box or any other widget's box changed."""
    screen = screen or app.screen
    widgets = [w for w in screen.query("*") if isinstance(w, KINDS) and w.can_focus and w.display and w.region.area > 0]
    def snapshot():
        # (the border's STYLE: its colour may change with focus, its presence or kind must not)
        return {id(w): (w.region, w.content_region.size, w.styles.border_top[0], w.styles.border_left[0]) for w in screen.query("*")
                if w.display and w.region.area > 0}
    base = snapshot()
    problems = []
    for w in widgets:
        w.focus()
        await pilot.pause()
        now = snapshot()
        for key, value in now.items():
            if key in base and base[key] != value:
                who = next((x for x in screen.query("*") if id(x) == key), None)
                problems.append((w.id or type(w).__name__, who.id or type(who).__name__, base[key], value))
        screen.set_focus(None)
        await pilot.pause()
    return len(widgets), problems


def test_focusing_any_list_in_the_builder_changes_nothing(home):
    u = vault.create_universe("W", ["western"])
    for i in range(30):
        u.new_entity("character", f"Person {i}")
    s = u.new_story("Tale", {"genre": "western"}, {"Premise": "A premise."})
    s.append_scene("Opening", "Text here.")
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="w", story="tale")
        async with app.run_test(size=(220, 55)) as pilot:
            await pilot.pause()
            result = []
            for key in ("6", "7", "8"):               # each tab of the right column
                await pilot.press(key)
                await pilot.pause()
                result.append(await geometry_changes(app, pilot, app.screen_ref))
            return result
    for n, problems in asyncio.run(go()):
        assert n >= 4 and problems == [], problems


def test_focusing_any_list_in_the_wheel_changes_nothing(home):
    vault.create_universe("W").new_entity("character", "Zed Quill")
    story = store.new_story()
    story["universes"] = ["w"]
    async def go():
        from storywheel import tui
        app = tui.StorywheelApp(story, make_engine(home))
        async with app.run_test(size=(220, 55)) as pilot:
            await pilot.pause()
            await pilot.press("k")
            await pilot.pause()
            return await geometry_changes(app, pilot, app.main)
    n, problems = asyncio.run(go())
    assert n >= 5 and problems == [], problems


def test_focusing_any_box_in_settings_changes_nothing(home):
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            out = []
            for tab in ("t-you", "t-writer", "t-stats"):
                app.screen.query_one("#tabs").active = tab
                await pilot.pause()
                out.append(await geometry_changes(app, pilot))
            return out
    for n, problems in asyncio.run(go()):
        assert problems == [], problems


# --- the Builder's layout ------------------------------------------------------------------------------------------------

def world(home):
    u = vault.create_universe("Thornwood", ["western"])
    hero = u.new_entity("character", "Stacie Anderson", {"job": "land clerk", "want": "a quiet claim that nobody else wants"})
    u.new_entity("thing", "The Horn", {"owner": hero.id})
    u.new_story("The Last Clause", {"genre": "western"}, {"Premise": "Stacie finds a clause."})
    return u


def run(script, size=(220, 55), universe="thornwood", **kw):
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe=universe, **kw)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


@pytest.mark.parametrize("size", [(220, 55), (180, 50), (160, 45)])
def test_buttons_and_titles_are_whole_at_desktop_sizes(home, size):
    world(home)
    async def script(app, pilot):
        return flat(screen_text(app))
    text = run(script, size=size)
    for needle in ("+Universe", "+Character", "Roll blanks", "Del", "Universes", "Stories in Thornwood", "Characters (1)", "Outline", "Scenes", "Entity notes",
                   "Outline", "Write", "Export", "+Wheel draft", "Backups…", "Rename"):
        assert needle in text, (size, needle)
    assert "2 entities" in text                                      # the universe's count has a label


def test_the_entity_buttons_have_room_for_their_labels(home):
    world(home)
    async def script(app, pilot):
        out = {}
        for wid in ("e-new", "e-blank", "e-delete", "u-new", "u-rename", "u-delete", "s-open", "s-write", "s-export", "s-draft", "s-backups"):
            b = app.screen_ref.query_one("#" + wid)
            out[wid] = (b.size.width, len(str(b.label)) + 2, b.region.right <= b.parent.region.right)
        return out
    for wid, (width, needed, inside) in run(script).items():
        assert width >= needed and inside, (wid, width, needed)


def test_the_entity_list_column_is_wide_and_the_card_uses_the_space(home):
    world(home)
    async def script(app, pilot):
        s = app.screen_ref
        return s.query_one("#entities").size.width, s.query_one("#card-box").size.width, s.query_one("#left").size.width
    entities, card, left = run(script)
    assert entities >= 30 and left >= 38 and card >= 70      # (the list needs room for its three buttons; the card gets the rest)


def test_links_and_appears_in_sit_at_the_bottom_of_the_entity_card(home):
    u = world(home)
    async def script(app, pilot):
        s = app.screen_ref
        box = s.query_one("#card-box")
        links, appears, card = s.query_one("#links"), s.query_one("#appears"), s.query_one("#card")
        return (links.region.y > card.region.y, appears.region.y > links.region.y, box.region.contains_region(appears.region),
                flat(screen_text(app)))
    below, order, inside, text = run(script)
    assert below and order and inside and "← The Horn (owner)" in text and "The Last Clause" in text


def test_the_notes_tab_is_only_for_notes(home):
    world(home)
    async def script(app, pilot):
        await pilot.press("8")
        await pilot.pause()
        s = app.screen_ref
        return s.query_one("#notes").size.height, flat(screen_text(app))
    height, text = run(script)
    assert height >= 20 and "Free-form notes" in text


def test_a_long_universe_name_is_not_cut_off(home):
    vault.create_universe("The Unbelievably Long-Named Universe Of Dry Country", ["western"]).new_story("Tale")
    async def script(app, pilot):
        return flat(screen_text(app))
    text = run(script, size=(220, 55), universe="the-unbelievably-long-named-universe-of-dry-country")
    assert "Unbelievably" in text


# --- found in the third-pass review ------------------------------------------------------------------------------------------------

def test_write_only_marker_has_a_gap_before_the_value(home):
    world(home)
    async def script(app, pilot):
        return screen_text(app)
    text = run(script)
    assert "✎(" not in text and "✎(blank)" not in text


def test_the_stats_tables_in_settings_show_whole_names(home):
    u = vault.create_universe("Thornwood")
    s = u.new_story("The Last Clause", {}, {})
    s.append_scene("Opening", "Five words are here now.")
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            app.screen.query_one("#tabs").active = "t-stats"
            await pilot.pause()
            return flat(screen_text(app))
    text = asyncio.run(go())
    assert "Thornwood" in text and "The Last Clause" in text


def test_counts_use_proper_plurals(home):
    u = world(home)
    u.stories()[0].append_scene("Opening", "Words here.")
    async def script(app, pilot):
        return flat(screen_text(app))
    assert "scene(s)" not in run(script)
