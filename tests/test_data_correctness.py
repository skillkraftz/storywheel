"""Apostrophes and possessives survive every stage; a hand-written title moves the motif; season is a real field."""
import asyncio
import glob
import json
import re
from pathlib import Path

import pytest

from storywheel import export, outline, promote, settings, store, threads, vault
from storywheel.engine import Engine
from storywheel.library import DATA
from storywheel.session import Session
from storywheel.text import motif_from, plural, singular
from conftest import make_engine, screen_text


# --- plurals and singulars ---------------------------------------------------------------------------------------------

def all_words(slot_dirs):
    words = set()
    for d in slot_dirs:
        for f in glob.glob(str(DATA / "lists" / d / "*.json")):
            for e in json.load(open(f)).get("entries", []):
                t = e if isinstance(e, str) else e["text"]
                if re.fullmatch(r"[a-z]+", t):
                    words.add(t)
    return words


def test_singular_undoes_plural_for_every_title_noun_and_noun():
    bad = [(w, plural(w), singular(plural(w))) for w in sorted(all_words(["title_noun", "noun"])) if singular(plural(w)) != w]
    assert bad == []


@pytest.mark.parametrize("plural_form,expected", [("gallowses", "gallows"), ("prairies", "prairie"), ("cactuses", "cactus"),
                                                   ("trellises", "trellis"), ("cities", "city"), ("houses", "house"), ("buses", "bus"),
                                                   ("boxes", "box"), ("stags", "stag"), ("wolves", "wolf")])
def test_singular_cases(plural_form, expected):
    assert singular(plural_form) == expected


def test_singular_leaves_possessives_alone():
    for w in ("sorcerer's", "witch's", "sorcerers'", "O'Brien"):
        assert singular(w) == w


def test_motif_from_a_title_with_a_possessive():
    assert motif_from("The Sorcerer's Apprentice", lambda: "x") == "apprentice"
    assert motif_from("The Last Bell of Glasswater", lambda: "x") == "bell"


# --- thread text is replaced by whole words only -------------------------------------------------------------------------------

def test_replace_text_never_reaches_into_a_longer_word():
    assert threads.replace_text("a sorcerer's apprentice and the sorcerer", "the sorcerer", "the witch")[0] == "a sorcerer's apprentice and the witch"
    assert threads.replace_text("the sorcerers came", "the sorcerer", "the witch")[0] == "the sorcerers came"
    assert threads.replace_text("The locked box was a fake", "the locked box", "the pistol")[0] == "The pistol was a fake"
    assert threads.replace_text("the locked box's lid", "the locked box", "the pistol")[0] == "the pistol's lid"


def test_a_pronoun_pass_does_not_eat_part_of_a_possessive_thread():
    t = {"text": "a sorcerer's apprentice", "beat": "x"}
    assert threads.verify(t, "Then a sorcerer's apprentice arrived.", "Er") == t
    t2 = {"text": "Amanda's first love", "beat": "x"}
    assert threads.verify(t2, "Amanda met their first love.", "Amanda")["shown"] == "their first love"
    t3 = {"text": "a sorcerer's apprentice", "beat": "x"}
    assert threads.verify(t3, "An apprentice arrived.", "sorcerer") is None


# --- the whole pipeline ------------------------------------------------------------------------------------------------------------

DRAFT_SPINE = {
    "once": "Once upon a time, Maeve O'Brien kept a witch's cottage near Dry Fork.",
    "every_day": "Every day, Maeve fed the sorcerer's apprentice.",
    "one_day": "One day, a sorcerer's apprentice brought a note on red thread from the miller's daughter.",
    "because_1": "Because of that, Maeve hid the apprentice in the witch's cottage.",
    "because_2": "Because of that, the sorcerer's apprentice told the king's steward.",
    "until": "Until finally, Maeve gave up the cottage to save the sorcerer's apprentice.",
    "ever_since": "Ever since then, O'Brien's cottage has stood empty.",
}


def draft():
    d = store.new_story()
    d["id"] = "20260101-000000"
    d["kept"] = {
        "genre": {"genre": "fairy tale", "mood": "wistful"},
        "structure": {"structure": "Story Spine"},
        "title": {"title": "The Sorcerer's Apprentice", "motif": "apprentice"},
        "protagonist": {"name": "Maeve O'Brien", "age": "34", "job": "witch's helper", "trait": "wary", "want": "a quiet cottage",
                        "need": "to trust the miller's daughter", "flaw": "pride", "secret": "she's afraid of the king's steward",
                        "rival": "king's steward"},
        "setting": {"place": "Dry Fork", "era": "the king's last winter", "season": "autumn", "landmark": "the witch's cottage",
                    "rumor": "the miller's daughter vanished"},
        "premise": {"premise": "A witch's helper hides a sorcerer's apprentice from the king's steward."},
        "spine": dict(DRAFT_SPINE),
        "twist": {"twist": "The sorcerer's apprentice was the miller's daughter all along."},
    }
    d["threads"] = {"someone": {"text": "a sorcerer's apprentice", "beat": "one_day", "features": ["human", "magic"]},
                    "message": {"text": "a note on red thread", "beat": "one_day", "features": ["physical"]}}
    return d


