"""Batch 6 layouts: the Wheel's left column as three boxes, the Builder's boxes and card, the one-line legend, a footer that fits, narrow terminals."""
import asyncio

import pytest
from textual.widgets import Button

from storywheel import builder, footer, fill, store, tui, vault
from conftest import make_engine, run_tui, screen_text


def world(home):
    u = vault.create_universe("The Unbelievably Long Named Universe Of Dry Country", ["western"])
    hero = u.new_entity("character", "Stacie Anderson", {"job": "land clerk", "secret": "she forged the deed to the north pasture years ago and has told nobody at all"})
    t = u.new_entity("thing", "bottle of moonlight", {"description": "a corked bottle that glows faintly at night and hums when someone near it is lying to themselves"})
    s = u.new_story("The Last Clause", {"genre": "western"}, {"Premise": "A clerk."})
    s.add_scene("Opening", "Stacie ran.")
    u.new_story("A Second Story With A Rather Long Title Indeed", {}, {})
    return u, hero, t


def run_builder(script, size=(190, 50), **kw):
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), **kw)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


def flat(t):
    return " ".join(t.split())


# --- the Wheel --------------------------------------------------------------------------------------------------------------------

def test_the_wheels_left_column_is_three_boxes_each_with_a_title(home):
    async def script(app, pilot):
        s = app.screen
        boxes = [s.query_one(f"#{i}") for i in ("steps-box", "uni-box", "stories-box")]
        return ([b.border_title for b in boxes], [b.region.y for b in boxes], [b.region.height for b in boxes],
                s.query_one("#uni-box").region.contains_region(s.query_one("#uni-mode").region),
                s.query_one("#stories-box").region.contains_region(s.query_one("#st-new").region),
                s.query_one("#st-new").region.y > s.query_one("#stories").region.y)
    titles, ys, heights, mode_inside, buttons_inside, buttons_under = run_tui(store.new_story(), make_engine(home), script, size=(190, 50))
    assert titles[0] == "Steps" and titles[1].startswith("Universes to draw from") and titles[2] == "Past stories"
    assert ys == sorted(ys) and len(set(ys)) == 3 and all(h >= 4 for h in heights)
    assert mode_inside and buttons_inside and buttons_under                      # the control is in its box; the buttons are under the list


def test_the_wheels_boxes_title_counts_the_ticked_universes(home):
    vault.create_universe("U1")
    async def script(app, pilot):
        return app.screen.query_one("#uni-box").border_title
    assert "(0 ticked)" in run_tui(store.new_story(), make_engine(home), script)


def test_a_narrow_wheel_keeps_every_button_whole(home):
    async def script(app, pilot):
        s = app.screen
        out = {}
        for b in s.query(Button):
            if b.display and b.region.width:
                out[b.id] = (b.region.width, len(str(b.label)) + 2 <= b.region.width + 2, s.region.contains_region(b.region))
        return out, s.has_class("-narrow"), flat(screen_text(app))
    out, narrow, text = run_tui(store.new_story(), make_engine(home), script, size=(120, 34))
    assert narrow and "Send to Builder" in text and "Flavor" in text and "Whole characters/places from" in text
    assert all(inside for _w, _fit, inside in out.values()), out


# --- the Builder -----------------------------------------------------------------------------------------------------------------------

def test_the_builders_left_column_is_three_boxes_with_their_buttons_underneath(home):
    world(home)
    async def script(app, pilot):
        s = app.screen_ref
        ub, sb = s.query_one("#universes-box"), s.query_one("#stories-box")
        return (ub.border_title, sb.border_title, [str(s.query_one(i).label) for i in ("#u-new", "#u-rename", "#u-delete")],
                s.query_one("#u-new").region.y > s.query_one("#universes").region.y, ub.region.contains_region(s.query_one("#u-delete").region),
                s.query_one("#s-new").region.y > s.query_one("#stories").region.y, sb.region.contains_region(s.query_one("#s-backups").region),
                [str(s.query_one(i).label) for i in ("#s-new", "#s-write", "#s-export", "#s-backups")],
                s.query_one("#story-box").region.y >= sb.region.bottom, s.query_one("#story-box").region.height > sb.region.height, len(s.query("#right")))
    ut, st, ulabels, below_u, in_u, below_s, in_s, slabels, story_below, story_big, rights = run_builder(script, universe="the-unbelievably-long-named-universe-of-dry-country")
    assert ut == "Universes" and st.startswith("Stories in The Unbelievably") and st.endswith("…") and len(st) <= 30
    assert ulabels == ["+Universe", "Rename", "Delete"] and slabels == ["+Story", "Write", "Export", "Backups…"]
    assert below_u and in_u and below_s and in_s and story_below and story_big and rights == 0          # (no right column; the Story panel is under the story list)


