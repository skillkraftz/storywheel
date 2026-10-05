"""Heist, adventure and coming-of-age (batch 14): their technology follows the era, their places are their own, and each has its core vocabulary."""
import collections

import pytest

from storywheel import genrefit
from storywheel.engine import Engine
from storywheel.library import Library
from storywheel.sample import build_story

NEW = ["heist", "adventure", "coming-of-age"]


@pytest.fixture(scope="module")
def lib():
    return Library.load()


def per_story(genre, stories=120, seed=5):
    e = Engine(seed=seed)
    e.trace = []
    out = []
    for _ in range(stories):
        before = len(e.trace)
        build_story(e, [genre])
        out.append(e.trace[before:])
    return e, out


def features(e, trace):
    found = set()
    for slot, _l, _t, text in trace:
        found.update(f for f in (e.features_of(slot, text) or ()) if f in ("modern", "period"))
    return found


def test_the_three_genres_have_a_default_technology_and_neighbors(lib):
    assert lib.tech["heist"] == "modern" and lib.tech["coming-of-age"] == "modern" and lib.tech["adventure"] == "period"
    import json
    from storywheel import library as lib_mod
    doc = json.loads((lib_mod.DATA / "genres.json").read_text(encoding="utf-8"))
    n = doc["_neighbors"]
    assert {"thriller", "noir"} <= set(n["heist"])
    assert {"fantasy", "western", "sci-fi"} <= set(n["adventure"])
    assert {"romance", "comedy"} <= set(n["coming-of-age"])


@pytest.mark.parametrize("genre", ["heist", "coming-of-age"])
def test_a_story_never_mixes_modern_and_period_technology(genre):
    e, stories = per_story(genre)
    mixed = [sorted({(s, t) for s, _l, _g, t in tr if (e.features_of(s, t) or ()) and {"modern", "period"} & set(e.features_of(s, t) or ())})[:4]
             for tr in stories if features(e, tr) == {"modern", "period"}]
    assert mixed == []
    kinds = collections.Counter(frozenset(features(e, tr)) for tr in stories)
    assert kinds[frozenset({"modern"})] >= 10                          # (technology of today does turn up)
    assert kinds[frozenset({"period"})] >= 1                           # (and so do the period eras)


def test_an_adventure_has_no_modern_technology():
    e, stories = per_story("adventure")
    assert all("modern" not in features(e, tr) for tr in stories)
    assert any("period" in features(e, tr) for tr in stories)


@pytest.mark.parametrize("genre", NEW)
def test_places_and_people_come_only_from_the_genres_own_lists(genre):
    _e, stories = per_story(genre, 150)
    trace = [t for tr in stories for t in tr]
    for slot in ("place", "place_adj", "place_feature", "landmark", "era", "rival"):
        foreign = collections.Counter((lid, text) for s, lid, tags, text in trace if s == slot and genre not in tags and "general" not in tags and tags)
        assert not foreign, (genre, slot, foreign.most_common(5))


@pytest.mark.parametrize("genre", NEW)
def test_the_core_vocabulary_has_forty_words_or_more(genre):
    words = genrefit.core_words()[genre]
    assert len(words["a"]) + len(words["v"]) >= 40
    assert len(words["a"]) >= 15 and len(words["v"]) >= 15


def test_each_genre_has_both_period_and_modern_eras_where_it_should(lib):
    def eras(genre):
        return [e for wl in lib.by_slot["era"] if genre in wl.tags for e in wl.entries]
    assert all("period" in e.features for e in eras("adventure"))
    for genre in ("heist", "coming-of-age"):
        feats = {f for e in eras(genre) for f in e.features}
        assert {"modern", "period"} <= feats
    assert all("modern" in e.features or "period" in e.features for g in NEW for e in eras(g))
