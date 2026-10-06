"""The Builder's tabbed right column (Outline, Scenes, Notes) and the writing-stats box on top."""
import asyncio
import contextlib
import datetime
import json

import pytest
from textual.widgets import Input, OptionList, TabbedContent

from storywheel import builder, fill, settings, state, vault, writer, writing_stats
from conftest import screen_text

TODAY = datetime.date.today()


def d(offset):
    return (TODAY - datetime.timedelta(days=offset)).isoformat()


def flat(text):
    return " ".join(text.split())


def write_stats(story, per_day):
    story.stats_path.write_text(json.dumps({"days": {k: {"words": v} for k, v in per_day.items()}, "sessions": []}))


@pytest.fixture
def world(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause", {"genre": "western"}, {"Premise": "A clerk finds a clause."})
    s.append_scene("Opening", "Stacie ran down the road.\n\nIt was dry.")
    s.append_scene("The Letter", "A letter came on Tuesday.\n\nBy Friday it was gone.")
    s2 = u.new_story("Other Tale")
    s2.append_scene("A", "Three words here.")
    u.new_entity("character", "Stacie", {"job": "clerk"})
    return u, s, s2


def run(script, universe="thornwood", story="the-last-clause", state_store=None, size=(220, 55), rtab=None):
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe=universe, story=story,
                                 state_store=state_store, rtab=rtab)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


# --- the numbers ------------------------------------------------------------------------------------------------

def test_words_per_day_add_up_across_every_story(world):
    u, s, s2 = world
    write_stats(s, {d(0): 300, d(1): 200})
    write_stats(s2, {d(0): 100, d(3): 50})
    per_day = writing_stats.days()
    assert per_day == {d(0): 400, d(1): 200, d(3): 50}
    assert writing_stats.story_days(s2) == {d(0): 100, d(3): 50}
    assert writing_stats.history() == [(d(0), 400), (d(1), 200), (d(3), 50)]


def test_a_broken_stats_file_is_just_no_stats(world):
    u, s, s2 = world
    s.stats_path.write_text("{ nope")
    assert writing_stats.story_days(s) == {}


def test_streaks():
    t = TODAY
    f = lambda *offs: {d(o): 100 for o in offs}
    assert writing_stats.streak(f(0, 1, 2), t) == (3, 3)
    assert writing_stats.streak(f(1, 2), t) == (2, 2)                  # nothing yet today: it still counts back from yesterday
    assert writing_stats.streak(f(2, 3), t) == (0, 2)                  # yesterday missed: the streak is broken
    assert writing_stats.streak(f(0, 1, 5, 6, 7, 8), t) == (2, 4)
    assert writing_stats.streak({d(0): 0}, t) == (0, 0)
    assert writing_stats.streak({}, t) == (0, 0)


def test_the_progress_bar():
    assert writing_stats.bar(0, 100, 10) == "░" * 10 and writing_stats.bar(50, 100, 10) == "█" * 5 + "░" * 5
    assert writing_stats.bar(500, 100, 10) == "█" * 10 and writing_stats.bar(5, 0) == ""


def test_the_summary(world):
    u, s, s2 = world
    settings.save_story(s.path, {"daily_goal": 1000})
    write_stats(s, {d(0): 640, d(1): 100})
    write_stats(s2, {d(0): 60, d(10): 5})
    sm = writing_stats.summary(u, s)
    assert sm["today"] == 700 and sm["goal"] == 1000 and sm["percent"] == 70 and sm["bar"].count("█") == 14
    assert sm["streak"] == 2 and sm["best_streak"] == 2 and sm["week"] == 800
    assert sm["story_words"] == s.word_count() == 18 and sm["story_scenes"] == 2
    assert sm["universe_words"] == 18 + 3 and sm["universe_stories"] == 2
    rows = writing_stats.per_story()
    assert ("Thornwood", "The Last Clause", 18, 640) in rows and ("Thornwood", "Other Tale", 3, 60) in rows


# --- the stats box ------------------------------------------------------------------------------------------------------

def test_the_top_box_is_a_stats_box(world):
    u, s, s2 = world
    settings.save_story(s.path, {"daily_goal": 1000})
    write_stats(s, {d(0): 640, d(1): 100, d(2): 50})
    async def script(app, pilot):
        return flat(screen_text(app))
    text = run(script)
    assert "Writing" in text and "Today 640 / 1,000 words" in text and "64%" in text
    assert "Streak 3 days (best 3)" in text and "This week 790 words" in text
    assert "Story 18 words in 2 scenes: The Last Clause" in text
    assert "Universe 21 words across 2 stories: Thornwood" in text


def test_the_stats_box_without_a_goal_or_a_story(world):
    async def script(app, pilot):
        return flat(screen_text(app))
    settings.save_global({"daily_goal": 0})
    text = run(script, story=None)
    assert "Today 0 words" in text and "Story " not in text.split("Writing")[1].split("Characters")[0]


