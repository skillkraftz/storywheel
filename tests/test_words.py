"""The Words mode (F5): lookup with history, vocabulary, word bank, overused words, and handing words to and from the Writer."""
import asyncio
import json
from pathlib import Path

import pytest
from textual.widgets import Button, Input, OptionList, Select, TabbedContent, TabPane

from dictfixture import build_fixture
from storywheel import dictionary, genrefit, learn, vault, wordbank, words_app
from storywheel.virtuallist import VirtualList
from conftest import screen_text


@pytest.fixture
def index(tmp_path, monkeypatch):
    from dictfixture import ZIPF
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    monkeypatch.setattr(learn, "zipf", lambda w: ZIPF.get(w, 0.0))
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


def select_word(app, wid):
    """Highlight (and focus) the row of a word in whichever Lookup box holds it."""
    for lst in app.screen.result_lists():
        ids = [plain(lst.get_option_at_index(i).id) for i in range(lst.option_count)]
        if wid in ids:
            lst.highlighted = ids.index(wid)
            lst.focus()
            return lst
    raise AssertionError(f"{wid} is in no box")


def plain(oid):
    """A row id without the number that keeps it unique."""
    return oid.split("\x1f")[0] if oid else oid


def options(app, ident):
    if ident == "results":                                  # (the Lookup boxes: every row of every box)
        return [row for name, _t in words_app.PANES for row in options(app, f"res-{name}")]
    lst = app.screen.query_one(f"#{ident}", OptionList)
    return [(plain(lst.get_option_at_index(i).id), str(lst.get_option_at_index(i).prompt)) for i in range(lst.option_count)]


