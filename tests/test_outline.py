"""The outline reads like the Wheel's 'story so far': plain text, one beat per row, no raw markdown, no doubled labels."""
import asyncio

import pytest
from textual.widgets import Input

from storywheel import builder, fill, outline, promote, vault
from storywheel.engine import Engine
from storywheel.sample import build_story
from conftest import make_engine, screen_text


def flat(text):
    return " ".join(text.split())


def promoted(home, structure, seed=3):
    d = build_story(make_engine(home, seed=seed), ["western"], structure=structure)
    d["id"] = f"d{seed}"
    plan = promote.build_plan(d, None, Engine(seed=1), "Thornwood")
    story, _ = promote.apply_plan(plan, None, d)
    return d, story


def test_the_story_spine_beats_are_plain_paragraphs_with_no_repeated_label(home):
    d, story = promoted(home, "story-spine")
    sections = story.sections()
    spine = sections["Story Spine"]
    assert "**" not in spine and "Once upon a time. Once upon a time" not in spine
    paragraphs = spine.split("\n\n")
    assert len(paragraphs) == len(d["kept"]["spine"]) and paragraphs[0].lower().startswith("once upon a time")
    assert paragraphs == list(d["kept"]["spine"].values())


def test_a_structure_that_shows_its_labels_keeps_them(home):
    d, story = promoted(home, "kishotenketsu")
    text = story.sections()["Kishōtenketsu"]
    assert text.count("**") == 2 * len(d["kept"]["spine"])
    rows = outline.rows(story)
    beats = [r for r in rows if r[0].startswith("beat:")]
    assert len(beats) == len(d["kept"]["spine"]) and all("**" not in r[2] for r in beats)
    assert [r[1] for r in beats] == ["Ki", "Shō", "Ten", "Ketsu"][:len(beats)] or all(r[1] for r in beats)


def test_rows_are_readable(home):
    d, story = promoted(home, "story-spine")
    rows = outline.rows(story)
    keys = [r[0] for r in rows]
    assert keys[:3] == ["meta:title", "meta:genre", "meta:structure"]
    assert [k for k in keys if k.startswith("setting:")] == [f"setting:{n}" for n in ("Place", "Era", "Season", "Landmark", "Rumor")]
    beats = [r for r in rows if r[0].startswith("beat:")]
    assert [r[1] for r in beats] == [f"{i + 1}." for i in range(len(beats))]          # numbered: the sentences carry their own openers
    everything = "\n".join(f"{l} {t}" for _k, l, t in rows)
    assert "**" not in everything and "\n- " not in everything and not any(t.startswith("- ") for _k, _l, t in rows)
    assert any(k == "section:Twist" for k in keys) and any(k == "section:Premise" for k in keys)


def test_old_style_outlines_with_doubled_labels_are_cleaned_for_showing(home):
    u = vault.create_universe("U")
    s = u.new_story("Tale", {"structure": "Story Spine"}, {
        "Story Spine": "**Once upon a time.** Once upon a time, Wade lived.\n\n**Every day.** Every day, Wade worked.\n\n**Setup.** Wade rode in."})
    labels = [(r[1], r[2]) for r in outline.rows(s) if r[0].startswith("beat:")]
    assert labels == [("1.", "Once upon a time, Wade lived."), ("2.", "Every day, Wade worked."), ("Setup", "Wade rode in.")]


def test_editing_one_beat_changes_only_that_paragraph(home):
    d, story = promoted(home, "story-spine")
    before = story.sections()["Story Spine"].split("\n\n")
    key = "beat:Story Spine:2"
    assert outline.raw(story, key) == before[2]
    outline.save(story, key, "Something else happened entirely.")
    after = story.sections()["Story Spine"].split("\n\n")
    assert after[2] == "Something else happened entirely." and after[:2] + after[3:] == before[:2] + before[3:]


def test_editing_a_beat_keeps_its_label_when_it_has_one(home):
    u = vault.create_universe("U")
    s = u.new_story("Tale", {}, {"Kishōtenketsu": "**Ki.** First.\n\n**Shō.** Second."})
    outline.save(s, "beat:Kishōtenketsu:1", "Changed.")
    assert s.sections()["Kishōtenketsu"] == "**Ki.** First.\n\n**Shō.** Changed."


def test_editing_a_setting_line_changes_only_that_line(home):
    d, story = promoted(home, "story-spine")
    before = story.sections()["Setting"].splitlines()
    outline.save(story, "setting:Era", "the great drought")
    after = story.sections()["Setting"].splitlines()
    assert [l for l in after if "Era" in l] == ["- **Era:** the great drought"] and len(after) == len(before)
    assert outline.raw(story, "setting:Era") == "the great drought" and outline.raw(story, "setting:Place") == d["kept"]["setting"]["place"]


def test_the_builder_shows_the_outline_as_plain_text_and_edits_one_row(home):
    d, story = promoted(home, "story-spine")
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="thornwood", story=story.slug)
        async with app.run_test(size=(220, 55)) as pilot:
            await pilot.pause()
            shown = flat(screen_text(app))
            keys = [r[0] for r in app.screen_ref.top_rows()]
            app.screen_ref.outline.focus()
            app.screen_ref.outline.highlighted = keys.index("beat:Story Spine:1")
            await pilot.pause()
            await pilot.press("e")
            await pilot.pause()
            box = app.screen.query_one(Input)
            was = box.value
            box.value = "A new second beat."
            await pilot.press("enter")
            await pilot.pause()
            return shown, was
    shown, was = asyncio.run(go())
    assert "**" not in shown and "Once upon a time. Once upon a time" not in shown
    assert was == d["kept"]["spine"][list(d["kept"]["spine"])[1]]
    assert story.sections()["Story Spine"].split("\n\n")[1] == "A new second beat."
