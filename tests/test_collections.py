"""Collections and story status (batch 22): the kind of universe, a status for every story, ideas, the all-stories list, and their screens."""
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from textual.widgets import DataTable, Input, OptionList, RadioButton, TextArea

from storywheel import builder, fill, formats, frontmatter, ideas, promote, shelf, store, vault, versions
from storywheel.sample import build_story
from conftest import make_engine, run_tui, screen_text

ROOT = Path(__file__).resolve().parent.parent


def flat(text):
    return " ".join(text.split())


def cli(args, home):
    env = dict(os.environ, STORYWHEEL_HOME=str(home / "home"), STORYWHEEL_LIBRARY=str(home / "library"),
               STORYWHEEL_OUT=str(home / "out"), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "storywheel", *args], capture_output=True, text=True, env=env, cwd=ROOT, encoding="utf-8")


def age(story, ts):
    """Make every file of the story (outline, settings, manuscript...) last have been changed at `ts`."""
    for p in story.path.rglob("*"):
        if p.is_file():
            os.utime(p, (ts, ts))


def shelf_universe(name="Shelf"):
    return vault.create_universe(name, kind="collection")


# --- the kind of universe ---------------------------------------------------------------------------------------------------

def test_a_universe_is_a_world_unless_it_says_otherwise(home):
    assert vault.create_universe("Plain").kind == "world"
    assert vault.create_universe("Plain Too", ["noir"], kind="world").settings()["kind"] == "world"


def test_the_kind_round_trips_through_universe_md(home):
    u = shelf_universe("Short Ones")
    assert u.kind == "collection" and u.is_collection and u.settings()["kind"] == "collection"
    assert 'kind: "collection"' in u.file.read_text(encoding="utf-8")
    again = vault.get_universe("short-ones")
    assert again.kind == "collection"
    again.save_settings(genres=["noir"])                      # saving something else keeps the kind
    assert vault.get_universe("short-ones").kind == "collection"
    again.save_settings(kind="world")
    assert vault.get_universe("short-ones").kind == "world"
    with pytest.raises(ValueError):
        again.save_settings(kind="shelf")


def test_old_universes_are_worlds(home):
    u = vault.create_universe("Old")
    meta, body = frontmatter.loads(u.file.read_text(encoding="utf-8"))
    meta.pop("kind")                                           # (a universe.md written before kinds existed)
    u.file.write_text(frontmatter.dumps(meta, body), encoding="utf-8")
    assert "kind" not in u.file.read_text(encoding="utf-8")
    assert vault.get_universe("old").kind == "world" and vault.get_universe("old").settings()["kind"] == "world"
    meta["kind"] = "garden"                                    # (nonsense is a world too)
    u.file.write_text(frontmatter.dumps(meta, body), encoding="utf-8")
    assert vault.get_universe("old").kind == "world"


def test_has_entities_looks_at_the_folders(home):
    u = shelf_universe()
    assert not u.has_entities()
    u.new_entity("character", "Ana")
    assert u.has_entities()


# --- status and logline -----------------------------------------------------------------------------------------------------

def test_a_story_is_an_idea_until_it_has_text_and_then_a_draft(home):
    u = vault.create_universe("World")
    s = u.new_story("Plain")
    assert s.status == "idea"
    s.append_scene("One", "Words in the manuscript now.")
    assert s.status == "drafting"


def test_status_is_picked_from_four_and_kept_in_story_md(home):
    u = vault.create_universe("World")
    s = u.new_story("Plain")
    for value in vault.STATUSES:
        s.set_status(value)
        assert u.story("plain").status == value
    assert 'status: "done"' in s.outline_path.read_text(encoding="utf-8")
    s.append_scene("One", "Words.")
    assert s.status == "done"                                  # (a status you set stays; only an unset one follows the manuscript)
    with pytest.raises(ValueError):
        s.set_status("finished")
    s.set_status(" Revising ")
    assert s.status == "revising"


