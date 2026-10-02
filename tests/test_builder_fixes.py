"""First-use fixes in the Builder: a steady entity list, a top box that only edits on right-click or e, proper names."""
import asyncio

from textual import events
from textual.widgets import Input

from storywheel import builder, fill, vault
from storywheel.engine import Engine
from storywheel.steps import Ctx, fill as fill_text
from conftest import screen_text


def flat(text):
    return " ".join(text.split())


def start(home, setup=None, story=None):
    u = vault.create_universe("W", ["western"])
    for i in range(40):
        u.new_entity("character", f"Person {i:02d}", {"job": "x" * (i % 7) + " job", "want": "w" * (i * 3)})
    if setup:
        setup(u)
    return u


def run(script, universe="w", story=None, size=(220, 55)):
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe=universe, story=story)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


def geometry(app):
    s = app.screen_ref
    return {w: (s.query_one(w).region, s.query_one(w).virtual_size) for w in ("#entities", "#entity-list", "#card-box", "#card")}


def test_clicking_an_entity_does_not_move_or_resize_the_list(home):
    start(home)
    async def script(app, pilot):
        s = app.screen_ref
        s.elist.scroll_to(y=5, animate=False)
        await pilot.pause()
        before, scroll = geometry(app), s.elist.scroll_y
        seen = []
        for y in (2, 6, 11, 19):
            await pilot.click("#entity-list", offset=(5, y))
            await pilot.pause()
            seen.append((s.entity.name, s.elist.scroll_y, geometry(app) == before))
        return scroll, seen
    scroll, seen = run(script)
    assert scroll == 5
    assert all(sy == 5 and same for _n, sy, same in seen), seen
    assert len({n for n, *_ in seen}) == 4                              # and each click did select a different person


def test_rolling_a_field_does_not_rebuild_or_move_the_list(home):
    start(home)
    async def script(app, pilot):
        s = app.screen_ref
        calls = []
        orig = s._build_entities
        s._build_entities = lambda: (calls.append(1), orig())[1]
        s.elist.scroll_to(y=5, animate=False)
        await pilot.pause()
        s.elist.highlighted = 12
        await pilot.pause()
        before, scroll = geometry(app), s.elist.scroll_y
        rows = [r[0] for r in s.rows()]
        for key in ("job", "trait", "want"):
            await pilot.click("#card", offset=(8, rows.index(key)))
            await pilot.pause()
        return len(calls), scroll, s.elist.scroll_y, geometry(app) == before
    calls, before, after, same = run(script)
    assert calls == 0 and before == after and same


def test_cards_of_very_different_length_leave_the_list_alone(home):
    start(home)
    async def script(app, pilot):
        s = app.screen_ref
        regions = set()
        for i in (1, 39, 2, 38):
            s.elist.highlighted = i
            await pilot.pause()
            regions.add((s.query_one("#entity-list").region, s.query_one("#entities").region))
        return len(regions)
    assert run(script) == 1


def test_a_new_name_keeps_the_list_where_it_was_if_the_row_is_still_in_view(home):
    start(home)
    async def script(app, pilot):
        s = app.screen_ref
        s.elist.scroll_to(y=5, animate=False)
        await pilot.pause()
        await pilot.click("#entity-list", offset=(5, 8))
        await pilot.pause()
        name_before = s.entity.name
        await pilot.press("f")                                    # f on the first row: the name
        await pilot.pause()
        await pilot.press("enter") if type(app.screen).__name__ == "RenamePreviewScreen" else None
        await pilot.pause()
        return s.entity.name != name_before, s.elist.scroll_y
    changed, scroll = run(script)
    assert changed is True and scroll in range(0, 12)


# --- the top box ----------------------------------------------------------------------------------------------

def with_story(u):
    sections = {f"Section {i}": f"Text of section {i}." for i in range(14)}
    u.new_story("Tale", {"genre": "western"}, sections)


def test_a_left_click_in_the_top_box_only_selects(home):
    start(home, with_story)
    async def script(app, pilot):
        s = app.screen_ref
        await pilot.click("#top", offset=(8, 2))
        await pilot.pause()
        return type(app.screen).__name__, s.top.highlighted
    assert run(script, story="tale")[0] == "BuilderScreen" and True
    name, highlighted = run(script, story="tale")
    assert name == "BuilderScreen" and highlighted == 2