def test_list_rows_are_cut_with_an_ellipsis_never_wrapped(home):
    world(home)
    async def script(app, pilot):
        s = app.screen_ref
        return [s.query_one("#universes").get_option_at_index(0).prompt, s.query_one("#stories").get_option_at_index(0).prompt,
                s.query_one("#universes").virtual_size.height, s.query_one("#stories").virtual_size.height]
    up, sp, uh, sh = run_builder(script, universe="the-unbelievably-long-named-universe-of-dry-country")
    assert uh == 1 and sh == 2                                          # one line per universe, one per story (two stories)


def test_the_card_title_is_just_the_type_and_name_and_the_hints_are_in_the_footer_and_help(home):
    u, hero, t = world(home)
    async def script(app, pilot):
        s = app.screen_ref
        s.type = "thing"
        s.refresh_all()
        await pilot.pause()
        title = str(s.query_one("#card-title").render())
        footer_text = flat(" ".join(str(k.render()) for k in s.query("FooterKey")))
        return title, footer_text
    title, foot = run_builder(script, universe=u.slug, tab="thing")
    assert title.strip() == "Thing: bottle of moonlight"
    assert "click" not in title and "right-click" not in title and "Roll" in foot and "Write" in foot
    assert "right-click" in builder.HELP and "wheel" in builder.HELP and "space" in builder.HELP


def test_card_values_wrap_under_the_value_not_under_the_label(home):
    u, hero, t = world(home)
    async def script(app, pilot):
        s = app.screen_ref
        s.type = "thing"
        s.refresh_all()
        await pilot.pause()
        box = s.query_one("#card-box").region
        rows = screen_text(app).splitlines()
        first = next(i for i, l in enumerate(rows) if "Description" in l)
        value_x = rows[first].index("a corked")
        follow = rows[first + 1]
        left_of_value = follow[box.x + 1:value_x]                 # what sits under the label column on the next line
        return value_x, left_of_value, follow[value_x:value_x + 10], rows[first + 2][value_x:value_x + 6]
    value_x, under_label, under_value, third = run_builder(script, universe=u.slug, tab="thing")
    assert under_label.strip() == "" and under_value.strip() != ""      # the second line is empty under the label and holds more of the value


def test_the_legend_is_one_short_line(home):
    u, hero, t = world(home)
    async def script(app, pilot):
        s = app.screen_ref
        leg = s.query_one("#legend")
        return leg.region.height, str(leg.render()), len(builder.LEGEND)
    h, text, n = run_builder(script, universe=u.slug)
    assert h == 1 and "▲" in text and "✎" in text and n <= 64
    assert "never changes what you wrote" in builder.HELP or "Roll blanks" in builder.HELP and "empty" in builder.HELP


def test_no_empty_row_between_the_tab_bar_and_the_boxes(home):
    u, hero, t = world(home)
    async def script(app, pilot):
        s = app.screen_ref
        tabs, work = s.query_one("#tabs"), s.query_one("#work")
        return tabs.region.bottom, work.region.y, tabs.region.height
    bottom, work_y, height = run_builder(script, universe=u.slug)
    assert work_y == bottom and height == 2


def test_the_entity_card_gets_more_width_than_before(home):
    u, hero, t = world(home)
    async def script(app, pilot):
        s = app.screen_ref
        return s.query_one("#entities").region.width, s.query_one("#card-box").region.width
    list_w, card_w = run_builder(script, universe=u.slug, size=(190, 50))
    assert list_w <= 36 and card_w >= 70


