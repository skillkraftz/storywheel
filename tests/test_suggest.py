"""Suggestions: words that fit the story's genres and are not used yet, words related to your characters and places, fresh alternatives
for the most overused words."""
from collections import Counter

import pytest

from dictfixture import ZIPF, build_fixture
from storywheel import dictionary, genrefit, suggest, vault, wordlists


@pytest.fixture
def index(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    monkeypatch.setattr(genrefit, "zipf_function", lambda: (lambda w: ZIPF.get(w) or 0.1))     # (a word the table lacks is rare, not a fragment)
    monkeypatch.setattr(genrefit, "seed_words", lambda lib: {"western": Counter({"goose": 1.0, "run": 1.0, "happy": 1.0, "wolf": 1.0})})
    monkeypatch.setattr(genrefit, "domain_names", lambda lib: {})
    dictionary.forget()
    from storywheel.library import Library
    genrefit.build(out, Library({}, {"western": {"western": 3}}))
    yield out
    dictionary.forget()


@pytest.fixture
def world(home, index):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    s.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "manuscript.md").write_text("The wolf ran. She ran and ran again. Then she ran home, and the leaf ran too, ran fast.\n", encoding="utf-8")
    return u, s


def test_genres_come_from_the_outline_else_the_universe(world):
    u, s = world
    assert suggest.story_genres(u, s) == ["western"]


def test_for_this_story_lists_high_fit_words_the_manuscript_does_not_use(world):
    u, s = world
    verbs = suggest.for_story(u, s, "v")
    words = [r["word"] for r in verbs]
    assert "run" not in words and "ran" not in words                           # used (as ran, a form of run)
    nouns = [r["word"] for r in suggest.for_story(u, s, "n")]
    assert "goose" in nouns and "wolf" not in nouns                              # wolf is in the manuscript
    assert all(r["fit"] >= suggest.MIN_FIT and r["mark"] for r in suggest.for_story(u, s, "n"))
    assert suggest.for_story(u, None, "n", genres=[]) == []                    # no genre, nothing to fit


def test_words_used_in_the_manuscript_are_found_through_their_forms(world):
    u, s = world
    used = suggest.used_forms(s)
    assert {"ran", "run", "wolf", "leaf"} <= used


def test_for_entities_relates_jobs_things_and_places_through_the_dictionary(world):
    u, s = world
    u.new_entity("thing", "the dog")
    u.new_entity("character", "Ann", {"role": "supporting", "job": "wretch"})
    rows = suggest.for_entities(u, s)
    words = {r["word"]: r for r in rows}
    assert {"puppy", "canine", "tail"} & set(words)                             # a narrower word, a broader one, a part of a dog
    assert words["puppy"]["note"].startswith("narrower of dog")
    assert all(r["note"] and r["definition"] for r in rows)
    assert "dog" not in words


def test_fresh_alternatives_follow_each_overused_word(world):
    u, s = world
    rows = suggest.fresh_alternatives(u, s, min_count=3)
    heads = [r for r in rows if r["head"]]
    assert heads and heads[0]["word"] in ("ran", "run") and "times" in heads[0]["definition"]
    alts = [r["word"] for r in rows if not r["head"]]
    assert {"sprint", "dash"} & set(alts) and "run" not in alts and "ran" not in alts
    assert all(r["note"].startswith("instead of ") for r in rows if not r["head"])


def test_no_story_no_alternatives(world):
    u, s = world
    assert suggest.fresh_alternatives(u, None) == []


# --- Vocabulary words that a manuscript already uses ---------------------------------------------------------------------------------

def test_a_word_a_manuscript_uses_is_found_through_its_forms_with_where(world):
    from storywheel import wordsused
    u, s = world
    found = wordsused.find(["run", "wolf", "dog", "leaf"])
    assert set(found) == {"run", "wolf", "leaf"}                               # ran -> run; dog is not written
    assert found["run"]["story"] == "The Last Clause" and found["run"]["line"] == 1
    assert "The Last Clause (Thornwood)" in wordsused.describe(found["run"]) and "line 1" in wordsused.describe(found["run"])


def test_auto_known_marks_the_word_known_removes_it_from_learning_and_notes_where(world, tmp_path):
    from storywheel import learn, wordsused
    my = learn.MyWords(tmp_path / "v.json")
    my.mark_learning("wolf", "noun", "a wild canine")
    my.mark_learning("kennel", "noun", "a shelter")
    got = wordsused.auto_known(my, ["wolf", "kennel", "Leaf"])
    assert set(got) == {"wolf", "leaf"} and "wolf" in my.known and "wolf" not in my.learning_words() and "kennel" in my.learning_words()
    again = learn.MyWords(tmp_path / "v.json")
    assert again.used_where("wolf")["story"] == "The Last Clause"
    entries = again.known_entries()
    assert [e["word"] for e in entries][:2] == ["leaf", "wolf"] and entries[0]["where"]["line"] == 1
    again.mark_learning("wolf")                                                 # learning it again forgets the note
    assert again.used_where("wolf") is None


def test_the_map_is_remembered_until_a_manuscript_changes(world):
    from storywheel import wordsused
    u, s = world
    first = wordsused.used_map()
    assert wordsused.used_map() is first
    (s.manuscript_dir / "manuscript.md").write_text("A goose.\n", encoding="utf-8")
    assert "goose" in wordsused.used_map() and "wolf" not in wordsused.used_map()
