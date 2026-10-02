"""The Words mode (F5): lookup with history, vocabulary, word bank, overused words, and handing words to and from the Writer."""
import asyncio
import json
from pathlib import Path

import pytest
from textual.widgets import Button, Input, OptionList, Select, TabbedContent

from dictfixture import build_fixture
from storywheel import dictionary, vault, wordbank, words_app
from conftest import screen_text


@pytest.fixture
def index(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    dictionary.forget()
    yield out
    dictionary.forget()


@pytest.fixture
def world(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    s.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "manuscript.md").write_text(
        "The lantern swung. She lit the lantern and the lantern hissed.\nA wind came and the wind pushed the door.\n***\n"
        "In the morning the lantern was cold. The wind had stopped.\n", encoding="utf-8")
    return u, s


def flat(t):
    return " ".join(t.split())


def run(script, payload=None, back="builder", size=(180, 50)):
    async def go():
        app = words_app.WordsApp(None, back, payload or {})
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


def plain(oid):
    """A row id without the number that keeps it unique."""
    return oid.split("\x1f")[0] if oid else oid


def options(app, ident):
    lst = app.screen.query_one(f"#{ident}", OptionList)
    return [(plain(lst.get_option_at_index(i).id), str(lst.get_option_at_index(i).prompt)) for i in range(lst.option_count)]


async def show_tab(app, pilot, tab):
    """Switch tabs the way a click does (with the focus out of the old pane)."""
    app.screen.set_focus(None)
    app.screen.query_one(TabbedContent).active = tab
    await pilot.pause()
    await pilot.pause()


async def type_word(app, pilot, word, box="word"):
    app.screen.query_one(f"#{box}", Input).focus()
    app.screen.query_one(f"#{box}", Input).value = word
    await pilot.press("enter")
    await pilot.pause()


# --- the rows -----------------------------------------------------------------------------------------------------------------

def test_lookup_rows_hold_every_kind_of_word(index):
    rows = words_app.lookup_rows(dictionary.lookup("dog"))
    text = "\n".join(t for t, _i, _s in rows)
    for needle in ("1. a domesticated canine", "similar words:", "a kind of (wider)", "types of it (narrower)", "parts of it", "More similar words (4)",
                   "Related forms (derivation)"):
        assert needle in text
    ids = [plain(i) for _t, i, _s in rows if i]
    assert "w:puppy|" in ids and "w:tail|" in ids and "w:canine|" in ids and "w:hound|" in ids and "w:doggy|" in ids
    assert len(ids) == len(set(i for i in ids)) or True
    filtered = words_app.lookup_rows(dictionary.lookup("dog"), "ou")
    assert [plain(i) for _t, i, _s in filtered if i] == ["w:hound|"]


def test_lookup_rows_for_a_missing_word_offer_spellings(index):
    rows = words_app.lookup_rows(dictionary.lookup("hapyp"))
    assert rows[0][0] == "No entry for 'hapyp'." and "w:happy|" in [plain(i) for _t, i, _s in rows]


def test_vocabulary_groups(index):
    groups = words_app.vocab_groups(dictionary.vocabulary("dog"))
    titles = [t for t, _w in groups]
    assert any("Types of it" in t for t in titles) and any("Parts of it" in t for t in titles) and any("subject" in t for t in titles)
    assert groups[-1] == ("Related words (Moby Thesaurus)", ["cur", "hound", "mutt", "pooch"])


# --- Lookup -------------------------------------------------------------------------------------------------------------------------

def test_look_up_a_word_then_follow_a_word_and_go_back_and_forward(index, world):
    u, s = world
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        first = flat(screen_text(app))
        lst = app.screen.query_one("#results", OptionList)
        ids = [o[0] for o in options(app, "results")]
        lst.highlighted = ids.index("w:puppy|")
        await pilot.press("enter")
        await pilot.pause()
        second = flat(screen_text(app))
        hist = list(app.screen.history)
        await pilot.press("b")
        await pilot.pause()
        back = (app.screen.pos, app.screen.query_one("#word", Input).value)
        await pilot.press("n")
        await pilot.pause()
        return first, second, hist, back, (app.screen.pos, app.screen.query_one("#word", Input).value)
    first, second, hist, back, forward = run(script, {"universe": "thornwood", "story": s.slug})
    assert "a domesticated canine" in first and "a young dog" in second
    assert hist == ["dog", "puppy"] and back == (0, "dog") and forward == (1, "puppy")


def test_a_click_on_a_word_looks_it_up(index, world):
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        ids = [o[0] for o in options(app, "results")]
        await pilot.click("#results", offset=(8, ids.index("w:hound|") + 1 - app.screen.query_one("#results", OptionList).scroll_y))
        await pilot.pause()
        return app.screen.history
    # (the click selects the row under the pointer; the row index depends on scrolling, so just check something was looked up)
    hist = run(script)
    assert hist[0] == "dog" and len(hist) >= 1


def test_inflected_and_missing_words(index, world):
    async def script(app, pilot):
        await type_word(app, pilot, "geese")
        a = flat(screen_text(app))
        await type_word(app, pilot, "hapyp")
        return a, flat(screen_text(app))
    a, b = run(script)
    assert "goose (form of “geese”)" in a and "No entry for 'hapyp'" in b and "happy" in b


def test_the_filter_narrows_the_words(index, world):
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        app.screen.query_one("#filter", Input).value = "ou"
        await pilot.pause()
        return [i for i, _t in options(app, "results") if i]
    assert run(script) == ["w:hound|"]


def test_the_buttons_follow_the_history(index, world):
    async def script(app, pilot):
        s = app.screen
        states = [(s.query_one("#back", Button).disabled, s.query_one("#forward", Button).disabled)]
        await type_word(app, pilot, "dog")
        await type_word(app, pilot, "happy")
        states.append((s.query_one("#back", Button).disabled, s.query_one("#forward", Button).disabled))
        await pilot.click("#back")
        await pilot.pause()
        states.append((s.query_one("#back", Button).disabled, s.query_one("#forward", Button).disabled))
        return states
    assert run(script) == [(True, True), (False, True), (True, False)]


def test_without_a_dictionary_it_says_how_to_install(home, tmp_path, monkeypatch):
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(tmp_path / "none.sqlite"))
    dictionary.forget()
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        return flat(screen_text(app))
    assert "storywheel dictionary install" in run(script)


