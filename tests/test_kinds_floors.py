"""Motif kinds, per-slot floors, the Markov filters, and the tagged psychology lists."""
import random
import re
from collections import Counter

import pytest

from storywheel.engine import Engine
from storywheel.library import DataError, Library
from storywheel.markov import NameMaker
from storywheel.mix import Mix, new_mix
from storywheel.sample import build_story
from storywheel.steps import Ctx
from conftest import make_library, mix_for, wl, write_json


# --- motif kinds ---------------------------------------------------------------------------------

def ctx_with_motif(engine, motif, threads=None):
    story = {"kept": {"title": {"title": "T", "motif": motif}}, "seeds": {}}
    return Ctx(engine, story, threads=threads if threads is not None else {}, record=False)


def test_title_nouns_carry_kinds():
    e = Engine(seed=1)
    assert e.motif_kind("rider") == "person" and e.motif_kind("marshal") == "person"
    assert e.motif_kind("raven") == "creature" and e.motif_kind("coyote") == "creature"
    assert e.motif_kind("mesa") == "place" and e.motif_kind("castle") == "place"
    assert e.motif_kind("curse") == "idea" and e.motif_kind("reckoning") == "idea"
    assert e.motif_kind("lantern") == "object" and e.motif_kind("Spindle") == "object"
    assert e.motif_kind("zebra-thing") == "object" and e.motif_kind(None) == "object"   # unknown: assume an object


def test_every_kind_in_the_data_is_valid_and_all_five_are_used():
    lib = Library.load()
    kinds = {e.kind for wl_ in lib.by_slot["title_noun"] for e in wl_.entries}
    assert {None, "person", "creature", "place", "idea"} <= kinds


def test_a_bad_kind_is_reported(tmp_path):
    write_json(tmp_path / "lists" / "title_noun" / "x.json",
               {"slot": "title_noun", "tags": ["general"], "entries": [{"text": "a", "kind": "vegetable"}]})
    with pytest.raises(DataError, match="vegetable"):
        Library.load(tmp_path)


def test_list_kind_is_the_default_for_its_entries(tmp_path):
    write_json(tmp_path / "lists" / "title_noun" / "x.json",
               {"slot": "title_noun", "tags": ["general"], "kind": "person",
                "entries": ["sheriff", {"text": "spur", "kind": "object"}]})
    lib = Library.load(tmp_path)
    entries = {e.text: e.kind for l in lib.lists.values() if l.id == "title_noun/x" for e in l.entries}
    assert entries == {"sheriff": "person", "spur": "object"}


def test_the_motif_is_used_as_an_object_only_when_it_is_one():
    e = Engine(seed=2)
    assert ctx_with_motif(e, "lantern")["the_motif"] == "the lantern"
    for motif in ("marshal", "raven", "mesa", "curse"):
        said = ctx_with_motif(e, motif)["the_motif"]
        assert motif not in said and said                      # a thing instead
    said = ctx_with_motif(e, "unknown-word")["the_motif"]
    assert said == "the unknown-word"                         # unknown counts as an object


def test_non_object_motif_falls_back_to_the_stories_own_thread():
    e = Engine(seed=3)
    c = ctx_with_motif(e, "marshal", threads={"thing": {"text": "a locked box", "beat": "one_day"}})
    assert c["the_motif"] == "the locked box"


def test_a_person_or_creature_motif_is_sometimes_offered_as_someone():
    e = Engine(seed=4)
    first_draw = sum(ctx_with_motif(e, "marshal").block("SOMEONE") == "the marshal" for _ in range(800))
    assert 0.18 < first_draw / 800 < 0.32                      # about a quarter of the time
    for _ in range(100):
        c = ctx_with_motif(e, "raven")
        assert [c.block("SOMEONE") for _ in range(20)].count("the raven") <= 1   # but once per roll


def test_object_place_and_idea_motifs_are_never_offered_as_someone():
    e = Engine(seed=5)
    for motif in ("lantern", "mesa", "curse"):
        assert not any(ctx_with_motif(e, motif).block("SOMEONE") == f"the {motif}" for _ in range(200))


def test_templates_use_the_motif_object_placeholder():
    lib = Library.load()
    users = [e.text for l in lib.lists.values() for e in l.entries if "{the_motif}" in e.text]
    assert len(users) >= 3
    plain = [e.text for l in lib.lists.values() for e in l.entries
             if re.search(r"(stealing|dug up|gave|finds|inherits|carrying) the \{motif\}", e.text)]
    assert not plain, plain


def test_stories_with_person_motifs_never_say_find_the_marshal():
    engine = Engine(seed=6)
    bad = 0
    for _ in range(150):
        s = build_story(engine, ["western", "fairy tale"])
        motif = s["kept"]["title"]["motif"]
        if engine.motif_kind(motif) in ("person", "creature", "place", "idea"):
            text = " ".join([s["kept"]["premise"]["premise"], *s["kept"]["spine"].values(),
                             s["kept"]["twist"]["twist"]])
            bad += bool(re.search(rf"(finds|inherits|carrying|stealing|dug up|burned) the {motif}\b", text))
    assert bad == 0


# --- per-slot floors -------------------------------------------------------------------------------------

def floor_library(floors):
    lib = make_library([], floor=0.12)
    lib.floors = floors
    return lib


