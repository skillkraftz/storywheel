"""Content built from atoms: lint rules, no repeats within a story, a memory that
persists across sessions, the repetition report, and the pronoun helpers."""
import json
import re
from collections import Counter

import pytest

from storywheel import report
from storywheel.engine import Engine
from storywheel.library import Library
from storywheel.mix import Mix, new_mix
from storywheel.report import MAX_ATOM_WORDS, MAX_FIXED_RUN, MIN_TEMPLATE_SLOTS, lint, longest_fixed_run, slot_count, word_count
from storywheel.sample import build_story
from storywheel.steps import STEPS, Ctx, step_by_key
from storywheel.text import implicit, pronouns
from conftest import make_library, mix_for, wl


# --- 1 and 2: the lint ---------------------------------------------------------------------------------------

def test_shipped_data_passes_the_lint():
    problems = lint(Library.load())
    assert not problems, "\n".join(f"{lid}: {text!r} ({why})" for lid, text, why in problems[:20])


def test_atoms_live_under_lists_and_templates_under_templates():
    lib = Library.load()
    templates = {wl_.slot for wl_ in lib.lists.values() if wl_.is_template}
    atoms = {wl_.slot for wl_ in lib.lists.values() if not wl_.is_template}
    assert not templates & atoms
    assert {"want", "need", "flaw", "secret", "rumor", "once", "routine", "inciting", "reaction", "escalation",
            "climax", "resolution", "premise", "twist", "title"} <= templates
    assert {"someone", "thing", "prize", "deadline", "act_person", "manner"} <= atoms


def test_the_lint_catches_what_it_is_for():
    lib = make_library([
        wl("thing/a", ["general"], ["a perfectly ordinary old brass bell", "a bell, rung", "a bell that rings",
                                     "their bell", "a bell"]),
        wl("reaction/b", ["general"], ["told the same three jokes to the same customers",
                                        "{first} left", "{first} left {THING}"]),
    ])
    lib.lists["reaction/b"].is_template = True
    why = {t: w for _l, t, w in lint(lib)}
    assert "6 words" in why["a perfectly ordinary old brass bell"]
    assert "punctuation" in why["a bell, rung"]
    assert "clause" in why["a bell that rings"]
    assert "pronoun" in why["their bell"]
    assert "a bell" not in why
    assert "fixed words" in why["told the same three jokes to the same customers"]
    assert "slot" in why["{first} left"]
    assert "{first} left {THING}" not in why


def test_lint_helpers():
    assert slot_count("{first} {ACT_PERSON} {SOMEONE}") == 3 and slot_count("{noun} {noun2}") == 2
    assert word_count("a {trait} {job}") == 3
    assert longest_fixed_run("the {rival}, wanted — a long way from here {first}") == 6
    assert (MAX_ATOM_WORDS, MAX_FIXED_RUN, MIN_TEMPLATE_SLOTS) == (5, 6, 2)


def test_templates_have_room_for_variety():
    """Every template has two slots, and each slot kind it uses has a good-sized pool."""
    lib = Library.load()
    for slot in ("someone", "thing", "act_person", "act_thing", "prize", "manner", "vice", "value"):
        assert sum(len(l.entries) for l in lib.by_slot[slot]) >= 20, slot
    for wl_ in lib.lists.values():
        if wl_.is_template:
            assert len(wl_.entries) >= 6, wl_.id


# --- 3: no atom repeats within a story ---------------------------------------------------------------------------

def test_no_atom_repeats_within_a_story():
    engine = Engine(seed=5)
    total = 0
    for _ in range(200):
        story = build_story(engine, ["western", "fairy tale"])
        atoms = [tuple(a) for lst in story["atoms"].values() for a in lst]
        total += len(atoms)
        assert len(atoms) == len(set(atoms)), [a for a, n in Counter(atoms).items() if n > 1]
    assert total > 5000


def test_the_engine_honors_a_stories_avoid_set_and_relaxes_when_it_must(engine):
    lib = make_library([wl("thing/a", ["general"], ["x", "y", "z"])])
    engine.library = lib
    mix = mix_for(lib)
    avoid = {("thing", "x"), ("thing", "y")}
    assert {engine.pick("thing", mix, avoid=avoid) for _ in range(40)} == {"z"}
    everything = avoid | {("thing", "z")}
    assert engine.pick("thing", mix, avoid=everything) in {"x", "y", "z"}      # all used: relax, don't fail


def test_keeping_a_step_records_its_atoms_and_later_steps_avoid_them():
    engine = Engine(seed=3)
    story = {"kept": {}, "seeds": {}, "atoms": {}}
    cand = step_by_key("protagonist").roll(engine, story)
    used = [tuple(a) for lst in cand["_atoms"].values() for a in lst]
    assert used
    story["atoms"]["protagonist"] = [list(a) for a in used]
    ctx = Ctx(engine, story, exclude="setting")
    assert set(used) <= ctx.used                              # a later step knows what's taken
    again = Ctx(engine, story, exclude="protagonist")
    assert not (set(used) & again.used)                       # but a step being redone doesn't count itself


def test_a_rerolled_field_avoids_the_atoms_its_siblings_use():
    from storywheel.refs import reroll_field
    engine = Engine(seed=4)
    story = {"kept": {}, "seeds": {}, "atoms": {}}
    spine = next(s for s in STEPS if s.key == "spine")
    for _ in range(40):
        cand = spine.roll(engine, story)
        new = reroll_field(spine, engine, story, cand, "reaction" if "reaction" in cand else "because_1")
        atoms = [tuple(a) for lst in new["_atoms"].values() for a in lst]
        assert len(atoms) == len(set(atoms))


