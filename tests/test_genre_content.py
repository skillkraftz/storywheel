"""The genres written so far (comedy, fantasy, mystery) the way western and fairy tale were: names with Markov training sets, atoms of every kind,
frames for every beat; about 80% of picks from the genre's own material, no recognizable repeats, nothing the lint objects to, and blends that
still read like both."""
from collections import defaultdict

import pytest

from storywheel import report
from storywheel.library import Library
from storywheel.mix import Mix, sync_base
from storywheel.sample import build_story
from storywheel.engine import Engine

FLAVORED_SLOTS = ["first_name", "last_name", "job", "place", "landmark", "thing", "someone", "disaster"]
GENRES = ["comedy", "fantasy"]
BLENDS = [["comedy", "fairy tale"]]
GENERAL = {"fantasy": 0.15}            # how much of the neutral, all-purpose material a genre lets in (0.3 unless its content says otherwise)
ATOM_SLOTS = ["someone", "thing", "disaster", "message", "hiding", "act_person", "act_thing", "act_place", "act_message", "do_thing", "do_person",
              "habit_thing", "habit_person", "habit_place", "manner", "prize", "deadline", "motive", "vice", "value", "temptation", "trait",
              "rival", "landmark", "job", "title_adj", "title_noun", "era"]
TEMPLATE_SLOTS = ["premise", "twist", "title", "once", "routine", "inciting", "reaction", "escalation", "climax", "resolution", "want", "need",
                  "flaw", "secret", "rumor", "act_setup", "act_incident", "act_turn", "act_midpoint", "act_trials", "act_crisis", "act_climax",
                  "act_resolution", "ki", "sho", "ten", "ketsu"]


def run(genres, stories=200, seed=2024):
    engine = Engine(seed=seed)
    engine.trace = []
    for _ in range(stories):
        build_story(engine, genres)
    story = {"kept": {"genre": {"genre": " / ".join(genres)}}}
    sync_base(story)
    mix = Mix.for_story(story, engine.library)
    flavor = {t for t, w in mix.weights().items() if w > 0 and t not in ("general", "modern")}
    return engine, flavor, engine.trace


def shares(genres, **kw):
    engine, flavor, trace = run(genres, **kw)
    seen = defaultdict(lambda: [0, 0])
    for slot, _lid, tags, _text in trace:
        seen[slot][1] += 1
        seen[slot][0] += bool(tags & flavor)
    return seen, flavor, trace


@pytest.fixture(scope="module")
def lib():
    return Library.load()


def genre_atoms(lib, slot, tag):
    n = 0
    for wl in lib.by_slot[slot]:
        n += len(wl.entries) if tag in wl.tags else sum(tag in e.tags for e in wl.entries)
    return n


@pytest.mark.parametrize("genre", GENRES)
def test_the_genre_has_a_profile_and_its_modern_share_is_chosen_not_defaulted(lib, genre):
    profile = lib.profiles[genre]
    assert profile[genre] >= 3 and profile["general"] == GENERAL.get(genre, 0.3) and "modern" in profile


@pytest.mark.parametrize("genre", GENRES)
def test_names_are_big_enough_to_train_the_name_maker(lib, genre):
    for slot in ("first_name", "last_name"):
        lists = [wl for wl in lib.by_slot[slot] if genre in wl.tags]
        assert lists and all(wl.markov == 0.5 and len(wl.entries) >= 40 for wl in lists), (genre, slot)


@pytest.mark.parametrize("genre", GENRES)
@pytest.mark.parametrize("slot", ATOM_SLOTS)
def test_genre_lives_on_the_atoms(lib, genre, slot):
    assert genre_atoms(lib, slot, genre) >= 6, (genre, slot)


@pytest.mark.parametrize("genre", GENRES)
@pytest.mark.parametrize("slot", TEMPLATE_SLOTS)
def test_every_beat_has_frames_for_the_genre(lib, genre, slot):
    lists = [wl for wl in lib.by_slot[slot] if genre in wl.tags]
    assert sum(len(wl.entries) for wl in lists) >= 6, (genre, slot)


@pytest.mark.parametrize("genre", GENRES)
def test_every_atom_of_the_genre_is_annotated_where_it_matters(lib, genre):
    """Things, people, places and disasters say what they are (features), so the frames can tell what fits."""
    for slot, needed in (("thing", 0.5), ("someone", 0.3), ("landmark", 0.9), ("disaster", 0.8), ("rival", 0.5)):
        entries = [e for wl in lib.by_slot[slot] if genre in wl.tags for e in wl.entries]
        annotated = sum(bool(e.features) for e in entries)
        assert annotated / len(entries) >= needed, (genre, slot, annotated, len(entries))


