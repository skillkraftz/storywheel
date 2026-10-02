"""The Settings mode (F4): edit settings.toml as you go, and see your writing stats."""
import asyncio
import datetime
import json
import os

import pytest
from textual.widgets import DataTable, Input, Select, Switch, TabbedContent, TextArea

from storywheel import builder, modes, paths, settings, settings_app, state, store, vault
from conftest import make_engine, run_tui, screen_text


def flat(text):
    return " ".join(text.split())


def run(script, back="builder", st=None, size=(180, 60)):
    async def go():
        app = settings_app.SettingsApp(st, back)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


def status(app):
    return str(app.screen.query_one("#status").content)


async def type_into(pilot, app, wid, text):
    box = app.screen.query_one(wid, Input)
    box.value = text
    await pilot.pause()


def test_every_tab_is_there_with_your_current_values(home):
    settings.save_global({"legal_name": "Andrew Writer", "daily_goal": 750, "notepad_mode": False})
    async def script(app, pilot):
        s = app.screen
        tabs = [p.id for p in s.query("TabPane")]
        return (tabs, s.query_one("#f-legal_name", Input).value, s.query_one("#f-daily_goal", Input).value,
                s.query_one("#f-notepad_mode", Switch).value, s.query_one("#f-library", Input).value)
    tabs, name, goal, notepad, lib = run(script)
    assert tabs == ["t-you", "t-goals", "t-appearance", "t-writer", "t-export", "t-keys", "t-universes", "t-library", "t-stats"]
    assert (name, goal, notepad) == ("Andrew Writer", "750", False) and lib == str(paths.library_root())


def test_text_changes_are_saved_as_you_type(home):
    async def script(app, pilot):
        await type_into(pilot, app, "#f-legal_name", "Andrew T. Writer")
        await type_into(pilot, app, "#f-email", "a@example.com")
    run(script)
    g = settings.load_global()
    assert g["legal_name"] == "Andrew T. Writer" and g["email"] == "a@example.com"
    assert 'legal_name = "Andrew T. Writer"' in (home / "home" / "settings.toml").read_text()


def test_numbers_must_be_numbers_and_a_bad_one_is_not_saved(home):
    async def script(app, pilot):
        await type_into(pilot, app, "#f-daily_goal", "900")
        await type_into(pilot, app, "#f-daily_goal", "9x")
        said = status(app)
        await type_into(pilot, app, "#f-writer_font_size", "18")
        await type_into(pilot, app, "#f-atom_boost", "2.5")
        await type_into(pilot, app, "#f-atom_boost", "0")
        return said
    said = run(script)
    g = settings.load_global()
    assert "Needs a whole number" in said
    assert g["daily_goal"] == 900 and g["writer_font_size"] == 18 and g["atom_boost"] == 2.5


def test_switches_and_choices_save_at_once(home):
    async def script(app, pilot):
        s = app.screen
        s.query_one("#f-notepad_mode", Switch).value = False
        s.query_one("#f-neovide", Switch).value = True
        s.query_one("#f-font", Select).value = "Courier New"
        s.query_one("#f-format", Select).value = "novel"
        await pilot.pause()
    run(script)
    g = settings.load_global()
    assert g["notepad_mode"] is False and g["neovide"] is True and g["font"] == "Courier New" and g["format"] == "novel"


def test_the_address_keeps_its_lines(home):
    async def script(app, pilot):
        app.screen.query_one("#f-address", TextArea).text = "1 Main Street\nDry Fork, WY 82000"
        await pilot.pause()
    run(script)
    assert settings.load_global()["address"] == "1 Main Street\nDry Fork, WY 82000"


def test_other_keys_in_the_file_are_not_lost(home):
    (home / "home").mkdir(parents=True, exist_ok=True)
    (home / "home" / "settings.toml").write_text('library = "/somewhere"\nlegal_name = "X"\n')
    async def script(app, pilot):
        await type_into(pilot, app, "#f-email", "e@x.org")
    run(script)
    assert 'library = "/somewhere"' in (home / "home" / "settings.toml").read_text()


