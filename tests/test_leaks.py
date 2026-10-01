"""No slot name, underscore token or stray bracket may ever reach the writer, and no verb is doubled."""
import re

import pytest

from storywheel import frames
from storywheel import threads as T
from storywheel.engine import Engine
from storywheel.library import Entry, Library, WordList
from storywheel.report import lint
from storywheel.sample import build_story
from storywheel.steps import Ctx, STEPS, public, step_by_key
from conftest import make_library

LIB = Library.load()


def all_text(story):
    """Every piece of text the writer would see for a story."""
    out = []
    for fields in story["kept"].values():
        out += [v for v in public(fields).values() if isinstance(v, str)]
    out += [t["text"] for t in story.get("threads", {}).values()]
    return out


# --- the parser --------------------------------------------------------------------------------------------

def test_a_requirement_may_contain_alternatives():
    slots = frames.parse("{DISASTER:manmade|magic} {was} no accident; {the_disaster:strikes|manmade} {lies|lie}", LIB)
    assert [(s.name, s.spec, s.alt, s.agree) for s in slots] == [
        ("DISASTER", ["manmade|magic"], None, False), ("was", [], None, True),
        ("the_disaster", ["strikes|manmade"], None, False), ("lies", [], "lie", True)]
    assert slots[0].atom == "disaster" and slots[2].field == "the_disaster"


def test_the_thread_gate_sees_requirements_with_alternatives():
    t = "{the_disaster:manmade|magic} {was} no accident"
    assert T.refs(t) == {"disaster"}
    assert T.weight(t, {}) == 0                     # never chosen without the thread
    assert T.weight(t, {"disaster": {"text": "a flood", "beat": "x"}}) == T.PREFERRED


def test_a_template_needing_a_thread_that_is_missing_is_never_drawn():
    engine = Engine(seed=3)
    c = Ctx(engine, {"kept": {}, "seeds": {}, "atoms": {}}, threads={})
    for _ in range(300):
        engine._recent.clear()
        c.drawn.clear()
        assert not T.refs(c.draw("twist"))              # {the_motif} is always available; real threads aren't


# --- unknown names ------------------------------------------------------------------------------------------

def test_names_nothing_can_fill_are_found():
    assert frames.unknown_names(LIB, "{DISASTR} and {nonsense} and {THING:buryable} and {the_motif}") == ["DISASTR", "nonsense"]
    assert frames.unknown_names(LIB, "{was} {lies|lie} {first} {ODDITY} {ACT_THING:stows}") == []


def test_the_lint_reports_a_placeholder_nothing_can_fill():
    lib = make_library([WordList("thing/a", "thing", ["general"], [Entry("x"), Entry("y"), Entry("z")]),
                        WordList("reaction/a", "reaction", ["general"], [Entry("{BOGUS} meets {THING}")], is_template=True)])
    assert any("nothing can fill {BOGUS}" in why for _lid, _t, why in lint(lib))


def test_a_frame_with_an_unknown_slot_is_set_aside_not_printed():
    lib = make_library([WordList("thing/a", "thing", ["general"], [Entry("a box"), Entry("a bell"), Entry("a key")]),
                        WordList("reaction/a", "reaction", ["general"],
                                 [Entry("{BOGUS} meets {THING}"), Entry("{first} left {THING}")], is_template=True)])
    engine = Engine(seed=2, library=lib)
    c = Ctx(engine, {"kept": {"protagonist": {"first": "Wade"}}, "seeds": {}, "atoms": {}})
    for _ in range(40):
        c.drawn.clear()
        text = c.sentence("reaction")
        assert "BOGUS" not in text and text.startswith("{first} left")


def test_shipped_templates_use_only_names_that_can_be_filled():
    bad = [(wl.id, e.text, n) for wl in LIB.lists.values() if wl.is_template for e in wl.entries
           for n in frames.unknown_names(LIB, e.text)]
    assert not bad, bad[:5]


