"""The mouse on the card, the buttons, and the universe panel."""
import json

from textual import events
from textual.widgets import Input, Tree

from storywheel import store
from storywheel import tui
from conftest import make_engine, run_tui, screen_text


def new_story():
    return store.new_story()


async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


async def go_to(app, pilot, step_key):
    while app.session.step.key != step_key:
        await press(pilot, "k")


async def click(pilot, offset, button=1, widget="#card"):
    await pilot.click(widget, offset=offset, button=button)
    await pilot.pause()


async def wheel(pilot, event, offset):
    await pilot._post_mouse_events([event], "#card", offset=offset)
    await pilot.pause()


def rate_x(app, field, which):
    """Where the ▲ (+1) or ▼ (-1) of a field's line is, as a card offset: they sit in a column at the right edge of the card."""
    return arrow_at(app, field, which)[0]


def arrow_at(app, field, which):
    """(x, y) of an arrow as a card offset, found on the screen (long values wrap, so a field's line is not its index)."""
    card = app.screen.query_one("#card")
    strips = app.screen._compositor.render_strips()                   # (column-true, unlike the flattened text)
    lines = ["".join(seg.text for seg in strip) for strip in strips][card.region.y:card.region.y + card.region.height]
    label = None if field is None else field.replace("_", " ")
    for y, line in enumerate(lines):
        inside = line[card.region.x:card.region.x + card.region.width]
        if (label is None or inside.strip().startswith(label)) and "▲" in inside:
            return inside.index("▲" if which > 0 else "▼"), y
    raise AssertionError(f"no arrows for {field}")


def row_of(app, field):
    return app.session.field_names.index(field)


# --- click, right-click, Enter, space ---------------------------------------------------------------------

def test_clicking_a_field_rerolls_only_that_field(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "protagonist")
        before, n = dict(s.fields), len(s.hist)
        await click(pilot, (6, row_of(app, "job")))
        return before, dict(s.fields), len(s.hist) - n
    before, after, added = run_tui(new_story(), make_engine(home), script)
    assert added == 1 and after["job"] != before["job"]
    assert after["name"] == before["name"] and after["age"] == before["age"] and after["trait"] == before["trait"]


def test_a_click_does_not_roll_the_whole_step(home):
    """The bug this replaces: every click used to fire 'select', which rolled everything."""
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "setting")
        before = dict(s.fields)
        for field in ("era", "landmark", "season"):
            await click(pilot, (6, row_of(app, field)))
        return before, dict(s.fields)
    before, after = run_tui(new_story(), make_engine(home), script)
    assert after["place"] == before["place"]


def test_right_click_edits_that_field_in_place(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "setting")
        n, current = len(s.hist), s.fields["era"]
        await click(pilot, (6, row_of(app, "era")), button=3)
        box = app.screen.query_one(Input)
        assert isinstance(app.screen, tui.EditScreen) and box.value == current
        assert len(list(app.screen.query(Input))) == 1
        assert len(s.hist) == n                                     # nothing rolled
        box.value = "an age of glass"
        await press(pilot, "enter")
        return s.fields["era"], s.cand["_src"], len(s.hist) - n
    assert run_tui(new_story(), make_engine(home), script) == ("an age of glass", "edited", 1)


def test_enter_on_a_highlighted_field_rerolls_that_field_like_a_click(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "protagonist")
        before = dict(s.fields)
        await press(pilot, "down", "down", "enter")
        return before, dict(s.fields), app.main.card_field()
    before, after, field = run_tui(new_story(), make_engine(home), script)
    assert field == "job" and after["job"] != before["job"] and after["name"] == before["name"]


def test_space_still_rolls_the_whole_step(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "protagonist")
        before = dict(s.fields)
        await press(pilot, "down", "down", "space")
        return before, dict(s.fields)
    before, after = run_tui(new_story(), make_engine(home), script)
    assert after["name"] != before["name"] and after["job"] != before["job"]


def test_click_vs_right_click_vs_enter_each_do_one_thing(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "setting")
        n = len(s.hist)
        await click(pilot, (6, 1))                                      # left: one reroll
        left = (len(s.hist) - n, type(app.screen).__name__)
        await click(pilot, (6, 1), button=3)                            # right: a dialog, no roll
        right = (len(s.hist) - n, type(app.screen).__name__)
        await press(pilot, "escape")
        await press(pilot, "enter")                                     # enter: a reroll again
        enter = (len(s.hist) - n, type(app.screen).__name__)
        return left, right, enter
    assert run_tui(new_story(), make_engine(home), script) == ((1, "MainScreen"), (1, "EditScreen"), (2, "MainScreen"))


def test_clicking_a_one_field_step_rolls_it(home):
    async def script(app, pilot):
        await go_to(app, pilot, "premise")
        n = len(app.session.hist)
        await click(pilot, (6, 0))
        return len(app.session.hist) - n
    assert run_tui(new_story(), make_engine(home), script) == 1


# --- the wheel ---------------------------------------------------------------------------------------------