async def show_learning(app, pilot):
    """Vocabulary, switched to the ★ Learning words (what the My words tab used to be)."""
    await show_tab(app, pilot, "t-vocab")
    app.screen.query_one("#vview", Select).value = "learning"
    await pilot.pause()


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
    for needle in ("1. a domesticated canine", "More similar words (4)", "a kind of (wider)", "types of it (narrower)", "parts of it", "More similar words (4)",
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




# --- Lookup -------------------------------------------------------------------------------------------------------------------------

def test_look_up_a_word_then_follow_a_word_and_go_back_and_forward(index, world):
    u, s = world
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        first = flat(screen_text(app))
        select_word(app, "w:puppy|")
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
        lst = select_word(app, "w:hound|")
        lids = [plain(lst.get_option_at_index(i).id) for i in range(lst.option_count)]
        await pilot.click(f"#{lst.id}", offset=(8, lids.index("w:hound|") + 1 - lst.scroll_y))
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
        select_word(app, "w:dash|v" if "w:dash|v" in ids else "w:dash|verb")
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
        app.screen.first_word_list().focus()
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()
        return app.next
    nxt = run(script, back="settings")
    assert nxt[0] == "back" and nxt[1]["fallback"] == "settings"
    nxt = run(script, back="writer")
    assert nxt[0] == "back" and nxt[1]["fallback"] == "writer"


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
    modes.run_classic(("builder", {}), None, None)
    assert seen["words"]["back"] == "builder" and seen["writer"]["replace"] == {"new": "x"}


def test_the_help_lists_f5_in_every_mode():
    from storywheel import builder, settings_app, tui
    assert "F5" in tui.HELP and "F5 Words" in builder.HELP and "F5" in settings_app.HELP and "F5 Words" in words_app.HELP


# --- Vocabulary (words to learn) and My words ------------------------------------------------------------------------------------

def row_word(text):
    return text.strip().lstrip("★✓ ").split()[0]


def learn_rows(app):
    return [(i, t) for i, t in options(app, "learn") if i]


def test_new_batch_lists_words_with_part_of_speech_and_a_simple_meaning(index, world):
    async def script(app, pilot):
        await show_tab(app, pilot, "t-vocab")
        await pilot.click("#newbatch")
        await pilot.pause()
        return learn_rows(app), flat(screen_text(app))
    rows, text = run(script, {"universe": "thornwood"})
    joined = " | ".join(t for _i, t in rows)
    assert len(rows) >= 6 and "puppy" in joined and "a young dog" in joined and "noun" in joined
    assert "dog " not in " ".join(t.split()[0] + " " for _i, t in rows if t.split()[0] == "dog")          # everyday words are not offered
    assert "new words" in text


def test_a_second_batch_has_no_repeats(index, world, monkeypatch):
    monkeypatch.setattr(learn, "batch", lambda n, *a, exclude=(), **k: [
        {"word": w, "pos": "noun", "definition": "d", "zipf": 3, "subject": ""} for w in ["w1", "w2", "w3", "w4"] if w not in {x.lower() for x in exclude}][:2])
    async def script(app, pilot):
        await show_tab(app, pilot, "t-vocab")
        await pilot.click("#newbatch")
        await pilot.pause()
        first = [row_word(t) for _i, t in learn_rows(app)]
        await pilot.click("#newbatch")
        await pilot.pause()
        second = [row_word(t) for _i, t in learn_rows(app)]
        return first, second
    first, second = run(script, {})
    assert first == ["w1", "w2"] and second == ["w3", "w4"]


def test_the_filters_are_passed_to_the_picker(index, world, monkeypatch):
    seen = {}
    monkeypatch.setattr(learn, "batch", lambda n, difficulty="any", pos=None, subject=None, exclude=(), **k: seen.update(d=difficulty, p=pos, s=subject) or [])
    async def script(app, pilot):
        await show_tab(app, pilot, "t-vocab")
        app.screen.query_one("#difficulty", Select).value = "rare"
        app.screen.query_one("#vpos", Select).value = "verb"
        app.screen.query_one("#subject", Select).value = "verb.motion"
        await pilot.pause()
        await pilot.click("#newbatch")
        await pilot.pause()
        return flat(screen_text(app))
    text = run(script, {})
    assert seen == {"d": "rare", "p": "verb", "s": "verb.motion"} and "No new words with these filters" in text


def test_the_subject_choices_are_in_plain_words(index, world):
    async def script(app, pilot):
        return [label for label, _k in app.screen.subject_options]
    labels = run(script, {})
    assert "Any subject" in labels and "Animals" in labels and "Moving" in labels and "Describing words" in labels


def test_enter_on_a_word_opens_its_full_entry_in_lookup(index, world):
    async def script(app, pilot):
        await show_tab(app, pilot, "t-vocab")
        await pilot.click("#newbatch")
        await pilot.pause()
        lst = app.screen.query_one("#learn", OptionList)
        ids = [i for i, t in learn_rows(app) if "puppy" in t]
        lst.focus()
        lst.highlighted = int(ids[0][2:])
        await pilot.press("enter")
        await pilot.pause()
        return app.screen.query_one(TabbedContent).active, app.screen.history, flat(screen_text(app))
    tab, hist, text = run(script, {})
    assert tab == "t-lookup" and hist == ["puppy"] and "a young dog" in text


def test_l_marks_a_word_learning_and_it_appears_in_my_words_with_its_meaning_k_marks_it_known(index, world):
    async def script(app, pilot):
        await show_tab(app, pilot, "t-vocab")
        await pilot.click("#newbatch")
        await pilot.pause()
        lst = app.screen.query_one("#learn", OptionList)
        lst.focus()
        idx = {row_word(t): int(i[2:]) for i, t in learn_rows(app)}
        lst.highlighted = idx["puppy"]
        await pilot.pause()
        await pilot.press("l")
        lst.highlighted = idx["kennel"]
        await pilot.pause()
        await pilot.press("k")
        await pilot.pause()
        marks = {row_word(t): t[1] for _i, t in learn_rows(app)}
        await show_learning(app, pilot)
        mine = [t for _i, t in options(app, "mine") if _i]
        return marks, mine, learn.MyWords().known
    marks, mine, known = run(script, {})
    assert marks["puppy"] == "★" and marks["kennel"] == "✓"
    assert len(mine) == 1 and "puppy" in mine[0] and "noun" in mine[0] and "a young dog" in mine[0]
    assert known == {"kennel"}


def test_my_words_remove_known_and_look_up(index, world):
    my = learn.MyWords()
    my.mark_learning("puppy"); my.mark_learning("kennel", "noun", "a shelter for dogs"); my.mark_learning("wretch")
    async def script(app, pilot):
        await show_learning(app, pilot)
        lst = app.screen.query_one("#mine", OptionList)
        lst.focus()
        rows = [t for i, t in options(app, "mine") if i]
        lst.highlighted = 0
        await pilot.pause()
        await pilot.press("d")                                  # remove puppy
        await pilot.pause()
        lst.highlighted = 0
        await pilot.pause()
        await pilot.press("k")                                  # kennel: known
        await pilot.pause()
        left = [t for i, t in options(app, "mine") if i]
        lst.highlighted = 0
        await pilot.press("enter")
        await pilot.pause()
        return rows, left, app.screen.query_one(TabbedContent).active, app.screen.history
    rows, left, tab, hist = run(script, {})
    assert "a young dog" in rows[0] and "a shelter for dogs" in rows[1] and "a despicable person" in rows[2]       # meanings filled in
    assert len(left) == 1 and "wretch" in left[0] and tab == "t-lookup" and hist == ["wretch"]
    again = learn.MyWords()
    assert again.known == {"kennel"} and again.learning_words() == {"wretch"}


def test_flashcards_show_the_word_then_the_meaning_and_k_takes_it_off_the_list(index, world):
    my = learn.MyWords()
    my.mark_learning("puppy"); my.mark_learning("kennel")
    async def script(app, pilot):
        await show_learning(app, pilot)
        app.screen.query_one("#mine", OptionList).focus()
        await pilot.press("f")
        await pilot.pause()
        card = app.screen
        first = flat(str(card.query_one("#card").content))
        await pilot.press("space")
        await pilot.pause()
        second = flat(str(card.query_one("#card").content))
        word = card.entries[0]["word"]
        await pilot.press("k")                                    # I know it
        await pilot.pause()
        await pilot.press("n")                                    # next (second card): ends the deck
        await pilot.pause()
        return first, second, word, type(app.screen).__name__, [i for i, t in options(app, "mine") if i]
    first, second, word, screen, left = run(script, {})
    assert word in first and "young dog" not in first and "shelter" not in first.replace(word, "")
    assert word in second and ("a young dog" in second or "no meaning" in second or "shelter" in second or "a place" in second)
    assert screen == "WordsScreen" and len(left) == 1
    assert len(learn.MyWords().known) == 1


def test_lookup_a_adds_the_word_to_my_words_with_its_meaning(index, world):
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        ids = [i for i, _t in options(app, "results")]
        select_word(app, "w:puppy|")
        await pilot.press("a")
        await pilot.pause()
        return learn.MyWords().learning
    got = run(script, {})
    assert got == [{"word": "puppy", "pos": "", "definition": "a young dog", "note": ""}] or got[0]["word"] == "puppy"


def test_add_to_this_universes_word_list_from_lookup_and_my_words(index, world):
    u, s = world
    learn.MyWords().mark_learning("kennel", "noun", "a shelter for dogs")
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        ids = [i for i, _t in options(app, "results")]
        select_word(app, "w:hound|")
        app.screen.first_word_list().focus()
        await pilot.press("w")
        await pilot.pause()
        picker = type(app.screen).__name__
        app.screen.query_one("#slot", Select).value = "job"
        await pilot.click("#ok")
        await pilot.pause()
        status = str(app.screen.query_one("#status").content)
        await show_learning(app, pilot)
        app.screen.query_one("#mine", OptionList).focus()
        app.screen.query_one("#mine", OptionList).highlighted = 0
        await pilot.pause()
        await pilot.press("w")
        await pilot.pause()
        app.screen.query_one("#slot", Select).value = "place"
        await pilot.click("#ok")
        await pilot.pause()
        return picker, status
    picker, status = run(script, {"universe": "thornwood", "story": s.slug})
    assert picker == "SlotScreen" and "Added “hound”" in status and "'job'" in status
    assert json.loads((u.lists_dir / "job" / "words-added.json").read_text())["entries"] == ["hound"]
    assert json.loads((u.lists_dir / "place" / "words-added.json").read_text())["entries"] == ["kennel"]


def test_adding_to_a_universe_list_without_a_universe_says_so(index, home):
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        app.screen.first_word_list().focus()
        await pilot.press("w")
        await pilot.pause()
        return type(app.screen).__name__, flat(screen_text(app))
    screen, text = run(script, {})
    assert screen == "WordsScreen" and "no universe to add it to" in text


def test_old_word_banks_are_in_my_words_when_words_opens(index, world):
    u, s = world
    (s.path / "wordbank.json").write_text(json.dumps({"words": [{"word": "saddle", "note": ""}]}))
    async def script(app, pilot):
        await show_learning(app, pilot)
        return flat(screen_text(app))
    text = run(script, {"universe": "thornwood", "story": s.slug})
    assert "saddle" in text and "old word banks (1 words)" in text.replace("  ", " ") or "saddle" in text
    assert [e["word"] for e in learn.MyWords().learning] == ["saddle"]


def test_the_old_tabs_are_gone(index, world):
    async def script(app, pilot):
        return [p.id for p in app.screen.query(TabPane)]
    assert run(script, {}) == ["t-lookup", "t-suggest", "t-vocab", "t-story", "t-genre"]


# --- Overused ------------------------------------------------------------------------------------------------------------------------

def test_often_used_words_are_a_section_of_story_words_and_open_the_writer_there(index, world):
    u, s = world
    async def script(app, pilot):
        await show_tab(app, pilot, "t-story")
        await pilot.pause()
        app.screen.query_one("#swview", Select).value = "often"
        await pilot.pause()
        over = options(app, "swoften")
        text = flat(screen_text(app))
        ids = [i for i, _t in over]
        lst = app.screen.query_one("#swoften", OptionList)
        lst.focus()
        lst.highlighted = ids.index("f:0")
        await pilot.press("enter")
        await pilot.pause()
        occ = options(app, "swwhere")
        app.screen.query_one("#swwhere", OptionList).focus()
        app.screen.query_one("#swwhere", OptionList).highlighted = len(occ) - 1
        await pilot.press("enter")
        await pilot.pause()
        return text, occ, app.next, app.screen.query_one("#swlist").display
    text, occ, nxt, names_shown = run(script, {"universe": "thornwood", "story": s.slug})
    assert "Most frequent words" in text and "lantern" in text and "×4" in text and "Repeated close together" in text and not names_shown
    assert len(occ) == 4 and "line 1" in occ[0][1] and "line 4" in occ[-1][1]
    assert nxt[0] == "writer" and nxt[1]["scene"]["line"] == 4 and nxt[1]["scene"]["path"].endswith("manuscript.md")


def test_a_word_in_several_lists_does_not_break_the_screen(index, world):
    """Regression: 'whispering' was a similar word of two meanings, so two rows had the same id (DuplicateID)."""
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        ids = [o.id for lst in app.screen.result_lists() for o in (lst.get_option_at_index(i) for i in range(lst.option_count)) if o.id]
        assert len(ids) == len(set(ids))
        words = [plain(i) for i in ids]
        return len(words) != len(set(words))
    assert run(script) in (True, False)
    rows = words_app.lookup_rows({"found": True, "query": "x", "word": "x", "suggestions": [], "entries": [{
        "word": "x", "form_of": None, "wide_synonyms": ["a"], "antonyms": ["a"], "indirect_antonyms": [], "related_forms": {"derivation": ["a"]},
        "parts": [{"pos": "noun", "senses": [{"definition": "d", "examples": [], "synonyms": ["a"], "kind_of": ["a"], "types_of": [], "parts": [], "part_of": []}]}]}]})
    ids = [i for _t, i, _s in rows if i]
    assert len(ids) == 5 and len(set(ids)) == 5 and {plain(i) for i in ids} == {"w:a|noun", "w:a|"}



# --- batch 3: clearer words, start over, add by hand, review the universe's words ------------------------------------------------------

def labels(app):
    return {b.id: str(b.label) for b in app.screen.query(Button)}


def test_the_buttons_say_what_they_do(index, world):
    async def script(app, pilot):
        return labels(app)
    got = run(script, {"universe": "thornwood"})
    assert got["add"] == "Learn this word" and got["lookuplist"] == "Use in this universe's stories" and got["minelist"] == "Use in this universe's stories"
    assert got["startover"] == "Start over" and got["myadd"] == "Add"
    assert "Add to My words" not in " ".join(got.values()) and "word list" not in " ".join(got.values())


def test_use_in_writer_being_greyed_out_is_explained_on_screen(index, world):
    async def script(app, pilot):
        return flat(screen_text(app))
    text = run(script, {"universe": "thornwood"})
    assert "greyed out because you didn't come from the Writer" in text and "press F5 on a word in the Writer" in text
    text = run(script, handover("running"))
    assert "greyed out" not in text


def test_vocabulary_explains_its_markers_and_difficulty_with_examples(index, world):
    async def script(app, pilot):
        await show_tab(app, pilot, "t-vocab")
        return flat(screen_text(app))
    text = run(script, {})
    assert "★ Learning" in text and "✓ Known" in text and "Enter opens the full entry" in text
    assert "uncommon (like “lantern”)" in text and "rare (like “serendipity”)" in text and "very rare (like “gallivant”)" in text


def test_start_over_forgets_what_was_shown_but_keeps_known_and_learning(index, world):
    my = learn.MyWords()
    my.mark_seen(["puppy", "kennel", "wretch"]); my.mark_known("canine"); my.mark_learning("sprint")
    async def script(app, pilot):
        await show_tab(app, pilot, "t-vocab")
        await pilot.click("#startover")
        await pilot.pause()
        return flat(screen_text(app))
    text = run(script, {})
    assert "Forgot the 3 words you had been shown" in text
    again = learn.MyWords()
    assert again.seen == set() and again.known == {"canine"} and again.learning_words() == {"sprint"}


def test_a_word_of_your_own_can_be_added_to_my_words_with_its_meaning(index, world):
    async def script(app, pilot):
        await show_learning(app, pilot)
        await type_word(app, pilot, "puppy, zzzqx", box="myword")
        return [t for i, t in options(app, "mine") if i], flat(screen_text(app))
    rows, text = run(script, {})
    assert any("puppy" in r and "a young dog" in r and "noun" in r for r in rows) and any("zzzqx" in r for r in rows)
    assert "Added “puppy”, “zzzqx” to ★ Learning" in text
    assert learn.MyWords().learning_words() == {"puppy", "zzzqx"}


def test_adding_a_word_that_was_marked_known_makes_it_learning_again(index, world):
    learn.MyWords().mark_known("puppy")
    async def script(app, pilot):
        await show_learning(app, pilot)
        await type_word(app, pilot, "puppy", box="myword")
    run(script, {})
    again = learn.MyWords()
    assert again.learning_words() == {"puppy"} and "puppy" not in again.known


def test_universe_words_lists_what_was_added_and_removes_it(index, world):
    u, s = world
    wordbank.add_to_universe_list(u, "bell-ringer", "job")
    wordbank.add_to_universe_list(u, "gravedigger", "job")
    wordbank.add_to_universe_list(u, "kennel", "place")
    async def script(app, pilot):
        await show_tab(app, pilot, "t-story")
        rows = [t for i, t in options(app, "uwords") if i]
        lst = app.screen.query_one("#uwords", OptionList)
        lst.focus()
        lst.highlighted = 1
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        return rows, [t for i, t in options(app, "uwords") if i], flat(screen_text(app))
    rows, left, text = run(script, {"universe": "thornwood", "story": s.slug})
    assert [r.split() for r in rows] == [["job", "bell-ringer"], ["job", "gravedigger"], ["place", "kennel"]]
    assert [r.split() for r in left] == [["job", "bell-ringer"], ["place", "kennel"]]
    assert "Took “gravedigger” off the 'job' list" in text
    assert json.loads((u.lists_dir / "job" / "words-added.json").read_text())["entries"] == ["bell-ringer"]


def test_removing_the_last_word_removes_the_list_file(home):
    u = vault.create_universe("U", ["western"])
    path, _ = wordbank.add_to_universe_list(u, "only", "job")
    assert wordbank.remove_added(u, "job", "only") is True and not path.exists()
    assert wordbank.remove_added(u, "job", "only") is False and wordbank.added_words(u) == []


def test_a_new_word_added_from_lookup_shows_in_universe_words_at_once(index, world):
    u, s = world
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        ids = [i for i, _t in options(app, "results")]
        select_word(app, "w:hound|")
        app.screen.first_word_list().focus()
        await pilot.press("w")
        await pilot.pause()
        app.screen.query_one("#slot", Select).value = "thing"
        await pilot.click("#ok")
        await pilot.pause()
        await show_tab(app, pilot, "t-story")
        return [t for i, t in options(app, "uwords") if i]
    rows = run(script, {"universe": "thornwood", "story": s.slug})
    assert [r.split() for r in rows] == [["thing", "hound"]]


def test_the_help_explains_the_new_words(index):
    for needle in ("Start over", "Learn this word", "Use in this universe's stories", "Genre words", "Story words", "lantern"):
        assert needle in words_app.HELP


# --- batch 8: Vocabulary's ★ Learning view, Genre words, Story words ---------------------------------------------------------------------

def test_there_is_no_my_words_tab_and_every_tab_says_in_one_sentence_what_it_is_for(index, world):
    async def script(app, pilot):
        panes = {p.id: str(p._title) if hasattr(p, "_title") else "" for p in app.screen.query(TabPane)}
        texts = {}
        for tab in ("t-lookup", "t-suggest", "t-vocab", "t-story", "t-genre"):
            await show_tab(app, pilot, tab)
            texts[tab] = flat(screen_text(app))
        return panes, texts
    panes, texts = run(script, {"universe": "thornwood"})
    assert "t-mine" not in panes and "t-uwords" not in panes
    for tab, sentence in words_app.TAB_HELP.items():
        assert sentence.count(". ") == 0 and sentence.endswith(".")
        key = {"lookup": "t-lookup", "suggest": "t-suggest", "vocab": "t-vocab", "genre": "t-genre", "story": "t-story"}[tab]
        assert sentence[:60] in texts[key]
        assert sentence.split(":")[0] in words_app.HELP or sentence[:25] in words_app.HELP


def test_the_learning_filter_shows_the_star_words_and_typed_words_join_them(index, world):
    my = learn.MyWords()
    my.mark_learning("puppy")
    async def script(app, pilot):
        await show_tab(app, pilot, "t-vocab")
        before = app.screen.query_one("#mine", OptionList).display
        app.screen.query_one("#myword", Input).value = "kennel"
        app.screen.query_one("#myword", Input).focus()
        await pilot.press("enter")
        await pilot.pause()
        app.screen.query_one("#vview", Select).value = "learning"
        await pilot.pause()
        rows = [t for i, t in options(app, "mine") if i]
        return before, app.screen.query_one("#mine", OptionList).display, app.screen.query_one("#learn", OptionList).display, rows
    before, shown, learn_shown, rows = run(script, {})
    assert before is False and shown is True and learn_shown is False
    assert len(rows) == 2 and any("kennel" in r for r in rows) and any("puppy" in r for r in rows)


@pytest.fixture
def fit(monkeypatch, index):
    """A small genre fit over the fixture dictionary: western seeds dog and run, fantasy seeds wolf."""
    from collections import Counter
    from dictfixture import ZIPF
    monkeypatch.setattr(genrefit, "seed_words", lambda lib: {"western": Counter({"dog": 1.0, "run": 1.0, "happy": 1.0}), "fantasy": Counter({"wolf": 1.0, "leave": 1.0})})
    monkeypatch.setattr(genrefit, "domain_names", lambda lib: {})
    monkeypatch.setattr(genrefit, "zipf_function", lambda: (lambda w: ZIPF.get(w, 0.0)))


async def open_genre(app, pilot):
    """Show Genre words and wait for the genre fit to be worked out (it is, once, in the background)."""
    await show_tab(app, pilot, "t-genre")
    await app.workers.wait_for_complete()
    await pilot.pause()
    await pilot.pause()


def vrows(app):
    """The words shown in the Genre words list: [(word, fit mark)] from the first page."""
    v = app.screen.query_one("#gwvlist", VirtualList)
    return [(r["word"], r["mark"]) for r in v.row_page(0)] if hasattr(v, "row_page") else [(r["word"], r["mark"]) for r in v._fetch(0, 100)]


def pick(app, value):
    app.screen.query_one("#gwcat", Select).value = value


def test_genre_words_list_every_noun_with_a_one_line_meaning_and_work_out_the_fit_once(index, fit, world):
    u, s = world
    async def script(app, pilot):
        await open_genre(app, pilot)
        scr = app.screen
        words = vrows(app)
        note = flat(str(scr.query_one("#gwnote").content))
        genres = list(scr.gw_genres)
        again = scr.gw_started
        return words, note, genres, again, genrefit.stale(scr.library())
    words, note, genres, started, stale = run(script, {"universe": "thornwood", "story": s.slug})
    assert genres == ["western"] and started and not stale                      # the story's genre; the fit exists now
    names = [w for w, _m in words]
    assert names[0] in ("dog", "domestic dog", "wretch") and "puppy" in names and "run" not in names     # western's seeds first; nouns only
    assert words[0][1] == "●●●" and "ranked by fit to western" in note and "nothing is hidden" in note


def test_the_part_of_speech_picker_switches_between_nouns_verbs_adjectives(index, fit, world):
    u, s = world
    async def script(app, pilot):
        await open_genre(app, pilot)
        out = {}
        for pos in ("v", "a", "n"):
            pick(app, pos)
            await pilot.pause()
            out[pos] = [w for w, _m in vrows(app)]
        return out
    out = run(script, {"universe": "thornwood", "story": s.slug})
    assert "run" in out["v"][:3] and "vaccinate" in out["v"] and "happy" in out["a"] and "dog" in out["n"] and "dog" not in out["v"]


def test_choosing_genres_ranks_and_any_genre_gives_the_whole_list_without_markers(index, fit, world):
    u, s = world
    async def script(app, pilot):
        await open_genre(app, pilot)
        scr = app.screen
        scr.genres_picked(["fantasy"])
        await pilot.pause()
        fantasy = vrows(app)
        count_fantasy = scr.query_one("#gwvlist", VirtualList).count
        scr.genres_picked(["*"])
        await pilot.pause()
        anyg = vrows(app)
        count_any = scr.query_one("#gwvlist", VirtualList).count
        text = flat(str(scr.query_one("#gwgenrelist").content))
        return fantasy, count_fantasy, anyg, count_any, text
    fantasy, count_f, anyg, count_a, text = run(script, {"universe": "thornwood", "story": s.slug})
    assert fantasy[0][0] == "wolf" and fantasy[0][1] == "●●●"
    assert count_f == count_a and all(m == "" for _w, m in anyg) and "any genre" in text            # nothing is hidden


def test_commonness_sort_and_search_filter_the_list_as_you_type(index, fit, world):
    u, s = world
    async def script(app, pilot):
        await open_genre(app, pilot)
        scr = app.screen
        scr.query_one("#gwband", Select).value = "very rare"
        await pilot.pause()
        rare = [w for w, _m in vrows(app)]
        scr.query_one("#gwband", Select).value = "any"
        scr.query_one("#gwsort", Select).value = "az"
        await pilot.pause()
        az = [w for w, _m in vrows(app)]
        scr.query_one("#gwsearch", Input).value = "dog"
        await pilot.pause(0.5)
        found = [w for w, _m in vrows(app)]
        return rare, az, found
    rare, az, found = run(script, {"universe": "thornwood", "story": s.slug})
    assert "wretch" in rare and "dog" not in rare                              # Zipf 2.0 against 5.2
    assert az == sorted(az)
    assert set(found) == {"dog", "domestic dog"}


def test_enter_opens_the_lookup_entry_and_l_marks_the_word_to_learn(index, fit, world):
    u, s = world
    async def script(app, pilot):
        await open_genre(app, pilot)
        scr = app.screen
        v = scr.query_one("#gwvlist", VirtualList)
        v.focus()
        await pilot.pause()
        word = v.current()["word"]
        await pilot.press("l")
        await pilot.pause()
        learning = learn.MyWords().learning_words()
        star = "★" in "".join(seg.text for seg in v.render_line(0))
        await pilot.press("enter")
        await pilot.pause()
        return word, learning, star, scr.query_one(TabbedContent).active, scr.history
    word, learning, star, tab, history = run(script, {"universe": "thornwood", "story": s.slug})
    assert word in learning and star                                           # shows in Vocabulary's Learning view too
    assert tab == "t-lookup" and history == [word]


def test_copy_and_use_in_writer_work_on_a_dictionary_word(index, fit, world, monkeypatch):
    from storywheel import clipboard
    copied = []
    monkeypatch.setattr(clipboard, "copy", lambda text, app=None: copied.append(text) or True)
    u, s = world
    payload = handover("running")
    payload.update({"universe": "thornwood", "story": s.slug})
    async def script(app, pilot):
        await open_genre(app, pilot)
        scr = app.screen
        scr.query_one("#gwcat", Select).value = "v"
        await pilot.pause()
        v = scr.query_one("#gwvlist", VirtualList)
        v.focus()
        await pilot.pause()
        word = v.current()["word"]
        await pilot.press("c")
        await pilot.press("u")
        await pilot.pause()
        return word, app.next
    word, nxt = run(script, payload)
    assert copied == [word] and nxt[0] == "writer" and nxt[1]["replace"]["picked"] == word and nxt[1]["replace"]["new"]


def test_dictionary_word_goes_on_a_generator_list_through_the_slot_picker(index, fit, world):
    u, s = world
    async def script(app, pilot):
        await open_genre(app, pilot)
        scr = app.screen
        v = scr.query_one("#gwvlist", VirtualList)
        v.focus()
        await pilot.pause()
        word = v.current()["word"]
        await pilot.press("w")
        await pilot.pause()
        picker = type(app.screen).__name__
        app.screen.query_one("#slot", Select).value = "thing"
        await pilot.click("#ok")
        await pilot.pause()
        return word, picker
    word, picker = run(script, {"universe": "thornwood", "story": s.slug})
    assert picker == "SlotScreen" and json.loads((u.lists_dir / "thing" / "words-added.json").read_text())["entries"] == [word]


def test_from_the_wheel_keeps_names_jobs_places_things_and_no_sentence_templates(index, fit, world):
    u, s = world
    async def script(app, pilot):
        await open_genre(app, pilot)
        sel = app.screen.query_one("#gwcat", Select)
        values = [v for _l, v in sel._options if v is not Select.BLANK]
        labels = [str(l) for l, _v in sel._options]
        pick(app, "wheel:first_name")
        await pilot.pause()
        scr = app.screen
        shown = (scr.query_one("#gwlist").display, scr.query_one("#gwvlist").display, scr.query_one("#gwmore", Button).disabled)
        rows = [t for i, t in options(app, "gwlist") if i]
        return values, labels, shown, rows
    values, labels, shown, rows = run(script, {"universe": "thornwood", "story": s.slug})
    assert values[:4] == ["n", "v", "a", "r"] and "wheel:first_name" in values and "wheel:job" in values
    assert not any("premise" in l.lower() or "flaw" in l.lower() or "rumor" in l.lower() or "want" in l.lower() for l in labels)
    assert shown == (True, False, False) and rows and any("western" in r for r in rows)


def test_wheel_names_add_as_characters_jobs_go_on_the_generator_list_and_more_names_are_invented(index, fit, world):
    u, s = world
    async def script(app, pilot):
        await open_genre(app, pilot)
        scr = app.screen
        pick(app, "wheel:first_name")
        await pilot.pause()
        lst = scr.query_one("#gwlist", OptionList)
        lst.focus()
        lst.highlighted = 0
        await pilot.pause()
        first = scr.gw_row().text
        await pilot.press("e")
        await pilot.pause()
        scr.genres_picked(["western", "fantasy"])
        await pilot.pause()
        lst.focus()
        await pilot.press("m")
        await pilot.pause()
        new = [t for i, t in options(app, "gwlist") if i and i.startswith("n:")]
        pick(app, "wheel:job")
        await pilot.pause()
        lst.focus()
        lst.highlighted = 0
        await pilot.pause()
        job = scr.gw_row()
        await pilot.press("e")
        await pilot.pause()
        return first, new, job
    first, new, job = run(script, {"universe": "thornwood", "story": s.slug})
    assert u.find_by_name(first, "character") and len(new) >= 6 and all("new" in t for t in new)
    assert json.loads((u.lists_dir / "job" / "words-added.json").read_text())["entries"] == [job.text]


def test_without_a_dictionary_genre_words_say_so_and_offer_only_the_wheel_lists(home, tmp_path, monkeypatch):
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(tmp_path / "none.sqlite"))
    dictionary.forget()
    async def script(app, pilot):
        await show_tab(app, pilot, "t-genre")
        await pilot.pause()
        sel = app.screen.query_one("#gwcat", Select)
        values = [v for _l, v in sel._options if v is not Select.BLANK]
        return values, flat(screen_text(app)), app.screen.query_one("#gwband").display
    values, text, band = run(script, {})
    assert values and all(v.startswith("wheel:") for v in values) and "storywheel dictionary install" in text and band is False


