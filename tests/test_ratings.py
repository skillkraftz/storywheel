"""Ratings: storage, the gentle down-weighting, and the report."""
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from storywheel import ratings as R
from storywheel.engine import Engine
from storywheel.library import Entry, Library, WordList
from storywheel.ratings import Ratings, format_report, provenance
from storywheel.sample import build_story
from storywheel.steps import Ctx
from conftest import make_library, mix_for

ROOT = Path(__file__).resolve().parent.parent


def rate(r, line, value, frame=None, atoms=(), story="s1", step="spine", field="because_1"):
    return r.rate(story, step, field, line, value, frame, atoms, title="A Story")


FRAME = {"slot": "reaction", "template": "{ACT_PERSON} {SOMEONE} {MANNER}"}
ATOMS = [["act_person", "enchanted"], ["someone", "a mule"]]


# --- storage -------------------------------------------------------------------------------------------------

def test_ratings_survive_a_save_and_load(tmp_path):
    r = Ratings(tmp_path / "ratings.json")
    rate(r, "Wade enchanted a mule.", -1, FRAME, ATOMS)
    again = Ratings.load(tmp_path)
    assert again.rating_of("s1", "spine", "because_1", "Wade enchanted a mule.") == -1
    saved = json.loads((tmp_path / "ratings.json").read_text())
    assert saved["version"] == 1 and saved["ratings"][0]["frame"] == FRAME and saved["ratings"][0]["atoms"] == ATOMS


def test_a_damaged_file_means_a_fresh_start(tmp_path):
    (tmp_path / "ratings.json").write_text("{ not json")
    assert Ratings.load(tmp_path).current() == []


def test_pressing_the_same_rating_again_clears_it_and_the_other_one_replaces_it(tmp_path):
    r = Ratings(tmp_path / "r.json")
    assert rate(r, "line", -1) == -1
    assert rate(r, "line", -1) == 0                       # again: cleared
    assert r.current() == []
    assert rate(r, "line", -1) == -1 and rate(r, "line", 1) == 1     # the other key: replaced
    assert [x["rating"] for x in r.current()] == [1]


def test_a_line_is_rated_per_story_step_field_and_text(tmp_path):
    r = Ratings(tmp_path / "r.json")
    rate(r, "same words", -1, story="a")
    rate(r, "same words", 1, story="b")
    assert r.rating_of("a", "spine", "because_1", "same words") == -1
    assert r.rating_of("b", "spine", "because_1", "same words") == 1
    assert r.rating_of("a", "spine", "because_1", "other words") == 0


def test_provenance_splits_the_frame_from_its_atoms():
    lib = Library.load()
    frame, atoms = provenance(lib, [["reaction", "{ACT_PERSON} {SOMEONE} {MANNER}"], ["act_person", "trusted"],
                                    ["someone", "a stranger"], ["manner", "at dawn"]])
    assert frame == {"slot": "reaction", "template": "{ACT_PERSON} {SOMEONE} {MANNER}"}
    assert atoms == [["act_person", "trusted"], ["someone", "a stranger"], ["manner", "at dawn"]]
    assert provenance(lib, [["job", "baker"]]) == (None, [["job", "baker"]])
    assert provenance(lib, None) == (None, [])


# --- the gentle part ----------------------------------------------------------------------------------------------

def test_one_dislike_is_no_evidence_at_all(tmp_path):
    r = Ratings(tmp_path / "r.json")
    rate(r, "a line", -1, FRAME, ATOMS)
    assert r.frame_factor(FRAME["slot"], FRAME["template"]) == 1.0
    assert r.combo_factor("act_person", "enchanted", [("someone", "a mule")]) == 1.0
    assert r.atom_factor("someone", "a mule") == 1.0


def test_a_frame_that_keeps_getting_minus_is_drawn_less_but_never_ruled_out(tmp_path):
    r = Ratings(tmp_path / "r.json")
    factors = []
    for n in range(12):
        rate(r, f"line {n}", -1, FRAME, [])
        factors.append(r.frame_factor(FRAME["slot"], FRAME["template"]))
    assert factors[0] == 1.0                              # net -1: nothing yet
    assert factors[1] == pytest.approx(0.8)               # net -2: a fifth less
    assert factors[2] == pytest.approx(0.64)
    assert all(a >= b for a, b in zip(factors, factors[1:]))
    assert factors[-1] == R.FRAME[1] == 0.25              # the floor


def test_pluses_outweigh_minuses_on_the_same_frame(tmp_path):
    r = Ratings(tmp_path / "r.json")
    for n in range(5):
        rate(r, f"bad {n}", -1, FRAME, [])
    low = r.frame_factor(FRAME["slot"], FRAME["template"])
    for n in range(4):
        rate(r, f"good {n}", 1, FRAME, [])
    assert r.frame_factor(FRAME["slot"], FRAME["template"]) > low
    for n in range(2):
        rate(r, f"better {n}", 1, FRAME, [])
    assert r.frame_factor(FRAME["slot"], FRAME["template"]) == 1.0


