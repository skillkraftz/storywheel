"""Versions in the Builder (batch 20): the New version form, the story list grouped by family, moving between versions."""
import asyncio

from textual.widgets import Input, OptionList

from storywheel import builder, fill, formats, vault, versions
from storywheel.versionform import VersionFormScreen
from conftest import screen_text
from test_versions import make


def run(script, universe="noirville", story=None, size=(200, 50)):
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe=universe, story=story)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


def flat(text):
    return " ".join(text.split())


def test_new_version_form_flow_by_key(home):
    s = make(home)

    async def script(app, pilot):
        await press(pilot, "v")
        form = app.screen
        assert isinstance(form, VersionFormScreen)
        text = flat(str(form.query_one("#explain").render()))
        assert "already shared" in text and "COPIED once" in text and form.heading.endswith("Cold Coffee”")
        assert form.title_value == "Cold Coffee" and form.fmt == "novel"                  # (the first format the family doesn't have)
        assert form.copy == list(versions.DEFAULT_COPY)
        rows = form.query_one("#copy", OptionList)
        assert [o.id for o in rows.options] == list(versions.COPY_OPTIONS)
        assert "files copied as they are" in flat(str(rows.get_option("manuscript").prompt))
        form.query_one("#title", Input).value = "Cold Coffee: The Film"
        form._format_chosen("feature-film")
        await pilot.pause()
        assert form.query_one("#target", Input).value == "110"
        assert "prose written into the script" in flat(str(rows.get_option("manuscript").prompt))
        rows.focus()
        rows.highlighted = versions.COPY_OPTIONS.index("manuscript")
        await press(pilot, "enter")                                                       # tick the manuscript
        rows.highlighted = versions.COPY_OPTIONS.index("notes")
        await press(pilot, "enter")                                                       # untick the notes
        assert "manuscript" in form.copy and "notes" not in form.copy
        assert "rough start" in flat(str(form.query_one("#note").render())).lower()
        await press(pilot, "ctrl+s")
        return type(app.screen).__name__, flat(str(app.screen_ref.query_one("#status").render())), app.screen_ref.story.slug

    after, text, current = run(script, story="cold-coffee")
    assert after == "BuilderScreen" and current == "cold-coffee-the-film"
    new = s.universe.story("cold-coffee-the-film")
    assert formats.of_story(new) == "feature-film" and new.title == "Cold Coffee: The Film"
    assert versions.family_of(new) == versions.family_of(s) == "cold-coffee"
    assert new.notes == "" and new.script_path.exists() and "Rough start" in new.script_path.read_text(encoding="utf-8")
    assert "Premise" in new.sections() and new.seed() == {"draft": 1}
    assert "Made the screenplay (feature film) version" in text and "Rough start" in text


def test_cancelling_the_form_changes_nothing(home):
    s = make(home)

    async def script(app, pilot):
        await press(pilot, "v")
        await press(pilot, "escape")
        return type(app.screen).__name__

    assert run(script, story="cold-coffee") == "BuilderScreen"
    assert [x.slug for x in s.universe.stories()] == [s.slug] and versions.family_of(s) == ""


def test_the_new_version_button_and_the_stories_list_key(home):
    make(home)

    async def script(app, pilot):
        await pilot.click("#s-version")
        await pilot.pause()
        first = type(app.screen).__name__
        await press(pilot, "escape")
        app.screen.query_one("#stories").focus()
        await press(pilot, "v")
        return first, type(app.screen).__name__

    assert run(script, story="cold-coffee") == ("VersionFormScreen", "VersionFormScreen")


def test_the_stories_list_shows_a_family_under_one_title_with_a_row_per_format(home):
    s = make(home)
    versions.new_version(s, "feature-film", title="Cold Coffee", copy=("outline", "manuscript"))
    make(home, title="Lonely Story")

    async def script(app, pilot):
        lst = app.screen_ref.query_one("#stories", OptionList)
        return [(o.id, o.disabled) for o in lst.options], flat(screen_text(app))

    options, text = run(script)
    assert options[0] == ("", True) and [o[0] for o in options[1:]] == ["cold-coffee", "cold-coffee-feature-film", "lonely-story"]
    assert text.count("Cold Coffee") >= 1 and "Short story" in text and "Feature film" in text
    assert "words" in text and "Lonely Story" in text


def test_a_story_with_no_versions_is_one_plain_row_as_before(home):
    s = make(home)

    async def script(app, pilot):
        return [(o.id, o.disabled) for o in app.screen_ref.query_one("#stories", OptionList).options]

    assert run(script) == [(s.slug, False)]


def test_brackets_move_between_the_versions_of_the_open_story(home):
    s = make(home)
    film, _ = versions.new_version(s, "feature-film")
    novel, _ = versions.new_version(s, "novel")

    async def script(app, pilot):
        seen = []
        await press(pilot, "right_square_bracket")
        seen.append(app.screen_ref.story.slug)
        await press(pilot, "right_square_bracket")
        seen.append(app.screen_ref.story.slug)
        await press(pilot, "right_square_bracket")
        seen.append(app.screen_ref.story.slug)
        await press(pilot, "left_square_bracket")
        seen.append(app.screen_ref.story.slug)
        return seen

    assert run(script, story="cold-coffee") == [film.slug, novel.slug, s.slug, novel.slug]


def test_brackets_on_a_story_with_no_siblings_say_so(home):
    make(home)

    async def script(app, pilot):
        await press(pilot, "right_square_bracket")
        return app.screen_ref.story.slug, flat(str(app.screen_ref.query_one("#status").render()))

    slug, text = run(script, story="cold-coffee")
    assert slug == "cold-coffee" and "no other versions" in text


def test_the_thin_layout_still_has_the_button(home):
    s = make(home)
    versions.new_version(s, "novel")

    async def script(app, pilot):
        btn = app.screen_ref.query_one("#s-version")
        return str(btn.label), btn.region.width, flat(str(app.screen_ref.query_one("#story-summary").render()))

    label, width, summary = run(script, story="cold-coffee", size=(120, 40))
    assert label == "New version" and width >= len(label) and "2 versions" in summary and "feature film" not in summary