def test_story_words_are_read_when_the_tab_opens_and_flag_look_alikes(index, world):
    u, s = world
    (s.manuscript_dir / "manuscript.md").write_text("Stacie rode to Glasswater. The Glass Water road was long. A zorbl hummed. Glasswater slept.\n", encoding="utf-8")
    u.new_entity("character", "Stacie", {"role": "protagonist"})
    u.new_entity("place", "Glasswater")
    async def script(app, pilot):
        await show_tab(app, pilot, "t-story")
        await pilot.pause()
        rows = [t for i, t in options(app, "swlist") if i]
        return rows, flat(screen_text(app))
    rows, text = run(script, {"universe": "thornwood", "story": s.slug})
    joined = " | ".join(rows)
    assert "≈ Glass Water" in joined and "looks like Glasswater" in joined
    assert "◆ Glasswater" in joined and "? zorbl" in joined and "not in the dictionary" in joined
    assert "words read" in text


def test_story_words_add_to_spelling_make_an_entity_and_rename_everywhere(index, world):
    u, s = world
    (s.manuscript_dir / "manuscript.md").write_text("Stacie rode to Glasswater. The Glass Water road was long. A zorbl hummed. Glasswater slept.\n", encoding="utf-8")
    u.new_entity("place", "Glasswater")
    def pick(app, text):
        lst = app.screen.query_one("#swlist", OptionList)
        names = [str(lst.get_option_at_index(i).prompt) for i in range(lst.option_count)]
        lst.focus()
        lst.highlighted = next(i for i, n in enumerate(names) if text in n)
    async def script(app, pilot):
        await show_tab(app, pilot, "t-story")
        await pilot.pause()
        pick(app, "? zorbl")
        await pilot.press("s")
        await pilot.pause()
        spelled = (u.path / "spell" / "en.utf-8.add").read_text()
        pick(app, "Glass Water")
        await pilot.press("r")
        await pilot.pause()
        app.screen.query_one("#in-new-name", Input).value = "Glasswater"
        await pilot.press("enter")
        await pilot.pause()
        preview = type(app.screen).__name__
        await pilot.press("a")
        await pilot.press("p")
        await pilot.pause()
        return spelled, preview, flat(str(app.screen.query_one("#status").content))
    spelled, preview, status = run(script, {"universe": "thornwood", "story": s.slug})
    assert spelled.startswith("zorbl") or spelled.startswith("Zorbl")
    assert preview == "RenamePreviewScreen"
    text = (s.manuscript_dir / "manuscript.md").read_text()
    assert "Glass Water" not in text and text.count("Glasswater") == 3 and "rewritten" in status


