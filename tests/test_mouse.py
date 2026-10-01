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
    """Where the ▲ (+1) or ▼ (-1) of a field's line is, as a card offset."""
    fields = app.session.fields
    if app.session.step.single:
        n = len(next(iter(fields.values())))
    else:
        width = max(len(k) for k in fields)
        n = len(f"{field.ljust(width)}  {fields[field]}")
    return n + (3 if which > 0 else 6)


def row_of(app, field):
    return app.session.field_names.index(field)


SAVE_THE_UNIVERSE = {"protagonist": {"name": "Wade Hollis", "age": "34", "job": "drover"},
                     "setting": {"place": "Dry Fork", "era": "the year of the strike", "season": "autumn",
                                 "landmark": "the mesa", "rumor": "Dry Fork was cursed"}}


def with_universe():
    for key, fields in SAVE_THE_UNIVERSE.items():
        store.add_to_universe(key, fields)


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
        row = row_of(app, "rumor")
        n = len(s.hist)
        await click(pilot, (rate_x(app, "rumor", 1), row))
        up = s.rating("rumor")
        await click(pilot, (rate_x(app, "rumor", -1), row))
        down = s.rating("rumor")
        await click(pilot, (rate_x(app, "rumor", -1), row))
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
        await click(pilot, (rate_x(app, None, -1), 0))
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
    for name in ("Roll", "Keep", "Back", "Skip", "Mix"):
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
        return " ".join(screen_text(app).split())
    text = run_tui(new_story(), make_engine(home), script, size=(120, 60))
    assert "Shift" in text and "drag" in text and "right-click" in text and "scroll" in text and "Universe panel" in text


# --- the universe panel ---------------------------------------------------------------------------------------------

def start_with_universe(app, pilot):
    """The prompt about the universe comes first; answer no."""
    return pilot.press("n")


def test_the_panel_groups_entries_by_kind_and_opens_a_group_with_enter(home):
    with_universe()
    async def script(app, pilot):
        await start_with_universe(app, pilot)
        await pilot.pause()
        closed = screen_text(app)
        await press(pilot, "v")
        assert app.focused.id == "universe"
        await press(pilot, "enter")                                # opens "Protagonist"
        opened = screen_text(app)
        await press(pilot, "enter" if False else "escape")
        return closed, opened, app.focused.id
    closed, opened, focus = run_tui(new_story(), make_engine(home), script)
    assert "Universe (2)" in closed and "Protagonist (1)" in closed and "Setting (1)" in closed
    assert "Wade Hollis" not in closed and "Wade Hollis" in opened and focus == "card"


def test_the_panel_shows_and_switches_the_mode_for_this_story(home):
    with_universe()
    async def script(app, pilot):
        await start_with_universe(app, pilot)
        await pilot.pause()
        s = app.session
        seen = [(s.universe_mode, "Use: no" in screen_text(app))]
        for _ in range(3):
            await pilot.click("#uni-mode"); await pilot.pause(0.4)      # (a button ignores a second click mid-press)
            seen.append((s.universe_mode, f"Use: {app.main.MODE_WORDS[s.universe_mode]}" in screen_text(app)))
        await press(pilot, "v", "t")
        seen.append(s.universe_mode)
        return seen
    assert run_tui(new_story(), make_engine(home), script) == [("n", True), ("m", True), ("o", True), ("n", True), "m"]


def test_the_chosen_mode_is_saved_with_the_story(home):
    with_universe()
    story = new_story()
    async def script(app, pilot):
        await pilot.press("m")                                      # the opening question: mix it in
        await pilot.pause()
        await press(pilot, "k")
    run_tui(story, make_engine(home), script)
    assert store.load(story["id"])["universe_mode"] == "m"