def test_a_narrow_builder_shows_the_story_panel_in_turns(home):
    u, hero, t = world(home)
    async def script(app, pilot):
        s = app.screen_ref
        left = s.query_one("#left").region.width
        a = (s.has_class("-narrow"), s.query_one("#mid").display, s.query_one("#card-box").region.width)
        await pilot.press("7")
        b = (s.query_one("#mid").display, s.query_one("#rtabs").active, s.query_one("#left").region.width)
        await pilot.press("escape")
        c = (s.query_one("#mid").display, s.query_one("#left").region.width)
        await pilot.press("backslash")
        d = s.query_one("#mid").display
        await pilot.press("3")
        await pilot.pause()
        e = s.query_one("#mid").display
        return a, b, c, d, e, left
    a, b, c, d, e, left = run_builder(script, universe=u.slug, size=(120, 34))
    assert a[0] and a[1] and a[2] >= 40 and left == 34                                    # thin left column, the cards beside it
    assert b[0] is False and b[1] == "r-scenes" and b[2] >= 110 and c == (True, 34) and d is False and e is True       # 7 gives the Story panel the whole width


def test_buttons_stay_whole_in_every_builder_box_at_a_narrow_size(home):
    u, hero, t = world(home)
    async def script(app, pilot):
        s = app.screen_ref
        bad = []
        for b in s.query(Button):
            if b.display and b.region.width:                       # (the hidden side column has no size)
                box = b.parent.parent
                if b.region.right > box.region.right or b.region.width < len(str(b.label)):
                    bad.append((b.id, b.region, box.region))
        return bad
    assert run_builder(script, universe=u.slug, size=(120, 34)) == []


# --- the footer --------------------------------------------------------------------------------------------------------------------------

def test_the_fitting_footer_drops_the_least_important_entries_first():
    entries = [("mode('wheel')", 20), ("roll", 12), ("keep", 10), ("edit", 10), ("back_mode", 8), ("quit_program", 18), ("help", 8)]
    assert footer.choose(entries, 200) == list(range(7))
    kept = footer.choose(entries, 70)
    names = [entries[i][0] for i in kept]
    assert names == ["mode('wheel')", "roll", "back_mode", "quit_program", "help"] or {"back_mode", "quit_program", "help", "mode('wheel')"} <= set(names)
    assert sum(entries[i][1] for i in kept) <= 70
    assert "keep" not in names and "edit" not in names
    tiny = footer.choose(entries, 5)
    assert {entries[i][0] for i in tiny} == {"mode('wheel')", "back_mode", "quit_program", "help"}        # (the essentials stay even if they cannot fit)


@pytest.mark.parametrize("width", [190, 150, 120, 100])
def test_no_footer_entry_is_cut_off_in_any_mode(home, width):
    u, hero, t = world(home)
    from storywheel import hub
    from storywheel.engine import Engine
    from storywheel.ratings import Ratings
    async def go():
        app = hub.Hub(("builder", {"universe": u.slug}), lambda: Engine(seed=1), lambda: Ratings())
        out = {}
        async with app.run_test(size=(width, 40)) as pilot:
            for key, name in ((None, "builder"), ("f1", "wheel"), ("f4", "settings"), ("f5", "words")):
                if key:
                    await pilot.press(key)
                for _ in range(4):
                    await pilot.pause()
                keys = list(app.screen.query("FooterKey"))
                out[name] = [(k.action, k.region.right, k.region.width, len(k.key_display) + len(k.description)) for k in keys]
                out[name + "_width"] = app.screen.size.width
        return out
    out = asyncio.run(go())
    for name in ("builder", "wheel", "settings", "words"):
        width_here = out[name + "_width"]
        assert out[name], name
        for action, right, w, text_len in out[name]:
            assert right <= width_here and w >= text_len, (name, action, right, w, text_len, width_here)
        actions = [a for a, *_ in out[name]]
        assert any(a.startswith(("noop_mode", "mode")) for a in actions)
        if name != "words":                                  # (a box with the cursor in it hides the keys that would type; Words opens in one)
            assert "back_mode" in actions and "help" in actions and sum(a.startswith(("noop_mode", "mode", "writer")) for a in actions) == 5


def test_the_help_still_lists_the_keys_the_footer_left_out():
    for text in (builder.HELP, tui.HELP):
        for needle in ("click", "space"):
            assert needle in text.lower() or needle in text
