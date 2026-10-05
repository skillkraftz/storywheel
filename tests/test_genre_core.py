"""The genre fit: a hand-picked core vocabulary per genre is the strongest seed, subject domains weigh little, and no numbers or fragments are browsed."""
import json
import sqlite3

import pytest

from dictfixture import ZIPF, build_fixture
from storywheel import dictionary, genrefit, wordlists
from storywheel.library import Entry, Library, WordList

def core():
    return genrefit.core_words()


@pytest.fixture
def index(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    monkeypatch.setattr(genrefit, "zipf_function", lambda: (lambda w: ZIPF.get(w) or 0.1))
    dictionary.forget()
    yield out
    dictionary.forget()


def test_every_written_genre_has_a_core_vocabulary_of_forty_to_eighty_words():
    from storywheel.library import Library
    lib = Library.load()
    written = ["western", "fairy tale", "comedy", "fantasy", "mystery", "horror", "sci-fi", "romance", "ghost story", "noir", "thriller", "heist", "adventure", "coming-of-age"]
    got = core()
    for genre in written:
        words = got[genre]["a"] + got[genre]["v"]
        assert 40 <= len(words) <= 80, (genre, len(words))
        assert len(got[genre]["a"]) >= 15 and len(got[genre]["v"]) >= 15, genre
        assert len(set(words)) == len(words), genre
        assert all(w.replace("-", "").isalpha() and w == w.lower() for w in words), genre
        assert genre in lib.profiles


def test_the_examples_from_the_brief_are_in():
    got = core()
    assert {"lingering", "hushed", "mournful", "faded", "haunt", "linger", "grieve"} <= set(got["ghost story"]["a"] + got["ghost story"]["v"])
    assert {"seedy", "jaded", "rain-slick", "crooked", "double-cross"} <= set(got["noir"]["a"] + got["noir"]["v"])


def test_core_words_fit_their_genre_completely_and_beat_a_subject_domain(index, monkeypatch):
    lib = Library({"w": WordList("w", "thing", ["western"], [Entry("dog")])}, {"western": {"western": 3}, "comedy": {"comedy": 3}, "general": {"general": 1}})
    monkeypatch.setattr(genrefit, "core_words", lambda: {"comedy": {"a": ["happy"], "v": ["run"]}})
    monkeypatch.setattr(genrefit, "domain_names", lambda library: {"comedy": ["veterinary medicine"]})
    genrefit.build(index, lib)
    db = sqlite3.connect(index)
    fit = {(g, w, p): s for g, w, p, s in db.execute("select f.genre, l.w, f.pos, f.score from fit f join lexicon l on l.word_id = f.word_id and l.pos = f.pos")}
    assert fit[("comedy", "happy", "a")] == 100 and fit[("comedy", "run", "v")] == 100
    assert fit[("comedy", "kennel", "n")] == round(100 * genrefit.DOMAIN_SHARE) < 100


def test_subject_domains_weigh_less_than_they_did():
    assert genrefit.DOMAIN_SHARE <= 0.35 and genrefit.CORE_SHARE == 1.0


@pytest.mark.parametrize("word,ok", [("fifty-four", False), ("twoscore", False), ("forty", False), ("ox", False), ("be", False),
                                     ("hundred", False), ("thirty-first", False), ("fourth", False),
                                     ("one-eyed", True), ("lingering", True), ("hard-boiled", True), ("double-cross", True), ("tonic", True), ("gone", True), ("oneness", True), ("fortune", True),
                                     ("mix", True), ("dim", True), ("civil", True), ("second", True), ("first", True)])
def test_numbers_number_words_and_short_words_are_not_browsed(word, ok):
    assert genrefit.is_browsable(word, 300) is ok


def test_an_unknown_short_word_is_a_fragment_but_an_unknown_long_word_is_just_rare():
    assert genrefit.is_browsable("liv", 0) is False
    assert genrefit.is_browsable("xiv", 0) is False and genrefit.is_browsable("xl", 40) is False
    assert genrefit.is_browsable("valorous", 0) is True
    assert genrefit.is_browsable("lamp", 300) is True


def test_the_built_lexicon_has_none_of_them(index):
    lib = Library({"w": WordList("w", "thing", ["western"], [Entry("dog")])}, {"western": {"western": 3}, "general": {"general": 1}})
    genrefit.build(index, lib)
    db = sqlite3.connect(index)
    words = [w for (w,) in db.execute("select w from lexicon")]
    assert words and all(len(w) >= 3 for w in words)


def test_the_stamp_changes_with_the_core_vocabulary(index, monkeypatch):
    lib = Library({"w": WordList("w", "thing", ["western"], [Entry("dog")])}, {"western": {"western": 3}, "general": {"general": 1}})
    db = sqlite3.connect(index)
    before = genrefit.stamp(lib, db)
    monkeypatch.setattr(genrefit, "core_words", lambda: {"western": {"a": ["dusty"], "v": []}})
    assert genrefit.stamp(lib, db) != before
