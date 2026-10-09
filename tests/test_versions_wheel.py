"""Promotion offers "Also start as" (batch 20): each ticked format makes a sibling version; the entities are created once."""
from textual.widgets import Input, OptionList

from storywheel import formats, store, vault, versions
from conftest import make_engine, run_tui
from test_promote_ui import keep_to, press, flat


def test_the_preview_offers_the_other_formats_and_a_tick_makes_a_second_version(home):
    story = store.new_story()

    async def script(app, pilot):
        await keep_to(app, pilot, "premise")
        await press(pilot, "Q", "n")
        app.screen.query_one(Input).value = "Thornwood"
        await press(pilot, "enter")
        assert type(app.screen).__name__ == "PromotePreviewScreen"
        lst = app.screen.query_one("#plan", OptionList)
        ids = [o.id for o in lst.options if o.id and str(o.id).startswith("fmt:")]
        own = formats.of_draft(app.session.story)
        shown = flat(" ".join(str(o.prompt) for o in lst.options))
        lst.focus()
        lst.highlighted = [o.id for o in lst.options].index("fmt:feature-film")
        await press(pilot, "enter")                                        # tick it
        lst.highlighted = [o.id for o in lst.options].index("fmt:novel")
        await press(pilot, "enter")
        await press(pilot, "enter")                                        # ...and untick the novel again
        ticked = list(app.screen.plan.also)
        await press(pilot, "p")
        return ids, own, shown, ticked, app.return_value

    ids, own, shown, ticked, message = run_tui(story, make_engine(home), script)
    assert own == "short-story" and ids == ["fmt:flash", "fmt:novel", "fmt:feature-film", "fmt:short-film"]       # (the story's own format is not offered)
    assert "Also start as" in shown and "(this story)" in shown and "screenplay (feature film)" in shown
    assert ticked == ["feature-film"]
    u = vault.get_universe("thornwood")
    assert len(u.stories()) == 2
    first = u.stories()[0]
    fam = versions.versions(first)
    assert [formats.of_story(s) for s in fam] == ["short-story", "feature-film"]
    assert versions.family_of(fam[1]) == first.slug
    assert "feature film version" in message.lower() or "screenplay (feature film) version" in message.lower()
    chars = u.entities("character")
    assert len({e.id for e in chars}) == len(chars) and not any(e.name.endswith(" 2") for e in chars)


def test_nothing_ticked_promotes_one_story_as_before(home):
    story = store.new_story()

    async def script(app, pilot):
        await keep_to(app, pilot, "premise")
        await press(pilot, "Q", "n")
        app.screen.query_one(Input).value = "Plain"
        await press(pilot, "enter")
        assert app.screen.plan.also == []
        await press(pilot, "p")

    run_tui(story, make_engine(home), script)
    u = vault.get_universe("plain")
    assert len(u.stories()) == 1 and versions.family_of(u.stories()[0]) == ""


# --- the Writer says which version you are in ------------------------------------------------------------------------------------

import pytest

from test_versions import make
from test_writer import run_lua


@pytest.mark.parametrize("fmt,label", [("short-story", "short story"), ("novel", "novel"), ("feature-film", "feature film"),
                                       ("short-film", "short film")])
def test_the_writer_status_line_and_window_title_say_the_title_and_the_format(home, fmt, label):
    s = make(home, fmt, title="Cold Coffee")
    r = run_lua(s, """
        require("sw.stats").refresh()
        R.line = require("sw.stats").line()
        R.title = vim.o.titlestring
    """, columns=150)
    assert r["line"].startswith(f"  Cold Coffee ({label})  ·  ") and r["title"] == f"storywheel: Cold Coffee ({label})"


def test_two_versions_of_one_story_are_told_apart_in_the_writer(home):
    s = make(home)
    film, _ = versions.new_version(s, "feature-film")
    a = run_lua(s, 'R.line = require("sw.stats").line()', columns=150)["line"]
    b = run_lua(film, 'R.line = require("sw.stats").line()', columns=150)["line"]
    assert "(short story)" in a and "(feature film)" in b and a.split("  ·  ")[0] != b.split("  ·  ")[0]


def test_a_long_title_is_shortened_but_the_format_stays(home):
    s = make(home, "feature-film", title="A Very Long Title That Will Not Fit In A Narrow Window At All, Whatever We Do")
    r = run_lua(s, 'R.line = require("sw.stats").line()', columns=60)
    assert r["line"].split("  ·  ")[0].endswith("(feature film)") and "…" in r["line"]