def test_anchor_slots_get_a_low_floor_and_one_off_slots_keep_the_default():
    lib = floor_library({"rival": 0.04})
    rivals = [wl("rival/west", ["western"]), wl("rival/space", ["sci-fi"])]
    disasters = [wl("disaster/west", ["western"]), wl("disaster/space", ["sci-fi"])]
    mix = mix_for(lib, "western")
    assert mix.list_probabilities(rivals) == pytest.approx([0.96, 0.04])
    assert mix.list_probabilities(disasters) == pytest.approx([0.88, 0.12])
    assert mix.floor_for("rival") == 0.04 and mix.floor_for("anything") == 0.12


def test_floors_are_configurable_in_genres_json(tmp_path):
    write_json(tmp_path / "genres.json", {"_floors": {"rival": 0.5}, "steampunk": {"steampunk": 3}})
    lib = Library.load(tmp_path)
    assert lib.floors["rival"] == 0.5 and lib.floors["job"] == 0.04     # merged over the shipped ones


def test_shipped_floors_cover_the_anchor_slots():
    lib = Library.load()
    for slot in ("rival", "job", "place", "first_name", "last_name"):
        assert 0.03 <= lib.floors[slot] <= 0.05
    assert lib.floor == 0.12
    assert "disaster" not in lib.floors


def test_a_western_story_rarely_has_a_fairy_tale_rival_but_often_a_fairy_tale_disaster():
    engine = Engine(seed=7)
    engine.trace = []
    for _ in range(300):
        build_story(engine, ["western"])
    def share(slot):
        picks = [t for t in engine.trace if t[0] == slot]
        return sum("fairy tale" in t[2] for t in picks) / len(picks)
    assert share("rival") < 0.09
    assert 0.05 < share("disaster") < 0.25


# --- markov filters -------------------------------------------------------------------------------------------

def test_name_maker_rejects_the_words_it_is_told_to():
    maker = NameMaker([e.text for e in Library.load().lists["last_name/fairy-tale"].entries])
    rng = random.Random(3)
    plain = {maker.make(rng) for _ in range(600)} - {None}
    banned = {n.lower() for n in plain if n}
    ruled_out = {n.lower() for n in list(banned)[:15]}
    again = {maker.make(random.Random(4), reject=ruled_out) for _ in range(300)} - {None}
    assert not ({n.lower() for n in again} & ruled_out)


def test_invented_names_are_at_least_four_letters_and_never_dictionary_words():
    engine = Engine(seed=8)
    for list_id in ("first_name/western", "last_name/western", "first_name/fairy-tale", "last_name/fairy-tale"):
        wl_ = engine.library.lists[list_id]
        real = {e.text for e in wl_.entries}
        mix = Mix(new_mix(["western", "fairy tale"]), engine.library)
        invented = {engine.pick_entry(wl_, mix).text for _ in range(500)} - real
        assert len(invented) > 10
        for name in invented:
            assert len(name) >= 4, name
            assert name.lower() not in engine.dictionary, name
    assert "thistle" in engine.dictionary and "bell" in engine.dictionary


# --- profiles and the psychology lists -----------------------------------------------------------------------------

def test_every_profile_has_general_03_and_modern_01():
    lib = Library.load()
    assert len(lib.profiles) >= 14
    for genre, profile in lib.profiles.items():
        assert profile["general"] == 0.3 and profile["modern"] == 0.1, genre


ATOM_SLOTS = ["someone", "thing", "disaster", "message", "hiding", "act_person", "act_thing", "act_place",
              "act_message", "do_thing", "do_person", "habit_thing", "habit_person", "habit_place", "manner",
              "prize", "deadline", "motive", "vice", "value", "temptation"]


def genre_atoms(lib, slot, tag):
    n = 0
    for wl_ in lib.by_slot[slot]:
        n += len(wl_.entries) if tag in wl_.tags else sum(tag in e.tags for e in wl_.entries)
    return n


@pytest.mark.parametrize("slot", ATOM_SLOTS)
def test_genre_lives_on_the_atoms(slot):
    lib = Library.load()
    assert genre_atoms(lib, slot, "western") >= 3, slot
    assert genre_atoms(lib, slot, "fairy tale") >= 3, slot


def test_verb_and_abstract_atoms_follow_the_genre_too():
    engine = Engine(seed=9)
    engine.trace = []
    for _ in range(200):
        build_story(engine, ["western", "fairy tale"])
    flavor = {"western", "fairy tale", "historical", "fantasy"}
    for slot in ("act_person", "act_thing", "manner", "prize", "deadline", "vice", "value"):
        picks = [t for t in engine.trace if t[0] == slot]
        assert len(picks) >= 60, slot
        assert sum(bool(t[2] & flavor) for t in picks) / len(picks) > 0.2, slot


def test_thread_templates_exist_for_the_later_beats():
    lib = Library.load()
    for slot in ("reaction", "escalation", "climax", "resolution", "twist"):
        assert sum("{the_" in e.text for e in lib.lists[f"{slot}/general"].entries) >= 4, slot


def test_invented_names_are_capitalized_like_names():
    cap = NameMaker._capitalize
    assert [cap("calloway"), cap("o'hare"), cap("mccrae"), cap("anne-marie")] == \
        ["Calloway", "O'Hare", "McCrae", "Anne-Marie"]
