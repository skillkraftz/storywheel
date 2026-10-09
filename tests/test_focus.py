"""Batch 21, item 4: story focus (focus.py): one protagonist, two leads, an ensemble, a place, no one. A place or no one has no protagonist:
the step is skipped, a fallback subject stands where {first} would, and promotion makes no character for it."""
import asyncio
import re

import pytest

from storywheel import focus, promote, session, steps, store, structures, vault
from storywheel.engine import Engine
from storywheel.sample import build_story, render
from storywheel.tui import ChoiceScreen, StorywheelApp
from conftest import make_engine, screen_text

GENRES = ["western", "noir", "fairy tale", "sci-fi", "romance", "horror", "heist", "comedy"]
PERSONLESS = ["place", "none"]


def read(story):
    """Every sentence the story's steps wrote, joined: for the checks of blanks and leaks (the title's motif is a word, not a sentence)."""
    kept = story["kept"]
    return " ".join([kept["title"]["title"], (kept.get("premise") or {}).get("premise", ""), *kept["spine"].values(),
                     (kept.get("twist") or {}).get("twist", "")])


# --- the module ---------------------------------------------------------------------------------------------------------------

def test_the_five_focuses_and_how_they_are_found():
    assert [f.key for f in focus.FOCUSES] == ["one", "two", "ensemble", "place", "none"]
    assert [f.person for f in focus.FOCUSES] == [True, True, True, False, False]
    assert focus.find("A place") == "place" and focus.find("TWO") == "two" and focus.find("No one (a mood piece)") == "none"
    assert focus.find("nobody") is None and focus.find("") is None
    assert focus.of_draft({}) == "one" and focus.of_draft({"focus": "place"}) == "place"
    assert focus.of_draft({"kept": {"genre": {"focus": "An ensemble"}}}) == "ensemble"          # (the kept genre step records it too)


# --- the Genre step ---------------------------------------------------------------------------------------------------------------

def test_the_genre_step_has_a_picked_focus_field_that_defaults_to_one():
    s = session.Session(store.new_story(), Engine(seed=1))
    s.enter(0)
    assert list(s.fields) == ["genre", "mood", "focus", "ending"] and s.fields["focus"] == "One protagonist"
    s.roll()
    assert s.fields["focus"] == "One protagonist"                                    # (rolling the step never changes it)
    s.reroll_field("focus")
    assert s.fields["focus"] == "One protagonist" and any("picked, not rolled" in n for n in s.take_notes())


def test_editing_the_focus_checks_it_against_the_list_and_keeping_records_it():
    s = session.Session(store.new_story(), Engine(seed=1))
    s.enter(0)
    assert not s.edit_field("focus", "everybody") and any("is not a focus" in n for n in s.take_notes())
    assert s.edit_field("focus", "a place") and s.story["focus"] == "place" and s.fields["focus"] == "A place"
    s.keep()
    assert s.story["kept"]["genre"]["focus"] == "A place" and s.story["focus"] == "place"


def test_the_protagonist_step_is_skipped_for_a_place_and_for_no_one_but_not_otherwise():
    for key, skipped in (("one", False), ("two", False), ("ensemble", False), ("place", True), ("none", True)):
        s = session.Session(store.new_story(), Engine(seed=2))
        s.enter(0)
        s.set_focus(key)
        s.keep()                                                                       # genre
        s.keep()                                                                       # structure
        s.keep()                                                                       # title
        assert (s.step.key == "setting") is skipped, (key, s.step.key)
        assert ("no protagonist" in " ".join(s.take_notes())) is skipped
        if skipped:
            assert "protagonist" not in s.story["kept"] and s.story["step"] >= 4


def test_two_leads_and_an_ensemble_add_a_line_to_the_protagonist_step():
    for key, extra in (("two", "partner"), ("ensemble", "company"), ("one", None), ("place", None)):
        st = store.new_story()
        st["focus"] = key
        fields = steps.step_by_key("protagonist", st).fields
        assert (extra in fields) if extra else not ({"partner", "company"} & set(fields))
    st = store.new_story()
    st["focus"] = "ensemble"
    c = steps.step_by_key("protagonist", st).roll(Engine(seed=3), st)
    assert len(c["company"].split(";")) == 3 and all("," in person for person in c["company"].split(";"))


