"""Genre fidelity: a western / fairy tale story should draw its names, jobs, places
and objects from western / fairy tale material, with the rest coming from the
general lists or the wildcard floor."""
from collections import defaultdict

from storywheel.engine import Engine
from storywheel.mix import Mix, sync_base
from storywheel.sample import build_story

THRESHOLD = 0.80
FLAVORED_SLOTS = ["first_name", "last_name", "job", "place", "landmark", "thing",
                  "someone", "disaster"]


def run(genres, stories=200, seed=2024):
    engine = Engine(seed=seed)
    engine.trace = []
    for _ in range(stories):
        build_story(engine, genres)
    story = {"kept": {"genre": {"genre": " / ".join(genres)}}}
    sync_base(story)
    mix = Mix.for_story(story, engine.library)
    weights = mix.weights()
    flavor = {t for t, w in weights.items() if w > 0 and t not in ("general", "modern")}
    return engine, mix, flavor, engine.trace


def test_western_fairy_tale_draws_from_matching_tags():
    engine, mix, flavor, trace = run(["western", "fairy tale"])
    assert {"western", "fairy tale", "historical", "medieval"} <= flavor

    seen = defaultdict(lambda: [0, 0])
    for slot, _list_id, tags, _text in trace:
        seen[slot][1] += 1
        seen[slot][0] += bool(tags & flavor)

    for slot in FLAVORED_SLOTS:
        hits, total = seen[slot]
        assert total >= 30, f"{slot}: only {total} picks, test is not measuring much"
        assert hits / total >= THRESHOLD, f"{slot}: {hits / total:.0%} of {total} match"

    hits = sum(seen[s][0] for s in FLAVORED_SLOTS)
    total = sum(seen[s][1] for s in FLAVORED_SLOTS)
    assert hits / total >= THRESHOLD + 0.05, f"overall {hits / total:.0%}"


def test_the_rest_is_general_modern_or_wildcard():
    engine, mix, flavor, trace = run(["western", "fairy tale"])
    weights = mix.weights()
    wild = misses = 0
    for slot, list_id, tags, _text in trace:
        if slot not in FLAVORED_SLOTS or tags & flavor:
            continue
        misses += 1
        wl = engine.library.lists[list_id]
        wild += mix.tags_weight(wl.tags, weights) == 0        # came through the floor
        assert tags & {"general", "modern"} or mix.tags_weight(wl.tags, weights) == 0, list_id
    assert misses > 0                                         # the floor does let surprises through
    assert wild / sum(1 for t in trace if t[0] in FLAVORED_SLOTS) < 0.15


def test_a_single_genre_stays_in_its_own_world():
    engine, mix, flavor, trace = run(["western"], stories=100)
    names = [t for t in trace if t[0] in ("first_name", "last_name")]
    assert sum(bool(t[2] & flavor) for t in names) / len(names) >= 0.8
    fairy_names = [t for t in trace if t[1] == "first_name/fairy-tale"]
    assert len(fairy_names) / len(names) < 0.2                # only through the floor


def test_excluding_a_tag_removes_it_even_from_the_floor():
    engine = Engine(seed=5)
    engine.trace = []
    for _ in range(100):
        build_story(engine, ["western"], exclude_tags=["fairy tale"])
    assert engine.trace
    assert not [t for t in engine.trace if "fairy tale" in t[2]]
    engine.trace = []
    for _ in range(100):
        build_story(engine, ["western"])
    assert [t for t in engine.trace if "fairy tale" in t[2]]      # without it, the floor lets some in
