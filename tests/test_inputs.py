"""What a candidate was built from: field rerolls, stand-ins, stale candidates."""
import pytest

from storywheel import steps, store
from storywheel.ratings import Ratings
from storywheel.session import Session
from conftest import make_engine


def start(home, seed=3):
    s = Session(store.new_story(), make_engine(home, seed=seed), ratings=None)
    s.enter(0)
    return s


def keep_to(s, key):
    while s.step.key != key:
        s.keep()


def index_of(s, key):
    return [st.key for st in s.steps].index(key)


# --- bug 1: a field reroll must not reuse what that field invented --------------------------------------------

def test_rerolling_name_gives_new_names(home):
    s = start(home)
    keep_to(s, "protagonist")
    names = [s.fields["name"]]
    for _ in range(4):
        s.reroll_field("name")
        names.append(s.fields["name"])
    assert len(set(names)) == 5, names


STEP_KEYS = ["genre", "structure", "title", "protagonist", "setting", "premise", "spine", "twist"]


@pytest.mark.parametrize("step_key", STEP_KEYS)
def test_no_field_reroll_repeats_itself_forever(home, step_key):
    """The audit: every field of every step, rerolled, must be able to change."""
    for seed in (5, 6):
        s = start(home, seed=seed)
        keep_to(s, step_key)
        for field in s.field_names:
            if field == "season" and steps.season_of(s.fields.get("era")):
                continue                      # (an era that names a season fixes it: batch 8)
            if field in ("format", "focus", "ending"):
                continue                      # (the format, focus and ending are picked from a list, never rolled: batches 18 and 21)
            seen = {s.fields[field]}
            for _ in range(10):
                s.reroll_field(field)
                seen.add(s.fields[field])
            assert len(seen) > 1, (step_key, field, seed)


@pytest.mark.parametrize("step_key", ["protagonist", "setting", "spine"])
def test_a_reroll_changes_only_its_own_field_unless_text_mentions_it(home, step_key):
    s = start(home, seed=9)
    keep_to(s, step_key)
    field = s.field_names[-1]
    before = dict(s.fields)
    s.reroll_field(field)
    after = s.fields
    changed = {k for k in before if before[k] != after[k]}
    assert field in changed
    assert len(changed) <= 2, changed


def test_rerolling_the_title_does_not_reuse_its_invented_name(home):
    s = start(home, seed=2)
    keep_to(s, "title")
    seen = {s.fields["title"]}
    for _ in range(8):
        s.reroll_field("title")
        seen.add(s.fields["title"])
    assert len(seen) > 4


# --- bug 2: stale stand-ins ------------------------------------------------------------------------------------

def spine_with_standin(home, seed=3):
    s = start(home, seed)
    keep_to(s, "title")
    s.keep()                                   # protagonist is now showing; leave it unkept
    s.jump(index_of(s, "spine"))
    return s


def test_a_spine_rolled_early_records_its_stand_ins(home):
    s = spine_with_standin(home)
    inputs = s.cand["_inputs"]
    assert inputs["first"]["standin"] and inputs["first"]["step"] == "protagonist"
    assert s.standins() and "stand-ins" in s.standin_line()
    assert any("Jumped ahead" in n for n in s.take_notes())


def test_rerolled_beats_use_the_kept_protagonist_not_the_stand_in(home):
    s = spine_with_standin(home)
    stand_in = s.cand["_made"]["first"]
    s.jump(index_of(s, "protagonist"))
    s.edit_field("name", "Stacie Anderson")
    s.keep()
    s.jump(index_of(s, "spine"))
    seen = []
    for beat in list(s.fields)[:4]:
        for _ in range(3):
            s.reroll_field(beat)
            assert stand_in not in s.fields[beat], (beat, s.fields[beat])
            seen.append("Stacie" in s.fields[beat])
    assert any(seen)                                  # and the kept name does turn up