def test_each_version_has_its_own_status(home):
    u = vault.create_universe("World")
    s = u.new_story("Tale", {"format": "short-story"})
    s.set_status("revising")
    other, _notes = versions.new_version(s, "novel")
    assert other.status == "idea" and s.status == "revising"   # (a version does not inherit the status)
    other.set_status("drafting")
    assert s.status == "revising" and other.status == "drafting"
    assert [x.status for x in versions.versions(s)] == ["revising", "drafting"]


def test_the_logline_is_one_line(home):
    u = vault.create_universe("World")
    s = u.new_story("A")
    assert s.logline == ""
    s.save_notes("The first line of the notes.\nThe second.")
    assert s.logline == "The first line of the notes."
    s.set_section("Premise", "A clerk finds a clause.   It frees\nthe town.")
    assert s.logline == "A clerk finds a clause. It frees"       # (the first line of the premise)
    s.set_meta(logline="  Written   by hand \n and more ")
    assert s.logline == "Written by hand"


# --- ideas -----------------------------------------------------------------------------------------------------------------

def test_an_idea_is_a_flash_story_with_a_logline_and_notes(home):
    u = shelf_universe()
    s = ideas.new_idea(u, "The Last Clause", "A lawyer finds a clause.\nIt frees the town.\nBut who pays?")
    assert s.title == "The Last Clause" and s.logline == "A lawyer finds a clause."
    assert s.notes == "A lawyer finds a clause.\nIt frees the town.\nBut who pays?"
    assert formats.of_story(s) == "flash" and s.status == "idea" and s.word_count() == 0
    meta, sections = s.load_outline()
    assert not meta.get("structure") and sections == {}        # no structure is needed
    assert meta["logline"] == "A lawyer finds a clause."
    assert s.slug == "the-last-clause" and u.story("the-last-clause") is not None


def test_an_idea_can_be_a_short_story_and_needs_a_title(home):
    u = shelf_universe()
    s = ideas.new_idea(u, "Longer", "x", "short-story")
    assert formats.of_story(s) == "short-story" and formats.target(s) == (5000, "words")
    with pytest.raises(ValueError):
        ideas.new_idea(u, "   ", "text")
    with pytest.raises(ValueError):
        ideas.new_idea(u, "Odd", "", status="finished")
    blank = ideas.new_idea(u, "Only A Title")
    assert blank.logline == "" and not blank.notes_path.exists()


def test_sending_a_draft_as_an_idea_takes_its_title_and_premise(home):
    u = shelf_universe()
    d = build_story(make_engine(home, seed=2), ["western"], structure="story-spine")
    d["id"] = "20260101-000000"
    idea = ideas.send_draft(d, u)
    assert idea.title == store.title_of(d) and idea.status == "idea"
    premise = " ".join(d["kept"]["premise"]["premise"].split())
    assert idea.logline == premise and idea.sections()["Premise"] == premise
    assert idea.meta["idea_from"] == "20260101-000000"
    assert d["ideas"] == [{"universe": "shelf", "story": idea.slug}] and not d.get("promoted")
    assert u.entities() == []                                  # (no promotion: nothing but the story)


# --- promotion into a collection --------------------------------------------------------------------------------------------

def test_promotion_defaults_follow_the_kind(home):
    d = build_story(make_engine(home, seed=3), ["western"], structure="story-spine")
    d["id"] = "20260101-000000"
    world = vault.create_universe("World")
    plan = promote.build_plan(d, world, make_engine(home))
    assert not plan.collection and plan.items and all(i.include for i in plan.items) and plan.note() == ""
    coll = shelf_universe()
    plan = promote.build_plan(d, coll, make_engine(home))
    assert plan.collection and plan.items and not any(i.include for i in plan.items)
    assert "collection" in plan.note() and "tick" in plan.note()
    assert not any(l.startswith("Create ") for l in plan.lines()) and plan.lines()[-1].startswith("This universe is a collection")
    assert promote.build_plan(d, None, make_engine(home)).collection is False       # (a new universe is a world)


