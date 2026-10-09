"""Name maker, the sample command, title motifs, and the shape of the new lists."""
import json
import random

from storywheel.engine import Engine
from storywheel.library import Library
from storywheel.markov import NameMaker
from storywheel.sample import build_story, render, sample
from storywheel.steps import STEPS, Ctx, step_by_key


def test_name_maker_invents_new_names_that_look_like_the_list():
    training = [e.text for e in Library.load().lists["last_name/western"].entries]
    maker = NameMaker(training)
    rng = random.Random(1)
    names = {maker.make(rng) for _ in range(200)} - {None}
    assert len(names) > 30
    known = {t.lower() for t in training}
    for n in names:
        assert n.lower() not in known and 4 <= len(n) <= 10 and n[0].isupper()
        assert set(n.lower()) <= set("".join(known))          # only letters the list uses


def test_name_maker_is_repeatable_and_survives_tiny_lists():
    a = [NameMaker(["Anna", "Bert"]).make(random.Random(3)) for _ in range(3)]
    b = [NameMaker(["Anna", "Bert"]).make(random.Random(3)) for _ in range(3)]
    assert a == b
    assert NameMaker(["Al"]).make(random.Random(1)) is None   # nothing to invent from: caller falls back


def test_markov_lists_mix_real_and_invented_names():
    engine = Engine(seed=4)
    wl = engine.library.lists["first_name/western"]
    assert wl.markov == 0.5
    from storywheel.mix import Mix, new_mix
    mix = Mix(new_mix(["western"]), engine.library)
    real = {e.text for e in wl.entries}
    picks = [engine.pick_entry(wl, mix).text for _ in range(400)]
    invented = [p for p in picks if p not in real]
    assert 0.35 < len(invented) / len(picks) < 0.65


def test_title_motif_is_the_title_noun():
    engine = Engine(seed=9)
    story = {"kept": {"genre": {"genre": "western / fairy tale"}}, "seeds": {}}
    from storywheel.mix import sync_base
    sync_base(story)
    nouns = {e.text for wl in engine.library.by_slot["title_noun"] for e in wl.entries}
    checked = 0
    for _ in range(200):
        cand = step_by_key("title").roll(engine, story)
        if cand["motif"] in nouns:
            checked += 1
            assert cand["motif"][:4].lower() in cand["title"].lower()   # plurals: bounty / Bounties
    assert checked > 100


def test_whole_sentence_steps_start_with_a_capital():
    engine = Engine(seed=2)
    story = {"kept": {}, "seeds": {}}
    for _ in range(100):
        for key in ("premise", "twist"):
            text = next(iter(step_by_key(key).roll(engine, story, fresh=True).values()))
            assert text[0].isupper(), text


def test_sample_prints_complete_stories_and_saves_nothing(home):
    lines = []
    sample(Engine(seed=1), ["western", "fairy tale"], 3, out=lines.append, structure="story-spine")
    text = "\n".join(lines)
    for needle in ("1. ", "2. ", "3. ", "Once upon a time", "Every day", "One day", "Because of that",
                   "Until finally", "Ever since then", "Twist:"):
        assert needle in text
    assert not (home / "home").exists() and not (home / "out").exists()


def test_sample_warns_about_unknown_genres():
    lines = []
    sample(Engine(seed=1), ["steampunk"], 1, out=lines.append)
    assert "No profile for steampunk" in lines[0]


def test_build_story_is_repeatable():
    a = render(build_story(Engine(seed=8), ["western"]))
    b = render(build_story(Engine(seed=8), ["western"]))
    assert a == b


def test_name_lists_are_big_enough_to_train_on():
    lib = Library.load()
    for list_id in ("first_name/western", "last_name/western", "first_name/fairy-tale",
                    "last_name/fairy-tale"):
        assert len(lib.lists[list_id].entries) >= 40, list_id


def test_every_list_is_documented_in_sources():
    """SOURCES.md must mention every list file, so provenance never goes stale."""
    from pathlib import Path
    sources = (Path(__file__).parent.parent / "SOURCES.md").read_text()
    missing = [i for i in Library.load().lists
               if i not in sources and not i.startswith(("adj/", "noun/", "verb/"))]
    # everything not covered by a group heading must be named; groups are written as slot/*
    missing = [i for i in missing if i.split("/")[0] + "/*" not in sources]
    assert not missing, missing


def test_a_seed_gives_the_same_stories_in_every_process():
    """Python randomizes string hashing per process; nothing in a seeded run may depend on it."""
    import os
    import subprocess
    import sys
    outputs = set()
    for hash_seed in ("1", "2", "3"):
        env = dict(os.environ, PYTHONHASHSEED=hash_seed)
        out = subprocess.run([sys.executable, "-m", "storywheel", "sample", "western", "fairy tale",
                              "-n", "6", "--seed", "1"], capture_output=True, text=True, env=env,
                             cwd=os.path.dirname(os.path.dirname(__file__)), check=True)
        outputs.add(out.stdout)
    assert len(outputs) == 1
