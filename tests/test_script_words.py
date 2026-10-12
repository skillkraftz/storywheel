"""Batch 24 B3: Story words and Overused words read a screenplay as words only (dialogue and action), and count who speaks."""
import pytest
from textual.widgets import OptionList, Select, TabbedContent

from storywheel import fountain, overused, storywords, vault
from test_words import index, run  # noqa: F401  (the small dictionary fixture, and the runner)

SCRIPT = """Title: The Lamp
Credit: Written by

FADE IN:

# Act One

= Synopsis wanderer words.

INT. ATTIC - NIGHT

Dust hangs in the lamplight. Lamplight everywhere. [[note: lamplight again]]

/* boneyard lamplight
lamplight */

MARA
(whispering lamplight)
Hello? Anybody home?

BRAM
Who's there? Mara?

MARA
Only me.

CUT TO:

INT. CELLAR - DAY

!INT. is not a heading here, Mara said. Damp walls.

BRAM
Come down.
(beat)
It is dry.

MARA (V.O.)
Never.

> THE END <
"""


@pytest.fixture
def script_story(home):
    u = vault.create_universe("Thornwood", ["horror"])
    s = u.new_story("The Lamp", {"structure": "Short Film"})
    s.script_path.parent.mkdir(parents=True, exist_ok=True)
    s.script_path.write_text(SCRIPT, encoding="utf-8")
    return u, s


def test_the_words_view_keeps_only_action_dialogue_and_keeps_every_line_and_column():
    view = fountain.words_view(SCRIPT)
    src = SCRIPT.split("\n")
    out = view.split("\n")
    assert len(out) == len(src)
    kept = {src[i].strip() for i, l in enumerate(out) if l.strip()}
    assert "Hello? Anybody home?" in kept and "Come down." in kept and "It is dry." in kept
    for left_out in ("INT. ATTIC - NIGHT", "MARA", "BRAM", "(whispering lamplight)", "(beat)", "CUT TO:", "# Act One", "= Synopsis wanderer words.",
                     "> THE END <", "Title: The Lamp", "MARA (V.O.)"):
        assert left_out not in kept
    dust = next(l for l in out if l.startswith("Dust"))
    assert dust.rstrip() == "Dust hangs in the lamplight. Lamplight everywhere." and "note" not in view and "boneyard" not in view
    forced = next(l for l in out if "is not a heading" in l)
    assert forced.startswith(" INT. is not") or forced.lstrip().startswith("INT. is not")                # (the ! is gone, the column is kept)
    assert out.index(dust) == src.index(next(l for l in src if l.startswith("Dust")))


def test_overused_counts_dialogue_and_action_but_not_cues_headings_notes_or_boneyard(script_story):
    _u, s = script_story
    toks = overused.tokens(s)
    words = [t[0] for t in toks]
    assert words.count("lamplight") == 2                                      # (the note, the boneyard and the parenthetical are not counted)
    for skipped in ("attic", "cellar", "synopsis", "wanderer", "cut", "act"):
        assert skipped not in words
    assert "mara" in words                                                    # (said in the action line, a real word of the story)
    assert words.count("mara") == 2 and {t[1] for t in toks} == {"INT. ATTIC - NIGHT", "INT. CELLAR - DAY"}
    top = overused.frequent(s, top=5, min_count=2)
    assert top[0]["word"] == "lamplight" and top[0]["count"] == 2
    where = top[0]["where"][0]
    assert where["scene"] == "INT. ATTIC - NIGHT" and SCRIPT.split("\n")[where["line"] - 1].startswith("Dust")


def test_story_words_does_not_flag_cues_headings_or_directions_as_odd_words(script_story):
    u, s = script_story
    u.new_entity("character", "Mara", {"role": "protagonist"})
    report = storywords.analyze(u, s, db=None)
    texts = {i.text.lower() for i in report["items"]}
    assert "bram" not in texts and "attic" not in texts and "cellar" not in texts and "wanderer" not in texts
    mara = next(i for i in report["items"] if i.kind == "name")
    assert mara.count == 2                                                    # (named twice in action and dialogue, not in the cues)
    assert mara.where[0]["scene"] == "INT. ATTIC - NIGHT" or mara.where[0]["scene"] == "INT. CELLAR - DAY"


def test_speech_counts_per_scene_and_in_all():
    sp = fountain.speech_by_scene(SCRIPT)
    assert [(sc["title"], [(r["name"], r["lines"], r["words"]) for r in sc["speakers"]]) for sc in sp["scenes"]] == [
        ("INT. ATTIC - NIGHT", [("MARA", 2, 5), ("BRAM", 1, 3)]),
        ("INT. CELLAR - DAY", [("BRAM", 1, 5), ("MARA", 1, 1)])]
    assert [(r["name"], r["lines"], r["words"]) for r in sp["totals"]] == [("BRAM", 2, 8), ("MARA", 3, 6)]
    text = storywords.speech_lines(sp)
    assert text[0].startswith("Who speaks") and any(l.startswith("  MARA") and "3 lines" in l for l in text) and "01 INT. ATTIC - NIGHT" in text
    assert storywords.speech_lines({"scenes": [], "totals": []}) == [] and storywords.speech_lines(None) == []


def test_a_dialogue_split_by_a_parenthetical_is_one_speech():
    sp = fountain.speech_by_scene("INT. A - DAY\n\nMARA\nOne two\n(beat)\nthree four five\n\nBRAM\nHm.\n")
    assert [(r["name"], r["lines"], r["words"]) for r in sp["totals"]] == [("MARA", 1, 5), ("BRAM", 1, 1)]


def test_analyze_has_speech_for_a_screenplay_only(script_story, home):
    u, s = script_story
    assert storywords.analyze(u, s, db=None)["speech"]["totals"][0]["name"] == "BRAM"
    prose = u.new_story("Plain")
    prose.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (prose.manuscript_dir / "manuscript.md").write_text("Some words here.\n", encoding="utf-8")
    assert "speech" not in storywords.analyze(u, prose, db=None)


def test_words_shows_who_speaks_for_a_screenplay(index, script_story):
    async def script(app, pilot):
        scr = app.screen
        scr.query_one(TabbedContent).active = "t-story"
        await pilot.pause()
        await pilot.pause()
        scr.query_one("#swview", Select).value = "speech"
        await pilot.pause()
        await pilot.pause()
        lst = scr.query_one("#swoften", OptionList)
        return scr.query_one("#swscope", Select).value, lst.display, [str(lst.get_option_at_index(i).prompt) for i in range(lst.option_count)]
    scope, shown, rows = run(script, {"universe": "thornwood", "story": "the-lamp", "back": "builder"})
    assert scope == "the-lamp" and shown
    assert rows[0].startswith("Who speaks") and any(r.strip().startswith("MARA") and "3 lines" in r for r in rows)