def test_right_click_or_e_edits_the_selected_row_and_enter_does_not(home):
    start(home, with_story)
    async def script(app, pilot):
        s = app.screen_ref
        await pilot.click("#top", offset=(8, 4))
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        after_enter = type(app.screen).__name__
        await pilot.press("e")
        await pilot.pause()
        via_e = type(app.screen).__name__, app.screen.query_one(Input).value
        await pilot.press("escape")
        await pilot.pause()
        await pilot.click("#top", offset=(8, 5), button=3)
        await pilot.pause()
        via_right = type(app.screen).__name__
        await pilot.press("escape")
        await pilot.pause()
        return after_enter, via_e, via_right
    after_enter, via_e, via_right = run(script, story="tale")
    assert after_enter == "BuilderScreen" and via_e[0] == "EditScreen" and via_right == "EditScreen"
    assert via_e[1].startswith("Text of section")


def test_the_top_box_scrolls_with_the_wheel_instead_of_stepping_a_history(home):
    start(home, with_story)
    async def script(app, pilot):
        s = app.screen_ref
        await pilot._post_mouse_events([events.MouseScrollDown], "#top", offset=(8, 3))
        await pilot._post_mouse_events([events.MouseScrollDown], "#top", offset=(8, 3))
        await pilot._post_mouse_events([events.MouseScrollDown], "#top", offset=(8, 3))
        await pilot.pause()
        return s.top.scroll_y, type(app.screen).__name__
    scroll, screen = run(script, story="tale")
    assert scroll > 0 and screen == "BuilderScreen"


def test_the_top_box_edit_is_saved(home):
    start(home, with_story)
    async def script(app, pilot):
        await pilot.click("#top", offset=(8, 4), button=3)
        await pilot.pause()
        app.screen.query_one(Input).value = "Changed text."
        await pilot.press("enter")
        await pilot.pause()
    run(script, story="tale")
    s = vault.get_universe("w").story("tale")
    assert "Changed text." in s.sections().values()


# --- proper names -------------------------------------------------------------------------------------------------------

def test_a_universe_character_reads_as_a_name_not_with_the(home):
    u = vault.create_universe("W", ["western"])
    u.new_entity("character", "Sheriff Lund")
    u.new_entity("place", "Red Draw")
    u.new_entity("character", "The Widow")                           # a name that already has its article: untouched
    e = Engine(seed=1)
    e.set_universes([u])
    c = Ctx(e, {"kept": {}, "seeds": {}, "atoms": {}, "threads": {}, "mix": {"base": [], "exclude_tags": [], "exclude_lists": [], "boost": {}}})
    assert fill_text(c, "She faced the Sheriff Lund at dawn.") == "She faced Sheriff Lund at dawn."
    assert fill_text(c, "The Sheriff Lund's horse bolted.") == "Sheriff Lund's horse bolted."
    assert fill_text(c, "A Red Draw winter, and the sheriff stayed.") == "Red Draw winter, and the sheriff stayed."
    assert fill_text(c, "the Widow came") == "the Widow came"
    assert fill_text(c, "the sheriffs of Lund") == "the sheriffs of Lund"


def test_the_rival_slot_with_a_universe_character_never_says_the_before_the_name(home):
    from storywheel.sample import build_story
    u = vault.create_universe("W", ["western"])
    u.new_entity("character", "Sheriff Lund")
    u.save_settings(atom_boost=20.0)
    e = Engine(seed=3)
    e.set_universes([vault.get_universe("w")])
    stories = [build_story(e, ["western"]) for _ in range(40)]
    texts = " ".join(" ".join(s["kept"]["spine"].values()) + s["kept"]["premise"]["premise"] + s["kept"]["protagonist"]["rival"]
                     for s in stories)
    assert "Sheriff Lund" in texts
    assert "the Sheriff Lund" not in texts and "The Sheriff Lund" not in texts and "a Sheriff Lund" not in texts


def test_without_universes_nothing_changes(home):
    e = Engine(seed=1)
    c = Ctx(e, {"kept": {}, "seeds": {}, "atoms": {}, "threads": {}, "mix": {"base": [], "exclude_tags": [], "exclude_lists": [], "boost": {}}})
    assert fill_text(c, "She faced the Sheriff at dawn.") == "She faced the Sheriff at dawn."


def test_the_sample_render_shows_names_and_common_rivals_correctly():
    from storywheel import sample
    assert sample._with_article("sheriff") == "the sheriff" and sample._with_article("Sheriff Lund") == "Sheriff Lund"


def test_on_a_short_screen_the_top_box_leaves_room_for_the_list_and_nothing_scrolls_the_column(home):
    start(home)
    async def script(app, pilot):
        s = app.screen_ref
        mid = s.query_one("#mid")
        rows = s.query_one("#entity-list").size.height
        await pilot.click("#entity-list", offset=(5, 1))
        await pilot.pause()
        return rows, mid.scroll_y, s.query_one("#top-box").size.height
    rows, scroll, top = run(script, size=(200, 30))
    assert rows >= 7 and scroll == 0 and top <= 9