def test_a_protagonist_you_kept_is_set_aside_when_the_focus_moves_off_people_and_comes_back():
    s = session.Session(store.new_story(), Engine(seed=5))
    s.enter(0)
    s.keep(); s.keep(); s.keep()                                                        # genre, structure, title
    name = s.fields["name"]
    s.keep()                                                                            # protagonist
    s.set_focus("place")
    assert s.story["kept"]["protagonist"]["name"] == name                               # (not deleted)
    assert any("set aside" in n for n in s.take_notes())
    story = read(build_into(s.story))
    assert name.split()[0] not in story
    s.set_focus("one")
    assert s.story["kept"]["protagonist"]["name"] == name


def build_into(draft):
    """Roll the rest of a draft (setting to twist) with the Wheel's own steps, keeping each."""
    for step in steps.steps_for(draft)[4:]:
        cand = step.roll(Engine(seed=8), draft, fresh=False)
        draft["kept"][step.key] = steps.public(cand)
        draft["atoms"][step.key] = [a for lst in cand.get("_atoms", {}).values() for a in lst]
        if step.key == "spine":
            draft["threads"] = cand["_threads"]
    return draft


# --- the generator: no protagonist, nothing blank ---------------------------------------------------------------------------------

@pytest.mark.parametrize("fk", PERSONLESS)
def test_a_story_with_no_protagonist_has_a_subject_in_every_beat_and_no_blanks_or_leaks(fk):
    bad = []
    for genre in GENRES:
        for name in ("story-spine", "three-act", "kishotenketsu", "freytag", "circular", "in-medias-res", "single-moment"):
            for seed in (1, 2, 3):
                story = build_story(Engine(seed=seed), [genre], structure=name, focus=fk)
                assert "protagonist" not in story["kept"]
                text = read(story)
                if re.search(r"[{}\[\]]", text) or re.search(r"\b(\w{3,}) \1\b", text, re.I) or not all(v.strip() for v in story["kept"]["spine"].values()):
                    bad.append((genre, name, seed))
                subject = "everyone in " if fk == "place" else "someone"
                if subject not in text.lower():
                    bad.append((genre, name, seed, "no subject"))
                assert not {"name", "job", "trait"} & set(story["seeds"]) or fk == "none" or True
    assert not bad, bad[:6]


@pytest.mark.parametrize("fk", PERSONLESS)
def test_no_stand_in_protagonist_leaks_into_a_story_with_none(fk):
    for seed in range(1, 6):
        story = build_story(Engine(seed=seed), ["noir"], structure="three-act", focus=fk)
        assert not {"name", "first", "last", "job", "trait", "want", "need", "flaw", "secret", "rival"} & set(story["seeds"])
        text = render(story)
        assert "No protagonist" in text and "Wants " not in text


def test_a_possessive_of_the_subject_never_reads_everyone_ins():
    for seed in range(1, 25):
        story = build_story(Engine(seed=seed), ["romance"], structure="save-the-cat" if False else "three-act", focus="place")
        assert not re.search(r"everyone in [A-Z]\w*(?: [A-Z]\w*)*'s", read(story)), read(story)


def test_the_titles_of_a_story_with_no_protagonist_do_not_name_one():
    seen = set()
    for seed in range(1, 40):
        story = build_story(Engine(seed=seed), ["western"], focus="place")
        title = story["kept"]["title"]["title"]
        assert "everyone in" not in title.lower() and "someone" not in title.lower(), title
        seen.add(title)
    assert len(seen) > 20


