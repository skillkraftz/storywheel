"""Leaving the Wheel with a kept story: the promotion message, the preview, and Past stories."""
import json

from textual.widgets import Input

from storywheel import store, tui, vault
from storywheel.sample import build_story
from conftest import make_engine, run_tui, screen_text


async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


async def keep_to(app, pilot, step):
    while app.session.step.key != step:
        await press(pilot, "k")


def flat(text):
    return " ".join(text.split())


def test_leaving_with_a_kept_story_shows_the_promotion_message_and_three_choices(home):
    async def script(app, pilot):
        await keep_to(app, pilot, "premise")
        await press(pilot, "Q")
        return type(app.screen).__name__, flat(screen_text(app))
    name, text = run_tui(store.new_story(), make_engine(home), script)
    assert name == "QuitScreen" and "Bringing this story into the Universe Builder" in text
    assert "New universe" in text and "Existing universe" in text and "Not now" in text and "Delete the draft" in text
    assert "where it grows into a" in text or "Universe Builder, where" in text


def test_a_story_with_nothing_kept_just_asks_keep_or_delete(home):
    async def script(app, pilot):
        await press(pilot, "Q")
        return flat(screen_text(app))
    text = run_tui(store.new_story(), make_engine(home), script)
    assert "Keep this story or delete it?" in text and "Universe Builder" not in text


def test_not_now_keeps_a_draft(home):
    story = store.new_story()
    async def script(app, pilot):
        await keep_to(app, pilot, "premise")
        await press(pilot, "Q", "k")
        return app.return_value, app.next
    message, nxt = run_tui(story, make_engine(home), script)
    assert "Resume with:  storywheel resume" in message and nxt is None
    assert "promoted" not in store.load(story["id"]) and vault.list_universes() == []


def test_new_universe_named_after_the_story_with_a_preview(home):
    story = store.new_story()
    async def script(app, pilot):
        await keep_to(app, pilot, "premise")
        await press(pilot, "Q", "n")
        box = app.screen.query_one(Input)
        title = store.title_of(app.session.story)
        assert type(app.screen).__name__ == "EditScreen" and box.value == title
        box.value = "Thornwood"
        await press(pilot, "enter")
        assert type(app.screen).__name__ == "PromotePreviewScreen"
        preview = flat(screen_text(app))
        assert vault.list_universes() == []                       # nothing written yet
        await press(pilot, "p")
        return app.return_value, app.next, preview
    message, nxt, preview = run_tui(story, make_engine(home), script)
    assert "New universe 'Thornwood'" in preview and "Create character" in preview and "Create place" in preview
    assert "Promoted into the universe 'Thornwood' as the story" in message
    assert message.index("PROTAGONIST") < message.index("Promoted into") < message.index("Resume with:")
    u = vault.get_universe("thornwood")
    assert u and len(u.stories()) == 1 and u.entities("character")
    assert nxt == ("builder", {"universe": "thornwood", "story": u.stories()[0].slug})
    assert store.load(story["id"])["promoted"] == {"universe": "thornwood", "story": u.stories()[0].slug}


def test_cancelling_the_preview_changes_nothing(home):
    story = store.new_story()
    async def script(app, pilot):
        await keep_to(app, pilot, "premise")
        await press(pilot, "Q", "n", "enter")
        await press(pilot, "escape")
        return type(app.screen).__name__, app.is_running
    assert run_tui(story, make_engine(home), script) == ("MainScreen", True)
    assert vault.list_universes() == [] and "promoted" not in store.load(story["id"]) if (home / "home" / "stories" / f"{story['id']}.json").exists() else True


def test_existing_universe_offers_merges_and_enter_switches_them(home):
    u = vault.create_universe("Existing")
    story = store.new_story()
    async def script(app, pilot):
        await keep_to(app, pilot, "premise")
        name = app.session.story["kept"]["protagonist"]["name"]
        u.new_entity("character", name, {"job": "keeper of nothing"})
        await press(pilot, "Q", "e")
        assert type(app.screen).__name__ == "PickUniverseScreen"
        await press(pilot, "enter")
        merged = flat(screen_text(app))
        lst = app.screen.query_one("#plan")
        idx = next(i for i in range(lst.option_count) if lst.get_option_at_index(i).id and
                   app.screen.plan.items[int(lst.get_option_at_index(i).id)].existing)
        lst.highlighted = idx
        await press(pilot, "enter")
        dup = flat(screen_text(app))
        await press(pilot, "enter")                               # back to merging
        await press(pilot, "p")
        return name, merged, dup, app.return_value
    name, merged, dup, message = run_tui(story, make_engine(home), script)
    assert f"Merge into the existing character '{name}'" in merged and "Yellow rows are same-name duplicates" in merged
    assert f"Create another character '{name}'" in dup
    assert "Merged into character" in message
    assert len([c for c in u.entities("character") if c.name == name]) == 1
    assert u.entity(vault.slugify(name)).fields["job"] == "keeper of nothing"


def test_no_existing_universe_falls_back_to_a_new_one(home):
    story = store.new_story()
    async def script(app, pilot):
        await keep_to(app, pilot, "premise")
        await press(pilot, "Q", "e")
        return type(app.screen).__name__
    assert run_tui(story, make_engine(home), script) == "EditScreen"


