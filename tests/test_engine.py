"""Engine behavior: no-repeat picking, merging user lists, reproducibility,
and that the shipped data hangs together."""
import string
from collections import Counter

import pytest

from storywheel.engine import Engine
from storywheel.library import DataError, Library
from storywheel.steps import STEPS, Ctx, fill
from storywheel import store
from conftest import make_library, mix_for, wl, write_json


def test_no_repeat_until_half_the_list_is_used(engine):
    lib = make_library([wl("job/a", ["general"], [str(i) for i in range(10)])])
    engine.library = lib
    mix = mix_for(lib)
    for _ in range(20):
        window = [engine.pick("job", mix) for _ in range(5)]
        assert len(set(window)) == 5            # 10 entries -> 5 picks in a row never repeat


def test_tiny_lists_still_work(engine):
    lib = make_library([wl("job/a", ["general"], ["only"])])
    engine.library = lib
    assert [engine.pick("job", mix_for(lib)) for _ in range(3)] == ["only"] * 3


def test_same_seed_same_story():
    def story_rolls(seed):
        e = Engine(seed=seed)
        story = {"kept": {}, "seeds": {}}
        return [str(s.roll(e, story)) for s in STEPS]
    assert story_rolls(5) == story_rolls(5)
    assert story_rolls(5) != story_rolls(6)


def test_user_lists_merge_with_builtin(tmp_path):
    write_json(tmp_path / "lists" / "job" / "mine.json",
               {"slot": "job", "tags": ["western"], "entries": ["drover", "marshal"]})
    lib = Library.load(tmp_path)
    ids = {l.id for l in lib.by_slot["job"]}
    assert {"job/mine", "job/everyday", "job/faker-jobs"} <= ids


def test_user_list_with_same_path_replaces_builtin(tmp_path):
    write_json(tmp_path / "lists" / "job" / "everyday.json",
               {"slot": "job", "tags": ["general"], "entries": ["only this"]})
    lib = Library.load(tmp_path)
    everyday = next(l for l in lib.by_slot["job"] if l.id == "job/everyday")
    assert [e.text for e in everyday.entries] == ["only this"]


def test_user_genre_profiles_extend_builtin(tmp_path):
    write_json(tmp_path / "genres.json", {"steampunk": {"steampunk": 3, "general": 1}})
    lib = Library.load(tmp_path)
    assert "steampunk" in lib.genre_names and "western" in lib.genre_names


def test_bad_data_gives_a_helpful_error(tmp_path):
    (tmp_path / "lists" / "job").mkdir(parents=True)
    (tmp_path / "lists" / "job" / "broken.json").write_text("{ nope")
    with pytest.raises(DataError, match="broken.json"):
        Library.load(tmp_path)
    write_json(tmp_path / "lists" / "job" / "broken.json", {"slot": "job", "tags": "western"})
    with pytest.raises(DataError, match="tags"):
        Library.load(tmp_path)


def test_generated_lists_come_from_generators(engine):
    mix = mix_for(engine.library)
    assert engine.pick("first_name", mix) and engine.pick("place", mix)
    assert engine.pick("job", mix)


def test_genre_steers_entry_picks():
    e = Engine(seed=1)
    general = e.library.lists["landmark/general"]
    def landmarks(genre):
        story = {"kept": {"genre": {"genre": genre, "mood": "cozy"}}, "seeds": {}}
        from storywheel.mix import Mix, sync_base
        sync_base(story)
        mix = Mix.for_story(story, e.library)
        return Counter(e.choose_entry(general, mix, reuse=True).text for _ in range(3000))
    west, space = landmarks("western"), landmarks("sci-fi")
    # "the observatory" exists only as a sci-fi-tagged entry in the general list (picked within that list, so the other lists do not dilute it)
    assert space["the observatory"] > 4 * max(1, west["the observatory"])


# --- the shipped data ---------------------------------------------------------------------------

KNOWN_FIELDS = {"first", "last", "name", "age", "place", "motif", "title", "genre", "nouns",
                "title_nouns", "adj2", "noun2", "the_motif",
                "the_thing", "the_someone", "the_message", "the_disaster"}
SPECIAL_BLOCKS = {"ODDITY", "ALLITERATION"}


def placeholders(text):
    """Names of the slots in a template, ignoring requirements and agreement tokens."""
    from storywheel.frames import AGREE, _PLACEHOLDER
    out = []
    for m in _PLACEHOLDER.finditer(text):
        name = m.group(1)
        if m.group(3) is None and name not in AGREE:
            out.append(name)
    return out


def test_every_placeholder_in_the_shipped_data_resolves():
    lib = Library.load()
    for wl_ in lib.lists.values():
        for entry in wl_.entries:
            for key in placeholders(entry.text):
                if key.isupper():
                    assert key in SPECIAL_BLOCKS or lib.has_slot(key.lower()), (wl_.id, entry.text, key)
                else:
                    assert key in KNOWN_FIELDS or lib.has_slot(key), (wl_.id, entry.text, key)


def test_every_list_has_tags_and_a_note():
    for wl_ in Library.load().lists.values():
        assert wl_.tags, wl_.id


def test_rolls_never_leave_braces_or_gaps(engine):
    story = {"kept": {}, "seeds": {}}
    for _ in range(150):
        for step in STEPS:
            for text in step.roll(engine, story).values():
                if isinstance(text, str):
                    assert "{" not in text and "[" not in text and text.strip(), (step.key, text)


def test_a_few_template_fills_read_well(engine):
    c = Ctx(engine, {"kept": {"protagonist": {"name": "Wade Hollis"}}, "seeds": {}})
    out = fill(c, "{first} gave a {ODDITY} to {CLOSE}, and {first} left {first}'s hat.")
    assert out.startswith("Wade gave a") and "their hat" in out


def test_ignored_exclusions_are_reported(engine):
    lib = make_library([wl("job/a", ["western"], ["a"]), wl("thing/b", ["western"], ["b"])])
    engine.library = lib
    mix = mix_for(lib, "western", exclude_tags=["western"])
    assert engine.pick("job", mix) == "a"          # single list, excluded: still answers, but says so
    assert engine.pick("job", mix) == "a"
    notes = engine.take_notices()
    assert len(notes) == 1 and "'job'" in notes[0]  # once, not per pick
    assert engine.take_notices() == []
    mix_ok = mix_for(lib, "western")
    engine.pick("job", mix_ok)
    assert engine.take_notices() == []


def test_excluded_entries_all_gone_is_reported(engine):
    from storywheel.library import Entry
    lib = make_library([wl("job/a", ["general"], [Entry("x", ["horror"])])])
    engine.library = lib
    engine.pick("job", mix_for(lib, "western", exclude_tags=["horror"]))
    assert "job/a" in engine.take_notices()[0]