def test_the_wheel_steps_through_a_fields_earlier_values_and_back(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "protagonist")
        row = row_of(app, "job")
        await click(pilot, (6, row))
        await click(pilot, (6, row))
        values = s.field_values("job")
        rest = {k: v for k, v in s.fields.items() if k not in ("job",)}
        n = len(s.hist)
        await wheel(pilot, events.MouseScrollUp, (6, row))
        first = s.fields["job"]
        await wheel(pilot, events.MouseScrollUp, (6, row))
        second = s.fields["job"]
        added = len(s.hist) - n
        await wheel(pilot, events.MouseScrollDown, (6, row))
        back = s.fields["job"]
        return values, first, second, back, added, {k: v for k, v in s.fields.items() if k != "job"} == rest
    values, first, second, back, added, rest_same = run_tui(new_story(), make_engine(home), script)
    assert len(values) == 3
    assert (first, second, back) == (values[1], values[0], values[1])
    assert added == 1                               # browsing is one candidate, not one per notch
    assert rest_same


def test_the_wheel_stops_at_the_oldest_value(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "protagonist")
        row = row_of(app, "job")
        for _ in range(3):
            await wheel(pilot, events.MouseScrollUp, (6, row))
        return s.fields["job"] == s.field_values("job")[0], screen_text(app)
    same, text = run_tui(new_story(), make_engine(home), script)
    assert same and "oldest value" in text


# --- the little arrows ------------------------------------------------------------------------------------------

def test_clicking_the_arrows_rates_that_line(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "setting")
        n = len(s.hist)
        await click(pilot, arrow_at(app, "rumor", 1))
        up = s.rating("rumor")
        await click(pilot, arrow_at(app, "rumor", -1))
        down = s.rating("rumor")
        await click(pilot, arrow_at(app, "rumor", -1))
        cleared = s.rating("rumor")
        return up, down, cleared, len(s.hist) - n, s.rating("place"), s.fields["rumor"]
    up, down, cleared, rolled, other, rumor = run_tui(new_story(), make_engine(home), script)
    assert (up, down, cleared, rolled, other) == (1, -1, 0, 0, 0)          # rating never rerolls
    saved = json.loads((home / "home" / "ratings.json").read_text())["ratings"]
    assert [r["rating"] for r in saved] == [1, -1, 0] and saved[0]["text"] == rumor and saved[0]["field"] == "rumor"


def test_the_arrows_work_on_a_one_field_step(home):
    async def script(app, pilot):
        await go_to(app, pilot, "premise")
        app.session.edit_field("premise", "A short one.")             # (a long premise would wrap)
        app.main.after()
        await pilot.pause()
        await click(pilot, arrow_at(app, None, -1))
        return app.session.rating(), len(app.session.hist)
    assert run_tui(new_story(), make_engine(home), script) == (-1, 2)


# --- buttons ----------------------------------------------------------------------------------------------------------

def test_the_buttons_do_what_their_keys_do(home):
    async def script(app, pilot):
        s = app.session
        out = []
        await pilot.click("#btn-roll"); await pilot.pause()
        out.append(len(s.hist))                                 # 2
        await pilot.click("#btn-keep"); await pilot.pause()
        out.append(s.step.key)                                  # structure
        await pilot.click("#btn-skip"); await pilot.pause()
        out.append((s.step.key, s.marker(1)))                   # title, skipped
        await pilot.click("#btn-back"); await pilot.pause()
        out.append(s.step.key)                                  # structure
        await pilot.click("#btn-mix"); await pilot.pause()
        out.append(type(app.screen).__name__)
        return out
    assert run_tui(new_story(), make_engine(home), script) == [2, "structure", ("title", "skipped"), "structure", "MixScreen"]


def test_the_button_row_is_on_screen_and_does_not_take_the_keyboard(home):
    async def script(app, pilot):
        await pilot.click("#btn-roll"); await pilot.pause()
        focused_after_click = app.focused.id
        await press(pilot, "tab")
        return screen_text(app), focused_after_click, app.focused.id
    text, after_click, after_tab = run_tui(new_story(), make_engine(home), script)
    for name in ("Roll", "Keep", "Back", "Skip", "Flavor"):
        assert name in text
    assert after_click == "card" and after_tab not in (None, "btn-keep")


# --- sidebar and history --------------------------------------------------------------------------------------------

def test_clicking_a_step_jumps_there(home):
    async def script(app, pilot):
        await pilot.click("#steps", offset=(4, 3)); await pilot.pause()
        return app.session.step.key, app.focused.id
    assert run_tui(new_story(), make_engine(home), script) == ("protagonist", "card")


def test_clicking_a_history_row_picks_it(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "setting")
        await press(pilot, "space", "space")
        first = s.hist[0]
        await pilot.click("#history", offset=(6, 0)); await pilot.pause()
        return s.cur, s.fields == {k: v for k, v in first.items() if not k.startswith("_")}
    assert run_tui(new_story(), make_engine(home), script) == (0, True)


def test_the_help_screen_explains_the_mouse_and_shift_drag(home):
    async def script(app, pilot):
        await press(pilot, "question_mark")
        guide = str(app.screen.query_one("#help-text").content)
        await press(pilot, "2")                                 # (Keys and Mouse are on the Keys tab)
        return " ".join((guide + str(app.screen.query_one("#help-text").content)).split())
    text = run_tui(new_story(), make_engine(home), script, size=(200, 120))
    assert "Shift" in text and "drag" in text and "Right-click" in text and "Scroll" in text and "universe panel" in text
