"""Versions (batch 20): the same story as several stories in different formats, in one universe (versions.py)."""
import itertools
import json

import pytest

from storywheel import formats, outline, settings, structures, vault, versions

FORMAT_KEYS = [f.key for f in formats.FORMATS]
SCRIPT = """Title: Cold Coffee
Credit: Written by

FADE IN:

INT. DINER - NIGHT

Rain on the glass. MARA stares at a cup.

MARA
(quietly)
It went cold an hour ago.

CUT TO:

EXT. ROAD - DAY

A truck passes.

BRAM
Don't wait up.
"""


def make(home, fmt="short-story", manuscript=True, title="Cold Coffee"):
    u = vault.get_universe("noirville") or vault.create_universe("Noirville", ["noir"])
    shape = formats.default_structure(fmt) or structures.find("Story Spine")
    s = u.new_story(title, {"genre": "noir", "structure": shape.label, "format": fmt, "motif": "a cup"},
                    {"Premise": "A waitress waits.", "Setting": "- **Place:** Dunmore", shape.label: outline.blank_beats(shape),
                     "Twist": "The cup was never hers."}, seed={"draft": 1})
    s.save_notes("Remember the rain.")
    if manuscript:
        if formats.is_script(fmt):
            vault._write(s.script_path, SCRIPT)
        else:
            vault._write(s.manuscript_dir / "manuscript.md", "She waited. It rained.\n\n* * * The Road\n\n\"Go,\" he said.\n")
    return s


# --- families ----------------------------------------------------------------------------------------------------------------

def test_a_story_with_no_family_has_no_siblings_and_is_untouched(home):
    s = make(home)
    assert versions.family_of(s) == "" and versions.siblings(s) == [] and versions.versions(s) == [s]
    assert versions.other_version(s) is None
    assert [e["members"] for e in versions.rows(s.universe)] == [[s]]
    assert "family" not in s.meta


def test_a_version_joins_a_family_and_the_source_gets_the_id_written(home):
    s = make(home)
    new, _ = versions.new_version(s, "feature-film", title="Cold Coffee: the film")
    assert versions.family_of(s) == s.slug == versions.family_of(new)
    assert [x.slug for x in versions.versions(new)] == [s.slug, new.slug]
    assert [x.slug for x in versions.siblings(s)] == [new.slug]
    assert versions.other_version(s).slug == new.slug and versions.other_version(new).slug == s.slug
    assert versions.other_version(new, -1).slug == s.slug


def test_the_slug_gets_a_format_suffix_when_the_title_is_taken(home):
    s = make(home)
    new, _ = versions.new_version(s, "feature-film")
    assert new.slug == f"{s.slug}-feature-film" and new.title == s.title
    again, _ = versions.new_version(s, "feature-film")
    assert again.slug not in (s.slug, new.slug) and len({x.slug for x in versions.versions(s)}) == 3
    fresh, _ = versions.new_version(s, "novel", title="A Different Name")
    assert fresh.slug == "a-different-name"


def test_rows_group_a_family_into_one_entry(home):
    s = make(home)
    other = make(home, title="Unrelated")
    new, _ = versions.new_version(s, "short-film")
    out = versions.rows(s.universe)
    assert [(e["title"], [m.slug for m in e["members"]]) for e in out] == [("Cold Coffee", [s.slug, new.slug]), ("Unrelated", [other.slug])]


def test_deleting_or_renaming_one_version_leaves_the_others(home):
    s = make(home)
    new, _ = versions.new_version(s, "novel", copy=("outline", "manuscript"))
    before = (s.path / "story.md").read_text(encoding="utf-8"), (s.manuscript_dir / "manuscript.md").read_text(encoding="utf-8")
    new.set_meta(title="Renamed")
    assert (s.path / "story.md").read_text(encoding="utf-8") == before[0] and s.title == "Cold Coffee"
    new.delete()
    assert (s.path / "story.md").read_text(encoding="utf-8") == before[0]
    assert (s.manuscript_dir / "manuscript.md").read_text(encoding="utf-8") == before[1]
    assert versions.siblings(s) == [] and (vault.root() / ".trash").exists()
    assert s.universe.story(s.slug) is not None


def test_deleting_the_first_story_keeps_the_family_of_the_others(home):
    s = make(home)
    a, _ = versions.new_version(s, "novel")
    b, _ = versions.new_version(s, "short-film")
    s.delete()
    assert [x.slug for x in versions.versions(a)] == [a.slug, b.slug]


def test_the_family_round_trips_through_story_md(home):
    s = make(home)
    new, _ = versions.new_version(s, "novel")
    text = (new.path / "story.md").read_text(encoding="utf-8")
    assert f"family: \"{s.slug}\"" in text or f"family: {s.slug}" in text
    again = vault.get_universe("noirville").story(new.slug)
    assert versions.family_of(again) == s.slug and again.meta["version"] == "2"