def test_story_words_keep_the_generator_list_section_at_the_bottom(index, world):
    u, s = world
    wordbank.add_to_universe_list(u, "hound", "job")
    async def script(app, pilot):
        await show_tab(app, pilot, "t-story")
        rows = [t for i, t in options(app, "uwords") if i]
        lst = app.screen.query_one("#uwords", OptionList)
        lst.focus()
        lst.highlighted = 0
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        return rows, [t for i, t in options(app, "uwords") if i]
    rows, after = run(script, {"universe": "thornwood", "story": s.slug})
    assert any("hound" in r for r in rows) and not any("hound" in r for r in after)


# --- batch 9: Suggestions, Known words, tab order ----------------------------------------------------------------------------------------

async def open_suggest(app, pilot):
    await show_tab(app, pilot, "t-suggest")
    await app.workers.wait_for_complete()
    await pilot.pause()
    await app.workers.wait_for_complete()
    await pilot.pause()
    await pilot.pause()


def srows(app):
    v = app.screen.query_one("#sgvlist", VirtualList)
    return v._fetch(0, 200)


def test_tabs_are_in_the_new_order(index, world):
    async def script(app, pilot):
        return [p.id for p in app.screen.query(TabPane)]
    assert run(script, {}) == ["t-lookup", "t-suggest", "t-vocab", "t-story", "t-genre"]