def test_editing_a_field_by_hand_clears_its_atoms():
    from storywheel.refs import with_field
    cand = {"a": "x", "b": "y", "_atoms": {"a": [["thing", "t1"]], "b": [["thing", "t2"]]}}
    new = with_field(cand, "a", "typed by hand")
    assert new["_atoms"] == {"a": [], "b": [["thing", "t2"]]}
    assert cand["_atoms"]["a"] == [["thing", "t1"]]


# --- 3b: the memory persists across sessions ----------------------------------------------------------------------

def test_recent_picks_persist_across_sessions(tmp_path):
    lib = make_library([wl("thing/a", ["general"], [str(i) for i in range(10)])])
    mix = mix_for(lib)
    first = Engine(seed=1, library=lib, user_dir=tmp_path, persist=True)
    seen = [first.pick("thing", mix) for _ in range(5)]
    first.save_memory()
    saved = json.loads((tmp_path / "recent.json").read_text())
    assert saved["recent"]["thing/a"] == seen
    for seed in range(20):
        second = Engine(seed=seed, library=lib, user_dir=tmp_path, persist=True)
        assert second.pick("thing", mix) not in seen            # 5 of 10 were just used: none come straight back


def test_a_new_session_picks_up_where_the_last_left_off(tmp_path):
    lib = make_library([wl("thing/a", ["general"], [str(i) for i in range(10)])])
    mix = mix_for(lib)
    a = Engine(seed=1, library=lib, user_dir=tmp_path, persist=True)
    seen = [a.pick("thing", mix) for _ in range(5)]
    a.save_memory()
    b = Engine(seed=9, library=lib, user_dir=tmp_path, persist=True)
    assert b.pick("thing", mix) not in seen                      # a fresh engine, the same memory


def test_persistence_is_off_unless_asked_for(tmp_path):
    e = Engine(seed=1, user_dir=tmp_path)
    e.pick("thing", Mix(new_mix(["western"]), e.library))
    e.save_memory()
    assert not (tmp_path / "recent.json").exists()


def test_a_damaged_memory_file_is_ignored(tmp_path):
    (tmp_path / "recent.json").write_text("{ not json")
    e = Engine(seed=1, user_dir=tmp_path, persist=True)
    assert e.pick("thing", Mix(new_mix(["western"]), e.library))


def test_the_memory_never_makes_a_seeded_run_differ(tmp_path):
    """sample and tests don't persist, so a seed always means the same stories."""
    a = build_story(Engine(seed=8, user_dir=tmp_path), ["western"])
    (tmp_path / "recent.json").write_text(json.dumps({"version": 1, "recent": {"thing/western": ["a stagecoach bell"]}}))
    b = build_story(Engine(seed=8, user_dir=tmp_path), ["western"])
    assert a["kept"] == b["kept"]


# --- 4: the report ------------------------------------------------------------------------------------------------

def test_the_report_runs_and_has_the_headline_numbers():
    r = report.build_report(["western", "fairy tale"], stories=40, seed=3)
    text = report.format_report(r)
    for needle in ("Headline:", "Most picked entries", "Most repeated rendered lines",
                   "Frozen templates", "Atoms that are too long"):
        assert needle in text
    assert r["lint"] == []


def test_assembled_stories_do_not_repeat_recognizable_lines():
    """The point of atoms: over 200 stories, few rendered lines are seen again and again."""
    r = report.build_report(["western", "fairy tale"], stories=200, seed=202)
    assert len(r["heavy_lines"]) <= 3, r["heavy_lines"][:5]
    assert not r["flagged"]                                    # nothing over 3x its fair share either


def test_normalize_blanks_names_and_places():
    story = {"kept": {"protagonist": {"name": "Wade Hollis"}, "setting": {"place": "Dry Fork", "landmark": "the mill"}}}
    assert report.normalize("Wade Hollis left Dry Fork; Hollis's horse stayed.", story) == "X left X; X horse stayed."


# --- pronoun helpers ---------------------------------------------------------------------------------------------

def test_object_verbs_take_them_after_the_first_mention():
    assert pronouns("Wade lied. The sheriff betrayed Wade", "Wade", ("betrayed",)) == "Wade lied. The sheriff betrayed them"
    assert pronouns("Wade lied. The sheriff betrayed Wade", "Wade") == "Wade lied. The sheriff betrayed Wade"


def test_character_card_text_says_their():
    assert implicit("to face down Vesna's one true ally", "Vesna") == "to face down their one true ally"
    assert implicit("revenge on Vesna's rival", "Vesna") == "revenge on their rival"
    assert implicit("peace and quiet", "Vesna") == "peace and quiet"


def test_wants_needs_flaws_and_secrets_never_name_the_character():
    engine = Engine(seed=6)
    story = {"kept": {}, "seeds": {}, "atoms": {}}
    for _ in range(200):
        cand = step_by_key("protagonist").roll(engine, story)
        first = cand["name"].split()[0]
        for key in ("want", "need", "flaw", "secret"):
            assert first not in cand[key], cand[key]


def test_every_sentence_starts_with_a_capital():
    import re
    engine = Engine(seed=12)
    for _ in range(300):
        story = build_story(engine, ["western", "fairy tale"])
        for step in ("premise", "twist"):
            for text in story["kept"][step].values():
                assert not re.search(r"[.!?] [a-z]", text), text
                assert text[0].isupper(), text