def test_the_showing_candidate_is_flagged_stale_with_a_banner(home):
    s = spine_with_standin(home)
    stand_in = s.cand["_made"]["first"]
    assert s.stale_banner() == ""
    s.jump(index_of(s, "protagonist"))
    s.edit_field("name", "Stacie Anderson")
    s.keep()
    s.jump(index_of(s, "spine"))
    assert s.is_stale()
    assert s.stale_banner().startswith(f"Built for {stand_in}; your protagonist is now Stacie Anderson")
    assert s.stale_tag(s.cur) == " (stale)"
    assert "protagonist" not in s.standins()           # (the setting is still unkept, so still a stand-in)


def test_update_swaps_the_kept_values_into_a_new_candidate(home):
    s = spine_with_standin(home)
    stand_in = s.cand["_made"]["first"]
    s.jump(index_of(s, "protagonist"))
    s.edit_field("name", "Stacie Anderson")
    s.keep()
    s.jump(index_of(s, "spine"))
    old = dict(s.fields)
    n = len(s.hist)
    assert s.update_inputs()
    assert len(s.hist) == n + 1 and s.hist[n - 1:][0]["_inputs"] is not None
    text = " ".join(s.fields.values())
    assert stand_in not in text and "Stacie" in text
    assert " ".join(old.values()).count(stand_in) > 0     # the old candidate is untouched
    assert not s.is_stale() and not s.update_inputs()


def test_a_single_beat_reroll_leaves_the_rest_stale_until_updated(home):
    s = spine_with_standin(home)
    s.jump(index_of(s, "protagonist"))
    s.edit_field("name", "Stacie Anderson")
    s.keep()
    s.jump(index_of(s, "spine"))
    s.reroll_field(list(s.fields)[0])
    assert s.is_stale()                               # the other beats still say the stand-in
    s.update_inputs()
    assert not s.is_stale()


def test_history_candidates_that_were_never_kept_are_marked_stale(home):
    s = spine_with_standin(home)
    s.roll()
    s.jump(index_of(s, "protagonist"))
    s.keep()
    s.jump(index_of(s, "spine"))
    assert all(s.stale_tag(n) for n in range(len(s.hist) - 0) if s.hist[n].get("_inputs") and s.is_stale(n))
    assert any(s.is_stale(n) for n in range(len(s.hist)))


def test_keeping_an_earlier_step_swaps_into_later_kept_stand_in_lines(home):
    s = spine_with_standin(home)
    stand_in = s.cand["_made"]["first"]
    s.keep()                                          # spine kept on a stand-in
    assert stand_in in " ".join(s.story["kept"]["spine"].values())
    s.jump(index_of(s, "protagonist"))
    s.edit_field("name", "Stacie Anderson")
    s.keep()
    kept = " ".join(s.story["kept"]["spine"].values())
    assert stand_in not in kept and "Stacie" in kept
    assert any("Swapped the kept" in n for n in s.take_notes())


def test_jumping_ahead_says_what_is_missing_and_a_normal_walk_does_not(home):
    s = start(home)
    s.jump(index_of(s, "spine"))
    note = [n for n in s.take_notes() if "Jumped ahead" in n]
    assert len(note) == 1 and "Protagonist" in note[0]
    t = start(home)
    keep_to(t, "twist")
    assert not [n for n in t.take_notes() if "Jumped ahead" in n]


def test_a_candidate_built_from_kept_steps_is_not_stale_and_uses_no_stand_ins(home):
    s = start(home)
    keep_to(s, "spine")
    assert not s.is_stale() and not s.standins() and s.standin_line() == ""
    assert not any(v["standin"] for v in s.cand["_inputs"].values())
    assert s.cand["_inputs"]["first"]["value"] == s.story["kept"]["protagonist"]["name"].split()[0]


def test_ignore_dismisses_the_banner_without_changing_the_candidate(home):
    s = spine_with_standin(home)
    s.jump(index_of(s, "protagonist"))
    s.edit_field("name", "Stacie Anderson")
    s.keep()
    s.jump(index_of(s, "spine"))
    before = dict(s.fields)
    n = len(s.hist)
    assert s.stale_banner() and s.ignore_stale()
    assert s.stale_banner() == "" and not s.is_stale()
    assert s.fields == before and len(s.hist) == n
    s.jump(index_of(s, "protagonist"))
    s.edit_field("name", "Moira Quist")                 # a different kept value brings it back
    s.keep()
    s.jump(index_of(s, "spine"))
    assert s.stale_banner()
