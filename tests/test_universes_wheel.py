"""Universes as input to the Wheel: atoms, boosts, genre leanings, whole-step candidates, the panel."""
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from storywheel import store, universe_atoms, vault
from storywheel.engine import Engine
from storywheel.mix import story_mix
from storywheel.session import Session
from storywheel.steps import Ctx
from conftest import make_engine, run_tui, screen_text

ROOT = Path(__file__).resolve().parent.parent


def thornwood():
    u = vault.create_universe("Thornwood", ["western"])
    u.new_entity("character", "Zebulon Quillfeather", {"job": "assayer", "want": "a quiet claim", "role": "ally"})
    u.new_entity("character", "Marguerite Voss")
    u.new_entity("place", "Red Draw", {"kind": "town", "era": "the year of the strike", "rumor": "it was cursed"})
    u.new_entity("place", "Hangman's Tree", {"kind": "landmark"})
    u.new_entity("thing", "Hunting Horn", {"features": "portable, magic"})
    return u


def other():
    u = vault.create_universe("Elsewhere", ["fantasy"])
    u.new_entity("character", "Ottoline Nightsoil")
    u.new_entity("place", "Gloamwick")
    return u


def story_with(*slugs):
    s = store.new_story()
    s["universes"] = list(slugs)
    return s


# --- atoms ---------------------------------------------------------------------------------------------------

def test_a_universes_entities_become_tagged_atoms_in_matching_slots(home):
    lists = {wl.slot: wl for wl in universe_atoms.build_lists(thornwood())}
    assert set(lists) == {"someone", "close", "rival", "first_name", "last_name", "place", "landmark", "thing"}
    assert all(wl.tags == ("universe:thornwood",) and wl.id == f"universe:thornwood/{wl.slot}" for wl in lists.values())
    texts = lambda slot: sorted(e.text for e in lists[slot].entries)
    assert texts("someone") == ["Marguerite Voss", "Zebulon Quillfeather"]
    assert texts("first_name") == ["Marguerite", "Zebulon"] and texts("last_name") == ["Quillfeather", "Voss"]
    assert texts("place") == ["Red Draw"] and texts("landmark") == ["the Hangman's Tree"]
    assert texts("thing") == ["the Hunting Horn"]
    assert lists["someone"].entries[0].features == ("human",) and lists["close"].entries[0].features == ("human", "friendly")
    assert lists["thing"].entries[0].features == ("portable", "magic")           # from the entity's own field
    assert lists["place"].entries[0].features == ("outdoor",)


def test_empty_types_add_no_lists(home):
    u = vault.create_universe("Bare")
    assert universe_atoms.build_lists(u) == []
    u.new_entity("character")                                                       # blank: no name, no atom
    assert universe_atoms.build_lists(u) == []


def test_set_universes_adds_and_removes_lists_and_clears_caches(home):
    u = thornwood()
    e = Engine(seed=1)
    base = len(e.library.lists)
    e.set_universes([u])
    assert len(e.library.lists) == base + 8 and any(wl.id.startswith("universe:") for wl in e.library.by_slot["someone"])
    assert e.features_of("someone", "Marguerite Voss") == ("human",)
    e.set_universes([])
    assert len(e.library.lists) == base and not any(wl.id.startswith("universe:") for wl in e.library.by_slot["someone"])


def test_the_boost_and_the_genre_leanings_join_the_mix_without_touching_the_story(home):
    u = thornwood()
    u.save_settings(genres=["western", "fantasy"], atom_boost=4.0)
    e = Engine(seed=1)
    e.set_universes([vault.get_universe("thornwood")])
    story = store.new_story()
    story["kept"]["genre"] = {"genre": "noir", "mood": "grim"}
    from storywheel.mix import sync_base
    sync_base(story)
    mix = e.mix_for(story)
    assert mix.data["base"] == ["noir", "western", "fantasy"] and mix.data["boost"] == {"universe:thornwood": 4.0}
    assert story["mix"]["base"] == ["noir"] and story["mix"]["boost"] == {}
    assert mix.weights()["universe:thornwood"] == 4.0


# --- how often they appear -------------------------------------------------------------------------------------