# --- what is copied -----------------------------------------------------------------------------------------------------------

def test_the_default_copy_is_everything_but_the_manuscript(home):
    s = make(home)
    new, notes = versions.new_version(s, "short-story", title="Cold Coffee Again")
    meta, sections = new.load_outline()
    assert meta["genre"] == "noir" and meta["structure"] == "Story Spine" and meta["motif"] == "a cup"
    assert sections["Premise"] == "A waitress waits." and sections["Twist"] == "The cup was never hers." and "Story Spine" in sections
    assert new.notes == "Remember the rain." and new.seed() == {"draft": 1}
    assert not new.files() and notes == []
    assert versions.DEFAULT_COPY == ("outline", "notes", "seed", "genres", "structure")


@pytest.mark.parametrize("off", ["outline", "notes", "seed", "genres", "structure"])
def test_each_copy_option_can_be_left_out(home, off):
    s = make(home)
    copy = tuple(c for c in versions.DEFAULT_COPY if c != off)
    new, _ = versions.new_version(s, "novel", title="Other", copy=copy)
    meta, sections = new.load_outline()
    if off == "outline":
        assert "Premise" not in sections and "Twist" not in sections and "Story Spine" in sections
    else:
        assert sections["Premise"] == "A waitress waits."
    assert (new.notes == "") == (off == "notes")
    assert (new.seed() is None) == (off == "seed")
    assert ("genre" not in meta) == (off == "genres")
    assert ("structure" not in meta and "Story Spine" not in sections) == (off == "structure")


def test_copies_are_separate_not_synced(home):
    s = make(home)
    new, _ = versions.new_version(s, "novel", title="Other")
    s.set_section("Premise", "Changed in the first.")
    new.save_notes("Changed in the second.")
    assert new.sections()["Premise"] == "A waitress waits." and s.notes == "Remember the rain."


def test_a_structure_that_does_not_fit_is_kept_and_the_new_formats_blank_one_is_added(home):
    s = make(home)
    new, notes = versions.new_version(s, "feature-film", title="Film")
    meta, sections = new.load_outline()
    assert "Story Spine" in sections and "Feature Film" in sections
    assert meta["structure"] == "Feature Film" and sections["Feature Film"] == outline.blank_beats(structures.find("Feature Film"))
    assert any("doesn't fit" in n for n in notes)
    assert formats.of_story(new) == "feature-film" and new.is_screenplay()
    assert settings.load_story(new.path)["target_pages"] == 110
    back, notes = versions.new_version(new, "short-story", title="Back")
    assert "Feature Film" in back.sections() and back.meta["structure"] == "Story Spine" or "Story Spine" in back.sections()
    assert back.meta["structure"] in ("Story Spine", "Feature Film")


def test_a_structure_that_fits_is_copied_without_adding_another(home):
    s = make(home)
    new, notes = versions.new_version(s, "novel", title="Novel")
    assert [h for h in new.sections() if outline.is_beat_section(h)] == ["Story Spine"] and notes == []


def test_bad_arguments_are_refused_plainly(home):
    s = make(home)
    with pytest.raises(versions.VersionError, match="Unknown format"):
        versions.new_version(s, "opera")
    with pytest.raises(versions.VersionError, match="Unknown thing"):
        versions.new_version(s, "novel", copy=("outline", "dreams"))
    assert len(s.universe.stories()) == 1


# --- every format pair ---------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("src,dst", list(itertools.product(FORMAT_KEYS, FORMAT_KEYS)))
def test_every_format_pair_with_and_without_the_manuscript(home, src, dst):
    s = make(home, src)
    plain, notes = versions.new_version(s, dst, title="Plain")
    assert formats.of_story(plain) == dst and not plain.files() and not any(n.startswith(versions.ROUGH) for n in notes)
    assert formats.fits(structures.find(plain.meta["structure"]), dst)               # (the new format's own structure is the active one)
    with_ms, notes = versions.new_version(s, dst, title="With", copy=versions.COPY_OPTIONS)
    assert formats.of_story(with_ms) == dst and with_ms.files() and with_ms.word_count() > 0
    assert any(n.startswith(versions.ROUGH) for n in notes)
    own = s.script_path if formats.is_script(src) else s.manuscript_dir / "manuscript.md"          # (the source is never changed)
    assert own.read_text(encoding="utf-8") == (SCRIPT if formats.is_script(src) else "She waited. It rained.\n\n* * * The Road\n\n\"Go,\" he said.\n")
    assert versions.family_of(plain) == versions.family_of(with_ms) == s.slug


