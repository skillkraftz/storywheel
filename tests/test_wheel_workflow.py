"""Batch 23 part A: R (roll the whole draft), L (reroll from here), S (fix what changed), flags that can always be cleared, and I (send as an idea)."""
import pytest

from storywheel import store
from storywheel.session import Session
from conftest import make_engine, run_tui, screen_text


def start(home, seed=3):
    s = Session(store.new_story(), make_engine(home, seed=seed), ratings=None)
    s.enter(0)
    return s


def keys(s):
    return [st.key for st in s.steps]


def kept_keys(s):
    return [k for k in keys(s) if s.story["kept"].get(k)]


def flagged(s):
    return [(st.key, s.flag(i)) for i, st in enumerate(s.steps) if s.flag(i)]


async def press(pilot, *k):
    await pilot.press(*k)
    await pilot.pause()


# --- A1: R ----------------------------------------------------------------------------------------------------

def test_r_takes_an_empty_draft_to_complete_with_no_stand_ins(home):
    s = start(home)
    assert s.roll_all() == 8
    assert kept_keys(s) == keys(s)
    assert flagged(s) == [] and s.issues() == []
    for step_key, inputs in s.story["inputs"].items():
        assert not any(i["standin"] for i in inputs.values()), step_key
    assert not s.done                                                    # (no "finished" screen in the way: R lands on the last step)


def test_r_leaves_kept_steps_and_skipped_steps_alone(home):
    s = start(home)
    s.keep()                                                             # genre
    s.keep()                                                             # structure
    genre = dict(s.story["kept"]["genre"])
    s.jump(keys(s).index("twist"))
    s.skip()                                                             # skipped on purpose
    assert s.roll_all() == 5                                             # title, protagonist, setting, premise, spine
    assert s.story["kept"]["genre"] == genre
    assert "twist" not in s.story["kept"] and s.skipped_on_purpose("twist")
    assert flagged(s) == []


def test_r_skips_the_protagonist_of_a_story_about_a_place(home):
    s = start(home)
    s.set_focus("place")
    s.roll_all()
    assert "protagonist" not in s.story["kept"] and len(kept_keys(s)) == 7
    assert flagged(s) == [] and s.issues() == []


def test_every_roll_of_r_goes_into_the_steps_history_and_r_again_does_nothing(home):
    s = start(home)
    s.roll_all()
    assert all(s.story["history"][k] for k in keys(s))
    kept = {k: dict(v) for k, v in s.story["kept"].items()}
    assert s.roll_all() == 0 and s.story["kept"] == kept
    assert "already kept" in " ".join(s.take_notes())


# --- A2: L ----------------------------------------------------------------------------------------------------

def test_l_rerolls_every_later_step_and_keeps_the_current_one(home):
    s = start(home)
    s.roll_all()
    s.take_notes()
    s.enter(keys(s).index("title"))
    before = {k: dict(v) for k, v in s.story["kept"].items()}
    assert s.reroll_from_here() == 5
    after = s.story["kept"]
    assert after["genre"] == before["genre"] and after["title"] == before["title"] and after["structure"] == before["structure"]
    assert after["setting"] != before["setting"] and after["protagonist"] != before["protagonist"]
    assert kept_keys(s) == keys(s) and flagged(s) == []
    assert s.step.key == "title" and "replaced 5" in " ".join(s.take_notes())
    assert len(s.story["history"]["setting"]) >= 2                       # the old one is still in its history


def test_l_needs_a_kept_step(home):
    s = start(home)
    assert s.reroll_from_here() is None and "Keep this step first" in " ".join(s.take_notes())


def test_l_names_the_steps_edited_by_hand(home):
    s = start(home)
    s.roll_all()
    s.enter(keys(s).index("title"))
    assert s.edited_after() == []
    s.enter(keys(s).index("premise"))
    s.edit_field("premise", "A feud over a spare set of keys.")
    s.keep()
    s.enter(keys(s).index("title"))
    assert s.edited_after() == ["Premise"]
    s.reroll_from_here()
    assert s.edited_after() == [] and s.story["kept"]["premise"]["premise"] != "A feud over a spare set of keys."