def test_the_library_location_is_a_setting_and_nothing_is_moved(home, monkeypatch, tmp_path):
    monkeypatch.delenv("STORYWHEEL_LIBRARY")
    default = paths.library_root()
    assert default.name == "storywheel"
    new = tmp_path / "elsewhere" / "lib"
    async def script(app, pilot):
        box = app.screen.query_one("#f-library", Input)
        box.value = str(new)
        await box.action_submit()
        await pilot.pause()
        return status(app)
    said = run(script)
    assert "Nothing was moved" in said and new.is_dir()
    assert paths.library_root() == new
    assert 'library = "%s"' % new in (home / "home" / "settings.toml").read_text()


def test_the_environment_variable_still_wins(home, tmp_path):
    (home / "home").mkdir(parents=True, exist_ok=True)
    (home / "home" / "settings.toml").write_text('library = "/never/used"\n')
    assert paths.library_root() == home / "library"                  # STORYWHEEL_LIBRARY is set by the test fixture


def test_a_library_folder_that_cannot_be_made_is_reported(home):
    async def script(app, pilot):
        box = app.screen.query_one("#f-library", Input)
        box.value = "/proc/nope/lib"
        await box.action_submit()
        await pilot.pause()
        return status(app)
    assert "Can't use that folder" in run(script)


# --- what the settings do ------------------------------------------------------------------------------------------------

def test_your_writer_preferences_are_the_default_for_every_story(home):
    u = vault.create_universe("U")
    s = u.new_story("Tale")
    assert settings.load_story(s.path)["notepad_mode"] is True and settings.load_story(s.path)["neovide"] is False
    settings.save_global({"notepad_mode": False, "neovide": True, "writer_font": "Iosevka", "writer_font_size": 17,
                          "line_spacing": 20, "paragraph_spacing": 1, "column_width": 66})
    st = settings.load_story(s.path)
    assert (st["notepad_mode"], st["neovide"], st["writer_font"], st["writer_font_size"], st["line_spacing"],
            st["paragraph_spacing"], st["column_width"]) == (False, True, "Iosevka", 17, 20, 1, 66)
    settings.save_story(s.path, {"neovide": False, "column_width": 80})
    st = settings.load_story(s.path)
    assert st["neovide"] is False and st["column_width"] == 80 and st["writer_font"] == "Iosevka"


def test_the_universe_boost_default_comes_from_settings_unless_the_universe_pins_its_own(home):
    u = vault.create_universe("U")
    assert u.settings()["atom_boost"] == 1.5 and not u.settings()["atom_boost_own"]
    settings.save_global({"atom_boost": 2.5})
    assert vault.get_universe("u").settings()["atom_boost"] == 2.5                      # the existing universe follows
    u.save_settings(atom_boost=4.0)
    assert vault.get_universe("u").settings()["atom_boost"] == 4.0
    settings.save_global({"atom_boost": 3.0})
    assert vault.get_universe("u").settings()["atom_boost"] == 4.0                      # pinned
    u.save_settings(atom_boost=None)                                                    # back to the default
    assert vault.get_universe("u").settings()["atom_boost"] == 3.0
    assert "atom_boost" not in (u.path / "universe.md").read_text()


def test_blank_boost_in_the_builders_universe_settings_means_your_default(home):
    u = vault.create_universe("U")
    u.save_settings(atom_boost=4.0)
    from storywheel import fill
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="u")
        async with app.run_test(size=(220, 55)) as pilot:
            await pilot.pause()
            await pilot.press("s")
            await pilot.pause()
            boxes = list(app.screen.query(Input))
            boxes[4].value = ""
            for _ in boxes:
                await pilot.press("enter")
    asyncio.run(go())
    assert not vault.get_universe("u").settings()["atom_boost_own"]


# --- the Stats tab ------------------------------------------------------------------------------------------------------------

