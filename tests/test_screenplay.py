"""Screenplay stories (batch 17): reading Fountain, screen structures, a script as a story's manuscript (no prose rules), starting the
script from the outline, the flip test, the page estimate and the `storywheel script` commands."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from storywheel import fountain, screenplay, screenplay_pdf, settings, structures, vault

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "screenplay" / "the-lamp.fountain"


def lamp():
    return FIXTURE.read_text(encoding="utf-8")


# --- reading Fountain ---------------------------------------------------------------------------------------------------------

def test_the_parser_finds_every_element_of_the_sample():
    s = fountain.parse(lamp())
    kinds = {e.type for e in s.elements}
    assert {"heading", "action", "character", "parenthetical", "dialogue", "transition", "centered", "page_break", "section", "synopsis",
            "lyrics"} <= kinds
    assert s.title["title"] == ["The Lamp in the Attic"] and s.title["author"] == ["Andy Example"]
    cues = [(e.name, e.ext, e.dual) for e in s.of("character")]
    assert ("MARA", "(V.O.)", False) in cues and ("VOICE", "(O.S.)", False) in cues and ("MARA", "(CONT'D)", False) in cues
    assert ("MARA", "", True) in cues                                    # the right-hand side of the dual dialogue
    assert [e.text for e in s.of("transition")] == ["CUT TO:", "DISSOLVE TO:", "FADE OUT."]
    assert s.characters()[:3] == ["MARA", "VOICE", "BRAM"]
    assert "HOLLOWAY HOUSE - ATTIC" in s.locations()


def test_notes_and_the_boneyard_are_left_out_but_lines_keep_their_numbers():
    text = "INT. ROOM - DAY\n\n/* hidden\nstill hidden */\n\nShe waits. [[a note]]\n"
    s = fountain.parse(text)
    assert [(e.type, e.line) for e in s.elements] == [("heading", 1), ("action", 6)]
    assert s.elements[1].text == "She waits."


@pytest.mark.parametrize("line,kind", [("INT. HOUSE - DAY", "heading"), ("ext. lane - night", "heading"), ("I/E. CAR - DAY", "heading"),
                                       (".FLASHBACK", "heading"), ("CUT TO:", "transition"), ("> FADE OUT.", "transition"),
                                       ("> THE END <", "centered"), ("===", "page_break"), ("!INT. NOT A HEADING", "action"),
                                       ("# Act One", "section"), ("= what happens", "synopsis"), ("~ la la", "lyrics")])
def test_single_lines_between_blank_lines(line, kind):
    s = fountain.parse("\n" + line + "\n\n")
    assert s.elements[0].type == kind


def test_a_cue_needs_words_after_it_and_a_blank_line_before():
    assert fountain.parse("\nMARA\nHello.\n").elements[0].type == "character"
    assert fountain.parse("\nMARA\n\nHello.\n").elements[0].type == "action"
    assert fountain.parse("Rain.\nMARA\nHello.\n").elements[0].type == "action"
    assert fountain.parse("\n@McCLANE\nYippee.\n").elements[0].name == "McCLANE"


def test_the_grammar_checker_reads_only_sentences():
    text = lamp()
    lines = text.split("\n")
    prose = fountain.prose_lines(text)
    kinds = fountain.line_types(text)
    assert all(kinds[k] in ("action", "dialogue", "parenthetical", "lyrics") for k in prose)
    heading = lines.index("INT. HOLLOWAY HOUSE - ATTIC - NIGHT") + 1
    cue = lines.index("BRAM") + 1
    assert heading not in prose and cue not in prose and lines.index("CUT TO:") + 1 not in prose


# --- screen structures ------------------------------------------------------------------------------------------------------

def test_screen_structures_exist_and_are_never_picked_at_random():
    ff, sf = structures.find("feature-film"), structures.find("Short Film")
    assert ff.screen and sf.screen and ff.pages == 110 and sf.pages == 12
    assert [b.act for b in ff.beats] == ["Act One"] * 2 + ["Act Two"] * 4 + ["Act Three"] * 2
    assert all(not s.screen for s in structures.prose()) and ff not in structures.prose()


def test_the_wheel_never_rolls_a_screen_structure_on_its_own():
    from storywheel.engine import Engine
    from storywheel.sample import build_story
    e = Engine(seed=3)
    picked = {build_story(e, ["horror"])["kept"]["structure"]["structure"] for _ in range(40)}
    assert not picked & {"Feature Film", "Short Film"}


def test_a_story_rolled_on_a_screen_structure_gets_screen_beats():
    from storywheel.engine import Engine
    from storywheel.sample import build_story
    st = build_story(Engine(seed=4), ["thriller"], structure="feature-film")
    assert list(st["kept"]["spine"]) == [b.key for b in structures.find("feature-film").beats]


# --- a screenplay story ------------------------------------------------------------------------------------------------------

@pytest.fixture
def shortfilm(home):
    u = vault.create_universe("Lamp", ["ghost story"])
    labels = [b.label for b in structures.find("short-film").beats]
    body = "\n\n".join(f"**{l}.** Beat {i}." for i, l in enumerate(labels, 1))
    return u.new_story("The Lamp in the Attic", {"structure": "Short Film", "genre": "ghost story"}, {"Short Film": body})


def test_a_story_on_a_screen_structure_is_a_screenplay_with_a_page_target(shortfilm):
    assert shortfilm.is_screenplay() and settings.load_story(shortfilm.path)["format"] == "screenplay"
    assert screenplay.target_pages(shortfilm) == 12
    assert "format" not in shortfilm.load_outline()[0]                     # (a setting, not part of the outline)


def test_a_blank_story_can_be_made_a_screenplay(home):
    u = vault.create_universe("Blank", ["noir"])
    s = u.new_story("Cold Coffee", {"format": "screenplay"})
    assert s.is_screenplay() and screenplay.target_pages(s) == 110                       # (a screenplay with no kind: a feature film)


def test_promoting_a_wheel_draft_on_a_screen_structure_makes_a_screenplay(home):
    from storywheel import promote, store
    from storywheel.engine import Engine
    from storywheel.sample import build_story
    draft = build_story(Engine(seed=5), ["noir"], structure="short-film")
    u = vault.create_universe("Rain City", ["noir"])
    plan = promote.build_plan(draft, u, Engine(seed=5), None)
    story, _report = promote.apply_plan(plan, u, draft)
    assert story.is_screenplay() and screenplay.target_pages(story) == 12


def test_starting_the_script_from_the_outline_writes_sections_and_synopses(shortfilm):
    path = screenplay.start_from_outline(shortfilm)
    text = path.read_text(encoding="utf-8")
    s = fountain.parse(text)
    assert path.name == "script.fountain" and s.title["title"] == ["The Lamp in the Attic"]
    assert [e.text for e in s.of("section")] == [b.label for b in structures.find("short-film").beats]
    assert [e.text for e in s.of("synopsis")][:2] == ["Beat 1.", "Beat 2."]
    printed = screenplay_pdf.paginate(text)
    assert not any("Beat 1" in (ln.text if ln else "") for p in printed for ln in p.lines)        # (sections and synopses never print)


def test_a_feature_film_outline_groups_sequences_under_acts(home):
    u = vault.create_universe("Big", ["thriller"])
    ff = structures.find("feature-film")
    body = "\n\n".join(f"**{b.label}.** Text {i}." for i, b in enumerate(ff.beats))
    s = u.new_story("Runner", {"structure": ff.label}, {ff.label: body})
    text = screenplay.start_from_outline(s).read_text(encoding="utf-8")
    sections = [(e.level, e.text) for e in fountain.parse(text).of("section")]
    assert sections[0] == (1, "Act One") and sections[1] == (2, "Sequence A: The world and the want")
    assert (1, "Act Two") in sections and (1, "Act Three") in sections


def test_an_existing_script_is_never_overwritten(shortfilm):
    screenplay.start_from_outline(shortfilm)
    shortfilm.script_path.write_text(shortfilm.script_path.read_text() + "\nINT. ROOM - DAY\n\nShe waits.\n")
    with pytest.raises(screenplay.ScriptExists):
        screenplay.start_from_outline(shortfilm)
    screenplay.start_from_outline(shortfilm, replace=True)
    backups = list((shortfilm.path / ".backups").glob("script-*/script.fountain"))
    assert backups and "She waits." in backups[0].read_text()


def test_the_prose_rules_never_touch_a_script(shortfilm):
    text = "Title: X\n\nINT. ROOM - DAY\n\nShe waits.\nAnd waits.\n\nMARA\nHello.\n"
    shortfilm.script_path.parent.mkdir(parents=True, exist_ok=True)
    shortfilm.script_path.write_text(text)
    (shortfilm.path / ".one-line-paragraphs").unlink()
    (shortfilm.path / ".one-file-manuscript").unlink(missing_ok=True)
    assert shortfilm.migrate_paragraphs() is None and shortfilm.migrate_manuscript() is None
    assert shortfilm.script_path.read_text() == text
    assert shortfilm.files() == [shortfilm.script_path] and shortfilm.extra_files() == []
    assert [sc["title"] for sc in shortfilm.scene_list()] == ["INT. ROOM - DAY"]
    assert shortfilm.word_count() == 9                                       # (headings and cues count; the title page does not)


def test_a_new_scene_in_a_script_is_a_scene_heading(shortfilm):
    where = shortfilm.append_scene("int. kitchen - night")
    lines = shortfilm.script_path.read_text().split("\n")
    assert lines[where["line"] - 1] == "INT. KITCHEN - NIGHT"


# --- the flip test and the page estimate --------------------------------------------------------------------------------------

def test_the_flip_test_finds_what_a_reader_notices():
    long_action = " ".join(["The rain keeps falling on the roof and the gutters overflow."] * 6)
    speech = " ".join(["I keep talking and talking about the house."] * 12)
    cuts = "\n\n".join(f"INT. ROOM {i} - DAY\n\nShe waits.\n\nCUT TO:" for i in range(3))
    text = f"INT. ATTIC - NIGHT\n\n{long_action}\n\nWe see the lamp swing. The CAMERA pans to the door.\n\nMARA\n{speech}\n\n{cuts}\n"
    found = screenplay.flip_test(text, target=40)
    kinds = [d["kind"] for d in found]
    assert "long-action" in kinds and "long-speech" in kinds and kinds.count("camera") == 1 and kinds.count("cut-to") == 3
    assert "length" in kinds
    assert found == sorted(found, key=lambda d: d["line"])
    lines = text.split("\n")
    assert lines[next(d["line"] for d in found if d["kind"] == "camera") - 1].startswith("We see")


def test_a_clean_short_script_passes_the_flip_test():
    assert screenplay.flip_test("INT. ROOM - DAY\n\nShe waits.\n\nMARA\nHello.\n") == []


def test_the_page_estimate_follows_the_layout():
    assert screenplay_pdf.estimate_pages("") == 0
    one = "\n\n".join(f"INT. ROOM {i} - DAY\n\nShe waits by the window." for i in range(10))
    assert 0.5 < screenplay_pdf.estimate_pages(one) < 1.0
    assert 3 <= screenplay_pdf.estimate_pages(lamp()) <= 5


# --- the command line --------------------------------------------------------------------------------------------------------

def cli(*args, env=None):
    return subprocess.run([sys.executable, "-m", "storywheel", *args], capture_output=True, text=True, env=env, cwd=ROOT)


def test_the_script_commands(shortfilm, tmp_path):
    import os
    env = dict(os.environ)
    target = f"{shortfilm.universe.slug}/{shortfilm.slug}"
    r = cli("script", "start", target, "--json", env=env)
    assert r.returncode == 0, r.stderr
    path = json.loads(r.stdout)["path"]
    assert Path(path).exists()
    f = tmp_path / "x.fountain"
    f.write_text(lamp())
    r = cli("script", "check", str(f), "--json", "--target-pages", "12", env=env)
    data = json.loads(r.stdout)
    assert r.returncode == 0 and data["pages"] > 0 and isinstance(data["problems"], list)
    r = cli("script", "scenes", str(f), "--json", env=env)
    assert [d["title"] for d in json.loads(r.stdout)][0] == "EXT. HOLLOWAY HOUSE - NIGHT"
    r = cli("story", "show", target, "--json", env=env)
    info = json.loads(r.stdout)
    assert info["screenplay"] is True and info["target_pages"] == 12 and info["script"].endswith("script.fountain")