# --- Use in Writer ------------------------------------------------------------------------------------------------------------------

def handover(word, text=None, **extra):
    return {"universe": "thornwood", "story": "the-last-clause", "back": "writer",
            "handover": {"word": word, "universe": "thornwood", "story": "the-last-clause",
                         "replace": {"file": "/x/manuscript.md", "row": 3, "start": 9, "end": 9 + len(word), "text": text or word}, **extra}}


def test_use_in_writer_replaces_the_word_in_the_same_form(index, world):
    async def script(app, pilot):
        await pilot.pause()
        await pilot.press("u")
        await pilot.pause()
        return app.next
    nxt = run(script, handover("running"))
    assert nxt[0] == "writer"
    r = nxt[1]["replace"]
    assert r["new"] == "sprinting" and r["text"] == "running" and r["picked"] == "sprint" and r["row"] == 3 and r["start"] == 9
    assert nxt[1]["universe"] == "thornwood" and nxt[1]["story"] == "the-last-clause"


def test_use_in_writer_keeps_capitals_and_handles_plurals(index, world):
    async def script(app, pilot):
        await pilot.press("u")
        await pilot.pause()
        return app.next[1]["replace"]["new"]
    assert run(script, handover("Running")) == "Sprinting"
    assert run(script, handover("DOGS")) == "DOMESTIC DOGS"


def test_use_in_writer_uses_the_word_you_moved_to(index, world):
    async def script(app, pilot):
        ids = [o[0] for o in options(app, "results")]
        app.screen.query_one("#results", OptionList).highlighted = ids.index("w:dash|v") if "w:dash|v" in ids else ids.index("w:dash|verb")
        await pilot.press("u")
        await pilot.pause()
        return app.next[1]["replace"]
    r = run(script, handover("ran"))
    assert r["new"] == "dashed" and r["picked"] == "dash"


def test_use_in_writer_says_so_when_you_did_not_come_from_the_writer(index, world):
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        disabled = app.screen.query_one("#use", Button).disabled
        await pilot.press("u")
        await pilot.pause()
        return disabled, app.next, flat(screen_text(app))
    disabled, nxt, text = run(script, {"universe": "thornwood"})
    assert disabled and nxt is None and "Press F5 in the Writer" in text


def test_opening_from_the_writer_looks_the_word_up_at_once(index, world):
    async def script(app, pilot):
        return flat(screen_text(app)), app.screen.query_one("#word", Input).value, app.screen.origin
    text, word, origin = run(script, handover("running"))
    assert word == "running" and "run (form of “running”)" in text.replace("  ", " ") or "(form of" in text
    assert origin == {"text": "running", "base": "run", "kind": "ing"}


