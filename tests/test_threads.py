"""Threads: spine beats introduce things and people, later beats pick them up,
and rerolling the introducing beat keeps the story straight."""
import copy

import pytest

from storywheel import store
from storywheel import threads as T
from storywheel.engine import Engine
from storywheel.mix import sync_base
from storywheel.refs import carry_threads, inherit, reroll_field, with_field
from storywheel.sample import build_story
from storywheel.steps import STEPS, Ctx

SPINE = next(s for s in STEPS if s.key == "spine")
LOCKED = {"text": "a locked box", "beat": "one_day"}


def cand_with_box():
    return {
        "once": "Once upon a time, Wade lived in Dry Fork.",
        "every_day": "Every day, Wade worked.",
        "one_day": "One day, Wade found a locked box under the floor.",
        "because_1": "Because of that, Wade hid the locked box at the mill.",
        "because_2": "Because of that, the sheriff demanded the locked box.",
        "until_finally": "Until finally, Wade burned the locked box.",
        "ever_since": "Ever since then, the locked box is ash.",
        "_threads": {"thing": dict(LOCKED)},
    }


class FakeSpine:
    """A stand-in step whose reroll returns what we tell it to."""
    threads = True

    def __init__(self, value, introduced):
        self.value, self.introduced = value, introduced

    def reroll_value(self, engine, story, current, field, threads=None, atoms=None, made=None):
        return self.value, self.introduced, []


# --- the small pieces ------------------------------------------------------------------

def test_definite_turns_a_into_the_and_leaves_names_alone():
    assert T.definite("a locked box") == "the locked box"
    assert T.definite("an old friend") == "the old friend"
    assert T.definite("Wade's first love") == "Wade's first love"
    assert T.definite("two men in suits") == "two men in suits"


def test_templates_that_use_a_live_thread_are_preferred_and_dead_ones_are_not_used():
    t = "{first} gave {the_thing} back"
    assert T.weight("{first} left", {}) == 1
    assert T.weight(t, {"thing": LOCKED}) == T.PREFERRED
    assert T.weight(t, {}) == 0
    assert T.weight("{the_thing} and {the_someone}", {"thing": LOCKED}) == 0     # needs both


def test_swap_replaces_both_article_forms_everywhere_but_the_skipped_field():
    c = cand_with_box()
    n = T.swap(c, LOCKED, {"text": "a rusted revolver", "beat": "one_day"}, skip=("one_day",))
    assert n == 4
    assert c["because_1"].endswith("hid the rusted revolver at the mill.")
    assert c["one_day"].endswith("a locked box under the floor.")


# --- recording during a roll ------------------------------------------------------------------

def test_spine_rolls_record_threads_that_match_their_beats():
    engine = Engine(seed=3)
    story = {"kept": {}, "seeds": {}}
    seen = 0
    for _ in range(150):
        cand = SPINE.roll(engine, story)
        for kind, t in cand["_threads"].items():
            assert kind in T.THREAD_KINDS
            forms = T.intro_forms(t)
            assert any(f in cand[t["beat"]] for f in forms), (t, cand[t["beat"]])
            first = next(n for n, v in cand.items() if not n.startswith("_") and any(T.mentions(v, f) for f in forms))
            assert first == t["beat"]                      # introduced where it says
            seen += 1
    assert seen > 150


def test_later_beats_say_the_not_a():
    engine = Engine(seed=4)
    story = {"kept": {}, "seeds": {}}
    callbacks = 0
    for _ in range(200):
        cand = SPINE.roll(engine, story)
        order = [n for n in cand if not n.startswith("_")]
        for kind, t in cand["_threads"].items():
            later = order[order.index(t["beat"]) + 1:]
            callbacks += sum(T.definite(t["text"]) in cand[n] for n in later if T.definite(t["text"]) != t["text"])
    assert callbacks > 40                                  # threads do come back


def test_a_live_thread_makes_threaded_templates_much_likelier():
    engine = Engine(seed=5)
    story = {"kept": {}, "seeds": {}}
    with_thing = Ctx(engine, story, threads={"thing": dict(LOCKED)}, record=True)
    without = Ctx(engine, story, threads={}, record=True)
    n = 1500
    def draws(ctx):
        out = []
        for _ in range(n):
            engine._recent.clear()                    # a real story draws each beat once
            out.append(ctx.draw("climax"))
        return out
    used = sum("{the_" in t for t in draws(with_thing))
    unused = sum("{the_" in t for t in draws(without))
    assert unused == 0                                    # impossible without threads
    assert used / n > 0.2


def test_the_reference_falls_back_to_a_fresh_block_and_introduces_it():
    engine = Engine(seed=6)
    c = Ctx(engine, {"kept": {}, "seeds": {}}, threads={}, record=True)
    c.field = "one_day"
    text = c["the_thing"]
    assert text and c.threads["thing"]["text"] == text and c.threads["thing"]["beat"] == "one_day"
    assert c["the_thing"] == text                          # same words afterwards


# --- rerolling the beat that introduced a thread ---------------------------------------------------------

def test_reroll_updates_the_thread_and_the_beats_that_used_it():
    new = reroll_field(FakeSpine("One day, Wade won a rusted revolver in a card game.",
                                  {"thing": {"text": "a rusted revolver", "beat": "one_day"}}),
                       None, {}, cand_with_box(), "one_day")
    assert new["_threads"] == {"thing": {"text": "a rusted revolver", "beat": "one_day"}}
    assert new["because_1"] == "Because of that, Wade hid the rusted revolver at the mill."
    assert new["until_finally"] == "Until finally, Wade burned the rusted revolver."
    assert "locked box" not in " ".join(v for k, v in new.items() if not k.startswith("_"))