def test_prose_to_prose_copies_the_files_as_they_are(home):
    s = make(home)
    new, notes = versions.new_version(s, "novel", copy=("manuscript",))
    assert (new.manuscript_dir / "manuscript.md").read_text(encoding="utf-8") == (s.manuscript_dir / "manuscript.md").read_text(encoding="utf-8")
    assert "separate copy" in notes[0]
    (new.manuscript_dir / "manuscript.md").write_text("changed", encoding="utf-8")
    assert "changed" not in s.manuscript_text()


def test_an_empty_manuscript_is_said_not_faked(home):
    s = make(home, manuscript=False)
    new, notes = versions.new_version(s, "feature-film", copy=("manuscript",))
    assert not new.files() and "nothing to copy" in notes[0]


# --- the rough conversions -----------------------------------------------------------------------------------------------------

def test_prose_becomes_fountain_action_with_forced_headings_for_breaks():
    out = versions.prose_to_fountain("She waited.\nIt rained.\n* * *\nNext.\n* * * The Road\n\"Go,\" he said.\n")
    assert out == 'She waited.\n\nIt rained.\n\n.NEW SCENE\n\nNext.\n\n.THE ROAD\n\n"Go," he said.\n'
    from storywheel import fountain
    kinds = [e.type for e in fountain.parse(out).elements]
    assert kinds.count("heading") == 2 and kinds.count("action") == 4


def test_a_prose_line_that_looks_like_a_heading_is_forced_to_action():
    from storywheel import fountain
    out = versions.prose_to_fountain("INT. a quarrel began.\n")
    assert fountain.parse(out).elements[0].type == "action"


def test_prose_to_script_file_has_a_title_page_a_note_and_the_prose(home):
    s = make(home)
    new, notes = versions.new_version(s, "short-film", title="Short Cold", copy=("manuscript",))
    text = new.script_path.read_text(encoding="utf-8")
    from storywheel import fountain
    script = fountain.parse(text)
    assert script.title["title"] == ["Short Cold"] and "Rough start" in text
    assert [e.text for e in script.of("action")][:2] == ["FADE IN:", "She waited. It rained."][:2] or "She waited. It rained." in text
    assert script.of("heading")[0].text == "THE ROAD" and "rough" in notes[0].lower()
    assert not (new.manuscript_dir / "manuscript.md").exists()


def test_a_script_becomes_prose_paragraphs():
    out = versions.fountain_to_prose(SCRIPT)
    lines = out.strip().split("\n")
    assert lines == ["* * * INT. DINER - NIGHT", "Rain on the glass. MARA stares at a cup.", '"It went cold an hour ago," Mara said.',
                     "* * * EXT. ROAD - DAY", "A truck passes.", "\"Don't wait up,\" Bram said."]
    assert "CUT TO" not in out and "quietly" not in out and "Title" not in out


def test_dialogue_keeps_a_question_or_an_exclamation_inside_the_quotes():
    out = versions.fountain_to_prose("INT. A - DAY\n\nMARA\nWho?\n\nBRAM\nRun!\n")
    assert '"Who?" Mara said.' in out and '"Run!" Bram said.' in out


def test_script_to_prose_in_a_novel_goes_into_a_chapter_file(home):
    s = make(home, "feature-film")
    new, _ = versions.new_version(s, "novel", copy=("manuscript",))
    assert [p.name for p in new.files()] == ["01-cold-coffee.md"] and "Mara said" in new.manuscript_text()
    assert new.word_count() > 0 and not new.is_screenplay()


def test_script_to_short_story_writes_the_one_manuscript_file(home):
    s = make(home, "short-film")
    new, _ = versions.new_version(s, "short-story", copy=("manuscript",))
    assert [p.name for p in new.files()] == ["manuscript.md"] and len(new.scene_list()) == 2
    assert s.script_path.read_text(encoding="utf-8") == SCRIPT


def test_size_text_is_words_for_prose_and_pages_for_a_script(home):
    s = make(home)
    assert versions.size_text(s) == f"{s.word_count():,} words"
    f, _ = versions.new_version(s, "short-film", copy=("manuscript",))
    assert "pages" in versions.size_text(f) or "words" in versions.size_text(f)
    empty, _ = versions.new_version(s, "novel")
    assert versions.size_text(empty) == "0 words"


# --- the CLI -------------------------------------------------------------------------------------------------------------------

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def cli(args, home):
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "home"), STORYWHEEL_LIBRARY=str(home / "library"),
               STORYWHEEL_OUT=str(home / "out"), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "storywheel", *args], capture_output=True, text=True, env=env, cwd=ROOT, encoding="utf-8")


