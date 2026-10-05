"""The lint knows the sentence shapes found by reading samples (batch 13), and the data has none of them."""
import re

from conftest import make_library, wl
from storywheel import report
from storywheel.library import Entry, Library


def library(*lists):
    return make_library(list(lists))


def tpl(slot, *texts, tags=("x",)):
    lst = wl(f"{slot}/t", list(tags), list(texts), slot=slot)
    lst.is_template = True
    return lst


def problems(*lists):
    return [p[2] for p in report.sentence_problems(library(*lists))]


def test_a_fear_verb_before_a_feeling_is_flagged():
    for text in ("{first} kept {THING} and feared {FEELING}", "once {ACT_MESSAGE} {MESSAGE} and still fears {FEELING}", "was afraid of {FEELING} and {VICE}"):
        assert any("fears fear" in m for m in problems(tpl("once", text))), text
    assert problems(tpl("once", "{first} carried {FEELING} and {VICE}")) == []


def test_a_want_placed_at_a_landmark_is_flagged():
    for text in ("{THING:portable,!living} from {landmark}", "{THING:valuable,!living} at {landmark}", "{PRIZE:material} near {landmark}"):
        assert any("location" in m for m in problems(tpl("want", text))), text
    assert problems(tpl("want", "{THING:valuable,!living} and the key to {landmark}")) == []
    assert problems(tpl("rumor", "{THING:valuable} lies at {landmark}")) == []                # (only wants)


def test_an_animal_must_be_marked_living():
    assert any("living" in m for m in problems(wl("thing/x", ["x"], [Entry("a mule", features=("portable",))])))
    assert problems(wl("thing/x", ["x"], [Entry("a mule", features=("living",))])) == []
    assert problems(wl("thing/x", ["x"], [Entry("a carved wooden horse", features=("portable",)), Entry("a stuffed owl", features=("portable",))])) == []


def test_an_enclosing_verb_needs_a_built_or_indoor_place():
    assert any("enclosing" in m for m in problems(wl("act_place/x", ["x"], [Entry("locked up")])))
    assert any("enclosing" in m for m in problems(wl("act_place/x", ["x"], [Entry("swept", object=("outdoor",))])))
    assert problems(wl("act_place/x", ["x"], [Entry("locked up", object=("indoor",)), Entry("swept", object=("built",))])) == []


def test_a_verb_that_ends_in_an_adverb_is_flagged():
    for verb in ("read twice", "found again", "read aloud"):
        assert any("adverb" in m for m in problems(wl("act_message/x", ["x"], [Entry(verb)]))), verb
    assert problems(wl("act_message/x", ["x"], [Entry("reread"), Entry("read out")])) == []


def test_a_verb_for_objects_must_keep_animals_out():
    assert any("opened a mule" in m for m in problems(wl("act_thing/x", ["x"], [Entry("opened")])))
    assert problems(wl("act_thing/x", ["x"], [Entry("opened", object=("!living",))])) == []


def test_the_real_data_has_none_of_them():
    assert report.sentence_problems(Library.load()) == []


def test_samples_of_the_new_genres_have_none_of_the_shapes_the_lint_names():
    from storywheel.engine import Engine
    from storywheel.sample import build_story
    bad = [(re.compile(r"\b(fears?|feared|dreaded|dreads?) (fear|dread)\b", re.I), "fears fear"),
           (re.compile(r"\bread (?:twice|aloud) (?:an? |the )", re.I), "read twice a letter"),
           (re.compile(r"\bopened (?:an? |the )?(?:mule|horse|dog|wolf|cat)\b", re.I), "opened an animal"),
           (re.compile(r"\b(?:locked up|swept|aired) the (?:fog-bound |old )?(?:moor|lake|marsh path|cliff path|sea wall|mill pond|forest road|mountain pass)\b", re.I), "locked up a place that has no door")]
    for genre in ("ghost story", "noir", "thriller"):
        e = Engine(seed=17)
        for _ in range(120):
            st = build_story(e, [genre])
            text = " ".join(str(v) for step in ("protagonist", "setting", "premise", "spine", "twist") for v in (st["kept"].get(step) or {}).values())
            for rx, name in bad:
                assert not rx.search(text), (genre, name, text[:240])