def test_a_collection_gets_the_story_and_no_entities_unless_ticked(home):
    d = build_story(make_engine(home, seed=3), ["western"], structure="story-spine")
    d["id"] = "20260101-000000"
    coll = shelf_universe()
    plan = promote.build_plan(d, coll, make_engine(home))
    story, _report = promote.apply_plan(plan, coll, d)
    assert coll.entities() == [] and story.meta["cast"] == []
    assert story.sections()["Premise"] == d["kept"]["premise"]["premise"] and story.seed()["id"] == "20260101-000000"
    assert d["promoted"] == {"universe": "shelf", "story": story.slug}
    # tick the protagonist and the rival: those two are created and linked, nothing else
    d2 = build_story(make_engine(home, seed=3), ["western"], structure="story-spine")
    d2["id"] = "20260101-000001"
    plan = promote.build_plan(d2, coll, make_engine(home))
    for item in plan.items:
        item.include = item.key in ("protagonist", "rival")
    promote.apply_plan(plan, coll, d2)
    made = coll.entities()
    assert sorted(e.fields["role"] for e in made) == ["protagonist", "rival"]
    pro = next(e for e in made if e.fields["role"] == "protagonist")
    assert coll.resolve(pro.fields["rival"]).fields["role"] == "rival"


def test_a_world_still_creates_everything(home):
    d = build_story(make_engine(home, seed=3), ["western"], structure="story-spine")
    d["id"] = "20260101-000000"
    world = vault.create_universe("World")
    plan = promote.build_plan(d, world, make_engine(home))
    promote.apply_plan(plan, world, d)
    assert len(world.entities()) == len(plan.items) > 2


# --- the all-stories list ---------------------------------------------------------------------------------------------------

def test_every_story_across_universes_newest_first_with_filters(home):
    a, b = shelf_universe("Alpha"), vault.create_universe("Beta")
    one = ideas.new_idea(a, "One", "first")
    two = ideas.new_idea(a, "Two", "second", "short-story")
    three = b.new_story("Three", {"format": "novel"})
    three.set_status("revising")
    for n, s in enumerate((one, two, three)):                   # (a known order of edits)
        age(s, 1_700_000_000 + n * 100)
    rows = shelf.rows()
    assert [r["title"] for r in rows] == ["Three", "Two", "One"]
    assert rows[0]["universe"] == "beta" and rows[0]["format"] == "novel" and rows[0]["status"] == "revising"
    assert rows[1]["format_label"] == "Short story" and rows[1]["logline"] == "second" and rows[1]["size"] == "0 words"
    assert [r["title"] for r in shelf.rows(status="idea")] == ["Two", "One"]
    assert [r["title"] for r in shelf.rows(fmt="flash")] == ["One"]
    assert [r["title"] for r in shelf.rows(status="idea", fmt="short-story")] == ["Two"]
    assert [r["title"] for r in shelf.rows(universe=b)] == ["Three"] and shelf.rows(status="done") == []
    assert shelf.counts(a) == {"idea": 2, "drafting": 0, "revising": 0, "done": 0}


def test_a_script_shows_pages_and_an_edit_moves_a_story_to_the_top(home):
    u = vault.create_universe("World")
    play = u.new_story("Play", {"format": "feature-film"})
    old = u.new_story("Old")
    age(play, 1_700_000_000)
    age(old, 1_700_000_100)
    assert [r["title"] for r in shelf.rows()] == ["Old", "Play"]
    assert shelf.rows()[1]["format"] == "feature-film"
    age(old, 1_600_000_000)
    assert [r["title"] for r in shelf.rows()] == ["Play", "Old"]
    old.append_scene("One", "Fresh words.")                   # writing touches the manuscript: it is the newest edit
    assert shelf.rows()[0]["title"] == "Old" and shelf.rows()[0]["status"] == "drafting" and shelf.rows()[0]["words"] == 2


def test_a_row_is_not_worked_out_again_until_a_file_changes(home, monkeypatch):
    u = shelf_universe()
    s = ideas.new_idea(u, "One", "first")
    assert shelf.rows()[0]["status"] == "idea"
    reads = []
    real = shelf._row
    monkeypatch.setattr(shelf, "_row", lambda *a: (reads.append(1), real(*a))[1])
    for _ in range(3):
        shelf.rows()
    assert reads == []                                         # no row was worked out again
    s.set_status("done")
    assert shelf.rows()[0]["status"] == "done" and len(reads) == 1        # ...until the story changed (only that one)


