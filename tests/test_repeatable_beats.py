"""Repeatable beats: a structure marks beats that can occur several times (min and max); the Wheel adds and removes them, threads follow."""
import pytest

from storywheel import store, structures
from storywheel.engine import Engine
from storywheel.session import Session
from storywheel.steps import steps_for


def story_with(structure="Story Spine"):
    st = store.new_story()
    st["kept"]["genre"] = {"genre": "western", "mood": "cozy"}
    st["kept"]["structure"] = {"structure": structure}
    from storywheel.mix import sync_base
    sync_base(st)
    return st


def session_on_spine(structure="Story Spine", seed=3):
    st = story_with(structure)
    s = Session(st, Engine(seed=seed))
    s.enter(next(i for i, step in enumerate(s.steps) if step.key == "spine"))
    return s


# --- the data ----------------------------------------------------------------------------------------------------------------------

def test_structures_mark_their_repeatable_beats_with_a_minimum_and_maximum():
    spine = structures.get("Story Spine")
    b = spine.beat("because_2")
    assert b.repeat == (1, 4) and b.min == 1 and b.max == 4
    assert structures.get("Three-Act Outline").beat("trials").repeat == (1, 4)
    assert structures.get("Kishōtenketsu").beat("sho").repeat == (1, 3)
    assert spine.beat("once").repeat is None and spine.beat("once").max == 1


def test_expand_numbers_the_occurrences_and_clamps_to_min_and_max():
    spine = structures.get("Story Spine")
    assert [b.key for b in spine.expand()] == spine.keys
    keys = [b.key for b in spine.expand({"because_2": 3})]
    assert keys == ["once", "every_day", "one_day", "because_1", "because_2", "because_2__2", "because_2__3", "until_finally", "ever_since"]
    assert spine.counts({"because_2": 9}) == {"because_2": 4} and spine.counts({"because_2": 0}) == {"because_2": 1}
    three = structures.get("Three-Act Outline").expand({"trials": 2})
    assert [b.label for b in three if b.key.startswith("trials")] == ["Act II: Rising action", "Act II: Rising action (2)"]   # numbered where labels show


def test_an_occurrence_key_finds_its_beat_and_label():
    spine = structures.get("Story Spine")
    assert structures.base_key("because_2__3") == "because_2" and structures.instance_number("because_2__3") == 3
    assert spine.labels["because_2__3"] == "Because of that" and spine.labels.get("because_2__2") == "Because of that"
    assert spine.labels.get("nothing") is None
    assert spine.beat("because_2__3") is spine.beat("because_2")


def test_a_bad_repeat_in_a_user_structure_is_refused(tmp_path):
    (tmp_path / "structures").mkdir()
    (tmp_path / "structures" / "x.json").write_text('{"name": "x", "beats": [{"key": "a", "repeat": {"min": 3, "max": 2}}]}')
    with pytest.raises(structures.StructureError):
        structures.load(tmp_path)


def test_steps_follow_the_story_s_repeats():
    st = story_with()
    base = next(s for s in steps_for(st) if s.key == "spine")
    st["repeats"] = {"because_2": 2}
    more = next(s for s in steps_for(st) if s.key == "spine")
    assert list(more.fields) == list(base.fields)[:5] + ["because_2__2"] + list(base.fields)[5:]


# --- in the Wheel ------------------------------------------------------------------------------------------------------------------

def test_adding_a_beat_rolls_a_new_one_after_the_others():
    s = session_on_spine()
    before = dict(s.fields)
    assert s.can_add_beat("because_2") and not s.can_remove_beat("because_2")
    new = s.add_beat("because_2")
    assert new == "because_2__2"
    assert list(s.fields) == ["once", "every_day", "one_day", "because_1", "because_2", "because_2__2", "until_finally", "ever_since"]
    assert s.fields["because_2__2"].strip() and s.fields["because_2__2"].startswith("Because of that, ")
    assert all(s.fields[k] == before[k] for k in before)                       # the others are untouched
    assert s.cand["_repeats"] == {"because_2": 2} and len(s.hist) == 1
    assert [st.key for st in s.steps][s.i] == "spine" and "because_2__2" in s.step.fields


