"""Words worth learning: picking by frequency, difficulty, part of speech and subject; Known/Learning; migrating old word banks."""
import json
import random
import sys

import pytest

from dictfixture import ZIPF, build_fixture
from storywheel import dictionary, learn, vault, wordbank

@pytest.fixture
def index(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    dictionary.forget()
    monkeypatch.setattr(learn, "zipf", lambda w: ZIPF.get(w, 0.0))
    yield out
    dictionary.forget()


def words(rows):
    return sorted(r["word"] for r in rows)


def test_simple_definitions_are_one_short_line():
    assert learn.simple_definition("a domesticated canine; occurs in many breeds") == "a domesticated canine"
    assert learn.simple_definition("cut of meat (especially mutton) consisting of part of the backbone") == "cut of meat consisting of part of the backbone"
    long = learn.simple_definition("word " * 60)
    assert len(long) <= 112 and long.endswith("…")
    assert learn.simple_definition("") == ""


def test_the_default_batch_leaves_out_everyday_and_obscure_words(index):
    got = words(learn.batch(50, rng=random.Random(1)))
    assert "dog" not in got and "happy" not in got and "tail" not in got and "sad" not in got           # everyday: zipf >= 3.8
    assert "doggy" not in got and "tintinnabulation" not in got                                        # too obscure (< 1.5) or unknown
    assert {"puppy", "kennel", "wretch", "canine", "sprint", "cheerful", "vaccinate"} <= set(got)


@pytest.mark.parametrize("difficulty,expected,absent", [
    ("uncommon", {"puppy", "sprint", "cheerful", "unhappy"}, {"kennel", "wretch", "vaccinate"}),
    ("rare", {"kennel", "canine"}, {"puppy", "sprint", "vaccinate"}),
    ("very rare", {"wretch", "vaccinate"}, {"puppy", "kennel"})])
def test_difficulty_picks_the_band(index, difficulty, expected, absent):
    got = set(words(learn.batch(50, difficulty, rng=random.Random(2))))
    assert expected <= got and not (absent & got)


def test_part_of_speech_filter(index):
    assert set(words(learn.batch(50, pos="verb", rng=random.Random(3)))) == {"sprint", "vaccinate"}
    assert set(words(learn.batch(50, pos="adjective", rng=random.Random(3)))) == {"cheerful", "unhappy"}
    nouns = set(words(learn.batch(50, pos="noun", rng=random.Random(3))))
    assert "puppy" in nouns and "sprint" not in nouns


def test_subject_filter_by_kind_of_meaning_and_by_subject_area(index):
    assert set(words(learn.batch(50, subject="noun.animal", rng=random.Random(4)))) == {"puppy", "canine", "goose"}
    subs = dict((label, key) for label, key in learn.subjects())
    assert subs["Animals"] == "noun.animal" and subs["Moving"] == "verb.motion" and subs["Any subject"] is None


def test_each_row_has_word_part_of_speech_and_a_simple_definition(index):
    rows = {r["word"]: r for r in learn.batch(50, rng=random.Random(5))}
    assert rows["puppy"]["pos"] == "noun" and rows["puppy"]["definition"] == "a young dog" and rows["puppy"]["subject"] == "Animals"
    assert rows["sprint"]["pos"] == "verb" and rows["sprint"]["definition"] == "move fast by using legs"
    assert rows["cheerful"]["pos"] == "adjective"


def test_a_new_batch_never_repeats_words_already_seen(index, tmp_path):
    my = learn.MyWords(tmp_path / "v.json")
    first = learn.batch(3, exclude=my.excluded(), rng=random.Random(6))
    my.mark_seen([r["word"] for r in first])
    second = learn.batch(3, exclude=my.excluded(), rng=random.Random(6))
    assert not (set(words(first)) & set(words(second)))
    pool = set()
    for _ in range(5):
        b = learn.batch(3, exclude=my.excluded(), rng=random.Random(7))
        my.mark_seen([r["word"] for r in b])
        assert not (set(words(b)) & pool)
        pool |= set(words(b))
    assert learn.batch(3, exclude=my.excluded()) == [] or len(learn.batch(3, exclude=my.excluded())) < 3          # the pool runs out


def test_known_and_learning_words_are_never_offered_and_the_state_is_saved(index, tmp_path):
    my = learn.MyWords(tmp_path / "v.json")
    my.mark_known("puppy")
    assert my.mark_learning("kennel", "noun", "a shelter for dogs") is True
    assert my.mark_learning("kennel") is False                                  # already there
    again = learn.MyWords(tmp_path / "v.json")
    assert again.known == {"puppy"} and again.learning_words() == {"kennel"}
    got = words(learn.batch(50, exclude=again.excluded(), rng=random.Random(8)))
    assert "puppy" not in got and "kennel" not in got
    again.mark_known("kennel")                                                  # known: leaves the list
    assert learn.MyWords(tmp_path / "v.json").learning == [] and "kennel" in learn.MyWords(tmp_path / "v.json").known
    again.mark_learning("puppy")                                                # learning again: no longer known
    assert "puppy" not in learn.MyWords(tmp_path / "v.json").known
    assert again.remove("PUPPY") == 1 and again.learning == []


def test_a_word_without_a_meaning_gets_one_from_the_dictionary(index):
    e = learn.fill_definition({"word": "puppy", "pos": "", "definition": "", "note": "from a word bank"})
    assert e["pos"] == "noun" and e["definition"] == "a young dog"
    assert learn.fill_definition({"word": "puppy", "definition": "mine"})["definition"] == "mine"
    assert learn.fill_definition({"word": "zzzqx"}).get("definition", "") == ""


_REAL_ZIPF = learn.zipf


def test_without_wordfreq_it_says_how_to_install_it(index, monkeypatch):
    monkeypatch.setattr(learn, "zipf", _REAL_ZIPF)
    monkeypatch.setitem(sys.modules, "wordfreq", None)                # (an import of it now fails)
    with pytest.raises(learn.WordfreqMissing, match="pipx inject storywheel wordfreq"):
        learn.batch(3)


def test_the_real_wordfreq_package_orders_words_as_expected():
    import importlib
    if importlib.util.find_spec("wordfreq") is None:
        pytest.skip("wordfreq is not installed")
    real = learn
    real.zipf = _REAL_ZIPF
    assert real.zipf("house") > 5 > real.zipf("serendipity") > 2 > real.zipf("sesquipedalian") > 1
    assert real.zipf("qzxjvk") == 0


# --- migrating the old word banks, and the universe word list -----------------------------------------------------------------------

def test_old_word_banks_move_into_my_words_and_are_kept_aside(home, tmp_path):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    (s.path / "wordbank.json").write_text(json.dumps({"name": "x", "words": [{"word": "saddle", "note": "a seat"}, {"word": "spur", "note": ""}]}))
    (u.path / "wordbank.json").write_text(json.dumps({"name": "y", "words": [{"word": "frontier", "note": ""}, {"word": "saddle", "note": ""}]}))
    my = learn.MyWords(tmp_path / "v.json")
    assert wordbank.migrate_banks(my) == 3                                       # saddle only once
    got = {e["word"]: e["note"] for e in my.learning}
    assert set(got) == {"saddle", "spur", "frontier"} and got["saddle"] == "word bank of Thornwood" and got["spur"] == "word bank of The Last Clause" or "word bank of" in got["spur"]
    assert not (s.path / "wordbank.json").exists() and (s.path / "wordbank.json.migrated").exists()
    assert (u.path / "wordbank.json.migrated").exists()
    assert wordbank.migrate_banks(my) == 0                                       # once


def test_add_to_this_universes_word_list_puts_the_word_on_the_slot_list_and_the_engine_uses_it(home):
    from storywheel import fill
    u = vault.create_universe("Thornwood", ["western"])
    path, new = wordbank.add_to_universe_list(u, "bell-ringer", "job")
    assert new and path == u.lists_dir / "job" / "words-added.json"
    assert wordbank.add_to_universe_list(u, "bell-ringer", "job")[1] is False
    wordbank.add_to_universe_list(u, "gravedigger", "job")
    doc = json.loads(path.read_text())
    assert doc["slot"] == "job" and doc["tags"] == ["western"] and doc["entries"] == ["bell-ringer", "gravedigger"]
    eng = fill.make_engine(u, seed=1)
    c = u.new_entity("character")
    seen = {fill.Filler(u, eng).roll(c, "job") for _ in range(300)}
    assert seen & {"bell-ringer", "gravedigger"}
    with pytest.raises(ValueError, match="not a slot"):
        wordbank.add_to_universe_list(u, "x", "zzz")
    with pytest.raises(ValueError, match="one to five words"):
        wordbank.add_to_universe_list(u, "one two three four five six", "job")