def test_the_box_has_no_edit_dialogs_anymore(world):
    async def script(app, pilot):
        await pilot.click("#stats")
        await pilot.pause()
        await pilot.click("#stats", button=3)
        await pilot.pause()
        return type(app.screen).__name__
    assert run(script) == "BuilderScreen"


# --- the tabbed right column -----------------------------------------------------------------------------------------------

def test_the_right_column_has_outline_scenes_and_notes_tabs(world):
    async def script(app, pilot):
        s = app.screen_ref
        tabs = s.query_one("#rtabs", TabbedContent)
        seen = [tabs.active]
        for key in ("7", "8", "6"):
            await pilot.press(key)
            await pilot.pause()
            seen.append(tabs.active)
        return seen, flat(screen_text(app))
    seen, text = run(script)
    assert seen == ["r-outline", "r-scenes", "r-notes", "r-outline"]
    assert "Outline" in text and "Scenes" in text and "Notes" in text and "A clerk finds a clause." in text


def test_the_outline_tab_shows_the_story_or_the_universe(world):
    async def script(app, pilot):
        story_text = flat(screen_text(app))
        await pilot.press("o")
        await pilot.pause()
        return story_text, flat(screen_text(app))
    story_text, uni_text = run(script)
    assert "Story outline: The Last Clause" in story_text and "A clerk finds a clause." in story_text
    assert "Universe: Thornwood" in uni_text and "Genre leanings" in uni_text


def test_links_appearances_and_entity_notes_are_under_the_card_and_the_story_has_its_own_notes_tab(world):
    u, s, s2 = world
    async def script(app, pilot):
        before = flat(screen_text(app))
        await pilot.press("8")
        await pilot.pause()
        return before, flat(screen_text(app))
    before, after = run(script)
    assert "Appears in" in before and "Links" in before and "Notes about this entity" in before          # (they describe the selected entity, so they sit under its card)
    assert "Free-form notes about this story" in after


def test_the_scenes_tab_lists_the_scenes_with_first_lines_and_words(world):
    async def script(app, pilot):
        await pilot.press("7")
        await pilot.pause()
        return flat(screen_text(app)), [e["title"] for e in app.screen_ref.scene_entries]
    text, titles = run(script)
    assert titles == ["Opening", "The Letter"]
    assert "1 Opening 8w" in text and "Stacie ran down the road." in text
    assert "2 The Letter" in text and "A letter came on Tuesday." in text


def test_the_scenes_tab_without_a_story_says_what_to_do(world):
    async def script(app, pilot):
        await pilot.press("7")
        await pilot.pause()
        return flat(screen_text(app))
    assert "Open a story" in run(script, story=None)


def test_enter_on_a_scene_opens_the_writer_at_that_scene(world, monkeypatch):
    u, s, s2 = world
    calls = []
    monkeypatch.setattr(writer, "run", lambda story, scene=None: calls.append((story.slug, scene)) or None)
    monkeypatch.setattr(writer, "check", lambda: None)
    async def script(app, pilot):
        monkeypatch.setattr(app, "suspend", lambda: contextlib.nullcontext())
        await pilot.press("7")
        await pilot.pause()
        lst = app.screen_ref.query_one("#scenes", OptionList)
        lst.focus()
        lst.highlighted = 1
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.click("#sc-write")
        await pilot.pause()
    run(script)
    assert calls[0][0] == "the-last-clause" and calls[0][1]["title"] == "The Letter"
    assert calls[0][1]["path"].endswith("manuscript.md") and calls[0][1]["line"] == 7      # the marker's line
    assert calls[1][1]["title"] == "The Letter"                      # the button writes at the highlighted scene


def test_the_writer_gets_the_scene_in_its_environment(world, monkeypatch):
    u, s, s2 = world
    seen = {}
    monkeypatch.setattr(writer, "check", lambda: None)
    monkeypatch.setattr(writer.subprocess, "call", lambda argv, env=None: seen.update(env=env) or 0)
    writer.run(s, {"path": "/x/02-the-letter.md", "line": 5})
    assert seen["env"]["STORYWHEEL_SCENE"] == "/x/02-the-letter.md:5"
    writer.run(s)
    assert "STORYWHEEL_SCENE" not in seen["env"]


def test_add_a_scene_from_the_tab(world):
    u, s, s2 = world
    async def script(app, pilot):
        await pilot.press("7")
        await pilot.pause()
        await pilot.click("#sc-add")
        await pilot.pause()
        app.screen.query_one(Input).value = "The Ending"
        await pilot.press("enter")
        await pilot.pause()
        return [e["title"] for e in app.screen_ref.scene_entries]
    assert run(script) == ["Opening", "The Letter", "The Ending"]


def test_the_chosen_tab_is_remembered(world):
    st = state.State()
    async def script(app, pilot):
        await pilot.press("7")
        await pilot.pause()
    run(script, state_store=st)
    assert state.State().get("rtab") == "r-scenes"
    async def script2(app, pilot):
        return app.screen_ref.query_one("#rtabs", TabbedContent).active
    assert run(script2, rtab="r-scenes") == "r-scenes"