def test_click_an_entry_to_preview_it(home):
    with_universe()
    async def script(app, pilot):
        await start_with_universe(app, pilot)
        await pilot.pause()
        await pilot.click("#universe", offset=(5, 0)); await pilot.pause()     # the group opens
        await pilot.click("#universe", offset=(8, 1)); await pilot.pause()     # the entry previews
        return type(app.screen).__name__, " ".join(screen_text(app).split())
    name, text = run_tui(new_story(), make_engine(home), script)
    assert name == "UniverseEntryScreen"
    assert "Wade Hollis" in text and "drover" in text and "Use in this story" in text and "Delete" in text and "Edit" in text


def test_use_in_this_story_adds_a_candidate_and_leaves_kept_steps_alone(home):
    with_universe()
    async def script(app, pilot):
        await start_with_universe(app, pilot)
        await pilot.pause()
        s = app.session
        await press(pilot, "k", "k", "k")                           # genre, structure, title kept
        kept_before = json.dumps(s.story["kept"], sort_keys=True)
        assert s.step.key == "protagonist"
        await press(pilot, "x")                                     # skipping protagonist leaves it unkept...
        await press(pilot, "v", "down", "enter", "down", "enter")   # open "Setting", then the entry
        assert isinstance(app.screen, tui.UniverseEntryScreen)
        await press(pilot, "enter")                                 # use
        kept_after = json.dumps(s.story["kept"], sort_keys=True)
        return (s.step.key, s.fields["place"], s.cand["_src"], len(s.hist), kept_before == kept_after,
                "setting" in s.story["kept"], app.focused.id)
    step, place, src, n, same, kept_setting, focus = run_tui(new_story(), make_engine(home), script)
    assert (step, place, src) == ("setting", "Dry Fork", "universe")
    assert n == 2 and same and not kept_setting and focus == "card"


def test_use_jumps_back_to_a_step_that_is_already_kept_and_does_not_change_it(home):
    with_universe()
    async def script(app, pilot):
        await start_with_universe(app, pilot)
        await pilot.pause()
        s = app.session
        await go_to(app, pilot, "premise")                          # protagonist and setting are kept
        old = dict(s.story["kept"]["setting"])
        await press(pilot, "v", "down", "enter", "down", "enter", "enter")
        return (s.step.key, s.cand["_src"], s.story["kept"]["setting"] == old, s.fields["place"],
                s.marker(4), len(s.hist))
    step, src, unchanged, place, marker, n = run_tui(new_story(), make_engine(home), script)
    assert step == "setting" and src == "universe" and unchanged and place == "Dry Fork"
    assert n == 2                                                   # the kept roll, and the universe one


def test_a_used_entry_only_becomes_kept_when_you_press_k(home):
    with_universe()
    async def script(app, pilot):
        await start_with_universe(app, pilot)
        await pilot.pause()
        await press(pilot, "v", "down", "enter", "down", "enter", "enter")
        s = app.session
        before = "setting" in s.story["kept"]
        await press(pilot, "k")
        return before, s.story["kept"]["setting"]["place"]
    assert run_tui(new_story(), make_engine(home), script) == (False, "Dry Fork")


def test_edit_an_entry_in_the_preview(home):
    with_universe()
    async def script(app, pilot):
        await start_with_universe(app, pilot)
        await pilot.pause()
        await press(pilot, "v", "enter", "down", "enter", "e")
        boxes = list(app.screen.query(Input))
        assert [b.value for b in boxes] == ["Wade Hollis", "34", "drover"]
        boxes[0].value = "Wade Hollis Jr."
        for _ in boxes:
            await press(pilot, "enter")
        return store.load_universe()["protagonist"], type(app.screen).__name__
    entries, screen = run_tui(new_story(), make_engine(home), script)
    assert entries == [{"name": "Wade Hollis Jr.", "age": "34", "job": "drover"}] and screen == "MainScreen"


def test_delete_asks_first_and_n_keeps_the_entry(home):
    with_universe()
    async def script(app, pilot):
        await start_with_universe(app, pilot)
        await pilot.pause()
        await press(pilot, "v", "enter", "down", "d")               # d on the highlighted entry
        asked = type(app.screen).__name__, " ".join(screen_text(app).split())
        await press(pilot, "n")
        kept = len(store.load_universe()["protagonist"])
        await press(pilot, "d")
        await press(pilot, "y")
        return asked, kept, store.load_universe()["protagonist"], type(app.screen).__name__
    asked, kept, left, screen = run_tui(new_story(), make_engine(home), script)
    assert asked[0] == "ConfirmScreen" and "Delete this from your universe" in asked[1] and "Wade Hollis" in asked[1]
    assert kept == 1 and left == [] and screen == "MainScreen"