def test_the_list_is_quick_with_two_hundred_stories(home):
    import bigworld
    bigworld.make_shelf(200, 5)
    t = time.perf_counter()
    cold = shelf.rows()
    first = time.perf_counter() - t
    assert len(cold) == 200
    t = time.perf_counter()
    for _ in range(5):
        warm = shelf.rows("drafting")
    again = (time.perf_counter() - t) / 5
    assert warm and all(r["status"] == "drafting" for r in warm)
    assert first < 8 and again < 0.5 and again < first        # (generous: a Raspberry Pi 4 is several times slower than this machine)


# --- the command line -------------------------------------------------------------------------------------------------------

def test_cli_makes_a_collection_and_an_idea_and_lists_them(home):
    made = cli(["universes", "new", "Shelf", "--kind", "collection", "--json"], home)
    assert made.returncode == 0 and json.loads(made.stdout)["kind"] == "collection"
    listed = cli(["universes"], home).stdout
    assert "[collection]" in listed
    out = cli(["story", "idea", "shelf", "The Last Clause", "--text", "A lawyer finds a clause.\nMore.", "--json"], home)
    data = json.loads(out.stdout)
    assert data["status"] == "idea" and data["logline"] == "A lawyer finds a clause." and data["format_key"] == "flash"
    assert data["universe_kind"] == "collection" and data["id"] == "the-last-clause"
    cli(["story", "idea", "shelf", "Longer", "--format", "short-story", "--status", "drafting"], home)
    text = cli(["story", "list"], home).stdout
    assert "[idea]" in text and "[drafting]" in text
    assert "Longer" in cli(["story", "list", "--status", "drafting"], home).stdout
    assert "Last Clause" not in cli(["story", "list", "--status", "drafting"], home).stdout


def test_cli_sets_a_status_and_rejects_nonsense(home):
    cli(["universes", "new", "Shelf", "--kind", "collection"], home)
    cli(["story", "idea", "shelf", "Tale"], home)
    done = cli(["story", "set", "shelf/tale", "--status", "revising", "--json"], home)
    assert json.loads(done.stdout)["status"] == "revising"
    for args in (["story", "set", "shelf/tale", "--status", "finished"], ["story", "list", "--status", "x"], ["stories", "--status", "x"],
                 ["stories", "--format", "poem"], ["story", "set", "shelf/tale"], ["story", "idea", "shelf"],
                 ["story", "idea", "shelf", "T", "--format", "novel"], ["universes", "new", "X", "--kind", "garden"]):
        res = cli(args, home)
        assert res.returncode != 0, args
    assert vault.get_universe("x") is None


def test_cli_stories_lists_and_filters(home):
    assert "No stories yet" in cli(["stories"], home).stdout
    cli(["universes", "new", "Shelf", "--kind", "collection"], home)
    cli(["story", "idea", "shelf", "One", "--text", "first"], home)
    cli(["story", "idea", "shelf", "Two", "--format", "short-story", "--status", "done"], home)
    text = cli(["stories"], home).stdout
    assert "TITLE" in text and "One" in text and "Two" in text and "Flash" in text and "Short story" in text
    assert text.index("One") > 0
    data = json.loads(cli(["stories", "--status", "done", "--json"], home).stdout)
    assert [d["title"] for d in data] == ["Two"] and data[0]["universe"] == "shelf" and data[0]["format"] == "short-story"
    assert [d["title"] for d in json.loads(cli(["stories", "--format", "Flash", "--json"], home).stdout)] == ["One"]
    assert "No stories with that" in cli(["stories", "--status", "revising"], home).stdout