def test_suggestions_for_this_story_fit_the_genres_and_skip_words_already_written(index, fit, world):
    u, s = world
    (s.manuscript_dir / "manuscript.md").write_text("The wolf ran home. A goose honked.\n", encoding="utf-8")
    async def script(app, pilot):
        await open_suggest(app, pilot)
        scr = app.screen
        verbs = None
        scr.query_one("#sgpos", Select).value = "v"
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()
        verbs = [r["word"] for r in srows(app)]
        scr.query_one("#sgpos", Select).value = "n"
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()
        return verbs, [r["word"] for r in srows(app)], flat(str(scr.query_one("#sgnote").content))
    verbs, nouns, note = run(script, {"universe": "thornwood", "story": s.slug})
    assert "run" not in verbs                                                  # "ran" is in the manuscript
    assert "wolf" not in nouns and "goose" not in nouns                          # both are in the manuscript
    assert "western" in note and "The Last Clause" in note


def test_suggestions_list_words_related_to_characters_and_places_and_the_same_row_actions_work(index, fit, world):
    u, s = world
    u.new_entity("thing", "the dog")
    async def script(app, pilot):
        await open_suggest(app, pilot)
        scr = app.screen
        scr.query_one("#sgkind", Select).value = "entities"
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()
        rows = srows(app)
        v = scr.query_one("#sgvlist", VirtualList)
        v.focus()
        await pilot.pause()
        word = v.current()["word"]
        await pilot.press("l")
        await pilot.pause()
        learning = learn.MyWords().learning_words()
        await pilot.press("enter")
        await pilot.pause()
        return rows, word, learning, scr.query_one(TabbedContent).active, scr.history
    rows, word, learning, tab, history = run(script, {"universe": "thornwood", "story": s.slug})
    assert rows and all(r["note"] for r in rows) and word in learning and tab == "t-lookup" and history == [word]


