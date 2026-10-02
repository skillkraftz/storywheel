"""'Send to Builder' is easy to find: a button and key in the Wheel, F2's offer, and Past stories."""
from textual.widgets import Button, Input

from storywheel import store, vault
from storywheel.sample import build_story
from conftest import make_engine, run_tui, screen_text


async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


def flat(text):
    return " ".join(text.split())


def test_the_button_is_there_but_disabled_until_something_is_kept(home):
    async def script(app, pilot):
        b = app.main.query_one("#btn-send", Button)
        before = (b.disabled, str(b.label), "Send to Builder" in flat(screen_text(app)))
        await press(pilot, "k")
        return before, (b.disabled, str(b.label))
    before, after = run_tui(store.new_story(), make_engine(home), script)
    assert before == (True, "Send to Builder", True) and after == (False, "Send to Builder")


def test_pressing_B_with_nothing_kept_says_why(home):
    async def script(app, pilot):
        await press(pilot, "B")
        return flat(screen_text(app)), type(app.screen).__name__
    text, screen = run_tui(store.new_story(), make_engine(home), script)
    assert "Nothing is kept yet" in text and screen == "MainScreen"


def test_the_button_sends_the_draft_through_the_same_steps_as_leaving(home):
    story = store.new_story()
    async def script(app, pilot):
        await press(pilot, "k", "k", "k", "k", "k")
        await pilot.click("#btn-send"); await pilot.pause()
        assert type(app.screen).__name__ == "ChoiceScreen"
        await press(pilot, "enter")                                   # a new universe
        assert type(app.screen).__name__ == "EditScreen"
        app.screen.query_one(Input).value = "Thornwood"
        await press(pilot, "enter")
        assert type(app.screen).__name__ == "PromotePreviewScreen"
        await press(pilot, "p")
        return app.next, app.return_value
    nxt, message = run_tui(story, make_engine(home), script)
    assert nxt[0] == "builder" and nxt[1]["universe"] == "thornwood"
    assert "Promoted into the universe 'Thornwood'" in message
    assert store.load(story["id"])["promoted"]["universe"] == "thornwood"


def test_the_key_B_does_the_same_and_an_existing_universe_can_be_chosen(home):
    vault.create_universe("Old World")
    story = store.new_story()
    async def script(app, pilot):
        await press(pilot, "k", "k", "k", "k", "k")
        await press(pilot, "B", "down", "enter")                      # an existing universe
        assert type(app.screen).__name__ == "PickUniverseScreen"
        await press(pilot, "enter", "p")
        return app.next
    nxt = run_tui(story, make_engine(home), script)
    assert nxt[1]["universe"] == "old-world"


def test_after_sending_the_button_opens_the_story_in_the_builder(home):
    d = build_story(make_engine(home, seed=1), ["western"])
    d["id"], d["step"] = "20200101-000000", 8
    d["promoted"] = {"universe": "thornwood", "story": "tale"}
    store.save(d)
    async def script(app, pilot):
        b = app.main.query_one("#btn-send", Button)
        label = str(b.label)
        await press(pilot, "B")
        return label, app.next
    story = store.load(d["id"])
    label, nxt = run_tui(story, make_engine(home), script)
    assert label == "Open in Builder" and nxt == ("builder", {"universe": "thornwood", "story": "tale"})


def test_F2_from_a_draft_with_kept_steps_offers_to_send_it_first(home):
    story = store.new_story()
    async def script(app, pilot):
        await press(pilot, "k")
        await press(pilot, "f2")
        asked = flat(screen_text(app))
        await press(pilot, "escape")
        stayed = (type(app.screen).__name__, app.next)
        await press(pilot, "f2", "enter")                             # "send it first"
        sending = type(app.screen).__name__
        return asked, stayed, sending
    asked, stayed, sending = run_tui(story, make_engine(home), script)
    assert "kept steps that are not in the Builder yet" in asked and "Send it to the Builder first" in asked
    assert stayed == ("MainScreen", None) and sending == "ChoiceScreen"


def test_F2_goes_straight_there_when_there_is_nothing_to_send(home):
    async def script(app, pilot):
        await press(pilot, "f2")
        return type(app.screen).__name__, app.next
    assert run_tui(store.new_story(), make_engine(home), script) == ("MainScreen", ("builder", {"universe": None}))


def test_F2_goes_straight_there_for_a_draft_already_sent(home):
    story = store.new_story()
    story["kept"] = {"genre": {"genre": "western", "mood": "cozy"}}
    story["promoted"] = {"universe": "x", "story": "y"}
    async def script(app, pilot):
        await press(pilot, "f2")
        return app.next
    assert run_tui(story, make_engine(home), script)[0] == "builder"


def test_past_stories_have_a_send_button_that_starts_the_same_flow(home):
    d = build_story(make_engine(home, seed=2), ["western"])
    d["id"], d["step"] = "20200101-000001", 8
    store.save(d)
    async def script(app, pilot):
        text = flat(screen_text(app))
        lst = app.main.stories_list
        lst.highlighted = [lst.get_option_at_index(i).id for i in range(lst.option_count)].index(d["id"])
        await pilot.click("#st-promote"); await pilot.pause()
        return text, type(app.screen).__name__
    text, screen = run_tui(store.new_story(), make_engine(home), script)
    assert "Send" in text
    assert screen == "QuitScreen"
