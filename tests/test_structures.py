"""Story structures as data: the registry, the steps built from them, sample, markdown,
the interactive flow, and threads in every shape."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from storywheel import store, structures
from storywheel.engine import Engine
from storywheel.library import Library
from storywheel.report import lint
from storywheel.sample import build_story, render, sample
from storywheel.steps import STEPS, spine_step, steps_for, step_by_key
from storywheel import threads as T
from conftest import write_json

ROOT = Path(__file__).resolve().parent.parent
NAMES = ["story-spine", "three-act", "kishotenketsu"]      # the order they are offered in


def run_cli(args, stdin, home, out):
    env = dict(os.environ, STORYWHEEL_HOME=str(home), STORYWHEEL_OUT=str(out), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "storywheel", *args], input=stdin, capture_output=True,
                          text=True, env=env, cwd=ROOT, encoding="utf-8")


# --- the data ------------------------------------------------------------------------------------

def test_three_structures_ship_with_the_story_spine_first():
    reg = structures.registry()
    assert list(reg) == NAMES
    assert reg["story-spine"].label == "Story Spine" and not reg["story-spine"].show_labels
    assert len(reg["story-spine"].beats) == 7 and len(reg["three-act"].beats) == 8 and len(reg["kishotenketsu"].beats) == 4
    assert reg["three-act"].show_labels and reg["kishotenketsu"].show_labels


def test_find_and_get_ignore_case_and_accept_name_or_label():
    assert structures.find("KISHŌTENKETSU").name == "kishotenketsu"
    assert structures.find("three-act").label == "Three-Act Outline"
    assert structures.find("nope") is None
    assert structures.get("nope").name == "story-spine" and structures.get(None).name == "story-spine"


def test_every_beat_has_templates_and_they_pass_the_lint():
    lib = Library.load()
    assert not lint(lib)
    for s in structures.registry().values():
        for b in s.beats:
            assert lib.has_slot(b.slot), (s.name, b.key, b.slot)
            assert all(wl.is_template for wl in lib.by_slot[b.slot]), b.slot
            assert sum(len(wl.entries) for wl in lib.by_slot[b.slot]) >= 6, b.slot


def test_beats_have_their_own_templates_and_share_no_slots():
    slots = [b.slot for s in structures.registry().values() for b in s.beats]
    assert len(slots) == len(set(slots))
    keys = [b.key for s in structures.registry().values() for b in s.beats]
    assert len(keys) == len(set(keys))                      # so thread labels are unambiguous


def test_the_story_spine_is_the_same_seven_beats_as_before():
    step = step_by_key("spine")
    assert list(step.fields) == ["once", "every_day", "one_day", "because_1", "because_2", "until_finally", "ever_since"]
    text = step.roll(Engine(seed=1), {"kept": {}, "seeds": {}, "atoms": {}})
    assert text["once"].startswith("Once upon a time, ") and text["every_day"].startswith("Every day, ")
    assert text["until_finally"].startswith("Until finally, ") and text["ever_since"].startswith("Ever since then, ")


def test_user_structures_merge_and_can_replace(tmp_path):
    write_json(tmp_path / "structures" / "mine.json", {
        "label": "Mine", "blurb": "Two beats.", "show_labels": True,
        "beats": [{"key": "m1", "slot": "once", "label": "First"}, {"key": "m2", "slot": "climax"}]})
    got = structures.load(tmp_path)
    assert list(got) == NAMES + ["mine"] and got["mine"].keys == ["m1", "m2"]
    assert got["mine"].beats[1].label == "m2"                  # label defaults to the key
    write_json(tmp_path / "structures" / "three-act.json", {
        "label": "Short Act", "beats": [{"key": "only", "slot": "act_setup"}]})
    assert structures.load(tmp_path)["three-act"].label == "Short Act"


def test_bad_structure_files_are_reported(tmp_path):
    write_json(tmp_path / "structures" / "bad.json", {"beats": [{"key": "a"}, {"key": "a"}]})
    with pytest.raises(structures.StructureError, match="bad.json"):
        structures.load(tmp_path)
    (tmp_path / "structures" / "bad.json").write_text("{ nope")
    with pytest.raises(structures.StructureError, match="bad.json"):
        structures.load(tmp_path)


# --- the steps -------------------------------------------------------------------------------------

def test_steps_follow_the_chosen_structure():
    for name in NAMES:
        story = {"kept": {"structure": {"structure": structures.registry()[name].label}}}
        steps = steps_for(story)
        assert [s.key for s in steps] == ["genre", "structure", "title", "protagonist", "setting",
                                          "premise", "spine", "twist"]
        spine = steps[6]
        assert list(spine.fields) == structures.registry()[name].keys
        assert spine.label == structures.registry()[name].label and spine.threads
    assert [s.key for s in STEPS][:2] == ["genre", "structure"]


def test_the_structure_step_rolls_every_structure():
    engine = Engine(seed=3)
    step = step_by_key("structure")
    seen = {step.roll(engine, {"kept": {}, "seeds": {}, "atoms": {}})["structure"] for _ in range(80)}
    assert seen == {s.label for s in structures.registry().values()}


def test_an_unknown_structure_falls_back_to_the_story_spine():
    story = {"kept": {"structure": {"structure": "something I typed"}}}
    assert list(steps_for(story)[6].fields) == structures.registry()["story-spine"].keys


# --- sample ------------------------------------------------------------------------------------------

def test_sample_picks_a_structure_at_random_per_story():
    engine = Engine(seed=5)
    seen = {build_story(engine, ["western"])["kept"]["structure"]["structure"] for _ in range(60)}
    assert seen == {s.label for s in structures.registry().values()}


@pytest.mark.parametrize("name", NAMES)
def test_sample_can_force_each_structure(name):
    engine = Engine(seed=6)
    for _ in range(25):
        story = build_story(engine, ["western", "fairy tale"], structure=name)
        shape = structures.registry()[name]
        assert story["kept"]["structure"]["structure"] == shape.label
        assert list(story["kept"]["spine"]) == shape.keys
        assert all(text.strip() for text in story["kept"]["spine"].values())
        assert "{" not in " ".join(story["kept"]["spine"].values())
    text = render(story)
    assert shape.label in text.splitlines()[1]
    if shape.show_labels:
        assert all(b.label in text for b in shape.beats)


def test_forcing_an_unknown_structure_is_an_error():
    with pytest.raises(ValueError, match="No structure called 'zigzag'"):
        build_story(Engine(seed=1), ["western"], structure="zigzag")


def test_the_sample_command_takes_a_structure_flag(home):
    ok = run_cli(["sample", "western", "-n", "2", "--seed", "1", "--structure", "kishotenketsu"], "", home / "h", home / "o")
    assert ok.returncode == 0 and ok.stdout.count("Kishōtenketsu") >= 2 and "Ki (introduction) —" in ok.stdout
    bad = run_cli(["sample", "western", "--structure", "zigzag"], "", home / "h", home / "o")
    assert bad.returncode != 0 and "No structure called 'zigzag'" in bad.stderr and "three-act" in bad.stderr
    assert not (home / "h" / "stories").exists()                 # nothing saved


def test_same_seed_same_structures_in_every_process(home):
    outs = {run_cli(["sample", "fantasy", "-n", "4", "--seed", "9"], "", home / "h", home / "o").stdout
            for _ in range(2)}
    assert len(outs) == 1


# --- threads in every shape --------------------------------------------------------------------------------

@pytest.mark.parametrize("name", NAMES)
def test_threads_work_in_every_structure(name):
    engine = Engine(seed=7)
    keys = set(structures.registry()[name].keys)
    callbacks = introduced = 0
    for _ in range(120):
        story = build_story(engine, ["western", "fairy tale"], structure=name)
        order = list(story["kept"]["spine"])
        for kind, t in story["threads"].items():
            assert t["beat"] in keys
            text = story["kept"]["spine"][t["beat"]]
            assert any(f in text for f in T.intro_forms(t))
            introduced += 1
            later = order[order.index(t["beat"]) + 1:]
            d = T.definite(t["text"])
            callbacks += d != t["text"] and any(d in story["kept"]["spine"][b] for b in later)
    assert introduced > 100 and callbacks > 20, (introduced, callbacks)


def test_thread_labels_cover_every_structure():
    for s in structures.registry().values():
        for b in s.beats:
            assert T.BEAT_LABELS[b.key] == b.label


# --- markdown ----------------------------------------------------------------------------------------------------

def test_markdown_labels_the_beats_of_labeled_structures_only():
    engine = Engine(seed=2)
    three = store.to_markdown(build_story(engine, ["western"], structure="three-act"))
    assert 'structure: "Three-Act Outline"' in three
    assert "## Three-Act Outline" in three and "**Act I: Setup.** " in three and "**Act III: Resolution.** " in three
    kisho = store.to_markdown(build_story(engine, ["western"], structure="kishotenketsu"))
    assert "## Kishōtenketsu" in kisho and "**Ten (twist).** " in kisho
    spine = store.to_markdown(build_story(engine, ["western"], structure="story-spine"))
    assert "## Story Spine\n\nOnce upon a time, " in spine and "**Once upon a time" not in spine
    assert "## Structure" not in spine                          # the structure step has no section of its own
    story = build_story(engine, ["western"], structure="three-act")
    assert "(introduced: Act" in store.to_markdown(story) or not story["threads"]


# --- older files -----------------------------------------------------------------------------------------------------

def test_older_stories_gain_the_structure_step_and_keep_their_place(home):
    old = {"id": "20260101-000000", "created": "2026-01-01T00:00", "step": 3,
           "kept": {"genre": {"genre": "western", "mood": "cozy"}, "title": {"title": "T", "motif": "m"},
                    "protagonist": {"name": "Wade Hollis"}}, "history": {}, "seeds": {}, "universe_mode": "n"}
    (home / "home" / "stories").mkdir(parents=True)
    (home / "home" / "stories" / f"{old['id']}.json").write_text(json.dumps(old))
    story = store.load(old["id"])
    assert story["kept"]["structure"] == {"structure": "Story Spine"}
    assert story["step"] == 4 and steps_for(story)[story["step"]].key == "setting"     # still about to do setting
    assert store.upgrade(story)["step"] == 4                                           # and only once


def test_a_brand_new_story_is_not_shifted():
    s = store.new_story()
    assert store.upgrade(s)["step"] == 0 and "structure" not in s["kept"]


# --- the interactive flow ----------------------------------------------------------------------------------------------

def test_pick_a_structure_finish_then_go_back_and_change_it(home):
    h, o = home / "h", home / "o"
    first = "\n".join(["k", "e", "Three-Act Outline", "k", "k", "k", "k", "k", "k", "k"]) + "\n"
    res = run_cli([], first, h, o)
    assert res.returncode == 0, res.stderr
    assert "STRUCTURE" in res.stdout and "Setup, a disruption, a choice" in res.stdout    # the blurb is shown
    saved = json.loads(next((h / "stories").glob("*.json")).read_text())
    assert saved["kept"]["structure"] == {"structure": "Three-Act Outline"}
    assert list(saved["kept"]["spine"]) == structures.registry()["three-act"].keys
    assert "**Act I: Setup.**" in next(o.glob("*.md")).read_text()

    # resume (a finished story opens on its last step; go back to the structure) and switch shape
    second = "\n".join(["b"] * 6 + ["e", "Kishotenketsu", "k"] + ["k"] * 6) + "\n"
    res = run_cli(["resume"], second, h, o)
    assert res.returncode == 0, res.stderr
    assert "New structure: the story body will be rolled again" in res.stdout
    saved = json.loads(next((h / "stories").glob("*.json")).read_text())
    assert saved["kept"]["structure"]["structure"] == "Kishōtenketsu"
    assert list(saved["kept"]["spine"]) == structures.registry()["kishotenketsu"].keys
    md = next(o.glob("*.md")).read_text()
    assert "**Ketsu (reconciliation).**" in md and "Act I: Setup" not in md


def test_an_unrecognized_structure_is_called_out_on_the_card(home):
    res = run_cli([], "\n".join(["k", "e", "zigzag", "q"]) + "\n", home / "h", home / "o")
    assert "Not one of the known structures" in res.stdout
