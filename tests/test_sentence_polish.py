"""Batch 8, part A: era and season agree, moods lean toward the genre, and the sentence breaks found in the batch 7 samples cannot come back."""
from collections import Counter

from storywheel import frames, report
from storywheel.engine import Engine
from storywheel.library import Library
from storywheel.report import roll_batch
from storywheel.steps import season_of, steps_for
from storywheel.text import fix_particles, particle_verbs


def setting_step(genres):
    story = {"kept": {"genre": {"genre": " / ".join(genres)}}, "seeds": {}, "mix": {"base": genres, "exclude_tags": [], "exclude_lists": [], "boost": {}}}
    return story, [s for s in steps_for(story) if s.key == "setting"][0]


def test_an_era_that_names_a_season_sets_it():
    assert season_of("the week before Christmas") == "winter"
    assert season_of("a foggy November") == "autumn"
    assert season_of("the flower show summer") == "summer"
    assert season_of("the 1880s") is None
    engine = Engine(seed=4)
    story, step = setting_step(["comedy", "mystery"])
    for _ in range(300):
        got = step.roll(engine, story)
        implied = season_of(got["era"])
        assert implied is None or implied == got["season"], got


def test_rerolling_the_era_passes_over_eras_that_name_another_season():
    engine = Engine(seed=5)
    story, step = setting_step(["comedy", "mystery"])
    current = {"place": "X", "era": "this very week", "season": "summer", "landmark": "y", "rumor": "z"}
    for _ in range(150):
        implied = season_of(step.reroll_value(engine, story, current, "era")[0])
        assert implied in (None, "summer")


def test_rerolling_the_season_follows_the_era():
    engine = Engine(seed=6)
    story, step = setting_step(["comedy"])
    current = {"place": "X", "era": "the week before Christmas", "season": "summer", "landmark": "y", "rumor": "z"}
    assert {step.reroll_value(engine, story, current, "season")[0] for _ in range(12)} == {"winter"}


def test_moods_lean_toward_the_genre():
    from storywheel.mix import Mix, sync_base
    lib = Library.load()
    def weights(genre):
        st = {"kept": {"genre": {"genre": genre}}}
        sync_base(st)
        mix = Mix.for_story(st, lib)
        wl = lib.lists["mood/general"]
        return {e.text: mix.entry_weight(e) for e in wl.entries}
    w = weights("comedy")
    assert w["absurd"] > 10 * w["eerie"]
    assert w["eerie"] <= 0.1 + 1e-9
    h = weights("horror")
    assert h["eerie"] > 10 * h["absurd"]


def test_particle_verbs_take_the_pronoun_in_the_middle():
    verbs = particle_verbs(Library.load())
    assert "traded away" in verbs
    assert fix_particles("Ann traded away it for a song", verbs) == "Ann traded it away for a song"
    assert fix_particles("Ann locked up them", verbs) == "Ann locked them up"
    assert fix_particles("Ann picked up her coat", verbs) == "Ann picked up her coat"      # her could be a possessive
    assert fix_particles("Ann jumped off it", verbs) == "Ann jumped off it"                  # not a particle verb of ours


def test_lint_catches_a_manner_after_a_preposition_and_a_prize_at_a_landmark():
    lib = Library.load()
    from storywheel.library import Entry
    wl = next(wl for wl in lib.lists.values() if wl.id == "secret/general")
    keep = list(wl.entries)
    try:
        wl.entries = keep + [Entry("owes {SOMEONE} a favor from {MANNER}"), Entry("{PRIZE:!inner} at {landmark}")]
        got = {why for _, _, why in report.grammar_problems(lib)}
    finally:
        wl.entries = keep
    assert "a manner phrase follows a preposition" in got
    assert any(w.startswith("a prize is placed at a landmark") for w in got)


def test_the_shipped_data_has_none_of_those_problems():
    assert report.grammar_problems(Library.load()) == []


def test_a_restricted_manner_is_drawn_only_where_a_frame_asks_for_it():
    lib = Library.load()
    speech = [e for wl in lib.by_slot["manner"] for e in wl.entries if "speech" in (e.features or ())]
    assert len(speech) >= 3
    assert not frames.allowed(["speech"], [])
    assert frames.allowed(["speech"], ["speech"])
    assert frames.allowed([], [])
    engine, batch = roll_batch(["fantasy"], 80, 3)
    texts = " ".join(" ".join(s["kept"]["spine"].values()) for s in batch)
    for bad in ("crawled out in the old tongue", "paid their memory of home in silent dread"):
        assert bad not in texts


def test_a_comedy_is_rarely_eerie_and_a_horror_story_often_is():
    def share(genre, moods, n=300):
        _, batch = roll_batch([genre], n, 17)
        return sum(s["kept"]["genre"]["mood"] in moods for s in batch) / n
    dark = {"eerie", "dreadful", "bleak", "uneasy"}
    assert share("comedy", dark) < 0.08
    assert share("mystery", dark) > 0.15