def test_atom_pairs_are_down_weighted_harder_than_single_atoms(tmp_path):
    r = Ratings(tmp_path / "r.json")
    for n in range(4):
        rate(r, f"line {n}", -1, None, ATOMS)
    pair = r.combo_factor("act_person", "enchanted", [("someone", "a mule")])
    single = r.atom_factor("act_person", "enchanted")
    assert pair == pytest.approx(0.7 ** 3) and single == pytest.approx(0.9 ** 2)    # net -4: the pair is on strike 3, the atom on 2
    assert pair < single
    assert r.atom_bias("act_person", "enchanted", [("someone", "a mule")]) < pair
    assert r.combo_factor("act_person", "enchanted", [("someone", "a fox")]) == 1.0    # other pairings untouched


def test_the_down_weighting_actually_changes_what_is_drawn(tmp_path):
    verbs = [Entry("buried"), Entry("hid"), Entry("stole")]
    things = [Entry("a locked box"), Entry("a bell")]
    lib = make_library([WordList("act_thing/a", "act_thing", ["general"], verbs),
                        WordList("thing/a", "thing", ["general"], things)])
    ratings = Ratings(tmp_path / "r.json")
    for n in range(6):
        rate(ratings, f"l{n}", -1, None, [["act_thing", "buried"], ["thing", "a locked box"]])
    def share(with_ratings):
        engine = Engine(seed=11, library=lib, ratings=ratings if with_ratings else None)
        c = Ctx(engine, {"kept": {"protagonist": {"first": "Wade"}}, "seeds": {}, "atoms": {}})
        from storywheel import frames
        hits = 0
        for _ in range(1500):
            engine._recent.clear(); c.drawn.clear(); c.atom_log.clear()
            hits += frames.solve(c, "{first} {ACT_THING} {THING}") == "{first} buried a locked box"
        return hits / 1500
    assert share(True) < share(False) * 0.6              # the disliked pairing is much rarer...
    assert share(True) > 0                               # ...but not gone


def test_a_disliked_frame_is_drawn_less_in_real_stories(tmp_path):
    lib = Library.load()
    target = next(e for e in lib.lists["reaction/general"].entries if e.text == "{ACT_PERSON} {SOMEONE} {MANNER}")
    ratings = Ratings(tmp_path / "r.json")
    for n in range(10):
        rate(ratings, f"l{n}", -1, {"slot": "reaction", "template": target.text}, [])
    def count(r):
        engine = Engine(seed=5, ratings=r)
        engine.trace = []
        for _ in range(300):
            build_story(engine, ["western"], structure="story-spine")
        return sum(1 for slot, _l, _t, text in engine.trace if slot == "reaction" and text == target.text)
    assert count(ratings) < count(None) * 0.7


def test_a_seeded_sample_never_reads_ratings(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    env = dict(os.environ, STORYWHEEL_HOME=str(home), STORYWHEEL_OUT=str(tmp_path / "out"))
    run = lambda: subprocess.run([sys.executable, "-m", "storywheel", "sample", "western", "-n", "3", "--seed", "4"],
                                 capture_output=True, text=True, env=env, cwd=ROOT).stdout
    before = run()
    r = Ratings(home / "ratings.json")
    for n in range(10):
        rate(r, f"l{n}", -1, {"slot": "reaction", "template": "{ACT_PERSON} {SOMEONE} {MANNER}"}, ATOMS)
    assert run() == before


# --- the report -------------------------------------------------------------------------------------------------------

def test_the_report_lists_worst_lines_frames_and_pairs(tmp_path):
    r = Ratings(tmp_path / "r.json")
    for n in range(3):
        rate(r, f"Wade enchanted a mule {n}.", -1, FRAME, ATOMS, field=f"f{n}")
    rate(r, "Wade fed a mule.", 1, {"slot": "reaction", "template": "{ACT_THING} {THING}"}, [["act_thing", "fed"]])
    text = format_report(r, 5)
    assert "4 rated lines: 1 liked, 3 disliked" in text
    assert "Worst-rated lines" in text and "Wade enchanted a mule 0." in text
    assert "frame: [reaction] {ACT_PERSON} {SOMEONE} {MANNER}" in text and "atoms: enchanted, a mule" in text
    assert "Frames that keep getting -" in text and "-3  (3 - / 0 +)" in text and "now drawn at 64%" in text
    assert '"a mule" + "enchanted"' in text or '"enchanted" + "a mule"' in text
    assert "A Story" in text


def test_the_report_orders_by_how_much_a_frame_is_disliked(tmp_path):
    r = Ratings(tmp_path / "r.json")
    other = {"slot": "reaction", "template": "{ACT_THING} {THING}"}
    for n in range(4):
        rate(r, f"bad {n}", -1, FRAME, [], field=f"a{n}")
    rate(r, "meh", -1, other, [], field="b")
    worst = r.worst_frames(5)
    assert worst[0][4] == FRAME["template"] and worst[0][0] == -4
    assert r.worst_lines(1)[0]["text"].startswith("bad")


def test_the_report_command(tmp_path):
    home = tmp_path / "home"
    env = dict(os.environ, STORYWHEEL_HOME=str(home), STORYWHEEL_OUT=str(tmp_path / "out"))
    out = subprocess.run([sys.executable, "-m", "storywheel", "report"], capture_output=True, text=True, env=env, cwd=ROOT)
    assert "No ratings yet" in out.stdout
    r = Ratings(home / "ratings.json")
    rate(r, "A bad line.", -1, FRAME, ATOMS)
    out = subprocess.run([sys.executable, "-m", "storywheel", "report", "-n", "3"], capture_output=True, text=True,
                         env=env, cwd=ROOT)
    assert "A bad line." in out.stdout and "[reaction]" in out.stdout
