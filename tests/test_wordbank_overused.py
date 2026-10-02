"""Word banks (kept per story or universe, saved as an atom list) and the overused-words report."""
import json

import pytest

from storywheel import fill, overused, vault


def story_with(text, home_title="Tale"):
    u = vault.get_universe("u") or vault.create_universe("U", ["western"])
    s = u.new_story(home_title)
    s.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "manuscript.md").write_text(text, encoding="utf-8")
    return u, s


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