def test_delete_from_the_preview_also_confirms(home):
    with_universe()
    async def script(app, pilot):
        await start_with_universe(app, pilot)
        await pilot.pause()
        await press(pilot, "v", "enter", "down", "enter", "d")
        confirm = type(app.screen).__name__
        await pilot.click("#yes"); await pilot.pause()
        return confirm, store.load_universe().get("protagonist")
    assert run_tui(new_story(), make_engine(home), script) == ("ConfirmScreen", [])


def test_add_a_new_entry_from_scratch_using_the_steps_fields(home):
    with_universe()
    async def script(app, pilot):
        await start_with_universe(app, pilot)
        await pilot.pause()
        await press(pilot, "v", "n")                                # the highlighted group is Protagonist
        boxes = list(app.screen.query(Input))
        names = [b.id for b in boxes]
        assert all(b.value == "" for b in boxes)
        boxes[0].value = "Ada Quill"
        boxes[2].value = "lamplighter"
        for _ in boxes:
            await press(pilot, "enter")
        return names, store.load_universe()["protagonist"][-1], screen_text(app)
    names, entry, text = run_tui(new_story(), make_engine(home), script)
    assert names[:3] == ["in-name", "in-age", "in-job"]
    assert entry == {"name": "Ada Quill", "job": "lamplighter"}


def test_the_new_button_adds_for_the_current_step_when_nothing_is_selected(home):
    async def script(app, pilot):
        s = app.session
        await go_to(app, pilot, "setting")
        await pilot.click("#uni-new"); await pilot.pause()
        boxes = list(app.screen.query(Input))
        assert [b.id for b in boxes] == [f"in-{n}" for n in s.field_names]
        boxes[0].value = "Pinewood"
        for _ in boxes:
            await press(pilot, "enter")
        return store.load_universe()
    assert run_tui(new_story(), make_engine(home), script) == {"setting": [{"place": "Pinewood"}]}


def test_an_entry_with_blank_fields_is_completed_when_used(home):
    store.add_to_universe("setting", {"place": "Pinewood"})
    async def script(app, pilot):
        await press(pilot, "n")
        s = app.session
        await press(pilot, "v", "enter", "down", "enter", "enter")
        return s.fields
    fields = run_tui(new_story(), make_engine(home), script)
    assert fields["place"] == "Pinewood" and all(fields.values()) and len(fields) == 5


def test_blank_new_entries_are_not_saved(home):
    async def script(app, pilot):
        await go_to(app, pilot, "setting")
        await pilot.click("#uni-new"); await pilot.pause()
        for _ in list(app.screen.query(Input)):
            await press(pilot, "enter")
        return store.load_universe(), "Nothing written" in screen_text(app)
    assert run_tui(new_story(), make_engine(home), script) == ({}, True)


def test_u_saves_and_the_panel_shows_it(home):
    async def script(app, pilot):
        await go_to(app, pilot, "setting")
        await press(pilot, "u")
        return screen_text(app)
    text = run_tui(new_story(), make_engine(home), script)
    assert "Universe (1)" in text and "Setting (1)" in text


def test_an_empty_universe_says_so(home):
    async def script(app, pilot):
        return screen_text(app)
    assert "nothing saved yet" in run_tui(new_story(), make_engine(home), script)


def test_groups_stay_open_after_the_panel_refreshes(home):
    with_universe()
    async def script(app, pilot):
        await start_with_universe(app, pilot)
        await pilot.pause()
        await press(pilot, "v", "enter", "escape")
        await press(pilot, "space")                                  # a roll refreshes everything
        return screen_text(app)
    assert "Wade Hollis" in run_tui(new_story(), make_engine(home), script)