# --- the leak detector ---------------------------------------------------------------------------------------------

def test_the_detector_finds_what_it_is_for():
    assert frames.leaks(LIB, "DISASTER was no accident")
    assert frames.leaks(LIB, "The_disaster came back")
    assert frames.leaks(LIB, "{first} left") and frames.leaks(LIB, "lies|lie") and frames.leaks(LIB, "the [KEY] here")
    assert not frames.leaks(LIB, "Wade met a DJ at the saloon. The disaster was no accident.")   # real words are fine


# --- nothing leaks, anywhere ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("genres", [["western", "fairy tale"], ["western"], ["fairy tale"], ["sci-fi"],
                                    ["noir", "romance"], ["horror"]])
def test_no_rendered_text_contains_a_slot_name_or_underscore_token(genres):
    engine = Engine(seed=71)
    for n in range(150):
        story = build_story(engine, genres)
        for text in all_text(story):
            assert not frames.leaks(engine.library, text), (text, story["kept"]["structure"])
    assert not [m for m in engine.notices if "unfilled slot" in m], engine.notices      # and the guard never had to act


@pytest.mark.parametrize("structure", ["story-spine", "three-act", "kishotenketsu"])
def test_every_structure_is_free_of_leaks(structure):
    engine = Engine(seed=72)
    for _ in range(200):
        story = build_story(engine, ["western", "fairy tale"], structure=structure)
        for text in all_text(story):
            assert not frames.leaks(engine.library, text), text
    assert not [m for m in engine.notices if "unfilled slot" in m]


def test_rerolling_beats_never_leaks_either():
    from storywheel.refs import reroll_field
    engine = Engine(seed=73)
    spine = step_by_key("spine")
    story = {"kept": {}, "seeds": {}, "atoms": {}}
    for _ in range(80):
        cand = spine.roll(engine, story)
        for field in spine.fields:
            cand = reroll_field(spine, engine, story, cand, field)
            assert not frames.leaks(engine.library, cand[field]), cand[field]


# --- doubled verbs --------------------------------------------------------------------------------------------------------

DOUBLED = re.compile(r"\b(\w{4,}?)(?:s|ed|ing)? to \1\b", re.IGNORECASE)      # learning to learn, wanted to want


def test_no_frame_doubles_its_verb():
    engine = Engine(seed=74)
    seen = 0
    for _ in range(400):
        story = build_story(engine, ["western", "fairy tale"])
        for text in all_text(story):
            assert not DOUBLED.search(text), text
            seen += "learn" in text
    assert seen > 20                                    # and 'learning' still turns up


def test_no_need_begins_with_a_verb_a_frame_already_supplies():
    needs = [e.text for wl in LIB.by_slot["need"] for e in wl.entries]
    assert not [n for n in needs if re.match(r"to (learn|understand|want|need|wish)\b", n)], needs
    frames_using_need = [(wl.id, e.text) for wl in LIB.lists.values() if wl.is_template for e in wl.entries
                         if "{need}" in e.text]
    assert frames_using_need and all(re.search(r"\b(learn|learned|learning)\s+\{need\}", t) or "{need}" in t
                                     for _i, t in frames_using_need)


# --- the random-word wildcard ---------------------------------------------------------------------------------------

def test_random_titles_never_use_slurs_or_hate_words():
    from storywheel.engine import BLOCKED_WORDS
    for bad in ("racism", "racist", "rape", "genocide"):
        assert BLOCKED_WORDS.search(bad)
    for fine in ("grape", "spice", "raccoon", "whorl", "scrape", "therapy", "racing"):
        assert not BLOCKED_WORDS.search(fine), fine
    engine = Engine(seed=8)
    seen = {engine.word(pos) for _ in range(1500) for pos in ("nouns", "adjectives", "verbs")}
    assert not [w for w in seen if BLOCKED_WORDS.search(w)] and len(seen) > 500
