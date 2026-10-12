"""Batch 23 B2: look a word up from a Wheel card or a Builder field (l, and Ctrl+L in the write dialog), opening Words on its Lookup tab."""
from textual.widgets import Input, TabbedContent

from storywheel import store, vault
from conftest import make_engine, run_tui, screen_text
from test_builder import run_builder, press, world, card_index
from test_words import index, run as run_words  # noqa: F401  (index: the small dictionary fixture)


def test_words_in_gives_the_distinct_words_of_a_field():
    from storywheel.tui import words_in
    assert words_in("Sad and slow, sad") == ["Sad", "and", "slow"]
    assert words_in("O'Brien-Smith's old mill") == ["O'Brien-Smith's", "old", "mill"]
    assert words_in("42 — x") == []


# --- the Wheel -----------------------------------------------------------------------------------------------------

def test_l_on_a_one_word_field_opens_words_on_that_word(home):
    s = store.new_story()

    async def script(app, pilot):
        app.screen.session.edit_field("genre", "Noir")
        app.screen.after()
        await press(pilot, "l")
        return app.next
    nxt = run_tui(s, make_engine(home), script)
    assert nxt == ("words", {"universe": None, "handover": {"word": "Noir"}})


def test_l_on_a_several_word_field_asks_which_word(home):
    async def script(app, pilot):
        app.screen.session.edit_field("genre", "slow burn noir")
        app.screen.after()
        await press(pilot, "l")
        picker = type(app.screen).__name__
        text = " ".join(screen_text(app).split())
        await press(pilot, "down", "enter")
        return picker, text, app.next
    picker, text, nxt = run_tui(store.new_story(), make_engine(home), script)
    assert picker == "ChoiceScreen" and "Look up which word?" in text
    assert nxt[0] == "words" and nxt[1]["handover"] == {"word": "burn"}


def test_the_write_dialog_has_a_look_up_key_and_looks_up_what_is_typed(home):
    async def script(app, pilot):
        app.screen.session.edit_field("genre", "Noir")
        app.screen.after()
        await press(pilot, "e")
        dialog = type(app.screen).__name__
        text = " ".join(screen_text(app).split())
        app.screen.query_one(Input).value = "gloaming"
        await press(pilot, "ctrl+l")
        return dialog, text, app.next
    dialog, text, nxt = run_tui(store.new_story(), make_engine(home), script)
    assert dialog == "EditScreen" and "ctrl+l: look a word up" in text
    assert nxt[1]["handover"] == {"word": "gloaming"}


def test_l_on_an_empty_field_says_so(home):
    async def script(app, pilot):
        app.screen.session.cand["mood"] = ""
        app.screen.after()
        app.screen.card.highlighted = app.screen.session.field_names.index("mood")
        await press(pilot, "l")
        return app.next, " ".join(screen_text(app).split())
    nxt, text = run_tui(store.new_story(), make_engine(home), script)
    assert not nxt and "no word in that field" in text


# --- the Builder ---------------------------------------------------------------------------------------------------

def test_l_on_a_builder_field_opens_words_with_the_universe(home):
    u = world(home)
    u.new_entity("character", "Stacie", {"job": "lamplighter"})

    async def script(app, pilot):
        s = app.screen_ref
        s.card.focus()
        s.card.highlighted = card_index(app, "job")
        await press(pilot, "l")
        return app.next
    nxt = run_builder(home, script)
    assert nxt[0] == "words" and nxt[1]["universe"] == "thornwood" and nxt[1]["handover"] == {"word": "lamplighter"}


def test_ctrl_l_in_the_builders_write_dialog_looks_up_the_text(home):
    u = world(home)
    u.new_entity("character", "Stacie", {"job": "lamplighter"})

    async def script(app, pilot):
        s = app.screen_ref
        s.card.focus()
        s.card.highlighted = card_index(app, "job")
        await press(pilot, "e")
        await press(pilot, "ctrl+l")
        return app.next
    nxt = run_builder(home, script)
    assert nxt[1]["handover"] == {"word": "lamplighter"}


# --- Words -----------------------------------------------------------------------------------------------------------

def test_words_opens_on_the_lookup_tab_with_the_word_and_use_in_writer_is_off(index, home):
    vault.create_universe("Thornwood", ["western"])

    async def script(app, pilot):
        await pilot.pause()
        scr = app.screen
        return scr.query_one(TabbedContent).active, scr.query_one("#word", Input).value, scr.query_one("#use").disabled
    tab, word, use_off = run_words(script, {"universe": "thornwood", "back": "wheel", "handover": {"word": "dog"}}, back="wheel")
    assert tab == "t-lookup" and word == "dog" and use_off
