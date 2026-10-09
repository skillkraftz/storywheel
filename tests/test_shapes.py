"""Batch 21: the Wheel beyond one arc. Flash fiction, the new structures (formats.py, data/structures/), their frames, and the fall-back to
the general frames for any genre without a file of its own."""
import json
import re

import pytest

from storywheel import formats, outline, settings, structures, vault, versions
from storywheel.engine import Engine
from storywheel.library import Library
from storywheel.sample import build_story

NEW = {
    "save-the-cat": (15, ["novel"]),
    "heros-journey": (12, ["novel"]),
    "seven-point": (7, ["novel"]),
    "freytag": (7, ["short-story", "novel"]),
    "single-moment": (3, ["flash", "short-story"]),
    "circular": (6, ["flash", "short-story"]),
    "in-medias-res": (6, ["flash", "short-story"]),
}
NEW_SLOTS = ["theme", "debate", "reward", "opening_image", "echo", "in_the_thick"]
GENRES = ["western", "fairy tale", "comedy", "fantasy", "mystery", "horror", "sci-fi", "romance", "ghost story", "noir", "thriller", "heist",
          "adventure", "coming-of-age"]


# --- flash fiction -------------------------------------------------------------------------------------------------------------

def test_flash_is_a_short_story_to_the_writer_and_the_export(home):
    f = formats.get("flash")
    assert (f.label, f.short, f.setting, f.unit, f.target) == ("Flash fiction", "Flash", "short-story", "words", 1000)
    assert [x.key for x in formats.FORMATS][:2] == ["flash", "short-story"]
    assert formats.find("Flash fiction") == "flash" and formats.find("flash") == "flash" and not formats.is_script("flash")
    u = vault.create_universe("Tiny", ["noir"])
    s = u.new_story("Cup", {"format": "flash"})
    st = settings.load_story(s.path)
    assert st["format"] == "short-story" and st["script_kind"] == "flash" and st["target_words"] == 1000
    assert formats.of_story(s) == "flash" and formats.target(s) == (1000, "words") and not s.is_screenplay()
    formats.apply(s, "short-story")                                        # back to a short story: the flash mark goes
    assert formats.of_story(s) == "short-story" and formats.target(s) == (5000, "words")


def test_the_default_format_can_be_flash(home):
    settings.save_global({"format": "short-story", "script_kind": "flash"})
    assert formats.global_default() == "flash" and formats.of_draft({}) == "flash"
    settings.save_global({"format": "screenplay", "script_kind": "short-film"})
    assert formats.global_default() == "short-film"


def test_flash_is_in_every_picker_and_the_cli(home):
    assert ("Flash fiction", "flash") in formats.choices()
    from test_versions import cli, make
    make(home)
    r = cli(["story", "version", "noirville/cold-coffee", "--format", "flash", "--title", "Cold Coffee, Flash", "--json"], home)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["format"] == "flash"
    shown = json.loads(cli(["story", "show", "noirville/cold-coffee-flash", "--json"], home).stdout)
    assert shown["format_key"] == "flash" and shown["settings"]["format"] == "short-story"


# --- the structures ------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,spec", NEW.items())
def test_each_new_structure_has_its_beats_formats_and_frames(name, spec):
    n, fits = spec
    lib = Library.load()
    s = structures.registry()[name]
    assert len(s.beats) == n and list(s.formats) == fits and s.show_labels and not s.screen and s.blurb
    for b in s.beats:
        assert lib.has_slot(b.slot) and sum(len(wl.entries) for wl in lib.by_slot[b.slot]) >= 6, (name, b.key, b.slot)
    for key in fits:
        assert s in formats.structures_for(key)
    for key in {f.key for f in formats.FORMATS} - set(fits):
        assert s not in formats.structures_for(key)


def test_the_counts_the_brief_names():
    reg = structures.registry()
    assert len(reg["save-the-cat"].beats) == 15 and len(reg["heros-journey"].beats) == 12 and len(reg["single-moment"].beats) == 3