@pytest.mark.parametrize("genre", GENRES)
def test_a_single_genre_draws_about_four_fifths_from_its_own_material(genre):
    seen, flavor, _ = shares([genre])
    assert genre in flavor
    for slot in FLAVORED_SLOTS:
        hits, total = seen[slot]
        assert total >= 30, (genre, slot, total)
        assert hits / total >= 0.77, f"{genre} {slot}: {hits / total:.0%} of {total}"
    hits = sum(seen[s][0] for s in FLAVORED_SLOTS)
    total = sum(seen[s][1] for s in FLAVORED_SLOTS)
    assert hits / total >= 0.82, f"{genre} overall {hits / total:.0%}"


@pytest.mark.parametrize("genre", GENRES)
def test_the_voice_follows_in_verbs_and_abstractions(genre):
    seen, flavor, trace = shares([genre])
    for slot in ("act_thing", "manner", "prize", "deadline", "vice", "value", "trait"):
        picks = [t for t in trace if t[0] == slot]
        assert len(picks) >= 60, (genre, slot)
        assert sum(bool(t[2] & flavor) for t in picks) / len(picks) >= 0.5, (genre, slot)


@pytest.mark.parametrize("genre", GENRES)
def test_no_repeats_and_nothing_far_above_its_fair_share(genre):
    r = report.build_report([genre], stories=200, seed=101)
    assert len(r["heavy_lines"]) == 0, r["heavy_lines"][:5]
    assert not r["flagged"], r["flagged"][:5]
    assert r["lint"] == []


@pytest.mark.parametrize("genres", BLENDS)
def test_blends_read_like_both_and_do_not_repeat(genres):
    seen, flavor, _ = shares(genres)
    for slot in FLAVORED_SLOTS:
        hits, total = seen[slot]
        assert hits / total >= 0.7, f"{genres} {slot}: {hits / total:.0%} of {total}"
    hits = sum(seen[s][0] for s in FLAVORED_SLOTS)
    total = sum(seen[s][1] for s in FLAVORED_SLOTS)
    assert hits / total >= 0.78, f"{genres} overall {hits / total:.0%}"
    assert all(g in flavor for g in genres)
    r = report.build_report(genres, stories=200, seed=101)
    assert len(r["heavy_lines"]) <= 1 and not r["flagged"] and r["lint"] == []
    # both sides really turn up: each genre's own tag is in a fair share of the picks of the main slots
    _, _, trace = run(genres, stories=100)
    for g in genres:
        own = sum(1 for slot, _l, tags, _t in trace if slot in FLAVORED_SLOTS and g in tags)
        assert own / sum(1 for t in trace if t[0] in FLAVORED_SLOTS) >= 0.2, g


def test_fantasy_and_fairy_tale_are_different_worlds(lib):
    """Fantasy is epic and high (orders, ruins, old wars, magic with a cost); fairy tale is woodcutters and talking foxes. No list is shared."""
    for wl in lib.lists.values():
        assert not ({"fantasy", "fairy tale"} <= set(wl.tags)), wl.id
    both = [(wl.id, e.text) for wl in lib.lists.values() for e in wl.entries if {"fantasy", "fairy tale"} <= set(e.tags)]
    assert len(both) <= 5, both                                           # a few things really are both (a castle ruin, a cursed mirror)
    for mine, other in (("fantasy", "fairy tale"), ("fairy tale", "fantasy")):
        _, flavor, trace = run([mine], stories=100)
        picks = [t for t in trace if t[0] in FLAVORED_SLOTS]
        theirs = sum(1 for t in picks if other in t[2] and mine not in t[2])
        assert theirs / len(picks) < 0.08, (mine, other, theirs / len(picks))
    seen, flavor, _ = shares(["fairy tale"])
    assert "fantasy" not in flavor and "medieval" in flavor


def test_fantasy_uses_no_modern_names_or_jobs_beyond_the_floor():
    _, flavor, trace = run(["fantasy"], stories=150)
    names = [t for t in trace if t[0] in ("first_name", "last_name", "job")]
    assert sum(1 for t in names if "modern" in t[2]) / len(names) < 0.02