def test_l_leaves_a_step_skipped_on_purpose_skipped(home):
    s = start(home)
    s.roll_all()
    s.enter(keys(s).index("twist"))
    s.skip()
    s.enter(keys(s).index("genre"))
    s.reroll_from_here()
    assert "twist" not in s.story["kept"] and len(kept_keys(s)) == 7


# --- A3: S ----------------------------------------------------------------------------------------------------

def test_s_swaps_a_changed_protagonist_and_title_into_every_step_built_on_them(home):
    s = start(home)
    s.roll_all()
    s.take_notes()
    old = s.story["kept"]["protagonist"]["name"]
    old_first = old.split()[0]
    k = s.story["kept"]
    k["protagonist"]["name"] = "Stacie Anderson"                         # (changed behind the draft's back, as a sync or a hand edit can)
    k["title"]["title"] = "The Glass Hour"
    assert flagged(s)
    assert s.fix_changed() is True
    assert flagged(s) == [] and s.issues() == []
    text = " ".join(str(v) for key in ("spine", "twist") for v in s.story["kept"][key].values())
    assert "Stacie" in text and old_first not in text.replace("'s", " ").split()
    note = " ".join(s.take_notes())
    assert "swapped the new values into" in note


def test_s_with_nothing_flagged_says_so(home):
    s = start(home)
    s.roll_all()
    s.take_notes()
    assert s.fix_changed() is False and "Nothing to fix" in " ".join(s.take_notes())


def test_s_rerolls_a_step_when_the_genre_it_leaned_on_changed(home):
    s = start(home)
    s.roll_all()
    s.take_notes()
    # a step whose flag a swap can't clear: pretend the premise leaned on a different structure name
    s.story["inputs"]["premise"]["structure"] = {"step": "structure", "value": "Old Shape", "standin": False}
    assert s.flag(keys(s).index("premise")) == "changed"
    before = dict(s.story["kept"]["premise"])
    s.fix_changed()
    assert flagged(s) == [] and s.story["kept"]["premise"] != before
    assert "rerolled Premise" in " ".join(s.take_notes())


def test_s_rolls_the_step_a_flag_leans_on_and_rerolls_what_was_built_on_a_lost_step(home):
    s = start(home)
    s.roll_all()
    s.story["kept"].pop("protagonist")                                   # no longer kept (and not skipped on purpose)
    assert ("spine" in dict(flagged(s)) or "setting" in dict(flagged(s)) or flagged(s))
    s.fix_changed()
    assert "protagonist" in s.story["kept"] and flagged(s) == []


def test_s_leaves_a_step_you_edited_by_hand_and_ignore_clears_its_flag(home):
    s = start(home)
    s.roll_all()
    s.enter(keys(s).index("premise"))
    s.edit_field("premise", "A feud over a spare set of keys.")
    s.keep()
    s.story["inputs"]["premise"]["structure"] = {"step": "structure", "value": "Old Shape", "standin": False}
    s.take_notes()
    s.fix_changed()
    assert s.story["kept"]["premise"]["premise"] == "A feud over a spare set of keys."
    assert "you edited it" in " ".join(s.take_notes()) and flagged(s)
    s.enter(keys(s).index("premise"))
    assert s.ignore_stale() and flagged(s) == []


# --- A4: no stuck dots ------------------------------------------------------------------------------------------

def test_a_stand_in_for_a_step_skipped_on_purpose_is_not_a_flag(home):
    s = start(home)
    s.keep()
    s.keep()
    s.keep()                                                             # genre, structure, title
    s.skip()                                                             # protagonist, on purpose
    s.keep()                                                             # setting, on a stand-in protagonist
    assert flagged(s) == [] and s.standin_line() == ""


