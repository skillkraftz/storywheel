"""Choosing a story's format (batch 18): formats.py, the story form in the Builder (+ Story, and m on a story), and the format and structure
pickers on the Wheel's structure step. Nothing is typed but a title and a number, so a typo can't silently become the default."""
import asyncio

import pytest
from textual.widgets import Input, OptionList

from storywheel import builder, fill, formats, promote, settings, store, structures, vault, writer
from storywheel.storyform import StoryFormScreen
from storywheel.tui import ChoiceScreen
from conftest import make_engine, run_tui


# --- formats.py ----------------------------------------------------------------------------------------------------------------

def test_each_format_offers_only_the_structures_that_fit_it():
    labels = lambda key: [s.label for s in formats.structures_for(key)]
    assert labels("short-story")[:3] == labels("novel")[:3] == ["Story Spine", "Three-Act Outline", "Kishōtenketsu"]
    assert "Save the Cat" in labels("novel") and "Save the Cat" not in labels("short-story") and "Single Moment" in labels("flash")
    assert labels("feature-film") == ["Feature Film"] and labels("short-film") == ["Short Film"]
    assert [f.label for f in formats.FORMATS] == ["Flash fiction", "Short story", "Novel", "Screenplay (feature film)", "Screenplay (short film)"]


def test_names_are_found_from_keys_and_labels_and_nothing_else():
    assert formats.find("Short story") == "short-story" and formats.find("SCREENPLAY (SHORT FILM)") == "short-film"
    assert formats.find("short-film") == "short-film" and formats.find("shrot story") is None and formats.find("") is None


def test_a_draft_s_format_comes_from_its_choice_then_its_structure_then_your_default(home):
    assert formats.of_draft({}) == "short-story"
    assert formats.of_draft({"format": "novel"}) == "novel"
    assert formats.of_draft({"kept": {"structure": {"structure": "Short Film"}}}) == "short-film"
    settings.save_global({"format": "screenplay"})
    assert formats.of_draft({}) == "feature-film"


def test_saving_a_format_keeps_the_settings_the_writer_reads(home):
    u = vault.create_universe("Forms", ["noir"])
    s = u.new_story("Cold Coffee", {"format": "novel", "target": 90000})
    st = settings.load_story(s.path)
    assert st["format"] == "novel" and st["target_words"] == 90000 and formats.target(s) == (90000, "words")
    formats.apply(s, "short-film", None)
    st = settings.load_story(s.path)
    assert (st["format"], st["script_kind"], st["target_pages"]) == ("screenplay", "short-film", 12) and s.is_screenplay()
    assert formats.of_story(s) == "short-film" and formats.target(s) == (12, "pages")


# --- the Builder's form --------------------------------------------------------------------------------------------------------

def run(script, universe="forms", story=None):
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe=universe, story=story)
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


async def choose_row(app, pilot, row):
    """Highlight a row of the form (format, structure, genres) and open its picker."""
    rows = app.screen.query_one("#rows", OptionList)
    rows.focus()
    rows.highlighted = StoryFormScreen.ROWS.index(row)
    await press(pilot, "enter")


def options(app):
    return [label for label, _value in app.screen.options]


@pytest.fixture
def forms(home):
    return vault.create_universe("Forms", ["noir", "thriller"])


def test_plus_story_is_a_form_of_pickers(forms):
    async def script(app, pilot):
        await press(pilot, "T")
        form = app.screen
        assert isinstance(form, StoryFormScreen) and form.genres == ["noir", "thriller"]          # (the universe's genres)
        form.query_one("#title", Input).value = "Night Shift"
        await choose_row(app, pilot, "format")
        assert isinstance(app.screen, ChoiceScreen) and options(app) == [f.label for f in formats.FORMATS]
        await press(pilot, "down", "down", "down", "down", "enter")                              # Screenplay (short film)
        assert form.structure == "Short Film" and form.query_one("#target", Input).value == "12"
        await choose_row(app, pilot, "structure")
        seen = options(app)
        await press(pilot, "escape")
        await press(pilot, "ctrl+s")
        return seen, type(app.screen).__name__
    seen, after = run(script)
    assert after == "BuilderScreen"
    assert seen[0].startswith("None") and [o.split(":")[0] for o in seen[1:]] == ["Short Film"]   # (only what fits a short film)
    s = forms.story("night-shift")
    st = settings.load_story(s.path)
    assert (st["format"], st["script_kind"], st["target_pages"]) == ("screenplay", "short-film", 12)
    meta, sections = s.load_outline()
    assert meta["genre"] == "noir / thriller" and meta["structure"] == "Short Film"
    assert sections["Short Film"].startswith("**Opening image.**")                               # (the beats, to fill in)