def picks(engine, story, slot, n=1500):
    mix = engine.mix_for(story)
    out = Counter()
    for _ in range(n):
        wl, entry = engine.pick_item(slot, mix, commit=False)
        out[wl.id.startswith("universe:")] += 1
    return out[True] / n


def test_selected_universe_atoms_appear_at_about_the_boosted_rate(home):
    thornwood()
    e = Engine(seed=4)
    e.set_universes([vault.get_universe("thornwood")])
    story = story_with("thornwood")
    story["kept"]["genre"] = {"genre": "western", "mood": "cozy"}
    from storywheel.mix import sync_base
    sync_base(story)
    expected = sum(p for wl, p in zip(e.library.by_slot["someone"], e.mix_for(story).list_probabilities(e.library.by_slot["someone"]))
                   if wl.id.startswith("universe:"))
    got = picks(e, story, "someone")
    assert expected > 0.15 and abs(got - expected) < 0.05, (got, expected)
    assert got < 0.6                                                              # boosted, but not everything


def test_a_bigger_boost_means_more_of_the_universe(home):
    u = thornwood()
    rates = []
    for boost in (0.5, 1.5, 6.0):
        u.save_settings(atom_boost=boost)
        e = Engine(seed=4)
        e.set_universes([vault.get_universe("thornwood")])
        rates.append(picks(e, story_with("thornwood"), "someone", 1200))
    assert rates[0] < rates[1] < rates[2]


def test_unselected_universes_never_appear(home):
    thornwood()
    other()
    e = Engine(seed=6)
    e.set_universes([vault.get_universe("thornwood")])
    names = Counter()
    mix = e.mix_for(story_with("thornwood"))
    for slot in ("someone", "place", "first_name", "last_name", "thing", "landmark", "rival", "close"):
        for _ in range(400):
            wl, entry = e.pick_item(slot, mix, commit=False)
            names[entry.text] += 1
    assert not [t for t in names if "Ottoline" in t or "Nightsoil" in t or "Gloamwick" in t]
    assert any("Quillfeather" in t or "Zebulon" in t or "Red Draw" in t for t in names)


def test_nothing_selected_means_nothing_from_any_universe(home):
    thornwood()
    s = Session(store.new_story(), make_engine(home))
    assert s.engine.universes == []
    assert picks(s.engine, s.story, "someone", 400) == 0


def test_whole_stories_use_the_universes_people_and_places(home):
    thornwood()
    from storywheel.sample import build_story
    e = make_engine(home, seed=2)
    e.set_universes([vault.get_universe("thornwood")])
    hits = 0
    for _ in range(40):
        text = json.dumps(build_story(e, ["western"]))
        hits += any(n in text for n in ("Zebulon", "Quillfeather", "Marguerite", "Red Draw", "Hunting Horn", "Hangman"))
    assert hits >= 12


def test_a_universe_character_used_as_protagonist_is_not_also_a_stranger(home):
    u = thornwood()
    e = Engine(seed=3)
    e.set_universes([u])
    story = story_with("thornwood")
    story["kept"]["protagonist"] = {"name": "Zebulon Quillfeather"}
    c = Ctx(e, story, exclude="premise")
    seen = set()
    for _ in range(300):
        c.drawn.clear()
        seen.add(c.draw("someone"))
    assert "Zebulon Quillfeather" not in seen and "Marguerite Voss" in seen
    c2 = Ctx(e, story, exclude="protagonist")
    assert ("someone", "Zebulon Quillfeather") not in c2.used                 # (rolling the protagonist itself is free)


# --- whole-step candidates (no / mix / only) ---------------------------------------------------------------------------

def run_steps(home, mode, n=40, seed=5):
    thornwood()
    story = story_with("thornwood")
    story["universe_mode"] = mode
    s = Session(story, make_engine(home, seed=seed))
    s.enter(0)
    while s.step.key != "protagonist":
        s.keep()
    found = []
    for _ in range(n):
        s.roll()
        found.append((s.fields["name"], s.cand.get("_src")))
    return s, found