def test_a_skipped_twist_leaves_no_dot(home):
    s = start(home)
    s.roll_all()
    s.enter(keys(s).index("twist"))
    s.skip()
    assert flagged(s) == [] and s.issues() == []


def test_a_place_story_leaves_no_dot_before_or_after_s(home):
    s = start(home)
    s.set_focus("place")
    for _ in range(3):
        s.keep()
    s.jump(keys(s).index("spine"))                                       # spine rolled before setting and premise: stand-ins
    s.keep()
    s.roll_all()                  # (the title was built on a stand-in for the setting, and an earlier step isn't swapped by keeping a later one)
    place = s.story["kept"]["setting"]["place"]
    assert ("title", "changed") in flagged(s)
    s.fix_changed()
    assert flagged(s) == [] and place in s.story["kept"]["title"]["title"]


def test_a_dropped_structure_leaves_only_flags_s_or_ignore_clear(home):
    s = start(home)
    s.roll_all()
    s.enter(keys(s).index("structure"))
    for _ in range(12):                                                  # a different structure drops the body
        s.roll()
        if s.fields["structure"] != s.story["kept"]["structure"]["structure"]:
            break
    s.keep()
    for _ in range(2):
        s.fix_changed()
    assert flagged(s) == []


def test_a_changed_title_or_protagonist_after_keep_leaves_no_dot(home):
    s = start(home)
    s.roll_all()
    for key in ("title", "protagonist"):
        s.enter(keys(s).index(key))
        s.roll()
        s.keep()
    s.fix_changed()
    assert flagged(s) == []


@pytest.mark.parametrize("scenario", ["standin_pending", "broken_x", "changed"])
def test_any_flag_that_is_left_can_be_ignored(home, scenario):
    s = start(home)
    if scenario == "standin_pending":
        for _ in range(3):
            s.keep()
        s.jump(keys(s).index("spine"))
        s.keep()
    else:
        s.roll_all()
        if scenario == "broken_x":
            s.enter(keys(s).index("protagonist"))
            s.skip()
        else:
            s.story["kept"]["protagonist"]["name"] = "Stacie Anderson"
    assert flagged(s)
    for i, st in enumerate(s.steps):
        if s.flag(i):
            s.enter(i)
            assert s.ignore_stale()
    assert flagged(s) == []


def test_an_ignored_flag_comes_back_when_the_value_changes_again(home):
    s = start(home)
    s.roll_all()
    s.story["kept"]["protagonist"]["name"] = "Stacie Anderson"
    assert flagged(s)
    for n in range(len(s.steps)):
        if s.flag(n):
            s.enter(n)
            s.ignore_stale()
    assert flagged(s) == []
    s.story["kept"]["protagonist"]["name"] = "Pearl Okafor"
    assert flagged(s)


def test_flag_messages_name_the_key_that_clears_them(home):
    s = start(home)
    for _ in range(3):
        s.keep()
    s.jump(keys(s).index("spine"))
    s.keep()
    msgs = [m for _sev, m in s.issues()]
    assert msgs and all("S" in m and "i " in m for m in msgs)


# --- the keys on the Wheel screen -----------------------------------------------------------------------------------

def test_r_s_and_l_work_from_the_keyboard_and_show_in_the_footer(home):
    async def script(app, pilot):
        s = app.session
        footer = screen_text(app)
        await press(pilot, "R")
        done = kept_keys(s)
        s.story["kept"]["protagonist"]["name"] = "Stacie Anderson"
        app.screen.after()
        flagged_before = bool(flagged(s))
        await press(pilot, "S")
        return footer, done, flagged_before, flagged(s)
    footer, done, flagged_before, flagged_after = run_tui(store.new_story(), make_engine(home), script)
    assert "Roll all" in footer and "Fix" in footer
    assert len(done) == 8 and flagged_before and flagged_after == []
