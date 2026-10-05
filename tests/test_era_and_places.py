"""Technology follows the era (no burner phone in the 1920s), and noir and thriller keep to their own kinds of places, people and shapes."""
import collections

import pytest

from storywheel import report
from storywheel.engine import Engine
from storywheel.library import Library
from storywheel.mix import sync_base
from storywheel.sample import build_story
from storywheel.steps import Ctx


@pytest.fixture(scope="module")
def lib():
    return Library.load()


def story_for(genres, **kept):
    story = {"kept": {"genre": {"genre": " / ".join(genres)}, **kept}, "seeds": {}, "atoms": {}}
    sync_base(story)
    return story


def trace_of(genre, stories=150, seed=3):
    e = Engine(seed=seed)
    e.trace = []
    for _ in range(stories):
        build_story(e, [genre])
    return e, e.trace


def test_atoms_carry_a_modern_or_period_feature_where_it_matters(lib):
    modern = [e.text for wl in lib.lists.values() if "thriller" in wl.tags and not wl.is_template for e in wl.entries if "modern" in (e.features or ())]
    for text in ("a burner phone", "a flash drive", "a pocket recorder", "a GPS tracker", "a hotel key card", "a stolen laptop", "a hard drive", "hacker"):
        assert text in modern, text
    assert len(modern) >= 15


def test_every_era_of_noir_is_a_period_and_every_era_of_thriller_is_modern(lib):
    for wl in lib.by_slot["era"]:
        if "noir" in wl.tags:
            assert all("period" in (e.features or ()) for e in wl.entries), wl.id
        if "thriller" in wl.tags:
            assert all("modern" in (e.features or ()) for e in wl.entries), wl.id
    assert "thriller" not in next(wl for wl in lib.by_slot["era"] if wl.id == "era/early-century").tags     # (the 1920s are not thriller eras any more)
    assert all("period" in (e.features or ()) for wl in lib.by_slot["era"] if wl.id == "era/early-century" for e in wl.entries)


def test_a_story_set_in_the_1920s_never_gets_modern_technology():
    e = Engine(seed=5)
    for _ in range(120):
        story = story_for(["thriller"], setting={"era": "the 1920s", "place": "Port Argent", "landmark": "the safe house", "season": "autumn", "rumor": "x"})
        c = Ctx(e, story)
        assert c.tech() == "period"                          # ("the 1920s" is an era of the early-century list)
        for slot in ("thing", "job", "message", "someone", "landmark", "disaster"):
            text = c.draw(slot)
            assert "modern" not in (e.features_of(slot, text) or ()), (slot, text)


def test_a_present_day_story_never_gets_period_technology():
    e = Engine(seed=6)
    for _ in range(120):
        story = story_for(["noir"], setting={"era": "present day", "place": "Port Mercer", "landmark": "the pool hall", "season": "autumn", "rumor": "x"})
        c = Ctx(e, story)
        assert c.tech() == "modern"
        for slot in ("thing", "job", "message", "someone"):
            text = c.draw(slot)
            assert "period" not in (e.features_of(slot, text) or ()), (slot, text)


def test_a_thriller_with_no_era_yet_assumes_modern_and_a_noir_assumes_period(lib):
    e = Engine(seed=1)
    assert Ctx(e, story_for(["thriller"])).tech() == "modern"
    assert Ctx(e, story_for(["noir"])).tech() == "period"
    assert Ctx(e, story_for(["western"])).tech() == "period"                 # (batch 15: western, fairy tale and fantasy are period too)
    assert Ctx(e, story_for(["noir", "thriller"])).tech() is None             # (they disagree: no rule)
    assert Ctx(e, story_for(["noir", "western"])).tech() == "period"
    assert Ctx(e, story_for(["mystery"])).tech() is None


def test_noir_stories_have_no_modern_technology_and_thrillers_no_period_technology():
    for genre, banned in (("noir", "modern"), ("thriller", "period")):
        e, trace = trace_of(genre)
        bad = [(slot, text) for slot, _l, _t, text in trace if banned in (e.features_of(slot, text) or ())]
        assert bad == [], (genre, bad[:5])
    e, trace = trace_of("thriller")
    used = {text for slot, _l, _t, text in trace if "modern" in (e.features_of(slot, text) or ())}
    assert len(used) >= 8                                                    # (the modern atoms do turn up)


def test_noir_and_thriller_places_come_only_from_their_own_lists():
    for genre in ("noir", "thriller"):
        _e, trace = trace_of(genre, 200)
        for slot in ("place", "place_adj", "place_feature", "landmark", "era"):
            foreign = collections.Counter((lid, text) for s, lid, tags, text in trace if s == slot and genre not in tags and "general" not in tags and tags)
            assert not foreign, (genre, slot, foreign.most_common(5))


def test_a_blend_still_uses_both_genres_places():
    e = Engine(seed=4)
    e.trace = []
    for _ in range(150):
        build_story(e, ["noir", "western"])
    tags = {t for slot, _l, tags, _x in e.trace if slot in ("place", "landmark") for t in tags}
    assert {"noir", "western"} <= tags


def test_ghost_story_keeps_to_its_own_people_places_and_titles():
    _e, trace = trace_of("ghost story", 200)
    for slot in ("someone", "rival", "job", "title_noun", "title_adj", "landmark", "message", "hiding", "era"):
        foreign = collections.Counter(lid for s, lid, tags, _t in trace if s == slot and "ghost story" not in tags and "general" not in tags and tags)
        assert not foreign, (slot, foreign.most_common(3))


def test_the_new_genres_story_shapes_are_their_own():
    for genre in ("ghost story", "noir", "thriller"):
        _e, trace = trace_of(genre, 100)
        shapes = [(lid, tags) for s, lid, tags, _t in trace if s in ("premise", "twist", "climax", "escalation", "once", "inciting")]
        own = sum(1 for _l, tags in shapes if genre in tags)
        assert own / len(shapes) >= 0.9, (genre, own, len(shapes))


def test_no_banned_leak_words_in_the_samples():
    """Sentences from the three genres read like the genre: no detective words in a ghost story or thriller."""
    import re
    detective = re.compile(r"\b(alibi|suspects?|motive)\b", re.I)
    for genre in ("ghost story", "thriller"):
        e = Engine(seed=9)
        for _ in range(80):
            st = build_story(e, [genre])
            text = " ".join(str(v) for step in ("premise", "twist", "spine", "body") for v in (st["kept"].get(step) or {}).values())
            assert not detective.search(text), (genre, text[:200])