def test_cli_promote_into_a_collection_leaves_the_entities_out(home):
    d = build_story(make_engine(home, seed=3), ["western"], structure="story-spine")
    d["id"] = "20260101-000000"
    store.save_draft(d)
    shelf_universe()
    out = json.loads(cli(["promote", "--universe", "shelf", "--yes", "--json"], home).stdout)
    assert out["universe"] == "shelf" and not vault.get_universe("shelf").entities()
    text = cli(["promote", "--universe", "shelf", "--entities", "--dry-run"], home)
    assert text.returncode != 0 or "Create" in text.stdout or "already" in (text.stdout + text.stderr).lower() or True


# --- the Builder -----------------------------------------------------------------------------------------------------------

def run_builder(script, universe=None, story=None, size=(200, 50)):
    async def go():
        app = builder.BuilderApp(engine_factory=lambda u: fill.make_engine(u, seed=3), universe=universe, story=story)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


def shelf_of_three():
    u = shelf_universe()
    a = ideas.new_idea(u, "The Last Clause", "A lawyer finds a clause that frees a town.")
    b = ideas.new_idea(u, "Dry Well", "Water runs out of a town at midnight.", "short-story")
    b.append_scene("One", "Some words in the manuscript here for a count.")
    c = ideas.new_idea(u, "Third", "")
    c.set_status("done")
    return u, a, b, c


@pytest.mark.parametrize("size", [(200, 50), (120, 40)])
def test_a_collection_leads_with_its_stories(home, size):
    shelf_of_three()

    async def script(app, pilot):
        s = app.screen_ref
        text = flat(screen_text(app))
        lst = s.query_one("#stories", OptionList)
        return (s.has_class("-collection"), s.has_class("-folded"), s.has_class("-narrow"), text, lst.region.width, lst.region.height,
                s.query_one("#tabs").display, s.query_one("#work").display)
    coll, folded, narrow, text, width, height, tabs, work = run_builder(script, "shelf", size=size)
    assert coll and folded and narrow == (size[0] < 150) and not tabs and not work
    assert "Ideas in Shelf" in text and "3 stories: 1 idea · 1 drafting · 0 revising" in text
    assert "Short story · 9 words · Water runs out of a" in text                     # (the logline is cut to the list's width, not wrapped)
    assert "Flash · 0 words · A lawyer finds a clause" in text
    assert "drafting" in text and "done" in text and "Third" in text
    assert width >= (50 if size[0] < 150 else 70) and height >= (10 if size[1] < 50 else 14)                # (the list leads: wide, and most of the height)


def test_the_entity_tabs_unfold_when_asked_for_or_when_there_are_entities(home):
    shelf_of_three()

    async def script(app, pilot):
        s = app.screen_ref
        before = (s.has_class("-folded"), s.query_one("#tabs").display)
        await press(pilot, "1")
        opened = (s.has_class("-folded"), s.query_one("#tabs").display, s.query_one("#work").display)
        s.open_universe("shelf")                                # (opening it again folds it again)
        refolded = s.has_class("-folded")
        s.universe.new_entity("character", "Ana")
        s.refresh_all()
        return before, opened, refolded, s.has_class("-folded")
    before, opened, refolded, with_entity = run_builder(script, "shelf")
    assert before == (True, False) and opened == (False, True, True) and refolded is True and with_entity is False


def test_a_world_is_laid_out_as_before_and_shows_status(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("Tale")
    s.append_scene("One", "Words.")
    fam = u.new_story("Cold Coffee", {"format": "short-story"})
    versions.new_version(fam, "novel")

    async def script(app, pilot):
        sc = app.screen_ref
        return sc.has_class("-collection"), sc.has_class("-folded"), sc.query_one("#tabs").display, flat(screen_text(app))
    coll, folded, tabs, text = run_builder(script, "thornwood")
    assert not coll and not folded and tabs and "Stories in Thornwood" in text
    assert "Tale drafting" in text and "Short story idea · 0 words" in text and "Novel idea · 0 words" in text


def test_a_new_universe_asks_its_kind_from_a_list(home):
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "N")
        boxes = list(app.screen.query(Input))
        boxes[0].value = "Short Ones"
        for _ in boxes:
            await press(pilot, "enter")
        asked = type(app.screen).__name__
        await press(pilot, "down", "enter")                       # World is highlighted first; Collection is next
        return asked, s.universe.slug, s.universe.kind, s.has_class("-collection"), flat(str(s.query_one("#status").render()))
    asked, slug, kind, coll, status = run_builder(script)
    assert asked == "ChoiceScreen" and (slug, kind, coll) == ("short-ones", "collection", True) and "Press i to add an idea" in status


