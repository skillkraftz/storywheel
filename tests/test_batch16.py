"""Batch 16: frames come only from the story's own genres, and the people around a protagonist fit the protagonist's age."""
import collections

import pytest

from storywheel import steps
from storywheel.engine import Engine
from storywheel.library import Library
from storywheel.mix import Mix
from storywheel.sample import build_story

GENRES = ["western", "fairy tale", "comedy", "fantasy", "mystery", "horror", "sci-fi", "romance", "ghost story", "noir", "thriller",
          "heist", "adventure", "coming-of-age"]


def rolled(genres, n, seed):
    e = Engine(seed=seed)
    e.trace = []
    out = []
    for _ in range(n):
        before = len(e.trace)
        st = build_story(e, genres)
        out.append((st, e.trace[before:]))
    return e, out


def foreign_frames(e, trace, genres):
    """Frames in a story's trace that belong to a genre the story does not have."""
    base = set(genres)
    bad = []
    for slot, lid, tags, text in trace:
        if not e.library.lists[lid].is_template:
            continue
        if tags & base or tags <= {"general"}:
            continue
        bad.append((lid, sorted(tags), text))
    return bad


@pytest.mark.parametrize("genre", GENRES)
def test_every_frame_comes_from_the_storys_own_genres(genre):
    e, stories = rolled([genre], 60, seed=16)
    bad = [b for _st, tr in stories for b in foreign_frames(e, tr, [genre])]
    assert bad == [], bad[:5]
    frames = sum(1 for _st, tr in stories for s, lid, _t, _x in tr if e.library.lists[lid].is_template)
    assert frames >= 60 * 8                                         # (the check is measuring something)


@pytest.mark.parametrize("genres", [["mystery", "western"], ["coming-of-age", "ghost story"], ["sci-fi", "romance"]])
def test_a_blend_uses_the_frames_of_both_genres_and_nothing_else(genres):
    e, stories = rolled(genres, 60, seed=17)
    assert [b for _st, tr in stories for b in foreign_frames(e, tr, genres)] == []
    seen = collections.Counter()
    for _st, tr in stories:
        for _s, lid, tags, _x in tr:
            if e.library.lists[lid].is_template:
                seen.update(t for t in tags if t in genres)
    assert all(seen[g] > 20 for g in genres if any(g in wl.tags for wl in e.library.lists.values() if wl.is_template)), seen


def test_neighbors_still_lend_atoms_but_not_frames():
    e, stories = rolled(["mystery"], 60, seed=18)
    atoms_from_neighbors = sum(1 for _st, tr in stories for s, lid, tags, _x in tr
                               if not e.library.lists[lid].is_template and tags & {"noir", "thriller"})
    assert atoms_from_neighbors > 0
    assert [b for _st, tr in stories for b in foreign_frames(e, tr, ["mystery"])] == []


def test_the_frame_rule_reads_entry_tags_too():
    lib = Library.load()
    mix = Mix({"base": ["mystery"], "exclude_tags": [], "exclude_lists": [], "boost": {}}, lib)
    general = next(wl for wl in lib.by_slot["premise"] if "general" in wl.tags)
    western = [en for en in general.entries if "western" in en.tags]
    plain = [en for en in general.entries if en.tags == ("general",)]
    assert western and not any(mix.frame_entry_ok(en) for en in western) or western == []
    assert all(mix.frame_entry_ok(en) for en in plain) or plain == []


# --- the people around the protagonist know their age ----------------------------------------------------------------------------

ADULT_ONLY_CLOSE = {"{first}'s spouse", "{first}'s son", "{first}'s daughter", "{first}'s best customer", "{first}'s only customer",
                    "{first}'s business partner", "{first}'s apprentice", "{first}'s landlady", "{first}'s old teacher"}
TEEN_CLOSE = {"{first}'s coach", "{first}'s first crush", "{first}'s lab partner", "{first}'s locker neighbor", "{first}'s best friend",
              "{first}'s homeroom teacher", "{first}'s stepfather"}


def test_close_people_carry_age_bands(lib=None):
    lib = Library.load()
    close = {en.text: en.features for wl in lib.by_slot["close"] for en in wl.entries}
    for text in ADULT_ONLY_CLOSE:
        assert not steps.person_fits(close[text], {"teen"}) and steps.person_fits(close[text], {"adult"}), text
    for text in TEEN_CLOSE:
        assert steps.person_fits(close[text], {"teen"}) and not steps.person_fits(close[text], {"adult"}), text
    for text in ("{first}'s mother", "{first}'s father", "{first}'s sister", "{first}'s grandmother", "{first}'s oldest friend"):
        assert steps.person_fits(close[text], {"teen"}), text
    assert all({"human", "friendly"} <= set(close[t]) for t in close if t not in ("{first}'s dog", "{first}'s ex"))


def test_a_coming_of_age_protagonist_has_parents_friends_and_coaches_never_a_spouse_or_customers():
    e, stories = rolled(["coming-of-age"], 120, seed=19)
    close = collections.Counter(t for _st, tr in stories for s, _l, _g, t in tr if s == "close")
    assert not set(close) & ADULT_ONLY_CLOSE, set(close) & ADULT_ONLY_CLOSE
    assert {"{first}'s coach", "{first}'s first crush", "{first}'s best friend", "{first}'s mother"} & set(close)
    people = [(s, t) for _st, tr in stories for s, _l, _g, t in tr if s in ("close", "someone")]
    assert all(steps.person_fits(e.features_of(s, t), {"teen"}) for s, t in people)
    text = " ".join(str(v) for st, _tr in stories for step in st["kept"].values() for v in step.values() if isinstance(v, str))
    for word in ("only customer", "best customer", "spouse", "an old flame", "a jilted fiancé"):
        assert word not in text, word


@pytest.mark.parametrize("genre", ["mystery", "romance", "western"])
def test_an_adult_protagonist_never_gets_a_teenagers_people(genre):
    e, stories = rolled([genre], 80, seed=20)
    close = {t for _st, tr in stories for s, _l, _g, t in tr if s == "close"}
    assert not close & {"{first}'s first crush", "{first}'s lab partner", "{first}'s locker neighbor", "{first}'s coach"}


def test_a_blend_with_coming_of_age_drops_romances_adult_suitors():
    e, stories = rolled(["coming-of-age", "romance"], 80, seed=21)
    people = {t for _st, tr in stories for s, _l, _g, t in tr if s == "someone"}
    assert not people & {"an old flame", "a jilted fiancé", "a wealthy suitor", "a rival suitor", "a nervous groom", "a determined bride"}


def test_the_builder_rolls_a_teen_characters_want_with_teen_people(home):
    from storywheel import fill, vault
    u = vault.create_universe("Elm Grove", ["coming-of-age"])
    c = u.new_entity("character", "Bo Hart", {"age": "15", "job": "paperboy"})
    f = fill.Filler(u, fill.make_engine(u, seed=4))
    for _ in range(25):
        for key in ("want", "need", "flaw", "secret"):
            text = f.roll(c, key)
            for word in ("spouse", "only customer", "best customer", "son", "daughter", "apprentice"):
                assert f"their {word}" not in text and f"Bo's {word}" not in text, (key, text)