EVERY_PHRASE = ["witch's cottage", "sorcerer's apprentice", "miller's daughter", "king's steward", "O'Brien"]


def check_phrases(text, what):
    for phrase in EVERY_PHRASE:
        if phrase in text:
            continue
        # a phrase the draft has must come out whole wherever it appears: no half-eaten versions
        stem = phrase.split("'")[0]
        mangled = re.findall(rf"\b{re.escape(stem[:-2])}\w*\b(?!')", text)
        assert not [m for m in mangled if m not in (stem, stem + "s") and m.startswith(stem[:5]) and "'" not in m
                    and m not in ("sorcerer", "sorcerers", "witch", "witches", "miller", "millers", "king", "kings", "steward")], (what, phrase, mangled)


def test_possessives_survive_wheel_promotion_outline_builder_and_export(home):
    d = draft()
    wheel_text = " ".join(d["kept"]["spine"].values()) + d["kept"]["premise"]["premise"] + d["kept"]["twist"]["twist"]
    plan = promote.build_plan(d, None, Engine(seed=1), "Thornwood")
    story, _ = promote.apply_plan(plan, None, d)
    meta, sections = story.load_outline()

    # promotion -> story.md (read back from disk)
    assert meta["title"] == "The Sorcerer's Apprentice"
    assert sections["Story Spine"].split("\n\n") == list(DRAFT_SPINE.values())
    assert sections["Premise"] == d["kept"]["premise"]["premise"] and sections["Twist"] == d["kept"]["twist"]["twist"]
    assert "- **Landmark:** the witch's cottage" in sections["Setting"]

    # the entities made from it
    u = story.universe
    names = {e.name for e in u.entities()}
    assert "Maeve O'Brien" in names and "a sorcerer's apprentice" in names and "king's steward" in names
    assert u.entity("maeve-obrien").fields["need"] == "to trust the miller's daughter"
    assert u.entity("maeve-obrien").fields["secret"] == "she's afraid of the king's steward"
    assert {e.id for e in u.entities()} >= {"maeve-obrien", "sorcerers-apprentice", "kings-steward"}

    # outline rows (what the Builder shows)
    rows = outline.rows(story)
    shown = " ".join(r[2] for r in rows)
    for phrase in EVERY_PHRASE:
        assert phrase in shown, phrase
    assert [r[2] for r in rows if r[0].startswith("beat:")] == list(DRAFT_SPINE.values())

    # an edit through the outline keeps apostrophes
    outline.save(story, "beat:Story Spine:1", "Every day, Maeve fed the sorcerer's apprentice and the witch's cat.")
    assert "the sorcerer's apprentice and the witch's cat." in story.sections()["Story Spine"]

    # the Builder, on screen
    from storywheel import builder, fill

    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="thornwood", story=story.slug)
        async with app.run_test(size=(220, 60)) as pilot:
            await pilot.pause()
            return " ".join(screen_text(app).split())
    screen = asyncio.run(go())
    for phrase in ("sorcerer's apprentice", "O'Brien", "The Sorcerer's Apprentice"):
        assert phrase in screen, phrase
    assert "sorcers" not in screen and "sorcerers apprentice" not in screen

    # a manuscript written from it, and the exports
    story.append_scene("Opening", "The sorcerer's apprentice knocked. Maeve O'Brien opened the witch's door.")
    settings.save_global({"legal_name": "A. Writer"})
    docx = pytest.importorskip("docx")
    result = export.export(story, "docx")
    paragraphs = [p.text for p in docx.Document(result["path"]).paragraphs]
    assert paragraphs[paragraphs.index("by A. Writer") - 1] == "The Sorcerer\u2019s Apprentice"                 # (the export makes quotes curly)
    assert "The sorcerer\u2019s apprentice knocked. Maeve O\u2019Brien opened the witch\u2019s door." in paragraphs
    assert "sorcerer\u2019s apprentice" in export.plain_text(story) and "O\u2019Brien" in Path(export.export(story, "md")["path"]).read_text(encoding="utf-8")
    assert "witch\u2019s door" in Path(export.export(story, "txt")["path"]).read_text(encoding="utf-8")