def test_the_help_mentions_the_new_keys(world):
    async def script(app, pilot):
        await pilot.press("question_mark", "2")                  # (the Keys tab)
        await pilot.pause()
        return flat(screen_text(app))
    text = run(script, size=(220, 90))
    assert "Story panel: the Scenes tab (Enter on a scene opens the Writer there)" in text and "Story panel: the story's own notes" in text


# --- batch 9: the Story panel, +Story, no right column ---------------------------------------------------------------------------------

def test_there_is_no_right_column_and_the_story_panel_sits_under_the_story_list(world):
    async def script(app, pilot):
        s = app.screen_ref
        stories, panel, mid = s.query_one("#stories-box"), s.query_one("#story-box"), s.query_one("#mid")
        return (len(s.query("#right")), panel.region.y >= stories.region.bottom, panel.region.x == stories.region.x, panel.region.height > stories.region.height,
                mid.region.x >= panel.region.right, [t.id for t in s.query_one("#rtabs").query("TabPane")], panel.border_title)
    rights, below, same_column, bigger, mid_beside, tabs, title = run(script)
    assert rights == 0 and below and same_column and bigger and mid_beside and tabs == ["r-outline", "r-scenes", "r-notes"]
    assert title.startswith("Story:") and "The Last Clause" in title


def test_the_story_list_shows_titles_only(world):
    async def script(app, pilot):
        lst = app.screen_ref.query_one("#stories")
        return [lst.get_option_at_index(i).prompt for i in range(lst.option_count)], flat(screen_text(app))
    prompts, text = run(script)
    assert len(prompts) == 2 and "The Last Clause" in text and "Other Tale" in text and "8w" not in text


def test_plus_story_makes_a_blank_story_with_no_wheel_draft(world):
    u, s, s2 = world
    async def script(app, pilot):
        await pilot.click("#s-new")
        await pilot.pause()
        scr = app.screen
        scr.query(Input).first().value = "A Brand New Tale"
        await pilot.press("ctrl+s")                                 # (the story form: a short story by default)
        await pilot.pause()
        return type(scr).__name__, app.screen_ref.story.title, flat(screen_text(app)), app.next
    kind, title, text, nxt = run(script)
    assert title == "A Brand New Tale" and nxt is None
    made = vault.get_universe("thornwood").story("a-brand-new-tale")
    assert made is not None and made.title == "A Brand New Tale" and made.word_count() == 0
    assert "Started 'A Brand New Tale'" in text and not (made.path / "seed.json").exists()


def test_the_builder_no_longer_starts_wheel_drafts(world):
    async def script(app, pilot):
        s = app.screen_ref
        return len(s.query("#s-draft")), hasattr(s, "action_new_draft"), "+Wheel draft" in flat(screen_text(app))
    assert run(script) == (0, False, False)


def test_story_notes_are_saved_as_you_type_and_come_back(world):
    u, s, s2 = world
    async def script(app, pilot):
        await pilot.press("8")
        await pilot.pause()
        box = app.screen_ref.query_one("#story-notes")
        box.focus()
        await pilot.pause()
        await pilot.press("h", "i")
        await pilot.pause()
        return box.text, (s.path / "notes.md").read_text()
    text, saved = run(script)
    assert text == "hi" and saved == "hi" and s.notes == "hi"
    assert s2.notes == ""


def test_entity_notes_are_under_the_card_and_still_save(world):
    u, s, s2 = world
    async def script(app, pilot):
        scr = app.screen_ref
        scr.entity = u.entities("character")[0]
        scr.refresh_all()
        await pilot.pause()
        box = scr.query_one("#notes")
        inside = scr.query_one("#card-box").region.contains_region(box.region)
        await pilot.press("E")
        await pilot.pause()
        focused = app.focused.id
        await pilot.press("o", "k")
        await pilot.pause()
        return inside, focused, u.entities("character")[0].body
    inside, focused, body = run(script)
    assert inside and focused == "notes" and body == "ok"



def test_p_starts_a_screenplay_from_its_outline_and_says_why_not_for_prose(world):
    u, s, s2 = world
    film = u.new_story("Night Shift", {"structure": "Short Film"}, {"Short Film": "**Opening image.** A diner at 3 a.m."})
    async def script(app, pilot):
        await pilot.press("P")
        await pilot.pause()
        return flat(screen_text(app))
    text = run(script, story="night-shift")
    assert film.script_path.exists() and "= A diner at 3 a.m." in film.script_path.read_text()
    assert "Started script.fountain from the outline" in text
    film.script_path.write_text(film.script_path.read_text() + "\nINT. DINER - NIGHT\n\nRain on the glass.\n")
    text = run(script, story="night-shift")
    assert "already has scenes in it; it was left alone" in text and "Rain on the glass." in film.script_path.read_text()
    text = run(script)
    assert "not a screenplay" in text and not (s.path / "manuscript" / "script.fountain").exists()