def test_story_version_command_and_show_json(home):
    s = make(home)
    shown = json.loads(cli(["story", "show", "noirville/cold-coffee", "--json"], home).stdout)
    assert shown["family"] == "" and shown["siblings"] == [] and shown["versions"] == []         # (a story with no versions)
    r = cli(["story", "version", "noirville/cold-coffee", "--format", "feature-film", "--title", "Cold Coffee, the Film",
             "--copy", "outline,notes,manuscript", "--json"], home)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["story"] == "cold-coffee-the-film" and out["format"] == "feature-film" and out["family"] == "cold-coffee"
    assert out["copied"] == ["outline", "notes", "manuscript"] and out["notes"]
    one = json.loads(cli(["story", "show", "noirville/cold-coffee", "--json"], home).stdout)
    other = json.loads(cli(["story", "show", "noirville/cold-coffee-the-film", "--json"], home).stdout)
    assert one["family"] == other["family"] == "cold-coffee"
    assert one["siblings"] == ["cold-coffee-the-film"] and other["siblings"] == ["cold-coffee"]
    assert [v["format_key"] for v in other["versions"]] == ["short-story", "feature-film"]
    assert other["format_key"] == "feature-film" and other["screenplay"] is True and other["words"] > 0
    assert "seed" not in other["settings"] and not (Path(other["path"]) / "seed.json").exists()


def test_story_version_command_refuses_bad_input_plainly(home):
    make(home)
    no_format = cli(["story", "version", "noirville/cold-coffee"], home)
    assert no_format.returncode != 0 and "--format" in no_format.stderr
    bad = cli(["story", "version", "noirville/cold-coffee", "--format", "novel", "--copy", "dreams"], home)
    assert bad.returncode != 0 and "Unknown thing" in bad.stderr
    plain = cli(["story", "version", "noirville/cold-coffee", "--format", "Screenplay (short film)", "--copy", "none"], home)
    assert plain.returncode == 0 and "screenplay (short film)" in plain.stdout


# --- promotion with more than one format ---------------------------------------------------------------------------------------

def test_promotion_with_two_formats_makes_one_set_of_entities_and_two_linked_stories(home):
    from storywheel import promote
    from storywheel.sample import build_story
    from conftest import make_engine

    def draft():
        d = build_story(make_engine(home, seed=3), ["western"], structure="story-spine")
        d["id"] = "20260101-000000"
        return d

    d = draft()
    one = promote.build_plan(d, None, make_engine(home), new_universe_name="Solo")
    promote.apply_plan(one, None, d)
    solo = vault.get_universe("solo")

    d2 = draft()
    plan = promote.build_plan(d2, None, make_engine(home), new_universe_name="Duo")
    plan.also = ["feature-film", "novel", "short-story"]                         # (short story is the draft's own format: no second copy)
    story, report = promote.apply_plan(plan, None, d2)
    duo = vault.get_universe("duo")
    assert len(duo.entities()) == len(solo.entities())                           # entities are created once
    family = versions.versions(story)
    assert [formats.of_story(s) for s in family] == ["short-story", "feature-film", "novel"]
    assert all(versions.family_of(s) == story.slug for s in family)
    assert sum("version" in r for r in report) == 2 and any("Also start as screenplay (feature film)" in l for l in plan.lines())
    film = family[1]
    assert film.sections()["Premise"] == story.sections()["Premise"] and film.meta["cast"] == story.meta["cast"]
    assert "Feature Film" in film.sections() and film.is_screenplay()
    assert d2["promoted"] == {"universe": "duo", "story": story.slug}


def test_promote_command_also(home):
    from storywheel import store
    from storywheel.sample import build_story
    from conftest import make_engine
    d = build_story(make_engine(home, seed=3), ["western"], structure="story-spine")
    d["id"] = "20260101-000001"
    store.save_draft(d)
    bad = cli(["promote", "20260101-000001", "--new", "Cmd", "--yes", "--also", "opera"], home)
    assert bad.returncode != 0 and "Unknown format" in bad.stderr
    r = cli(["promote", "20260101-000001", "--new", "Cmd", "--yes", "--also", "short-film", "--json"], home)
    assert r.returncode == 0, r.stderr
    stories = json.loads(cli(["story", "list", "--universe", "cmd", "--json"], home).stdout)
    assert sorted(s["format_key"] for s in stories) == ["short-film", "short-story"] and len({s["family"] for s in stories}) == 1


def test_a_story_without_a_family_exports_and_lists_as_before(home):
    s = make(home)
    from storywheel import export
    assert export.compile_text(s) and export.plain_text(s)
    assert [r["family"] for r in versions.rows(s.universe)] == [""]
    assert "family" not in (s.path / "story.md").read_text(encoding="utf-8")