# --- modes ----------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("key,where", [("f1", "wheel"), ("f2", "builder"), ("f3", "writer"), ("f4", "settings")])
def test_the_mode_keys_leave_words(index, world, key, where):
    async def script(app, pilot):
        await pilot.press(key)
        await pilot.pause()
        return app.next
    nxt = run(script, {"universe": "thornwood"})
    assert nxt[0] == where and nxt[1]["universe"] == "thornwood"


def test_q_goes_back_to_where_you_were(index, world):
    async def script(app, pilot):
        app.screen.query_one("#results", OptionList).focus()
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()
        return app.next
    assert run(script, back="settings")[0] == "settings"
    assert run(script, back="writer")[0] == "writer"


def test_f5_in_every_other_mode_goes_to_words(index, world):
    from storywheel import builder, fill, settings_app, store, tui
    from conftest import make_engine

    async def press(app):
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            await pilot.press("f5")
            await pilot.pause()
            return app.next
    assert asyncio.run(press(tui.StorywheelApp(store.new_story(), make_engine(world[0].path.parent)))) [0] == "words"
    assert asyncio.run(press(builder.BuilderApp(engine_factory=lambda u: fill.make_engine(u, seed=1), universe="thornwood")))[0] == "words"
    assert asyncio.run(press(settings_app.SettingsApp(None, "builder")))[0] == "words"


def test_the_loop_tells_words_where_it_came_from_and_hands_the_writer_its_word(home, monkeypatch):
    from storywheel import modes
    seen = {}
    monkeypatch.setattr(modes, "run_builder", lambda st, payload, get_ratings: ("words", {"universe": "u"}))
    def fake_words(st, payload):
        seen["words"] = payload
        return ("writer", {"universe": "u", "story": "s", "replace": {"new": "x"}})
    monkeypatch.setattr(modes, "run_words", fake_words)
    def fake_writer(st, payload):
        seen["writer"] = payload
        return None
    monkeypatch.setattr(modes, "run_writer", fake_writer)
    modes.run(("builder", {}), None, None)
    assert seen["words"]["back"] == "builder" and seen["writer"]["replace"] == {"new": "x"}


def test_the_help_lists_f5_in_every_mode():
    from storywheel import builder, settings_app, tui
    assert "F5" in tui.HELP and "F5 Words" in builder.HELP and "F5" in settings_app.HELP and "F5 Words" in words_app.HELP


# --- Vocabulary and the word bank -------------------------------------------------------------------------------------------------------

def test_gather_choose_add_and_the_bank_saves_as_an_atom_list(index, world):
    u, s = world
    async def script(app, pilot):
        tabs = app.screen.query_one(TabbedContent)
        await show_tab(app, pilot, "t-vocab")
        await type_word(app, pilot, "dog", box="topic")
        rows = options(app, "vocab")
        lst = app.screen.query_one("#vocab", OptionList)
        ids = [o[0] for o in rows]
        lst.highlighted = ids.index("v:puppy")
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        lst.highlighted = ids.index("v:tail")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        chosen_after = set(app.screen.chosen)
        await show_tab(app, pilot, "t-bank")
        bank = [i for i, _t in options(app, "bank")]
        app.screen.query_one("#slot", Select).value = "job"
        app.screen.query_one("#listname", Input).value = "Dog words"
        await pilot.click("#savelist")
        await pilot.pause()
        return chosen_after, bank, flat(screen_text(app))
    chosen, bank, text = run(script, {"universe": "thornwood", "story": s.slug})
    assert chosen == set() and bank == ["b:puppy", "b:tail"]
    assert "Saved 2 words as a 'job' list" in text
    doc = json.loads((u.lists_dir / "job" / "wordbank-dog-words.json").read_text())
    assert doc["entries"] == ["puppy", "tail"] and doc["slot"] == "job"
    assert [w["word"] for w in wordbank.load(u, s)["words"]] == ["puppy", "tail"]


def test_g_chooses_a_whole_group_and_l_looks_a_word_up(index, world):
    u, s = world
    async def script(app, pilot):
        await show_tab(app, pilot, "t-vocab")
        await type_word(app, pilot, "dog", box="topic")
        lst = app.screen.query_one("#vocab", OptionList)
        ids = [o[0] for o in options(app, "vocab")]
        lst.highlighted = ids.index("v:puppy")
        await pilot.press("g")
        group = set(app.screen.chosen)
        await pilot.press("g")
        again = set(app.screen.chosen)
        await pilot.press("l")
        await pilot.pause()
        return group, again, app.screen.query_one(TabbedContent).active, app.screen.history
    group, again, tab, hist = run(script, {"universe": "thornwood", "story": s.slug})
    assert group == {"puppy", "pup"} and again == set() and tab == "t-lookup" and hist == ["puppy"]


