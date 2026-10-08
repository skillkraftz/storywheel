"""Polish 2 (ISSUES #19-36): what a writer does, and what they see."""
from test_polish1 import ann, builder_run  # noqa: F401  (the fixture and helper of polish 1)


def status(s):
    w = s.query_one("#status")
    for name in ("content", "renderable"):
        if hasattr(w, name):
            return str(getattr(w, name))
    return str(w.render())


# --- 19. messages name the key that works -----------------------------------------------------------------------------------

def test_19_the_structure_row_points_to_m(home, ann):
    async def script(app, pilot):
        s = app.screen_ref
        await pilot.click("#outline", offset=(5, 2))
        await pilot.pause()
        for _ in range(40):
            if s.top_rows()[s.outline.highlighted or 0][0] == "meta:structure":
                break
            await pilot.press("down")
        await pilot.press("e")
        await pilot.pause()
        return status(s)
    msg = builder_run(script)
    assert "with m" in msg and "Wheel" not in msg, msg


def test_19_p_on_a_prose_story_points_to_m(home, ann):
    async def script(app, pilot):
        s = app.screen_ref
        await pilot.press("P")
        await pilot.pause()
        return status(s)
    msg = builder_run(script)
    assert "not a screenplay" in msg and "with m" in msg and "(S, story settings)" not in msg, msg



# --- 20. story settings (S) and your details (G) -----------------------------------------------------------------------------

from storywheel import settings, vault  # noqa: E402
from textual.widgets import Input, Select, Tabs  # noqa: E402
from test_polish1 import _hub_run  # noqa: E402


def test_20_story_settings_are_choices_and_say_what_follows_your_default(home, ann):
    settings.save_global({**settings.load_global(), "daily_goal": 800})

    async def script(app, pilot):
        s = app.screen_ref
        await pilot.press("S")
        await pilot.pause()
        dlg = app.screen
        notes = {k: str(dlg.query_one(f"#note-{k}").content) for k in ("daily_goal", "typewriter", "font")}
        goal = dlg.query_one("#f-daily_goal", Input)
        shown = goal.placeholder
        goal.focus()
        await pilot.pause()
        for ch in "1200":
            await pilot.press(ch)
        sel = dlg.query_one("#f-typewriter", Select)
        sel.focus()
        await pilot.pause()
        await pilot.press("enter", "down", "enter")                   # your default -> on
        await pilot.pause()
        typed = (sel.value, str(dlg.query_one("#note-typewriter").content), str(dlg.query_one("#note-daily_goal").content))
        await pilot.click("#save")
        await pilot.pause()
        return notes, shown, typed, type(app.screen).__name__
    notes, shown, typed, after = builder_run(script)
    assert "follows your default: 800" in notes["daily_goal"] and "follows your default: off" in notes["typewriter"]
    assert shown == "your default (800)"
    assert typed[0] == "on" and "this story's own" in typed[1] and "this story's own" in typed[2]
    assert after != "StorySettingsScreen"
    own = settings.story_own(vault.get_universe("thornwood").story("the-last-clause").path)
    assert own == {"daily_goal": 1200, "typewriter": True}               # only what was chosen is stored; the font and the rest still follow


def test_20_clearing_a_story_setting_goes_back_to_your_default(home, ann):
    story = ann.story("the-last-clause")
    settings.save_story(story.path, {"daily_goal": 1200, "typewriter": True, "font": "Courier New"})

    async def script(app, pilot):
        await pilot.press("S")
        await pilot.pause()
        dlg = app.screen
        assert dlg.query_one("#f-daily_goal", Input).value == "1200" and dlg.query_one("#f-typewriter", Select).value == "on"
        dlg.query_one("#f-daily_goal", Input).focus()
        await pilot.pause()
        for _ in range(4):
            await pilot.press("backspace")
        sel = dlg.query_one("#f-typewriter", Select)
        sel.focus()
        await pilot.pause()
        await pilot.press("enter", "up", "enter")                      # on -> your default
        await pilot.pause()
        await pilot.click("#save")
        await pilot.pause()
    builder_run(script)
    assert settings.story_own(story.path) == {"font": "Courier New"}
    assert settings.load_story(story.path)["daily_goal"] == 500 and settings.load_story(story.path)["typewriter"] is False


def test_20_escape_changes_nothing(home, ann):
    story = ann.story("the-last-clause")

    async def script(app, pilot):
        await pilot.press("S")
        await pilot.pause()
        app.screen.query_one("#f-daily_goal", Input).focus()
        await pilot.pause()
        await pilot.press("9", "escape")
        await pilot.pause()
    builder_run(script)
    assert not (story.path / "settings.toml").exists() or settings.story_own(story.path) == {}


def test_20_g_opens_settings_on_the_you_tab_with_the_tab_bar_focused(home, ann):
    async def script(app, pilot):
        await pilot.press("G")
        await pilot.pause()
        await pilot.pause()
        scr = app.screen
        return app.mode_name, scr.query_one("#tabs").active, isinstance(scr.focused, Tabs)
    assert _hub_run(script, ("builder", {"universe": "thornwood", "story": "the-last-clause"})) == ("settings", "t-you", True)