def test_the_wheel_itself_keeps_possessives_when_an_earlier_step_changes(home):
    d = draft()
    s = Session(d, make_engine(home))
    d["step"] = 3
    s.enter(3)
    old = dict(d["kept"]["protagonist"])
    s.edit_field("name", "Moira Quill")
    s.keep()
    spine = " ".join(d["kept"]["spine"].values())
    assert "sorcerer's apprentice" in spine and "witch's cottage" in spine and "king's steward" in spine
    assert "Moira" in spine and "O'Brien's cottage" not in spine                 # the name was swapped, the rest left alone


def test_a_standin_swap_keeps_possessives_whole(home):
    d = draft()
    s = Session(d, make_engine(home))
    s.enter(3)
    cand = {"once": "Once upon a time, Joaquin kept the sorcerer's cottage.", "_inputs": {"first": {"value": "Joaquin", "step": "protagonist", "standin": True}}}
    new = s.update_candidate(cand, [("first", "protagonist", "Joaquin", "Maeve"), ("job", "protagonist", "sorcerer", "baker")])
    assert new["once"] == "Once upon a time, Maeve kept the baker's cottage."     # (a stand-in job inside a possessive is replaced as a word)
    other = s.update_candidate({"once": "The sorcerers met."}, [("job", "protagonist", "sorcerer", "baker")])
    assert other["once"] == "The sorcerers met."


# --- the motif follows a hand-written title -----------------------------------------------------------------------------------------

def title_session(home):
    s = Session(store.new_story(), make_engine(home, seed=3))
    s.enter(0)
    while s.step.key != "title":
        s.keep()
    return s


def test_a_hand_written_title_moves_the_motif(home):
    s = title_session(home)
    s.cand["motif"] = "whiskey"
    s.edit_field("title", "The Last Bell of Glasswater")
    assert s.fields["title"] == "The Last Bell of Glasswater" and s.fields["motif"] == "bell"
    assert any("motif now follows your title" in n for n in s.take_notes())


def test_editing_the_motif_itself_is_left_alone(home):
    s = title_session(home)
    s.edit_field("title", "The Last Bell of Glasswater")
    s.edit_field("motif", "lantern")
    assert s.fields["motif"] == "lantern" and s.fields["title"] == "The Last Bell of Glasswater"


def test_writing_the_whole_item_follows_the_title_unless_you_changed_the_motif_too(home):
    s = title_session(home)
    s.replace_fields({"title": "A Key for the Widow", "motif": s.fields["motif"]})
    assert s.fields["motif"] == "key"
    s.replace_fields({"title": "A Rose for the Widow", "motif": "ghost"})
    assert s.fields["motif"] == "ghost"


def test_the_title_step_kept_with_a_new_title_has_the_matching_motif(home):
    s = title_session(home)
    s.edit_field("title", "The Last Bell of Glasswater")
    s.keep()
    assert s.story["kept"]["title"] == {"title": "The Last Bell of Glasswater", "motif": "bell"}


# --- season, and where a place is ----------------------------------------------------------------------------------------------------------

def test_season_is_a_real_place_field(home):
    from storywheel import schemas
    keys = schemas.field_keys("place")
    assert keys.index("season") == keys.index("era") + 1
    spec = schemas.field_spec("place", "season")
    assert spec["label"] == "Season" and schemas.can_roll(spec)
    assert schemas.field_spec("place", "parent")["label"] == "Located in"


def test_promotion_stores_the_season_as_a_field_not_a_custom_one(home):
    d = draft()
    story, _ = promote.apply_plan(promote.build_plan(d, None, Engine(seed=1), "Thornwood"), None, d)
    town = story.universe.entity("dry-fork")
    assert town.fields["season"] == "autumn" and town.custom == {}
    assert "season: \"autumn\"" in town.path.read_text() and "custom" not in town.path.read_text()
    landmark = next(e for e in story.universe.entities("place") if e.fields["kind"] == "landmark")
    assert landmark.fields["parent"] == "dry-fork"


def test_an_older_place_with_a_custom_season_is_read_as_a_field(home):
    u = vault.create_universe("U")
    p = u.new_entity("place", "Old Town", {"kind": "town"})
    text = p.path.read_text().replace("created:", 'custom:\n  season: "winter"\ncreated:')
    p.path.write_text(text)
    again = vault.get_universe("u").entity("old-town")
    assert again.fields["season"] == "winter" and again.custom == {}


def test_a_place_rolled_in_the_builder_gets_a_season(home):
    from storywheel import fill
    u = vault.create_universe("U", ["western"])
    place = u.new_entity("place")
    done = fill.Filler(u, fill.make_engine(u, seed=3)).roll_blank(place)
    assert "season" in done and place.fields["season"]