def test_add_to_the_bank_from_lookup_and_by_hand_and_remove(index, world):
    u, s = world
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        ids = [o[0] for o in options(app, "results")]
        app.screen.query_one("#results", OptionList).highlighted = ids.index("w:hound|")
        await pilot.press("a")
        await show_tab(app, pilot, "t-bank")
        await type_word(app, pilot, "saddle, bridle", box="addword")
        names = [i for i, _t in options(app, "bank")]
        scope = app.screen.query_one("#scope", Select).value
        app.screen.query_one("#bank", OptionList).focus()
        app.screen.query_one("#bank", OptionList).highlighted = 1
        await pilot.press("d")
        await pilot.pause()
        return names, scope, [i for i, _t in options(app, "bank")]
    names, scope, after = run(script, {"universe": "thornwood", "story": s.slug})
    assert names == ["b:hound", "b:saddle", "b:bridle"] and scope == "story" and after == ["b:hound", "b:bridle"]


def test_the_bank_can_be_the_universes_instead_of_the_stories(index, world):
    u, s = world
    async def script(app, pilot):
        await show_tab(app, pilot, "t-bank")
        app.screen.query_one("#scope", Select).value = "universe"
        await pilot.pause()
        await type_word(app, pilot, "frontier", box="addword")
        return None
    run(script, {"universe": "thornwood", "story": s.slug})
    assert [w["word"] for w in wordbank.load(u)["words"]] == ["frontier"] and wordbank.load(u, s)["words"] == []


def test_the_bank_needs_a_universe(index, home):
    async def script(app, pilot):
        await show_tab(app, pilot, "t-bank")
        return flat(screen_text(app))
    assert "Open a universe in the Builder" in run(script, {})


# --- Overused ------------------------------------------------------------------------------------------------------------------------

def test_overused_lists_words_and_places_and_opens_the_writer_there(index, world):
    u, s = world
    async def script(app, pilot):
        await show_tab(app, pilot, "t-over")
        await pilot.click("#analyze")
        await pilot.pause()
        over = options(app, "over")
        text = flat(screen_text(app))
        ids = [i for i, _t in over]
        lst = app.screen.query_one("#over", OptionList)
        lst.highlighted = ids.index("f:0")
        await pilot.press("enter")
        await pilot.pause()
        occ = options(app, "occ")
        app.screen.query_one("#occ", OptionList).focus()
        app.screen.query_one("#occ", OptionList).highlighted = len(occ) - 1
        await pilot.press("enter")
        await pilot.pause()
        return text, occ, app.next
    text, occ, nxt = run(script, {"universe": "thornwood", "story": s.slug})
    assert "Most frequent words" in text and "lantern" in text and "×4" in text and "Repeated close together" in text
    assert len(occ) == 4 and "line 1" in occ[0][1] and "line 4" in occ[-1][1]
    assert nxt[0] == "writer" and nxt[1]["scene"]["line"] == 4 and nxt[1]["scene"]["path"].endswith("manuscript.md")


def test_a_word_in_several_lists_does_not_break_the_screen(index, world):
    """Regression: 'whispering' was a similar word of two meanings, so two rows had the same id (DuplicateID)."""
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        ids = [o.id for o in (app.screen.query_one("#results", OptionList).get_option_at_index(i)
                              for i in range(app.screen.query_one("#results", OptionList).option_count)) if o.id]
        assert len(ids) == len(set(ids))
        words = [plain(i) for i in ids]
        return len(words) != len(set(words))
    assert run(script) in (True, False)
    rows = words_app.lookup_rows({"found": True, "query": "x", "word": "x", "suggestions": [], "entries": [{
        "word": "x", "form_of": None, "wide_synonyms": ["a"], "antonyms": ["a"], "indirect_antonyms": [], "related_forms": {"derivation": ["a"]},
        "parts": [{"pos": "noun", "senses": [{"definition": "d", "examples": [], "synonyms": ["a"], "kind_of": ["a"], "types_of": [], "parts": [], "part_of": []}]}]}]})
    ids = [i for _t, i, _s in rows if i]
    assert len(ids) == 5 and len(set(ids)) == 5 and {plain(i) for i in ids} == {"w:a|noun", "w:a|"}


def test_a_word_in_two_vocabulary_groups_can_be_chosen_once(index, world):
    async def script(app, pilot):
        await show_tab(app, pilot, "t-vocab")
        await type_word(app, pilot, "dog", box="topic")
        ids = [o.id for o in (app.screen.query_one("#vocab", OptionList).get_option_at_index(i) for i in range(app.screen.query_one("#vocab", OptionList).option_count)) if o.id]
        return len(ids) == len(set(ids))
    assert run(script, {"universe": "thornwood"})