def test_only_mode_offers_only_universe_characters_and_fills_blanks(home):
    s, found = run_steps(home, "o")
    assert {src for _n, src in found} == {"universe"} and {n for n, _s in found} == {"Zebulon Quillfeather", "Marguerite Voss"}
    zeb = next(c for c in s.hist if c["name"] == "Zebulon Quillfeather")
    assert zeb["job"] == "assayer" and zeb["want"] == "a quiet claim"             # from the entity
    assert all(zeb[k] for k in ("age", "trait", "need", "flaw", "secret", "rival"))   # blanks completed by a roll
    marg = next(c for c in s.hist if c["name"] == "Marguerite Voss")
    assert all(marg[k] for k in ("age", "job", "trait", "want", "need", "flaw", "secret", "rival"))


def test_mix_mode_mixes_them_in_and_no_mode_never_does(home):
    _s, mixed = run_steps(home, "m", 80)
    share = sum(src == "universe" for _n, src in mixed) / len(mixed)
    assert 0.15 < share < 0.6
    _s, none = run_steps(home, "n", 40)
    assert not any(src == "universe" for _n, src in none)


def test_the_setting_step_offers_places_and_the_landmark_inside_a_town(home):
    thornwood()
    story = story_with("thornwood")
    story["universe_mode"] = "o"
    s = Session(story, make_engine(home, seed=1))
    s.enter(0)
    while s.step.key != "setting":
        s.keep()
    s.roll()
    f = s.fields
    assert f["place"] == "Red Draw" and f["era"] == "the year of the strike" and f["rumor"] == "it was cursed"
    assert f["landmark"] and f["season"]                                              # blanks filled


def test_a_universe_with_nothing_for_a_step_just_rolls_normally(home):
    vault.create_universe("Empty")
    story = story_with("empty")
    story["universe_mode"] = "o"
    s = Session(story, make_engine(home, seed=1))
    s.enter(0)
    while s.step.key != "protagonist":
        s.keep()
    s.roll()
    assert s.cand.get("_src") != "universe" and s.fields["name"]


# --- selecting, saving ---------------------------------------------------------------------------------------------------------

def test_the_selection_belongs_to_the_draft_and_is_saved(home):
    thornwood()
    other()
    s = Session(store.new_story(), make_engine(home))
    s.enter(0)
    assert s.toggle_universe("thornwood") and not s.toggle_universe("nope")
    assert s.story["universes"] == ["thornwood"] and [u.slug for u in s.engine.universes] == ["thornwood"]
    assert s.toggle_universe("elsewhere") and not s.toggle_universe("thornwood")
    assert s.story["universes"] == ["elsewhere"]
    s.keep()
    assert store.load(s.story["id"])["universes"] == ["elsewhere"]
    again = Session(store.load(s.story["id"]), make_engine(home))
    assert [u.slug for u in again.engine.universes] == ["elsewhere"]                  # restored on resume


def test_a_draft_started_inside_a_universe_has_it_ticked(home):
    thornwood()
    s = Session(store.new_story() | {"universes": ["thornwood"]}, make_engine(home))
    assert [u.slug for u in s.selected_universes()] == ["thornwood"]


def test_a_deleted_universe_is_dropped_quietly(home):
    u = thornwood()
    story = story_with("thornwood")
    u.delete()
    s = Session(story, make_engine(home))
    assert s.selected_universes() == [] and s.engine.universes == []


def test_save_a_protagonist_and_a_setting_into_a_universe(home):
    u = vault.create_universe("Bank")
    s = Session(store.new_story(), make_engine(home, seed=3))
    s.enter(0)
    while s.step.key != "protagonist":
        s.keep()
    s.save_to_universe(u)
    hero = u.entities("character")[0]
    assert hero.name == s.fields["name"] and hero.fields["role"] == "protagonist" and hero.fields["want"] == s.fields["want"]
    s.take_notes()
    s.save_to_universe(u)
    assert len(u.entities("character")) == 1 and "already in Bank" in s.take_notes()[0]
    s.keep()
    s.keep() if s.step.key != "setting" else None
    while s.step.key != "setting":
        s.keep()
    s.save_to_universe(u)
    town = u.entities("place")[0] if u.entities("place")[0].fields["kind"] == "town" else u.entities("place")[1]
    assert town.name == s.fields["place"] and town.custom["season"] == s.fields["season"]
    landmark = [p for p in u.entities("place") if p.fields["kind"] == "landmark"][0]
    assert landmark.fields["parent"] == town.id