def test_delete_the_draft_from_the_promotion_message(home):
    story = store.new_story()
    async def script(app, pilot):
        await keep_to(app, pilot, "premise")
        await press(pilot, "Q", "d")
        return app.return_value
    assert "Deleted" in run_tui(story, make_engine(home), script)
    assert not (home / "home" / "stories" / f"{story['id']}.json").exists()


def saved_draft(home, seed, id_):
    d = build_story(make_engine(home, seed=seed), ["western"])
    d["id"] = id_
    d["step"] = 8
    store.save(d)
    return d


def test_past_stories_show_which_drafts_were_promoted_and_can_promote_later(home):
    a = saved_draft(home, 1, "20200101-000000")
    b = saved_draft(home, 2, "20200102-000000")
    async def script(app, pilot):
        before = screen_text(app)
        lst = app.main.stories_list
        ids = [lst.get_option_at_index(i).id for i in range(lst.option_count)]
        lst.focus(); await pilot.pause()
        lst.highlighted = ids.index(a["id"])
        await press(pilot, "P")                                   # the promotion message appears
        assert type(app.screen).__name__ == "QuitScreen"
        await press(pilot, "n", "enter", "p")                     # new universe, default name, promote
        after = screen_text(app)
        lst.focus(); await pilot.pause()
        await press(pilot, "P")                                   # already promoted: says so
        again = flat(screen_text(app))
        return before, after, again, type(app.screen).__name__
    before, after, again, screen = run_tui(store.new_story(), make_engine(home), script)
    assert "⇢" not in before and "⇢" in after
    assert "was already promoted to the universe" in again and screen == "MainScreen"
    assert store.load(a["id"])["promoted"]["universe"] and "promoted" not in store.load(b["id"])
    assert len(vault.list_universes()) == 1


def test_a_draft_with_nothing_kept_cannot_be_promoted_from_past_stories(home):
    d = store.new_story()
    d["id"] = "20200101-000001"
    d["kept"] = {}
    store.save_draft(d)
    async def script(app, pilot):
        lst = app.main.stories_list
        lst.focus(); await pilot.pause()
        lst.highlighted = 0
        await press(pilot, "P")
        return flat(screen_text(app))
    assert "nothing kept yet, so there is nothing to promote" in run_tui(store.new_story(), make_engine(home), script)


# --- a draft belongs to a universe (batch 9) -----------------------------------------------------------------------------------------

def test_choosing_which_universe_a_draft_belongs_to_ticks_it_and_saves_it(home):
    u = vault.create_universe("Thornwood", ["western"])
    story = store.new_story()
    async def script(app, pilot):
        before = str(app.screen.query_one("#uni-home").label).strip()
        await keep_to(app, pilot, "title")
        app.screen.choose_home()
        await pilot.pause()
        assert type(app.screen).__name__ == "ChoiceScreen"
        options = [str(app.screen.options[i][0]) for i in range(len(app.screen.options))]
        app.screen.dismiss("thornwood")
        await pilot.pause()
        return before, options, str(app.screen.query_one("#uni-home").label).strip(), app.session.story["universes"]
    before, options, after, ticked = run_tui(story, make_engine(home), script)
    assert before == "(not chosen)" and options == ["Not decided: ask me when I promote it", "Thornwood"] and after == "Thornwood" and ticked == ["thornwood"]
    assert store.load(story["id"])["home"] == "thornwood"


def test_a_draft_that_belongs_to_a_universe_goes_straight_to_its_preview_and_into_its_stories(home):
    u = vault.create_universe("Thornwood", ["western"])
    story = store.new_story()
    story["home"] = "thornwood"
    async def script(app, pilot):
        await keep_to(app, pilot, "premise")
        await press(pilot, "B")
        screen = type(app.screen).__name__
        text = flat(screen_text(app))
        await press(pilot, "p")
        return screen, text, app.return_value, app.next
    screen, text, message, nxt = run_tui(story, make_engine(home), script)
    assert screen == "PromotePreviewScreen" and "Thornwood" in text
    assert nxt[0] == "builder" and nxt[1]["universe"] == "thornwood" and nxt[1]["story"]
    assert len(vault.get_universe("thornwood").stories()) == 1 and len(vault.list_universes()) == 1


def test_the_quit_screen_offers_the_home_universe_first(home):
    vault.create_universe("Thornwood", ["western"])
    story = store.new_story()
    story["home"] = "thornwood"
    async def script(app, pilot):
        await keep_to(app, pilot, "premise")
        await press(pilot, "Q")
        text = flat(screen_text(app))
        await press(pilot, "p")
        return text, type(app.screen).__name__
    text, screen = run_tui(story, make_engine(home), script)
    assert "Into Thornwood (p)" in text and "Not now" in text and screen == "PromotePreviewScreen"


def test_without_a_home_the_choices_are_as_before(home):
    vault.create_universe("Thornwood", ["western"])
    async def script(app, pilot):
        await keep_to(app, pilot, "premise")
        await press(pilot, "Q")
        text = flat(screen_text(app))
        await press(pilot, "p")                                          # (p does nothing: there is no home)
        return text, type(app.screen).__name__
    text, screen = run_tui(store.new_story(), make_engine(home), script)
    assert "Into " not in text and screen == "QuitScreen"
