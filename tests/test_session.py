"""The Session: what each key does, with no screen involved."""
import pytest

from storywheel import store
from storywheel.ratings import Ratings
from storywheel.session import Session
from storywheel.steps import public
from conftest import make_engine


@pytest.fixture
def sess(home):
    story = store.new_story()
    s = Session(story, make_engine(home), ratings=Ratings(home / "home" / "ratings.json"))
    s.enter(0)
    return s


def to_step(sess, key):
    while sess.step.key != key:
        sess.keep()


def test_a_new_session_shows_the_first_step_with_one_roll(sess):
    assert sess.i == 0 and sess.step.key == "genre" and len(sess.hist) == 1 and sess.cur == 0
    assert set(sess.field_names) == {"genre", "mood"}


def test_roll_adds_a_new_candidate_and_shows_it(sess):
    first = dict(sess.fields)
    sess.roll()
    assert len(sess.hist) == 2 and sess.cur == 1 and sess.fields != first


def test_keep_saves_moves_on_and_marks_the_step(sess, home):
    kept = dict(sess.fields)
    sess.keep()
    assert sess.step.key == "structure" and sess.story["kept"]["genre"] == kept
    assert sess.marker(0) == "kept" and sess.marker(1) == "current" and sess.marker(2) == "pending"
    assert list((home / "home" / "stories").glob("*.json"))             # saved
    assert sess.story["mix"]["base"]                                     # the mix follows the genre


def test_back_and_skip(sess):
    assert not sess.back() and "first step" in sess.take_notes()[0]
    sess.keep()
    sess.skip()
    assert sess.step.key == "title" and sess.marker(1) == "skipped"
    assert sess.back() and sess.step.key == "structure"
    assert sess.story["kept"].get("structure") is None


def test_going_back_shows_what_was_kept(sess):
    kept = dict(sess.fields)
    sess.keep()
    sess.back()
    assert sess.fields == kept


def test_jump_to_any_step(sess):
    sess.jump(3)
    assert sess.step.key == "protagonist" and sess.i == 3
    assert sess.marker(0) == "pending"


def test_rerolling_one_field_changes_only_that_field(sess):
    to_step(sess, "protagonist")
    before = dict(sess.fields)
    sess.reroll_field("job")
    after = sess.fields
    assert after["job"] != before["job"] and len(sess.hist) == 2
    assert after["name"] == before["name"] and after["age"] == before["age"] and after["trait"] == before["trait"]


def test_editing_a_field_updates_mentions_in_the_same_item(sess):
    to_step(sess, "setting")
    cur = sess.fields
    assert sess.edit_field("landmark", "the new lighthouse")
    new = sess.fields
    assert new["landmark"] == "the new lighthouse" and sess.cand["_src"] == "edited"
    if cur["landmark"] in cur["rumor"]:
        assert "the new lighthouse" in new["rumor"]
    assert not sess.edit_field("landmark", "the new lighthouse")        # no change: nothing added


def test_replace_fields_for_the_whole_item(sess):
    to_step(sess, "setting")
    new = dict(sess.fields, place="Nowhere")
    assert sess.replace_fields(new) and sess.fields["place"] == "Nowhere"
    assert not sess.replace_fields(dict(sess.fields))


def test_pick_and_field_history(sess):
    to_step(sess, "protagonist")
    sess.reroll_field("job")
    sess.reroll_field("job")
    values = sess.field_values("job")
    assert len(values) == 3
    old = values[0]
    assert sess.pick_value("job", old) and sess.fields["job"] == old
    assert sess.fields["name"] == sess.hist[0]["name"]                  # the rest is untouched
    assert sess.pick(0) and sess.cur == 0 and not sess.pick(99)


def test_change_summary_shows_what_changed_between_rolls(sess):
    to_step(sess, "protagonist")
    sess.reroll_field("job")
    summary = sess.change_summary(1)
    assert summary.startswith("job: ") and "name" not in summary
    assert sess.change_summary(0).count("·") == 2                        # the first one: a summary of all
    sess.edit_field("job", "wheelwright")
    assert sess.source_tag(sess.cur) == " (your edit)"


def test_a_change_to_an_earlier_step_updates_later_ones(sess):
    to_step(sess, "twist")
    protagonist = sess.story["kept"]["protagonist"]["name"]
    first = protagonist.split()[0]
    sess.jump(3)
    sess.edit_field("name", "Zed Quill")
    sess.keep()
    assert sess.note and any("Updated" in n for n in sess.take_notes())
    spine = " ".join(sess.story["kept"]["spine"].values())
    assert first not in spine or "Zed" in spine




def test_finishing_the_last_step_sets_done(sess):
    while not sess.done:
        sess.keep()
    assert sess.done and sess.story["step"] == len(sess.steps)


def test_changing_the_structure_rolls_the_body_again(sess):
    while sess.step.key != "twist":
        sess.keep()
    assert sess.story["kept"]["spine"]
    sess.jump(1)
    sess.edit_field("structure", "Kishotenketsu" if sess.fields["structure"] != "Kishōtenketsu" else "Three-Act Outline")
    sess.keep()
    assert "spine" not in sess.story["kept"] and any("New structure" in n for n in sess.take_notes())


# --- ratings through the session ---------------------------------------------------------------------------------

def test_rating_a_field_records_its_frame_and_atoms(sess):
    to_step(sess, "setting")
    now = sess.rate(-1, "rumor")
    assert now == -1 and sess.rating("rumor") == -1 and sess.rating("place") == 0
    record = sess.ratings.current()[0]
    assert record["step"] == "setting" and record["field"] == "rumor" and record["text"] == sess.fields["rumor"]
    assert record["frame"]["slot"] == "rumor" and record["atoms"]
    assert sess.rate(-1, "rumor") == 0 and sess.rating("rumor") == 0       # again: cleared


def test_rating_a_single_field_step_needs_no_field(sess):
    to_step(sess, "premise")
    assert sess.rate(1) == 1 and sess.rating() == 1


def test_a_multi_field_step_asks_for_a_field(sess):
    to_step(sess, "setting")
    assert sess.rate(1) == 0 and "Select a field" in sess.take_notes()[0]


def test_ratings_off(home):
    s = Session(store.new_story(), make_engine(home, ratings=False))
    s.enter(0)
    assert s.rate(1, "genre") == 0 and "off" in s.take_notes()[0]


def test_the_mix_belongs_to_the_story(sess):
    sess.keep()
    mix = sess.mix()
    mix.exclude_tag("rural")
    assert sess.story["mix"]["exclude_tags"] == ["rural"]


# --- browsing a field, and the universe ----------------------------------------------------------------------

def test_step_value_browses_without_piling_up_candidates(sess):
    to_step(sess, "protagonist")
    sess.reroll_field("job")
    sess.reroll_field("job")
    values = sess.field_values("job")
    n = len(sess.hist)
    assert sess.step_value("job", -1) and sess.fields["job"] == values[1] and len(sess.hist) == n + 1
    assert sess.step_value("job", -1) and sess.fields["job"] == values[0] and len(sess.hist) == n + 1
    assert not sess.step_value("job", -1)                               # nothing older
    assert sess.step_value("job", 1) and sess.fields["job"] == values[1]
    sess.reroll_field("job")                                            # a real reroll starts a new stop
    assert len(sess.hist) == n + 2