# --- the panel ------------------------------------------------------------------------------------------------------------------

async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


def flat(text):
    return " ".join(text.split())


def test_the_panel_is_a_checklist_with_no_startup_question(home):
    thornwood()
    other()
    async def script(app, pilot):
        return flat(screen_text(app)), type(app.screen).__name__
    text, screen = run_tui(store.new_story(), make_engine(home), script)
    assert screen == "MainScreen" and "Universes to draw from (0 ticked)" in text
    assert "☐ Thornwood" in text and "☐ Elsewhere" in text and "tick a universe above" in text


def test_ticking_a_universe_saves_it_and_shows_its_people_and_places(home):
    thornwood()
    story = store.new_story()
    async def script(app, pilot):
        s = app.session
        await press(pilot, "v", "enter")
        ticked = flat(screen_text(app))
        picked = list(s.story["universes"])
        await press(pilot, "k")
        return ticked, picked
    ticked, picked = run_tui(story, make_engine(home), script)
    assert "☑ Thornwood" in ticked and "(1 ticked)" in ticked and "Characters (2)" in ticked and "Places (2)" in ticked and "Things (1)" in ticked and "2 characters · 2 places · 1 thing" in ticked
    assert picked == ["thornwood"] and store.load(story["id"])["universes"] == ["thornwood"]


def test_clicking_the_checkbox_row_ticks_it_too(home):
    thornwood()
    async def script(app, pilot):
        await pilot.click("#uni-check", offset=(4, 0)); await pilot.pause()
        return app.session.story["universes"]
    assert run_tui(store.new_story(), make_engine(home), script) == ["thornwood"]


def test_click_an_entity_to_preview_it_and_use_it_without_touching_kept_steps(home):
    thornwood()
    async def script(app, pilot):
        s = app.session
        await press(pilot, "v", "enter")                                   # tick Thornwood
        for _ in range(3):
            await press(pilot, "k")
        before = json.dumps(s.story["kept"], sort_keys=True)
        assert s.step.key == "protagonist"
        await pilot.click("#universe", offset=(5, 0)); await pilot.pause()      # open Characters
        await pilot.click("#universe", offset=(8, 1)); await pilot.pause()      # first character
        preview = (type(app.screen).__name__, flat(screen_text(app)))
        await press(pilot, "enter")                                        # use
        return preview, s.fields["name"], s.cand["_src"], json.dumps(s.story["kept"], sort_keys=True) == before, len(s.hist)
    (screen, text), name, src, same, n = run_tui(store.new_story(), make_engine(home), script)
    assert screen == "UniverseEntryScreen" and "from the universe Thornwood" in text and "Use in this story" in text
    assert "Delete" not in text and "enter: use as a new candidate" in text
    assert name in ("Marguerite Voss", "Zebulon Quillfeather") and src == "universe" and same and n == 2


def test_using_a_place_jumps_to_the_setting_step(home):
    thornwood()
    async def script(app, pilot):
        s = app.session
        await press(pilot, "v", "enter")
        await pilot.click("#universe", offset=(5, 1)); await pilot.pause()      # Places group (second)
        await pilot.click("#universe", offset=(8, 3)); await pilot.pause()      # (Hangman's Tree comes first, then Red Draw)
        await press(pilot, "enter")
        return s.step.key, s.fields["place"]
    assert run_tui(store.new_story(), make_engine(home), script) == ("setting", "Red Draw")


def test_the_mode_button_cycles_and_is_saved_per_draft(home):
    thornwood()
    story = store.new_story()
    async def script(app, pilot):
        s = app.session
        seen = []
        for _ in range(3):
            await pilot.click("#uni-mode"); await pilot.pause(0.4)
            seen.append(s.universe_mode)
        await press(pilot, "v", "t")
        seen.append(s.universe_mode)
        return seen
    assert run_tui(story, make_engine(home), script) == ["m", "o", "n", "m"]


