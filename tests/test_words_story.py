"""Batch 23 B5: Words (F5) knows the story you are working on: Genre words starts on its genres and Story words on it."""
import asyncio

import pytest
from textual.widgets import Select, TabbedContent

from storywheel import vault, words_app
from test_words import index, run  # noqa: F401  (the small dictionary fixture, and the runner)


@pytest.fixture
def two_stories(home):
    u = vault.create_universe("Thornwood", ["western"])
    a = u.new_story("Dry Well", {"genre": "Western / Noir"})
    b = u.new_story("Night Ferry", {"genre": "Fantasy"})
    for s, text in ((a, "The lantern swung over the dry well."), (b, "The ferry glided past the pale moon.")):
        s.manuscript_dir.mkdir(parents=True, exist_ok=True)
        (s.manuscript_dir / "manuscript.md").write_text(text + "\n", encoding="utf-8")
    return u, a, b


async def open_tab(pilot, app, tab):
    app.screen.query_one(TabbedContent).active = tab
    await pilot.pause()
    await pilot.pause()


def test_opened_with_a_story_genre_words_ranks_by_its_genres_and_story_words_reads_it(index, two_stories):
    async def script(app, pilot):
        scr = app.screen
        scope = scr.query_one("#swscope", Select).value
        await open_tab(pilot, app, "t-genre")
        return scope, list(scr.gw_genres)
    scope, genres = run(script, {"universe": "thornwood", "story": "night-ferry", "back": "builder"})
    assert scope == "night-ferry" and genres == ["fantasy"]


def test_a_universe_without_a_story_genre_uses_its_own_leanings(index, two_stories):
    u, a, b = two_stories
    b.set_meta(genre="")

    async def script(app, pilot):
        await open_tab(pilot, app, "t-genre")
        return list(app.screen.gw_genres)
    assert run(script, {"universe": "thornwood", "story": "night-ferry", "back": "builder"}) == ["western"]


def test_coming_back_to_words_for_another_story_of_the_same_universe_follows_it(index, two_stories):
    """The hub keeps Words alive; F5 from a different story must not leave it on the last one."""
    async def script(app, pilot):
        scr = app.screen
        await open_tab(pilot, app, "t-genre")
        first = (scr.query_one("#swscope", Select).value, list(scr.gw_genres))
        scr.enter({"universe": "thornwood", "story": "night-ferry", "back": "builder"})
        await pilot.pause()
        await pilot.pause()
        after_scope = scr.query_one("#swscope", Select).value
        await open_tab(pilot, app, "t-genre")                  # (Genre words is worked out again, for the new story, when it is opened)
        after_genres = list(scr.gw_genres)
        return first, after_scope, after_genres
    first, scope, genres = run(script, {"universe": "thornwood", "story": "dry-well", "back": "builder"})
    assert first == ("dry-well", ["western", "noir"])
    assert scope == "night-ferry" and genres == ["fantasy"]


def test_entering_again_for_the_same_story_leaves_what_you_chose_alone(index, two_stories):
    async def script(app, pilot):
        scr = app.screen
        await open_tab(pilot, app, "t-genre")
        scr.gw_genres = ["horror"]                               # (picked by hand in the genre list)
        scr.enter({"universe": "thornwood", "story": "dry-well", "back": "builder"})
        await pilot.pause()
        return list(scr.gw_genres)
    assert run(script, {"universe": "thornwood", "story": "dry-well", "back": "builder"}) == ["horror"]