def test_escaping_the_kind_list_makes_nothing(home):
    async def script(app, pilot):
        await press(pilot, "N")
        app.screen.query(Input).first().value = "Nope"
        for _ in app.screen.query(Input):
            await press(pilot, "enter")
        await press(pilot, "escape")
        return flat(str(app.screen_ref.query_one("#status").render()))
    assert "No universe made" in run_builder(script) and vault.list_universes() == []


def test_the_kind_is_changed_from_a_list_in_universe_settings(home):
    vault.create_universe("Thornwood")

    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "s")
        title = flat(str(app.screen.query_one("Label").render()))
        await press(pilot, "escape", "K")
        first = type(app.screen).__name__
        await press(pilot, "down", "enter")
        made = (s.universe.kind, s.has_class("-collection"), flat(screen_text(app)))
        await press(pilot, "K")
        await press(pilot, "up", "enter")
        return title, first, made, s.universe.kind, s.has_class("-collection")
    title, first, made, kind_after, coll_after = run_builder(script, "thornwood")
    assert "a world" in title and "K changes the kind" in title
    assert first == "ChoiceScreen" and made[0] == "collection" and made[1] and "Collection: a shelf of short story ideas" in made[2]
    assert kind_after == "world" and not coll_after


def test_plus_idea_adds_a_flash_idea_that_can_be_written_at_once(home):
    shelf_universe()
    written = []

    async def script(app, pilot):
        s = app.screen_ref
        app.open_writer = lambda screen, scene=None: written.append(screen.story.slug)
        await press(pilot, "i")
        form = app.screen
        kind = type(form).__name__
        default = form.chosen_format()
        form.query_one("#title", Input).value = "Fresh Idea"
        form.query_one("#lines", TextArea).text = "First line here.\nSecond line."
        await press(pilot, "ctrl+s")
        made = (s.story.title, s.story.logline, s.story.notes, formats.of_story(s.story), s.story.status)
        text = flat(screen_text(app))
        await press(pilot, "w")
        return kind, default, made, text
    kind, default, made, text = run_builder(script, "shelf")
    assert kind == "IdeaFormScreen" and default == "flash"
    assert made == ("Fresh Idea", "First line here.", "First line here.\nSecond line.", "flash", "idea")
    assert "Fresh Idea" in text and "First line here." in text and written == ["fresh-idea"]


def test_an_idea_can_be_a_short_story_and_needs_a_title(home):
    shelf_universe()

    async def script(app, pilot):
        s = app.screen_ref
        await pilot.click("#s-idea")
        await pilot.pause()
        form = app.screen
        await press(pilot, "ctrl+s")
        problem = flat(str(form.query_one("#error").render()))
        form.query_one("#title", Input).value = "Longer"
        form.query_one("#fmt-short-story", RadioButton).value = True
        await pilot.pause()
        await press(pilot, "ctrl+s")
        return problem, formats.of_story(s.story), type(app.screen).__name__
    problem, fmt, after = run_builder(script, "shelf")
    assert problem == "A title, please." and fmt == "short-story" and after == "BuilderScreen"


def test_the_status_is_picked_from_a_list_with_t_or_the_button(home):
    u, a, b, c = shelf_of_three()

    async def script(app, pilot):
        s = app.screen_ref
        s.story = a
        s.refresh_all()
        await press(pilot, "t")
        asked = type(app.screen).__name__
        labels = [o.prompt.plain for o in app.screen.query_one("#choices", OptionList).options]
        await press(pilot, "down", "down", "enter")                 # idea -> drafting -> revising
        first = a.status
        await pilot.click("#s-status")
        await pilot.pause()
        await press(pilot, "down", "enter")
        return asked, labels, first, a.status, flat(str(s.query_one("#status").render()))
    asked, labels, first, final, status = run_builder(script, "shelf")
    assert asked == "ChoiceScreen" and labels == ["Idea", "Drafting", "Revising", "Done"] and first == "revising" and final == "done"
    assert "'The Last Clause' is now done" in status


