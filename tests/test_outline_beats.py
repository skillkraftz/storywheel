"""The Builder's outline: add and remove a repeatable beat (written back into story.md, with the count kept in its front matter)."""
import asyncio

import pytest

from storywheel import builder, fill, outline, vault
from storywheel.steps import public
from conftest import screen_text

SPINE = ["Once upon a time, Ann lived in Redwater.", "Every day, Ann swept the porch.", "One day, a stranger came.", "Because of that, Ann hid the key.",
         "Because of that, the stranger followed.", "Until finally, Ann ran.", "Ever since then, Ann sleeps lightly."]


@pytest.fixture
def story(home):
    u = vault.create_universe("Thornwood", ["western"])
    u.new_entity("character", "Ann Lowell", {"role": "protagonist", "job": "teacher"})
    s = u.new_story("The Last Clause", {"structure": "Story Spine", "genre": "western", "mood": "cozy"},
                    {"Story Spine": "\n\n".join(SPINE)})
    return u, s


def key_of(story, text):
    return next(k for k, _l, t in outline.rows(story) if text in t)


def fake_text(beat, texts):
    return f"Because of that, a new thing happened ({beat.key.replace('_', '')})."


def test_a_story_with_the_minimum_beats_can_add_but_not_remove(story):
    u, s = story
    k = key_of(s, "the stranger followed")
    assert outline.can_add(s, k) and not outline.can_remove(s, k)
    assert not outline.can_add(s, key_of(s, "Ann swept")) and not outline.can_remove(s, key_of(s, "Ann swept"))


def test_adding_puts_the_new_beat_after_the_last_of_its_kind_and_remembers_the_count(story):
    u, s = story
    new = outline.add_beat(s, key_of(s, "the stranger followed"), fake_text)
    assert new is not None
    texts = [t for _k, _l, t in outline.rows(s) if _k.startswith("beat:")]
    assert texts[:6] == SPINE[:5] + ["Because of that, a new thing happened (because22)."] and texts[6:] == SPINE[5:]
    assert s.load_outline()[0]["repeats"] == "because_2=2"
    assert outline.can_remove(s, new) and outline.can_add(s, new)


def test_the_maximum_stops_adding_and_the_minimum_stops_removing(story):
    u, s = story
    k = key_of(s, "the stranger followed")
    for _ in range(3):
        assert outline.add_beat(s, k, fake_text)
    assert not outline.can_add(s, k) and outline.add_beat(s, k, fake_text) is None
    assert s.load_outline()[0]["repeats"] == "because_2=4"
    for _ in range(3):
        last = [key for key, _l, t in outline.rows(s) if key.startswith("beat:") and t.startswith("Because of that")][-1]
        assert outline.remove_beat(s, last)
    assert not outline.can_remove(s, k) and outline.remove_beat(s, k) is False
    assert [t for _k, _l, t in outline.rows(s) if _k.startswith("beat:")] == SPINE and s.load_outline()[0]["repeats"] == ""


def test_removing_a_middle_one_keeps_the_rest_in_order(story):
    u, s = story
    k = key_of(s, "the stranger followed")
    outline.add_beat(s, k, lambda b, t: "Because of that, second.")
    outline.add_beat(s, k, lambda b, t: "Because of that, third.")
    middle = key_of(s, "Because of that, second.")
    assert outline.remove_beat(s, middle)
    texts = [t for _k, _l, t in outline.rows(s) if _k.startswith("beat:")]
    assert texts == SPINE[:5] + ["Because of that, third."] + SPINE[5:]


def test_an_old_story_with_one_extra_paragraph_is_read_from_its_count(story):
    u, s = story
    s.set_section("Story Spine", "\n\n".join(SPINE[:5] + ["Because of that, extra."] + SPINE[5:]))
    assert s.load_outline()[0].get("repeats") in (None, "")
    k = key_of(s, "extra")
    assert outline.can_remove(s, k) and outline.can_add(s, k)
    assert outline.remove_beat(s, k)
    assert [t for _k, _l, t in outline.rows(s) if _k.startswith("beat:")] == SPINE


def test_a_story_that_does_not_match_its_structure_is_left_alone(story):
    u, s = story
    s.set_section("Story Spine", "One paragraph only.")
    assert outline.beat_plan(s) is None and not outline.can_add(s, "beat:Story Spine:0")


def test_labelled_structures_number_the_new_beats(home):
    u = vault.create_universe("T", ["western"])
    s = u.new_story("Tale", {"structure": "Three-Act Outline"}, {"Three-Act Outline": "\n\n".join(
        f"**{l}.** {t}" for l, t in [("Act I: Setup", "a"), ("Act I: Inciting incident", "b"), ("Act I: First turn", "c"), ("Act II: Rising action", "d"),
                                    ("Act II: Midpoint", "e"), ("Act II: Crisis", "f"), ("Act III: Climax", "g"), ("Act III: Resolution", "h")])})
    k = key_of(s, "d")
    outline.add_beat(s, k, lambda b, t: "new")
    labels = [l for key, l, _t in outline.rows(s) if key.startswith("beat:")]
    assert labels[3:5] == ["Act II: Rising action", "Act II: Rising action (2)"]
    outline.remove_beat(s, key_of(s, "new"))
    assert [l for key, l, _t in outline.rows(s) if key.startswith("beat:")][3] == "Act II: Rising action"


def test_roll_beat_uses_the_generator_and_the_universe(story):
    u, s = story
    shape_beat = __import__("storywheel.structures", fromlist=["x"]).get("Story Spine").beat("because_2")
    texts = []
    for seed in range(6):                     # (one seed's frame may not name the protagonist: look across a few)
        filler = fill.Filler(u, fill.make_engine(u, seed=seed))
        texts.append(outline.roll_beat(s, u, filler, shape_beat, SPINE))
    assert all(t.startswith("Because of that, ") and "{" not in t for t in texts)
    assert any("Ann" in t for t in texts), texts


def test_the_builder_keys_add_and_remove_a_beat(story):
    u, s = story
    async def go():
        app = builder.BuilderApp(engine_factory=lambda un: fill.make_engine(un, seed=1), universe="thornwood")
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            scr = app.screen
            scr.story = s
            scr.refresh_all()
            await pilot.pause()
            rows = scr.top_rows()
            at = next(i for i, r in enumerate(rows) if "the stranger followed" in r[2])
            scr.outline.focus()
            scr.outline.highlighted = at
            await pilot.pause()
            await pilot.press("A")
            await pilot.pause()
            after = [t for _k, _l, t in outline.rows(s) if _k.startswith("beat:")]
            status_add = str(scr.query_one("#status").content)
            await pilot.press("X")
            await pilot.pause()
            back = [t for _k, _l, t in outline.rows(s) if _k.startswith("beat:")]
            scr.outline.highlighted = 0
            await pilot.pause()
            await pilot.press("A")
            await pilot.pause()
            return after, back, status_add, str(scr.query_one("#status").content)
    after, back, status_add, status_off = asyncio.run(go())
    assert len(after) == 8 and after[:5] == SPINE[:5] and after[5].startswith("Because of that, ") and "Added a beat" in status_add
    assert back == SPINE and "Move to one of the story's beats" in status_off
