"""Word forms: classify a form of a word, and give the same form of another word."""
import pytest

from dictfixture import build_fixture
from storywheel import dictionary, inflect


@pytest.mark.parametrize("original,base,kind", [
    ("running", "run", "ing"), ("ran", "run", "past"), ("run", "run", "base"), ("runs", "run", "s"), ("geese", "goose", "s"),
    ("wolves", "wolf", "s"), ("dogs", "dog", "s"), ("walked", "walk", "past"), ("walking", "walk", "ing"), ("tried", "try", "past"),
    ("tries", "try", "s"), ("made", "make", "past"), ("making", "make", "ing"), ("written", "write", "pp"), ("wrote", "write", "past"),
    ("better", "good", "er"), ("best", "good", "est"), ("happier", "happy", "er"), ("happiest", "happy", "est"), ("bigger", "big", "er"),
    ("stopped", "stop", "past"), ("children", "child", "s"), ("went", "go", "past"), ("gone", "go", "pp"), ("sang", "sing", "past"),
    ("lying", "lie", "ing"), ("taxes", "tax", "s"), ("boxes", "box", "s"), ("began", "begin", "past"), ("beginning", "begin", "ing")])
def test_classify(original, base, kind):
    assert inflect.classify(original, base) == kind


def test_classify_returns_none_for_something_that_is_not_a_form():
    assert inflect.classify("table", "run") is None


@pytest.mark.parametrize("base,kind,pos,expected", [
    ("sprint", "ing", "verb", "sprinting"), ("sprint", "past", "verb", "sprinted"), ("sprint", "s", "verb", "sprints"),
    ("dash", "s", "verb", "dashes"), ("dash", "ing", "verb", "dashing"), ("stop", "past", "verb", "stopped"), ("visit", "ing", "verb", "visiting"),
    ("make", "ing", "verb", "making"), ("bake", "past", "verb", "baked"), ("try", "past", "verb", "tried"), ("try", "s", "verb", "tries"),
    ("take", "past", "verb", "took"), ("take", "pp", "verb", "taken"), ("begin", "ing", "verb", "beginning"), ("lie", "ing", "verb", "lying"),
    ("goose", "s", "noun", "geese"), ("dog", "s", "noun", "dogs"), ("city", "s", "noun", "cities"), ("box", "s", "noun", "boxes"),
    ("leaf", "s", "noun", "leaves"), ("hero", "s", "noun", "heroes"), ("photo", "s", "noun", "photos"), ("child", "s", "noun", "children"),
    ("happy", "er", "adjective", "happier"), ("glad", "er", "adjective", "gladder"), ("big", "est", "adjective", "biggest"),
    ("joyful", "er", "adjective", "more joyful"), ("joyful", "est", "adjective", "most joyful"), ("good", "er", "adjective", "better"),
    ("nice", "er", "adjective", "nicer"), ("noble", "est", "adjective", "noblest"),
    ("domestic dog", "s", "noun", "domestic dogs"), ("take to the woods", "ing", "verb", "taking to the woods"),
    ("run away", "past", "verb", "ran away"), ("sprint", "er", "verb", "sprint"), ("dog", "ing", "noun", "dog"), ("quick", "s", "adjective", "quick")])
def test_inflect(base, kind, pos, expected):
    assert inflect.inflect(base, kind, pos) == expected


def test_reinflect_matches_the_form_of_the_original():
    r = inflect.reinflect
    assert r("running", "run", "sprint", "verb") == "sprinting"
    assert r("ran", "run", "sprint", "verb") == "sprinted"
    assert r("ran", "run", "dash", "verb") == "dashed"
    assert r("geese", "goose", "swan", "noun") == "swans"
    assert r("wolves", "wolf", "hound", "noun") == "hounds"
    assert r("happier", "happy", "glad", "adjective") == "gladder"
    assert r("happiest", "happy", "joyful", "adjective") == "most joyful"
    assert r("run", "run", "sprint", "verb") == "sprint"                      # the base form stays the base form
    assert r("table", "run", "sprint", "verb") == "sprint"                    # not a form of it: unchanged


def test_the_part_of_speech_is_guessed_from_the_dictionary_when_not_given(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path)
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    dictionary.forget()
    db = dictionary.connect()
    assert inflect.reinflect("running", "run", "sprint", db=db) == "sprinting"
    assert inflect.reinflect("dogs", "dog", "wolf", db=db) == "wolves"
    assert inflect.reinflect("happier", "happy", "glad", db=db) == "gladder"
    assert inflect.reinflect("ran", "run", "unknownword", db=db) == "unknownworded"        # no entry: a verb for a past form
    dictionary.forget()


def test_capital_letters_are_left_alone():
    assert inflect.inflect("sprint", "ing", "verb") == "sprinting"