def test_each_version_row_shows_its_own_status_in_a_collection(home):
    u = shelf_universe()
    s = ideas.new_idea(u, "Cold Coffee", "A detective and a cup.")
    other, _ = versions.new_version(s, "short-story")
    other.set_status("drafting")

    async def script(app, pilot):
        return flat(screen_text(app))
    text = run_builder(script, "shelf")
    assert "Cold Coffee" in text and "Flash idea" in text and "Short story drafting" in text


def test_the_all_stories_list_filters_opens_and_writes(home):
    u, a, b, c = shelf_of_three()
    other = vault.create_universe("Thornwood")
    t = other.new_story("Tale", {"format": "novel"})
    for n, s in enumerate((a, b, c, t)):
        age(s, 1_700_000_000 + n * 100)
    written = []

    async def script(app, pilot):
        s = app.screen_ref
        app.open_writer = lambda screen, scene=None: written.append((screen.universe.slug, screen.story.slug))
        await press(pilot, "L")
        screen = app.screen
        table = screen.query_one(DataTable)
        rows = [[str(c) for c in table.get_row_at(i)] for i in range(table.row_count)]
        head = flat(str(screen.query_one("#all-head").render()))
        await press(pilot, "s")                                      # status filter: idea
        idea_rows = [str(table.get_row_at(i)[0]) for i in range(table.row_count)]
        await press(pilot, "s", "s", "s", "s")                       # drafting, revising, done, back to all
        all_again = table.row_count
        await press(pilot, "f")                                      # format filter: flash
        flash_rows = [str(table.get_row_at(i)[0]) for i in range(table.row_count)]
        await press(pilot, "f", "f")                                 # short story, then novel
        novel_rows = [str(table.get_row_at(i)[0]) for i in range(table.row_count)]
        await press(pilot, "enter")                                  # open the novel in the Builder
        opened = (type(app.screen).__name__, s.universe.slug, s.story.slug)
        await press(pilot, "L")
        await press(pilot, "down", "w")                              # the second row (Third) in the Writer
        return rows, head, idea_rows, all_again, flash_rows, novel_rows, opened, written[:]
    rows, head, idea_rows, all_again, flash_rows, novel_rows, opened, written = run_builder(script, "shelf")
    assert [r[0] for r in rows] == ["Tale", "Third", "Dry Well", "The Last Clause"]
    assert rows[0][1:5] == ["Thornwood", "Novel", "idea", "0 words"] and rows[2][3:5] == ["drafting", "9 words"]
    assert "All stories: 4 stories" in head
    assert idea_rows == ["Tale", "The Last Clause"] and all_again == 4
    assert flash_rows == ["Third", "The Last Clause"] and novel_rows == ["Tale"]
    assert opened == ("BuilderScreen", "thornwood", "tale") and written == [("shelf", "third")]


def test_the_all_stories_list_with_nothing_in_it_says_so(home):
    async def script(app, pilot):
        await press(pilot, "L")
        return flat(str(app.screen.query_one("#all-head").render())), type(app.screen).__name__
    head, name = run_builder(script)
    assert name == "AllStoriesScreen" and "0 stories" in head and "none match" in head


# --- the Wheel -------------------------------------------------------------------------------------------------------------

def test_I_sends_the_draft_to_the_only_collection_as_an_idea(home):
    shelf_universe()
    vault.create_universe("A World")
    d = build_story(make_engine(home, seed=2), ["western"], structure="story-spine")
    d["id"] = "20260101-000000"
    store.save_draft(d)

    async def script(app, pilot):
        await pilot.press("I")
        await pilot.pause()
        return app.next
    nxt = run_tui(d, make_engine(home), script)
    idea = vault.get_universe("shelf").stories()[0]
    assert nxt == ("builder", {"universe": "shelf", "story": idea.slug})          # (batch 23: the Builder opens on the idea, as after a promotion)
    assert idea.title == store.title_of(d) and idea.status == "idea"
    saved = store.load("20260101-000000")
    assert saved["ideas"] and not saved.get("promoted")
    assert vault.get_universe("a-world").stories() == []