def test_the_stats_tab_shows_days_streaks_and_story_totals(home):
    u = vault.create_universe("Thornwood")
    s = u.new_story("The Clause")
    s.add_scene("A", "one two three four five")
    t = datetime.date.today()
    day = lambda n: (t - datetime.timedelta(days=n)).isoformat()
    s.stats_path.write_text(json.dumps({"days": {day(0): {"words": 300}, day(1): {"words": 450}, day(4): {"words": 50}}}))
    settings.save_global({"daily_goal": 600})
    async def script(app, pilot):
        app.screen.query_one("#tabs", TabbedContent).active = "t-stats"
        await pilot.pause()
        summary = str(app.screen.query_one("#summary").content)
        days = app.screen.query_one("#days", DataTable)
        stories = app.screen.query_one("#stories", DataTable)
        return summary, [days.get_row_at(i)[:2] for i in range(days.row_count)], [stories.get_row_at(i) for i in range(stories.row_count)]
    summary, days, stories = run(script)
    assert "Today  300 / 600 words" in summary and "Streak  2 days   (best 2)" in summary and "Words recorded  800" in summary
    assert days == [[day(0), "300"], [day(1), "450"], [day(4), "50"]]
    assert stories == [["Thornwood", "The Clause", "5", "300"]]


def test_the_stats_tab_with_nothing_written_yet(home):
    async def script(app, pilot):
        app.screen.query_one("#tabs", TabbedContent).active = "t-stats"
        await pilot.pause()
        return str(app.screen.query_one("#summary").content), app.screen.query_one("#days", DataTable).row_count
    summary, rows = run(script)
    assert "Streak  0 days" in summary and rows == 0


# --- keys and modes ----------------------------------------------------------------------------------------------------------------

def test_the_mode_keys_leave_settings_and_q_goes_back(home):
    for key, expect in (("f1", "wheel"), ("f2", "builder"), ("f3", "writer")):
        async def script(app, pilot, key=key):
            await pilot.press(key)
            await pilot.pause()
            return app.next
        assert run(script) == (expect, {})
    async def back(app, pilot):
        await pilot.press("q")
        await pilot.pause()
        return app.next
    assert run(back, back="wheel") == ("back", {"fallback": "wheel"}) and run(back, back="builder") == ("back", {"fallback": "builder"})


def test_typing_q_in_a_box_does_not_leave(home):
    async def script(app, pilot):
        box = app.screen.query_one("#f-legal_name", Input)
        box.focus()
        await pilot.pause()
        await pilot.press("q", "u", "i", "t")
        await pilot.pause()
        return box.value, app.next
    assert run(script) == ("quit", None)


def test_f4_is_in_every_help_screen_and_every_mode_has_the_key(home):
    from storywheel.nvim import __file__ as _unused  # noqa: F401  (the package folder exists)
    async def wheel(app, pilot):
        await pilot.press("question_mark")
        await pilot.pause()
        return flat(screen_text(app))
    assert "Wheel (this), Universe Builder, Writer, Settings" in run_tui(store.new_story(), make_engine(home), wheel, size=(200, 100))
    assert "F4 Settings" in builder.HELP and "F4 Settings" in settings_app.HELP
    from pathlib import Path
    lua = (Path(__file__).resolve().parent.parent / "storywheel" / "nvim" / "lua" / "sw" / "init.lua").read_text()
    assert "F4 Settings" in lua and '"<F4>"' in lua


def test_f4_in_the_wheel_and_the_builder_goes_to_settings(home):
    async def wheel(app, pilot):
        await pilot.press("f4")
        await pilot.pause()
        return app.next
    assert run_tui(store.new_story(), make_engine(home), wheel)[0] == "settings"
    vault.create_universe("U")
    async def go():
        app = builder.BuilderApp(universe="u")
        async with app.run_test(size=(220, 55)) as pilot:
            await pilot.pause()
            await pilot.press("f4")
            await pilot.pause()
        return app.next
    assert asyncio.run(go())[0] == "settings"


def test_the_mode_loop_remembers_where_to_come_back_to(home, monkeypatch):
    seen = []
    script = iter([("settings", {}), ("builder", {}), None])
    monkeypatch.setattr(modes, "run_wheel", lambda *a, **k: next(script))
    monkeypatch.setattr(modes, "run_settings", lambda st, payload: (seen.append(payload.get("back")), next(script))[1])
    monkeypatch.setattr(modes, "run_builder", lambda *a, **k: next(script))
    modes.run(("wheel", {}), None, None)
    assert seen == ["wheel"]


def test_settings_is_remembered_as_where_you_were(home):
    st = state.State()
    async def script(app, pilot):
        pass
    run(script, back="wheel", st=st)
    assert state.State().get("mode") == "settings" and state.State().get("back") == "wheel"