def test_beat_keys_are_unique_across_every_structure():
    keys = [b.key for s in structures.registry().values() for b in s.beats]
    assert len(keys) == len(set(keys))


def test_each_format_is_offered_the_right_structures():
    names = lambda key: [s.name for s in formats.structures_for(key)]
    assert names("novel") == ["story-spine", "three-act", "kishotenketsu", "save-the-cat", "heros-journey", "seven-point", "freytag"]
    assert names("short-story") == ["story-spine", "three-act", "kishotenketsu", "freytag", "single-moment", "circular", "in-medias-res"]
    assert names("flash") == ["story-spine", "kishotenketsu", "single-moment", "circular", "in-medias-res"]
    assert formats.default_structure("flash").name == "story-spine"


# --- the frames: every genre falls back to the general ones -----------------------------------------------------------------------

def test_the_new_slots_have_general_frames_only_and_every_genre_still_fills_them():
    lib = Library.load()
    for slot in NEW_SLOTS:
        assert [wl.id for wl in lib.by_slot[slot]] == [f"{slot}/general"]
    bad = []
    for genre in GENRES:
        for name in NEW:
            for seed in (1, 2):
                story = build_story(Engine(seed=seed), [genre], structure=name)
                for key, text in story["kept"]["spine"].items():
                    if not text.strip() or re.search(r"[{}]", text) or re.search(r"\b(\w{3,}) \1\b", text, re.I):
                        bad.append((genre, name, seed, key, text))
    assert not bad, bad[:5]


def test_a_genre_with_no_file_for_a_slot_falls_back_to_general():
    """western and fairy tale have no frame files of their own for any slot: their stories on a general-only slot still read."""
    lib = Library.load()
    for slot in NEW_SLOTS + ["act_setup", "act_turn"]:
        files = {wl.id for wl in lib.by_slot[slot]}
        assert f"{slot}/western" not in files and f"{slot}/fairy-tale" not in files
    for genre in ("western", "fairy tale"):
        story = build_story(Engine(seed=9), [genre], structure="circular")
        assert len(story["kept"]["spine"]) >= 6 and all(v.strip() for v in story["kept"]["spine"].values())


def test_the_circular_story_comes_back_to_its_place():
    """The echo repeats the opening image's place, landmark or season (fields of the story), so the end is where the beginning was."""
    hits = 0
    for seed in range(1, 21):
        story = build_story(Engine(seed=seed), ["noir"], structure="circular")
        first, last = story["kept"]["spine"]["ci_opening"], story["kept"]["spine"]["ci_echo"]
        setting = story["kept"]["setting"]
        hits += any(setting.get(k) and setting[k] in first and setting[k] in last for k in ("landmark", "place", "season"))
    assert hits >= 16, hits


# --- the "structure doesn't fit" path of a new version -------------------------------------------------------------------------

def story_on(name, fmt):
    u = vault.get_universe("noirville") or vault.create_universe("Noirville", ["noir"])
    shape = structures.registry()[name]
    return u.new_story(f"On {name}", {"genre": "noir", "structure": shape.label, "format": fmt},
                       {"Premise": "A waitress waits.", shape.label: outline.blank_beats(shape)})


@pytest.mark.parametrize("name", list(NEW))
@pytest.mark.parametrize("fmt", [f.key for f in formats.FORMATS])
def test_a_new_version_of_a_story_on_each_structure_in_each_format(home, name, fmt):
    shape = structures.registry()[name]
    s = story_on(name, shape.formats[0])
    new, notes = versions.new_version(s, fmt, title="Other")
    meta, sections = new.load_outline()
    assert formats.of_story(new) == fmt
    if formats.fits(shape, fmt):
        assert meta["structure"] == shape.label and not notes
        assert [h for h in sections if outline.is_beat_section(h)] == [shape.label]
    else:
        fit = formats.default_structure(fmt)
        assert meta["structure"] == fit.label and any("doesn't fit" in n for n in notes)
        assert {shape.label, fit.label} <= set(sections)                       # (the old beats stay; the new format's blank ones are added)
        assert sections[fit.label] == outline.blank_beats(fit)
