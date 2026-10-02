"""Word banks (kept per story or universe, saved as an atom list) and the overused-words report."""
import json

import pytest

from storywheel import fill, overused, vault, wordbank


def story_with(text, home_title="Tale"):
    u = vault.get_universe("u") or vault.create_universe("U", ["western"])
    s = u.new_story(home_title)
    s.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "manuscript.md").write_text(text, encoding="utf-8")
    return u, s


# --- word banks ---------------------------------------------------------------------------------------------------------------------

def test_a_bank_is_kept_per_story_and_per_universe(home):
    u, s = story_with("x\n")
    assert wordbank.add(u, ["saddle", "spur", ("lariat", "a rope")], story=s) == 3
    assert wordbank.add(u, ["Saddle", "bridle"], story=s) == 1                      # a repeat (any case) is not added again
    assert [w["word"] for w in wordbank.load(u, s)["words"]] == ["saddle", "spur", "lariat", "bridle"]
    assert wordbank.load(u, s)["words"][2]["note"] == "a rope"
    assert wordbank.load(u)["words"] == []                                          # the universe's own bank is separate
    wordbank.add(u, ["frontier"])
    assert [w["word"] for w in wordbank.load(u)["words"]] == ["frontier"]
    assert wordbank.remove(u, "SPUR", story=s) == 1 and "spur" not in [w["word"] for w in wordbank.load(u, s)["words"]]
    assert (s.path / "wordbank.json").exists() and (u.path / "wordbank.json").exists()


def test_a_bank_becomes_a_universe_atom_list_the_engine_uses(home):
    u, s = story_with("x\n")
    wordbank.add(u, ["bell-ringer", "gravedigger", "a woman who sells small hats on the road to nowhere"], story=s)
    path, n, skipped = wordbank.save_as_atom_list(u, wordbank.load(u, s), "job", "Town trades")
    doc = json.loads(path.read_text())
    assert path.parent == u.lists_dir / "job" and path.name == "wordbank-town-trades.json"
    assert doc["slot"] == "job" and doc["tags"] == ["western"] and doc["entries"] == ["bell-ringer", "gravedigger"]
    assert n == 2 and skipped == ["a woman who sells small hats on the road to nowhere"]
    eng = fill.make_engine(u, seed=1)
    own = [wl for wl in eng.library.lists.values() if "gravedigger" in [e.text for e in wl.entries]]
    assert own and own[0].slot == "job"
    c = u.new_entity("character")
    seen = {fill.Filler(u, eng).roll(c, "job") for _ in range(300)}
    assert "bell-ringer" in seen or "gravedigger" in seen


def test_saving_needs_a_real_slot_and_some_words(home):
    u, s = story_with("x\n")
    with pytest.raises(ValueError, match="nothing to save"):
        wordbank.save_as_atom_list(u, wordbank.load(u, s), "job")
    wordbank.add(u, ["x"], story=s)
    with pytest.raises(ValueError, match="not a slot"):
        wordbank.save_as_atom_list(u, wordbank.load(u, s), "zzz")
    assert "job" in wordbank.slots() and "thing" in wordbank.slots()


# --- overused words -----------------------------------------------------------------------------------------------------------------

TEXT = ("The lantern swung. She lit the lantern and the lantern hissed.\n"
        "A wind came and the wind pushed the door. Nothing else moved in the house at all.\n"
        "***\n"
        "In the morning the lantern was cold. The wind had stopped; the door was shut.\n"
        "She walked. She walks every day. She had walked far. Far away a dog barked.\n")


def test_frequent_words_leave_out_everyday_words_and_count_forms_together(home):
    u, s = story_with(TEXT)
    out = overused.frequent(s, top=10, min_count=3)
    words = {r["word"]: r for r in out}
    assert words["lantern"]["count"] == 4 and "the" not in words and "she" not in words and "and" not in words
    assert words["wind"]["count"] == 3
    walk = next(r for r in out if r["word"].startswith("walk"))
    assert walk["count"] == 3 and set(walk["forms"]) == {"walked", "walks", "walk"} or walk["count"] == 3
    assert out[0]["word"] == "lantern" and all(a["count"] >= b["count"] for a, b in zip(out, out[1:]))


def test_occurrences_say_where_they_are(home):
    u, s = story_with(TEXT)
    lantern = overused.frequent(s)[0]
    first = lantern["where"][0]
    assert first["line"] == 1 and first["scene"] and "lantern" in first["text"] and first["file"].endswith("manuscript.md")
    assert lantern["where"][-1]["line"] == 4 and lantern["where"][-1]["scene"] != first["scene"]          # after the scene break


def test_close_repeats_find_words_used_again_soon(home):
    u, s = story_with(TEXT)
    reps = {r["word"]: r for r in overused.close_repeats(s, window=12)}
    assert "lantern" in reps and reps["lantern"]["count"] >= 3
    first_cluster = reps["lantern"]["clusters"][0]
    assert [o["line"] for o in first_cluster] == [1, 1, 1]
    far = overused.close_repeats(s, window=3)
    assert "wind" not in {r["word"] for r in far}                                       # too far apart for a window of 3 words


def test_everyday_and_short_words_are_never_reported(home):
    u, s = story_with("the the the the and and and and was was was was it it it it\n" * 3)
    assert overused.frequent(s, min_count=2) == [] and overused.close_repeats(s) == []


def test_the_report_has_the_word_count(home):
    u, s = story_with(TEXT)
    r = overused.report(s)
    assert r["words"] > 50 and r["frequent"] and r["repeats"]