def test_the_maximum_and_minimum_are_kept():
    s = session_on_spine()
    for _ in range(3):
        assert s.add_beat("because_2")
    assert not s.can_add_beat("because_2") and s.add_beat("because_2") is False
    assert "at most 4" in " ".join(s.take_notes())
    for _ in range(3):
        assert s.remove_beat("because_2")
    assert s.remove_beat("because_2") is False and "at least 1" in " ".join(s.take_notes())


def test_a_beat_that_cannot_repeat_says_so():
    s = session_on_spine()
    assert s.beat_group("once") is None and s.add_beat("once") is False and s.remove_beat("once") is False


def test_removing_a_middle_beat_moves_the_later_ones_up():
    s = session_on_spine()
    s.add_beat("because_2")
    s.add_beat("because_2")
    texts = dict(s.fields)
    assert s.remove_beat("because_2__2")
    assert list(s.fields)[4:7] == ["because_2", "because_2__2", "until_finally"]
    assert s.fields["because_2"] == texts["because_2"] and s.fields["because_2__2"] == texts["because_2__3"]
    assert s.cand["_repeats"] == {"because_2": 2}


def test_removing_the_first_occurrence_keeps_the_others():
    s = session_on_spine(seed=4)          # (a later beat that names a thing the first introduced is rewritten when the first goes: seed 3 draws such a frame)
    s.add_beat("because_2")
    texts = dict(s.fields)
    assert s.remove_beat("because_2")
    assert s.fields["because_2"] == texts["because_2__2"] and "because_2__2" not in s.fields


def test_threads_follow_the_text_when_a_beat_is_added_or_removed():
    for seed in range(1, 12):
        s = session_on_spine(seed=seed)
        s.add_beat("because_2")
        for t in s.cand.get("_threads", {}).values():
            assert t["beat"] in s.fields                                         # every thread points at a beat that exists
        s.remove_beat("because_2__2")
        for t in s.cand.get("_threads", {}).values():
            assert t["beat"] in s.fields and (t["text"] in s.fields[t["beat"]] or t["text"].lower() in s.fields[t["beat"]].lower())


def test_keeping_stores_the_repeats_and_reopening_shows_them():
    s = session_on_spine()
    s.add_beat("because_2")
    s.keep()
    assert s.story["repeats"] == {"because_2": 2} and "because_2__2" in s.story["kept"]["spine"]
    again = Session(s.story, Engine(seed=4))
    again.enter(next(i for i, step in enumerate(again.steps) if step.key == "spine"))
    assert again.cand["_repeats"] == {"because_2": 2} and "because_2__2" in again.fields
    again.remove_beat("because_2__2")
    again.keep()
    assert not again.story.get("repeats") and "because_2__2" not in again.story["kept"]["spine"]


def test_rolling_again_keeps_the_shape_and_changing_structure_resets_it():
    s = session_on_spine()
    s.add_beat("because_2")
    s.roll()
    assert "because_2__2" in s.fields and s.cand["_repeats"] == {"because_2": 2}
    s.reroll_field("because_2__2")
    assert "because_2__2" in s.fields
    s.keep()
    s.enter(1)                                                                    # the structure step
    assert s.story["repeats"] == {"because_2": 2}
    s.hist.append({"structure": "Three-Act Outline"})
    s.cur = len(s.hist) - 1
    s.keep()
    assert "repeats" not in s.story and "spine" not in s.story["kept"]


def test_three_act_and_kishotenketsu_repeat_too():
    s = session_on_spine("Three-Act Outline")
    assert s.add_beat("trials") == "trials__2" and s.fields["trials__2"]
    k = session_on_spine("Kishōtenketsu")
    assert k.add_beat("sho") == "sho__2"
    assert not k.can_add_beat("ten")


def test_stories_render_and_promote_with_repeated_beats(home):
    from storywheel import promote
    s = session_on_spine()
    s.add_beat("because_2")
    s.keep()
    spine = s.story["kept"]["spine"]
    for text in (store.to_markdown(s.story), store.to_plain(s.story)):
        assert spine["because_2__2"] in text.replace("\n", " ") or " ".join(spine["because_2__2"].split()) in " ".join(text.split())
    plan = promote.build_plan(s.story)
    body = next(v for k, v in plan.sections.items() if k == "Story Spine")
    assert spine["because_2__2"] in body