def test_the_target_takes_only_a_number_and_a_title_is_needed(forms):
    async def script(app, pilot):
        await press(pilot, "T")
        form = app.screen
        box = form.query_one("#target", Input)
        box.focus()
        box.value = ""
        await press(pilot, *"5k")                                   # (letters can't be typed in the box)
        typed = box.value
        await press(pilot, "ctrl+s")
        error = str(form.query_one("#error").render())
        box.value = ""
        form.query_one("#title", Input).value = "Untargeted"
        await press(pilot, "ctrl+s")
        error2 = str(form.query_one("#error").render())
        box.value = "4,500"
        await press(pilot, "ctrl+s")
        return typed, error, error2, type(app.screen).__name__
    typed, error, error2, after = run(script)
    assert typed == "5" and "A title, please." in error and "whole number of words" in error2 and after == "BuilderScreen"
    assert settings.load_story(forms.story("untargeted").path)["target_words"] == 4500


def test_genres_are_picked_from_the_generator_s_genres(forms):
    async def script(app, pilot):
        await press(pilot, "T")
        form = app.screen
        form.query_one("#title", Input).value = "Two Genres"
        await choose_row(app, pilot, "genres")
        listed = options(app)
        await press(pilot, "space")                                  # (the first genre listed)
        await press(pilot, "d")
        await press(pilot, "ctrl+s")
        return listed
    listed = run(script)
    assert "western" in listed and "screenplay" not in listed and len(listed) >= 14
    chosen = forms.story("two-genres").load_outline()[0]["genre"].split(" / ")
    assert sorted(chosen) == sorted([listed[0], "noir", "thriller"]) and chosen == sorted(chosen, key=listed.index)      # (in the list's order)


def test_m_changes_a_story_and_warns_when_writing_would_move(forms):
    story = forms.new_story("The Clause", {"format": "short-story"})
    story.append_scene("Opening", "Stacie ran down the road.")
    async def script(app, pilot):
        await press(pilot, "m")
        form = app.screen
        before = str(form.query_one("#note").render())
        await choose_row(app, pilot, "format")
        await press(pilot, "down", "down", "down", "enter")         # Screenplay (feature film)
        warning = str(form.query_one("#note").render())
        await press(pilot, "ctrl+s")
        return before, warning, form.structure
    before, warning, structure = run(script, story="the-clause")
    assert before == "" and "already has prose" in warning and structure == "Feature Film"
    assert story.is_screenplay() and formats.of_story(story) == "feature-film" and formats.target(story) == (110, "pages")
    assert story.extra_files() == []                                # (the prose file is parked, never offered for deleting)
    assert "Stacie ran down the road." in (story.manuscript_dir / "manuscript.md").read_text()
    meta, sections = story.load_outline()
    assert meta["structure"] == "Feature Film" and "Feature Film" in sections


# --- the Wheel's structure step ----------------------------------------------------------------------------------------------

def test_the_wheel_picks_a_format_then_a_structure_that_fits(home):
    async def script(app, pilot):
        s = app.session
        await press(pilot, "k")                                      # genre kept: on the structure step
        assert s.step.key == "structure" and s.fields["format"] == "Short story"
        app.main.card.highlighted = 0                                # the format line
        await press(pilot, "f")                                      # (a format is picked, never rolled)
        formats_offered = options(app)
        await press(pilot, "down", "down", "down", "down", "enter")
        after_format = dict(s.fields)
        app.main.card.highlighted = 1
        await press(pilot, "e")
        structures_offered = options(app)
        await press(pilot, "enter")
        await press(pilot, "k")
        return formats_offered, after_format, structures_offered, dict(s.story["kept"]["structure"]), s.story["format"]
    offered, after, shapes, kept, fmt = run_tui(store.new_story(), make_engine(home), script)
    assert offered == [f.label for f in formats.FORMATS]
    assert after == {"format": "Screenplay (short film)", "structure": "Short Film"}
    assert [o.split(":")[0] for o in shapes] == ["Short Film"]
    assert kept == {"format": "Screenplay (short film)", "structure": "Short Film"} and fmt == "short-film"


def test_rolling_the_structure_step_stays_inside_the_format(home):
    from storywheel import session
    from storywheel.engine import Engine
    st = store.new_story()
    s = session.Session(st, Engine(seed=4))
    s.enter(0)
    s.keep()
    s.set_format("novel")
    seen = set()
    for _ in range(30):
        s.roll()
        seen.add(s.fields["structure"])
        assert s.fields["format"] == "Novel"
    assert seen == {s.label for s in formats.structures_for("novel")}


def test_a_wheel_draft_promotes_into_its_format(home):
    from storywheel.engine import Engine
    from storywheel.sample import build_story
    draft = build_story(Engine(seed=5), ["noir"], structure="three-act")
    draft["format"] = "novel"
    u = vault.create_universe("Rain City", ["noir"])
    story, _report = promote.apply_plan(promote.build_plan(draft, u, Engine(seed=5), None), u, draft)
    assert formats.of_story(story) == "novel" and formats.target(story) == (80000, "words") and not story.is_screenplay()


# --- the Writer's status line ------------------------------------------------------------------------------------------------

@pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")
def test_the_status_line_shows_the_story_against_its_target(home):
    from test_notepad import run as run_writer
    u = vault.create_universe("Lines", ["noir"])
    s = u.new_story("Short One", {"format": "short-story", "target": 5000})
    s.append_scene("Opening", "Rain on the window and nobody home.")
    r = run_writer(s, "", "", "R.line = require('sw.stats').line()")
    assert "in the story 7 / 5,000 words · 0%" in r["line"]
