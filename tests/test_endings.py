"""Batch 21, item 5: the ending (endings.py), a picked field on the Genre step. Climax and resolution frames may carry an "ending";
an untagged frame fits any ending; with one picked, frames for other endings are never drawn."""
import asyncio
import json
import re

import pytest

from storywheel import endings, library, session, store, steps
from storywheel.engine import Engine
from storywheel.library import DataError, Library
from storywheel.sample import build_story
from storywheel.tui import ChoiceScreen, StorywheelApp
from conftest import make_engine

PICKED = ["triumph", "bittersweet", "tragic", "open"]
SLOTS = ["climax", "resolution", "act_climax", "act_resolution", "ketsu"]


# --- the module and the data ------------------------------------------------------------------------------------------------------

def test_the_endings_and_how_they_are_found():
    assert [e.key for e in endings.ENDINGS] == ["any"] + PICKED
    assert endings.find("Tragic") == "tragic" and endings.find("any (let the story decide)") == "any" and endings.find("sad") is None
    assert endings.of_draft({}) == "any" and endings.of_draft({"ending": "open"}) == "open"
    assert endings.of_draft({"kept": {"genre": {"ending": "Bittersweet"}}}) == "bittersweet"


def test_a_template_names_its_endings_as_a_string_or_a_list(tmp_path):
    root = tmp_path / "templates"
    (root / "climax").mkdir(parents=True)
    path = root / "climax" / "x.json"
    path.write_text(json.dumps({"slot": "climax", "tags": ["general"], "entries": [
        "{first} {ACT_PERSON} {SOMEONE}", {"text": "{first} lost {LOSS}", "ending": "tragic"},
        {"text": "{first} won {WINDFALL}", "ending": ["triumph", "bittersweet"]}]}))
    wl = library._read_list(path, root, True)
    assert [e.ending for e in wl.entries] == [(), ("tragic",), ("triumph", "bittersweet")]
    path.write_text(json.dumps({"slot": "climax", "tags": ["general"], "entries": [{"text": "{first} lost {LOSS}", "ending": "sad"}]}))
    with pytest.raises(DataError, match="ending 'sad'"):
        library._read_list(path, root, True)


def test_every_ending_has_real_variety_in_every_climax_and_resolution_slot():
    lib = Library.load()
    for slot in SLOTS:
        entries = [e for wl in lib.by_slot[slot] if wl.is_template for e in wl.entries]
        for key in PICKED:
            own = {e.text for e in entries if key in e.ending}
            fits = {e.text for e in entries if not e.ending or key in e.ending}
            assert len(own) >= 3 and len(fits) >= 8, (slot, key, len(own), len(fits))


def test_the_default_changes_nothing():
    a = build_story(Engine(seed=11), ["noir"], structure="three-act")
    b = build_story(Engine(seed=11), ["noir"], structure="three-act", ending="any")
    assert a["kept"]["spine"] == b["kept"]["spine"] and a["kept"]["twist"] == b["kept"]["twist"]


# --- the generator --------------------------------------------------------------------------------------------------------------------

def picks(ending, genre="noir", structure="three-act", seeds=range(1, 13)):
    """[(slot, entry text)] every template drawn for a climax or resolution slot."""
    lib = Engine(seed=1).library
    tags = {(wl.slot, e.text): e.ending for wl in lib.lists.values() if wl.is_template for e in wl.entries}
    out = []
    for seed in seeds:
        e = Engine(seed=seed)
        e.trace = []
        build_story(e, [genre], structure=structure, ending=ending)
        out += [(slot, text, tags.get((slot, text), ())) for slot, _id, _t, text in e.trace if slot in SLOTS]
    return out


@pytest.mark.parametrize("ending", PICKED)
def test_a_story_with_an_ending_never_draws_a_frame_written_for_another(ending):
    drawn = picks(ending)
    assert drawn and not [d for d in drawn if d[2] and ending not in d[2]]
    own = [d for d in drawn if ending in d[2]]
    assert len(own) >= 0.35 * len(drawn), (ending, len(own), len(drawn))             # (genre frames carry no ending; about ENDING_SHARE of draws are its own)


def test_the_four_endings_read_differently():
    texts = {}
    for key in PICKED:
        story = build_story(Engine(seed=5), ["western"], structure="story-spine", ending=key)
        texts[key] = (story["kept"]["spine"]["until_finally"], story["kept"]["spine"]["ever_since"])
    assert len({t for t in texts.values()}) == 4


@pytest.mark.slow
@pytest.mark.parametrize("ending", PICKED)
def test_every_ending_reads(ending):
    bad = []
    for genre in ("western", "fairy tale", "noir", "romance", "sci-fi", "horror"):
        for structure in ("story-spine", "three-act", "kishotenketsu", "freytag", "in-medias-res", "circular"):
            for seed in (1, 2):
                story = build_story(Engine(seed=seed), [genre], structure=structure, ending=ending)
                text = " ".join(story["kept"]["spine"].values())
                if re.search(r"[{}\[\]]", text) or re.search(r"\b(\w{3,}) \1\b", text, re.I) or not all(v.strip() for v in story["kept"]["spine"].values()):
                    bad.append((genre, structure, seed))
    assert not bad, bad[:6]


# --- the Genre step ---------------------------------------------------------------------------------------------------------------------

def test_the_ending_is_a_picked_field_checked_against_the_list_and_kept_with_the_genre():
    s = session.Session(store.new_story(), Engine(seed=1))
    s.enter(0)
    assert list(s.fields) == ["genre", "mood", "focus", "ending"] and s.fields["ending"] == "Any (let the story decide)"
    s.reroll_field("ending")
    assert s.fields["ending"] == "Any (let the story decide)" and any("picked, not rolled" in n for n in s.take_notes())
    assert not s.edit_field("ending", "sad") and any("is not an ending" in n for n in s.take_notes())
    assert s.edit_field("ending", "tragic") and s.story["ending"] == "tragic" and s.fields["ending"] == "Tragic"
    s.roll()
    assert s.fields["ending"] == "Tragic"                                              # (rolling the step keeps it)
    s.keep()
    assert s.story["kept"]["genre"]["ending"] == "Tragic"


def test_changing_the_ending_after_the_body_is_kept_says_which_beats_to_reroll():
    st = store.new_story()
    st["kept"]["genre"] = {"genre": "noir", "mood": "wry", "focus": "One protagonist", "ending": "Any (let the story decide)"}
    st["kept"]["spine"] = {"once": "x"}
    s = session.Session(st, Engine(seed=2))
    s.enter(0)
    assert s.set_ending("open") and any("reroll its climax and resolution" in n for n in s.take_notes())
    assert st["kept"]["genre"]["ending"] == "Open"


def test_the_ending_is_picked_from_a_list_on_the_screen(home):
    async def go():
        app = StorywheelApp(store.new_story(), make_engine(home))
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            s = app.session
            app.main.card.highlighted = s.field_names.index("ending")
            await pilot.press("e")
            await pilot.pause()
            dlg = app.screen
            assert isinstance(dlg, ChoiceScreen) and [v for _l, v in dlg.options] == [e.key for e in endings.ENDINGS]
            dlg.query_one("#choices").highlighted = 3                                   # tragic
            await pilot.press("enter")
            await pilot.pause()
            return s.fields["ending"], s.story["ending"]
    assert asyncio.run(go()) == ("Tragic", "tragic")