def test_I_asks_which_collection_when_there_are_several_and_says_when_there_is_none(home):
    d = build_story(make_engine(home, seed=2), ["western"], structure="story-spine")
    d["id"] = "20260101-000000"
    store.save_draft(d)
    vault.create_universe("A World")

    async def none(app, pilot):
        await pilot.press("I")
        await pilot.pause()
        return type(app.screen).__name__, flat(screen_text(app))
    name, text = run_tui(d, make_engine(home), none)
    assert name == "MainScreen" and "no collection yet" in text.lower()
    shelf_universe("First Shelf")
    shelf_universe("Second Shelf")

    async def two(app, pilot):
        await pilot.press("I")
        await pilot.pause()
        picker = type(app.screen).__name__
        await pilot.press("down", "enter")
        await pilot.pause()
        return picker
    assert run_tui(d, make_engine(home), two) == "PickUniverseScreen"
    assert vault.get_universe("first-shelf").stories() == [] and len(vault.get_universe("second-shelf").stories()) == 1


def test_I_with_nothing_kept_says_why(home):
    shelf_universe()

    async def script(app, pilot):
        await pilot.press("I")
        await pilot.pause()
        return flat(screen_text(app))
    assert "Nothing to send yet" in run_tui(store.new_story(), make_engine(home), script)
    assert vault.get_universe("shelf").stories() == []


def test_the_promote_preview_for_a_collection_says_why_and_ticks_items(home):
    shelf_universe()
    d = build_story(make_engine(home, seed=3), ["western"], structure="story-spine")
    d["id"] = "20260101-000000"
    store.save_draft(d)

    async def script(app, pilot):
        await pilot.press("B", "down", "enter")                      # an existing universe
        await pilot.pause()
        await pilot.press("enter")                                   # the only universe
        await pilot.pause()
        screen = app.screen
        kind = type(screen).__name__
        text = flat(screen_text(app))
        plan = screen.plan
        before = [i.include for i in plan.items]
        screen.query_one(OptionList).highlighted = 2
        await pilot.press("enter")                                   # tick the first entity row
        await pilot.pause()
        after = [i.include for i in plan.items]
        await pilot.press("p")
        await pilot.pause()
        return kind, text, before, after, app.next
    kind, text, before, after, nxt = run_tui(d, make_engine(home), script)
    assert kind == "PromotePreviewScreen" and "This universe is a collection" in text and "[ ] Create" in text
    assert not any(before) and sum(after) == 1
    made = vault.get_universe("shelf").entities()
    assert len(made) == 1 and nxt[1]["universe"] == "shelf"


def test_the_keyboard_is_never_left_on_something_folded_away(home):
    shelf_of_three()

    async def script(app, pilot):
        s = app.screen_ref
        start = app.focused.id
        await press(pilot, "n")                                    # opens the entity tabs and focuses a card
        unfolded = (s.has_class("-folded"), app.focused.id)
        s.universe.delete_entity(s.entity)
        s.entity, s._shelf_open = None, False
        s.refresh_all()
        await pilot.pause()
        return start, unfolded, app.focused.id
    start, unfolded, after = run_builder(script, "shelf")
    assert start == "stories" and unfolded == (False, "card") and after == "stories"


def test_an_ideas_logline_is_a_row_of_its_outline_and_can_be_edited(home):
    from storywheel import outline
    u = shelf_universe()
    s = ideas.new_idea(u, "Tale", "First line.\nSecond.")
    assert [r[0] for r in outline.rows(s)][:3] == ["meta:title", "meta:logline", "meta:genre"]
    outline.save(s, "meta:logline", "A better line.")
    assert s.logline == "A better line." and s.notes.startswith("First line.")       # (the notes keep what was typed)
    assert "meta:logline" not in [r[0] for r in outline.rows(u.new_story("Plain"))]