def test_u_saves_the_candidate_to_the_single_ticked_universe(home):
    u = thornwood()
    async def script(app, pilot):
        s = app.session
        await press(pilot, "v", "enter", "escape")
        while s.step.key != "protagonist":
            await press(pilot, "k")
        await press(pilot, "u")
        return s.fields["name"], flat(screen_text(app))
    name, text = run_tui(store.new_story(), make_engine(home), script)
    assert vault.get_universe("thornwood").find_by_name(name, "character")
    assert f"Saved '{name}' to Thornwood" in text or f"'{name}' is already in Thornwood" in text


def test_u_with_nothing_ticked_asks_which_universe(home):
    thornwood()
    other()
    async def script(app, pilot):
        s = app.session
        while s.step.key != "protagonist":
            await press(pilot, "k")
        await press(pilot, "u")
        asked = type(app.screen).__name__
        await press(pilot, "down", "enter")
        return asked, s.fields["name"]
    asked, name = run_tui(store.new_story(), make_engine(home), script)
    assert asked == "ChoiceScreen" and vault.get_universe("thornwood").find_by_name(name) or vault.get_universe("elsewhere").find_by_name(name)


def test_u_with_no_universes_says_how_to_make_one(home):
    async def script(app, pilot):
        await press(pilot, "u")
        return flat(screen_text(app))
    assert "There is no universe yet" in run_tui(store.new_story(), make_engine(home), script)


def test_upper_u_points_to_the_builder_for_deleting(home):
    async def script(app, pilot):
        await press(pilot, "U")
        return flat(screen_text(app))
    assert "open it in the Builder" in run_tui(store.new_story(), make_engine(home), script)


def test_f2_leaves_the_wheel_for_the_builder_and_saves_the_draft(home):
    thornwood()
    story = store.new_story()
    async def script(app, pilot):
        await press(pilot, "v", "enter", "escape", "k")
        await press(pilot, "f2")
        assert type(app.screen).__name__ == "ChoiceScreen"            # a draft with kept steps is offered a send first
        await press(pilot, "down", "enter")                           # "just go"
        return app.next
    assert run_tui(story, make_engine(home), script) == ("builder", {"universe": "thornwood"})
    assert store.load(story["id"])["universes"] == ["thornwood"]


def test_send_a_past_storys_protagonist_to_a_chosen_universe(home):
    from storywheel.sample import build_story
    d = build_story(make_engine(home, seed=1), ["western"])
    d["id"], d["step"] = "20200101-000000", 8
    store.save(d)
    u = thornwood()
    async def script(app, pilot):
        lst = app.main.stories_list
        lst.focus(); await pilot.pause()
        lst.highlighted = [lst.get_option_at_index(i).id for i in range(lst.option_count)].index(d["id"])
        await press(pilot, "p")
        assert type(app.screen).__name__ == "ChoiceScreen"
        await press(pilot, "enter")
        return flat(screen_text(app))
    text = run_tui(store.new_story(), make_engine(home), script)
    assert vault.get_universe("thornwood").find_by_name(d["kept"]["protagonist"]["name"], "character")


# --- the plain prompt and old commands ---------------------------------------------------------------------------------------------------------

def cli(args, home, stdin=""):
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "home"), STORYWHEEL_LIBRARY=str(home / "library"),
               STORYWHEEL_OUT=str(home / "out"), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "storywheel", *args], input=stdin, capture_output=True, text=True,
                          env=env, cwd=ROOT, encoding="utf-8")


def test_the_plain_prompt_asks_which_universes_to_draw_from(home):
    thornwood()
    res = cli(["--plain"], home, "1\no\nk\nk\nk\nq\nl\n")
    assert res.returncode == 0, res.stderr
    assert "Draw from which?" in res.stdout and "Thornwood" in res.stdout
    drafts = sorted((home / "home" / "stories").glob("*.json"))
    saved = json.loads(drafts[-1].read_text())
    assert saved["universes"] == ["thornwood"] and saved["universe_mode"] == "o"


def test_the_old_universe_command_migrates_and_points_to_the_new_world(home):
    (home / "home").mkdir(parents=True, exist_ok=True)
    (home / "home" / "universe.json").write_text(json.dumps({"protagonist": [{"name": "Wade Hollis", "job": "drover"}]}))
    res = cli(["universe"], home)
    assert "Loose Ends" in res.stdout and vault.get_universe("loose-ends").entity("wade-hollis")