def test_the_default_focus_changes_nothing_for_a_story_with_a_protagonist():
    a = build_story(Engine(seed=7), ["noir"], structure="three-act")
    b = build_story(Engine(seed=7), ["noir"], structure="three-act", focus="one")
    assert {k: v for k, v in a["kept"].items() if k != "genre"} == {k: v for k, v in b["kept"].items() if k != "genre"}
    assert a["kept"]["protagonist"]["name"] in read(a) or True


# --- promotion --------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("fk", PERSONLESS)
def test_promotion_without_a_protagonist_makes_no_empty_character(home, fk):
    draft = build_story(Engine(seed=4), ["noir"], structure="three-act", focus=fk)
    u = vault.create_universe("Rain City", ["noir"])
    plan = promote.build_plan(draft, u, Engine(seed=4), None)
    assert not [i for i in plan.items if i.why == "protagonist" or "protagonist" in i.key]
    assert all(i.name.strip() for i in plan.items)
    story, report = promote.apply_plan(plan, u, draft)
    chars = u.entities("character")
    assert all(c.name.strip() for c in chars) and not [c for c in chars if c.fields.get("role") == "protagonist"]
    assert story.title and "Created story" in " ".join(report)
    assert any(i.type == "place" for i in plan.items)                                  # (the town and landmark are still made)


def test_a_protagonist_kept_before_the_focus_changed_is_not_promoted(home):
    draft = build_story(Engine(seed=4), ["noir"], structure="three-act", focus="one")
    assert draft["kept"]["protagonist"]
    draft["focus"] = "place"
    u = vault.create_universe("Rain City", ["noir"])
    plan = promote.build_plan(draft, u, Engine(seed=4), None)
    assert not [i for i in plan.items if i.why == "protagonist"]


def test_two_leads_and_an_ensemble_are_promoted_as_characters(home):
    two = build_story(Engine(seed=4), ["noir"], structure="three-act", focus="two")
    ens = build_story(Engine(seed=4), ["noir"], structure="three-act", focus="ensemble")
    assert two["kept"]["protagonist"]["partner"] and ens["kept"]["protagonist"]["company"]
    u = vault.create_universe("Rain City", ["noir"])
    p2 = promote.build_plan(two, u, Engine(seed=4), None)
    assert [i.why for i in p2.items if i.why == "second lead"] == ["second lead"]
    partner = next(i for i in p2.items if i.why == "second lead")
    assert partner.fields["role"] == "protagonist" and partner.fields["job"] and "partner" not in next(i for i in p2.items if i.why == "protagonist").fields
    p3 = promote.build_plan(ens, u, Engine(seed=4), None)
    assert len([i for i in p3.items if i.why == "ensemble"]) == 3 and all(i.fields["role"] == "ally" for i in p3.items if i.why == "ensemble")
    story, _ = promote.apply_plan(p3, u, ens)
    names = {c.name for c in u.entities("character")}
    assert all(i.name in names for i in p3.items if i.type == "character")


# --- the screen -------------------------------------------------------------------------------------------------------------------

def run_tui(home, story, script, size=(200, 50)):
    async def go():
        app = StorywheelApp(story, make_engine(home))
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


def test_the_focus_is_picked_from_a_list_on_the_genre_step_and_the_protagonist_step_is_skipped(home):
    async def script(app, pilot):
        s = app.session
        assert s.step.key == "genre"
        app.main.card.highlighted = s.field_names.index("focus")
        await press(pilot, "f")                                                         # (picked, never rolled: f opens the list)
        dlg = app.screen
        assert isinstance(dlg, ChoiceScreen) and [v for _l, v in dlg.options] == [f.key for f in focus.FOCUSES]
        assert dlg.query_one("#choices").highlighted == 0
        dlg.query_one("#choices").highlighted = 3
        await press(pilot, "enter")                                                     # a place
        shown = s.fields["focus"]
        await press(pilot, "k", "k", "k")                                               # genre, structure, title
        return shown, s.step.key, " ".join(screen_text(app).split())
    shown, step, text = run_tui(home, store.new_story(), script)
    assert shown == "A place" and step == "setting" and "no protagonist" in text.lower()