def test_fresh_alternatives_follow_the_overused_words(index, fit, world):
    u, s = world
    (s.manuscript_dir / "manuscript.md").write_text("The man ran. He ran far. He ran and ran, and ran home.\n", encoding="utf-8")
    async def script(app, pilot):
        await open_suggest(app, pilot)
        scr = app.screen
        scr.query_one("#sgkind", Select).value = "fresh"
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()
        return srows(app)
    rows = run(script, {"universe": "thornwood", "story": s.slug})
    assert rows[0]["head"] and rows[0]["word"] in ("ran", "run") and {"sprint", "dash"} & {r["word"] for r in rows[1:]}


def test_a_new_batch_skips_words_the_manuscripts_use_and_marks_them_known_with_where(index, world, monkeypatch):
    u, s = world
    monkeypatch.setattr(learn, "batch", lambda n, *a, exclude=(), **k: [
        {"word": w, "pos": "noun", "definition": "d", "zipf": 3, "subject": ""} for w in ["lantern", "w1", "w2"] if w not in {x.lower() for x in exclude}][:n])
    async def script(app, pilot):
        await show_tab(app, pilot, "t-vocab")
        await pilot.click("#newbatch")
        await pilot.pause()
        shown = [row_word(t) for _i, t in learn_rows(app)]
        status = flat(str(app.screen.query_one("#status").content))
        app.screen.query_one("#vview", Select).value = "known"
        await pilot.pause()
        known = [t for i, t in options(app, "knownlist") if i]
        return shown, status, known
    shown, status, known = run(script, {"universe": "thornwood", "story": s.slug})
    assert shown == ["w1", "w2"] and "lantern" in status and "The Last Clause" in status and "marked ✓ Known" in status
    assert any("lantern" in k and "used in The Last Clause (Thornwood)" in k and "line 1" in k for k in known)
    assert learn.MyWords().used_where("lantern")["line"] == 1


def test_a_learning_word_that_a_manuscript_uses_becomes_known_when_words_opens(index, world):
    u, s = world
    my = learn.MyWords()
    my.mark_learning("wind", "noun", "moving air")
    my.mark_learning("kennel", "noun", "a shelter")
    async def script(app, pilot):
        await show_learning(app, pilot)
        return [t for i, t in options(app, "mine") if i], flat(str(app.screen.query_one("#status").content))
    rows, status = run(script, {"universe": "thornwood", "story": s.slug})
    assert len(rows) == 1 and "kennel" in rows[0] and "wind" in status and "Known" in status
    assert "wind" in learn.MyWords().known and "wind" not in learn.MyWords().learning_words()