def test_reroll_without_a_new_thing_keeps_the_old_one_alive_in_a_later_beat():
    new = reroll_field(FakeSpine("One day, a stranger rode in.", {}), None, {}, cand_with_box(), "one_day")
    assert new["_threads"]["thing"]["beat"] == "because_1"          # first mention is now its introduction
    assert new["because_1"] == "Because of that, Wade hid a locked box at the mill."
    assert new["until_finally"].endswith("burned the locked box.")  # later ones still say 'the'


def test_reroll_retires_a_thread_nobody_else_mentions():
    c = {"once": "Once upon a time, Wade lived.", "one_day": "One day, Wade found a locked box.",
         "until_finally": "Until finally, Wade left.", "_threads": {"thing": dict(LOCKED)}}
    new = reroll_field(FakeSpine("One day, it rained.", {}), None, {}, c, "one_day")
    assert new["_threads"] == {}


def test_reroll_of_a_beat_that_did_not_introduce_anything_leaves_threads_alone():
    c = cand_with_box()
    new = reroll_field(FakeSpine("Every day, Wade whittled.", {}), None, {}, c, "every_day")
    assert new["_threads"] == c["_threads"]
    assert new["every_day"] == "Every day, Wade whittled."


def test_a_beat_cannot_pick_up_a_thread_from_a_later_beat():
    engine = Engine(seed=8)
    story = {"kept": {}, "seeds": {}}
    later = {"text": "a zeppelin made of cheese", "beat": "until_finally"}
    current = {k: "x" for k in SPINE.fields}
    for _ in range(150):
        value, introduced, _atoms = SPINE.reroll_value(engine, story, current, "one_day", {"thing": later})
        assert "zeppelin" not in value
        assert "thing" not in introduced              # already introduced further on: not ours


def test_real_rerolls_keep_threads_consistent():
    engine = Engine(seed=9)
    story = {"kept": {}, "seeds": {}}
    for _ in range(60):
        cand = SPINE.roll(engine, story)
        for field in SPINE.fields:
            cand = reroll_field(SPINE, engine, story, cand, field)
            for kind, t in cand["_threads"].items():
                assert any(f in cand[t["beat"]] for f in T.intro_forms(t))
                earlier = [n for n in SPINE.fields if n == t["beat"]]
                assert earlier


def test_editing_a_beat_by_hand_resettles_threads():
    c = cand_with_box()
    new = with_field(c, "one_day", "One day, Wade found nothing at all.")
    assert new["_threads"]["thing"]["beat"] == "because_1"
    whole = inherit({k: v for k, v in c.items() if not k.startswith("_")}, c)
    assert whole["_threads"] == c["_threads"]
    assert c["_threads"] == {"thing": LOCKED}                 # the original is not touched


def test_changed_threads_carry_into_later_kept_steps():
    story = {"kept": {"spine": {}, "twist": {"twist": "The locked box was a fake. A locked box is no use."}}}
    n = carry_threads(story, 5, {"thing": dict(LOCKED)}, {"thing": {"text": "a pistol", "beat": "one_day"}})
    assert n == 2
    assert story["kept"]["twist"]["twist"] == "The pistol was a fake. A pistol is no use."


# --- story, markdown, sample ---------------------------------------------------------------------------------

def test_build_story_keeps_threads_and_markdown_lists_them():
    story = build_story(Engine(seed=11), ["western", "fairy tale"])
    assert story["threads"]
    md = store.to_markdown(story)
    assert "## Threads" in md
    for kind, t in story["threads"].items():
        assert f"- **{kind.title()}:** {t['text']}" in md
        assert T.BEAT_LABELS[t["beat"]] in md


def test_no_threads_no_section():
    story = store.new_story()
    story["kept"] = {"title": {"title": "X", "motif": "x"}, "spine": {"once": "Once upon a time, x."}}
    assert "Threads" not in store.to_markdown(story)


def test_threads_survive_a_save_and_load(home):
    story = build_story(Engine(seed=12), ["western"])
    store.save(story)
    assert store.load(story["id"])["threads"] == story["threads"]


def test_old_story_files_get_an_empty_thread_list(home):
    story = build_story(Engine(seed=12), ["western"])
    del story["threads"]
    store.save(story)
    assert store.load(story["id"])["threads"] == {}


def test_settle_does_not_mutate_when_nothing_changed():
    c = cand_with_box()
    before = copy.deepcopy(c)
    assert T.settle(c) == before


def test_a_thread_is_not_mistaken_for_a_longer_phrase():
    assert T.mentions("a stranger asked", "a stranger")
    assert not T.mentions("gives in whenever a stranger's praise appears", "a stranger")
    assert not T.mentions("two strangers met", "a stranger")
    assert T.mentions("They left the locked box here.", "the locked box")
    c = {"once": "Krista gives in whenever a stranger's praise appears.", "one_day": "A stranger asked Krista to leave.",
         "_threads": {"someone": {"text": "a stranger", "beat": "one_day"}}}
    assert T.settle(c)["_threads"]["someone"]["beat"] == "one_day"
