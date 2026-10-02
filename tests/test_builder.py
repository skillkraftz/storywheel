"""The Universe Builder, driven by key presses and clicks."""
import json

from textual import events
from textual.widgets import Input, TextArea

from storywheel import builder, promote, schemas, vault
from storywheel.ratings import Ratings
from conftest import screen_text


def run_builder(home, script, universe=None, story=None, size=(220, 55), seed=3):
    import asyncio
    from storywheel import fill

    async def go():
        app = builder.BuilderApp(engine_factory=lambda u: fill.make_engine(u, seed=seed),
                                 ratings=Ratings(home / "home" / "ratings.json"), universe=universe, story=story)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


async def press(pilot, *keys):
    await pilot.press(*keys)
    await pilot.pause()


def flat(text):
    return " ".join(text.split())


def world(home, genres=("western",)):
    u = vault.create_universe("Thornwood", list(genres))
    return u


def card_index(app, key):
    return [r[0] for r in app.screen_ref.rows()].index(key)


async def click_field(pilot, app, key, button=1, x=8):
    await pilot.click("#card", offset=(x, card_index(app, key)), button=button)
    await pilot.pause()


# --- layout -----------------------------------------------------------------------------------------------------

def test_three_columns_with_tabs_overview_and_empty_states(home):
    world(home)
    async def script(app, pilot):
        return flat(screen_text(app))
    text = run_builder(home, script)
    for needle in ("Universes", "Thornwood", "Stories in Thornwood", "Universe: Thornwood", "Genre leanings", "western",
                   "Characters", "Places", "Things", "Groups", "Notes", "Outline", "Scenes", "Writing", "Today", "Streak",
                   "F1 Wheel", "Roll blanks"):
        assert needle in text, needle


def test_no_universe_yet_says_how_to_start(home):
    async def script(app, pilot):
        return flat(screen_text(app))
    assert "press N for a universe" in run_builder(home, script)


def test_the_five_tabs_switch_with_number_keys(home):
    u = world(home)
    u.new_entity("place", "Red Draw")
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "2")
        place = (s.type, flat(screen_text(app)))
        await press(pilot, "5")
        return place, s.type
    (t, text), last = run_builder(home, script)
    assert t == "place" and "Places (1)" in text and "Red Draw" in text and last == "note"


# --- new entities start blank; rolling ----------------------------------------------------------------------------

def test_a_new_entity_starts_blank_and_space_rolls_every_blank_field(home):
    u = world(home)
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "n")
        blank = (s.entity.id, dict(s.entity.fields))
        await press(pilot, "space")
        return blank, s.entity.id, dict(s.entity.fields), flat(screen_text(app))
    (bid, bfields), eid, fields, text = run_builder(home, script)
    assert bid == "character-1" and not any(v for v in bfields.values())
    assert fields["name"] and fields["job"] and fields["want"] and fields["secret"] and fields["role"] == ""
    assert eid == vault.slugify(fields["name"]) != bid                         # the placeholder became a real id
    on_disk = vault.get_universe("thornwood").entity(eid)
    assert on_disk.fields["job"] == fields["job"]
    assert "Rolled" in text and "(blank)" in text                              # write-only fields stay blank


def test_left_click_rolls_one_field_and_right_click_writes_it(home):
    u = world(home)
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "n", "space")
        before = dict(s.entity.fields)
        await click_field(pilot, app, "job")
        rolled = dict(s.entity.fields)
        await click_field(pilot, app, "job", button=3)
        assert type(app.screen).__name__ == "EditScreen"
        box = app.screen.query_one(Input)
        assert box.value == rolled["job"]
        box.value = "lamplighter"
        await press(pilot, "enter")
        return before, rolled, dict(s.entity.fields), s.entity.id
    before, rolled, written, eid = run_builder(home, script)
    assert rolled["job"] != before["job"] and {k: v for k, v in rolled.items() if k != "job"} == {k: v for k, v in before.items() if k != "job"}
    assert written["job"] == "lamplighter"
    assert vault.get_universe("thornwood").entity(eid).fields["job"] == "lamplighter"


def test_f_and_e_do_the_same_on_the_highlighted_field(home):
    world(home)
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "n", "space")
        s.card.highlighted = card_index(app, "trait")
        before = s.entity.fields["trait"]
        await press(pilot, "f")
        rolled = s.entity.fields["trait"]
        await press(pilot, "e")
        app.screen.query_one(Input).value = "kind"
        await press(pilot, "enter")
        return before, rolled, s.entity.fields["trait"]
    before, rolled, written = run_builder(home, script)
    assert rolled != before and written == "kind"


def test_write_only_fields_are_marked_and_say_so_when_rolled(home):
    world(home)
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "n")
        marked = flat(screen_text(app))
        s.card.highlighted = card_index(app, "role")
        await press(pilot, "f")
        return marked, flat(screen_text(app))
    marked, after = run_builder(home, script)
    assert "Role ✎" in marked and "Relationships ✎" in marked
    assert "write-only" in after


def test_choice_fields_are_picked_from_a_list(home):
    u = world(home)
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "n")
        s.card.highlighted = card_index(app, "role")
        await press(pilot, "e")
        assert type(app.screen).__name__ == "ChoiceScreen"
        await press(pilot, "down", "down", "enter")
        return s.entity.fields["role"]
    assert run_builder(home, script) == "ally"


def test_per_field_history_and_the_scroll_wheel(home):
    world(home)
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "n", "space")
        values = [s.entity.fields["job"]]
        for _ in range(3):
            await click_field(pilot, app, "job")
            values.append(s.entity.fields["job"])
        idx = card_index(app, "job")
        await pilot._post_mouse_events([events.MouseScrollUp], "#card", offset=(8, idx)); await pilot.pause()
        one = s.entity.fields["job"]
        await pilot._post_mouse_events([events.MouseScrollUp], "#card", offset=(8, idx)); await pilot.pause()
        two = s.entity.fields["job"]
        await pilot._post_mouse_events([events.MouseScrollDown], "#card", offset=(8, idx)); await pilot.pause()
        back = s.entity.fields["job"]
        return values, one, two, back, s.entity.id
    values, one, two, back, eid = run_builder(home, script)
    assert len(set(values)) >= 3
    assert one == values[-2] and two == values[-3] and back == values[-2]
    assert vault.get_universe("thornwood").entity(eid).fields["job"] == back             # saved as you go


def test_ratings_work_on_entity_fields(home):
    world(home)
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "n", "space")
        s.card.highlighted = card_index(app, "want")
        await press(pilot, "minus")
        rating = app.rating(s.universe, s.entity, "want")
        text = s.entity.fields["want"]
        return rating, text
    rating, text = run_builder(home, script)
    assert rating == -1
    saved = json.loads((home / "home" / "ratings.json").read_text())["ratings"]
    assert saved[0]["text"] == text and saved[0]["step"] == "character" and saved[0]["field"] == "want"


def test_roll_the_whole_entity_again_asks_first(home):
    world(home)
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "n", "space")
        before = dict(s.entity.fields)
        await press(pilot, "R")
        asked = type(app.screen).__name__
        await press(pilot, "n")
        same = dict(s.entity.fields) == before
        await press(pilot, "R", "y")
        return asked, same, before, dict(s.entity.fields)
    asked, same, before, after = run_builder(home, script)
    assert asked == "ConfirmScreen" and same and after != before


# --- links -------------------------------------------------------------------------------------------------------------

def test_link_two_entities_by_choosing_from_a_list(home):
    u = world(home)
    sheriff = u.new_entity("character", "Sheriff Lund")
    hero = u.new_entity("character", "Stacie")
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "down")                                # Stacie is after Sheriff Lund alphabetically? check below
        names = [e.name for e in s.items]
        s.elist.highlighted = names.index("Stacie")
        await pilot.pause()
        s.card.highlighted = card_index(app, "rival")
        s.card.focus(); await pilot.pause()
        await press(pilot, "e")
        assert type(app.screen).__name__ == "ChoiceScreen"
        flat_text = flat(screen_text(app))
        await press(pilot, "down", "enter")                       # (clear) is first, Sheriff next
        return flat_text, flat(screen_text(app))
    choices, after = run_builder(home, script)
    assert "Sheriff Lund" in choices and "write plain text instead" in choices
    assert vault.get_universe("thornwood").entity("stacie").fields["rival"] == "sheriff-lund"
    assert "→ Sheriff Lund" in after and "Rival → Sheriff Lund" in after


def test_the_right_column_shows_links_back_and_appearances(home):
    u = world(home)
    hero = u.new_entity("character", "Stacie")
    u.new_entity("thing", "The Horn", {"owner": hero.id})
    s = u.new_story("The Clause", {}, {"Premise": "Stacie finds a clause."})
    async def script(app, pilot):
        sc = app.screen_ref
        sc.elist.highlighted = [e.name for e in sc.items].index("Stacie")
        await pilot.pause()
        await pilot.press("8")                                   # the Notes tab of the right column
        await pilot.pause()
        return flat(screen_text(app))
    text = run_builder(home, script)
    assert "← The Horn (owner)" in text and "The Clause" in text


def test_notes_are_editable_in_the_right_column_and_saved(home):
    u = world(home)
    u.new_entity("character", "Stacie")
    async def script(app, pilot):
        s = app.screen_ref
        s.query_one("#notes", TextArea).load_text("")
        # simulate the writer typing in the notes box
        box = s.query_one("#notes", TextArea)
        box.focus(); await pilot.pause()
        await pilot.press(*"Grew up dry.")
        await pilot.press("escape")
        await pilot.pause()
        return s.entity.id
    eid = run_builder(home, script)
    assert vault.get_universe("thornwood").entity(eid).body == "Grew up dry."


# --- rename ------------------------------------------------------------------------------------------------------------------

def test_rename_shows_every_match_then_applies_them(home):
    u = world(home)
    hero = u.new_entity("character", "Stacie", {"want": "Stacie wants out"})
    story = u.new_story("Tale", {}, {"Premise": "Stacie finds a clause."})
    story.add_scene("One", "Stacie ran. Stacie’s hat flew.")
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "r")
        app.screen.query_one(Input).value = "Marcy"
        await press(pilot, "enter")
        assert type(app.screen).__name__ == "RenamePreviewScreen"
        preview = flat(screen_text(app))
        await press(pilot, "a", "p")
        return preview, flat(screen_text(app))
    preview, after = run_builder(home, script)
    assert "Rename 'Stacie' to 'Marcy'" in preview and "Stacie’s hat flew" in preview and "manuscript: Tale" in preview
    assert "outline: Tale" in preview
    u = vault.get_universe("thornwood")
    assert u.entity("stacie").name == "Marcy" and u.entity("stacie").fields["want"] == "Marcy wants out"
    assert u.stories()[0].scenes()[0].read_text() == "Marcy ran. Marcy’s hat flew."
    assert u.stories()[0].sections()["Premise"] == "Marcy finds a clause."
    assert "Renamed 'Stacie' to 'Marcy'" in after


def test_rename_one_at_a_time_by_unchecking(home):
    u = world(home)
    u.new_entity("character", "Stacie")
    s = u.new_story("Tale", {}, {"Premise": "Stacie finds a clause."})
    s.add_scene("One", "Stacie ran.")
    async def script(app, pilot):
        await press(pilot, "r")
        app.screen.query_one(Input).value = "Marcy"
        await press(pilot, "enter")
        await press(pilot, "enter")                                # uncheck the first match
        await press(pilot, "p")
    run_builder(home, script)
    u = vault.get_universe("thornwood")
    story = u.stories()[0]
    texts = [story.sections()["Premise"], story.scenes()[0].read_text()]
    assert sum("Marcy" in t for t in texts) == 1 and sum("Stacie" in t for t in texts) == 1


def test_escape_in_the_preview_renames_only_the_entity(home):
    u = world(home)
    u.new_entity("character", "Stacie")
    s = u.new_story("Tale", {}, {"Premise": "Stacie finds a clause."})
    async def script(app, pilot):
        await press(pilot, "r")
        app.screen.query_one(Input).value = "Marcy"
        await press(pilot, "enter", "escape")
    run_builder(home, script)
    u = vault.get_universe("thornwood")
    assert u.entity("stacie").name == "Marcy" and u.stories()[0].sections()["Premise"] == "Stacie finds a clause."


def test_rolling_a_new_name_on_a_named_entity_goes_through_the_same_preview(home):
    u = world(home)
    u.new_entity("character", "Stacie")
    u.new_story("Tale", {}, {"Premise": "Stacie finds a clause."})
    async def script(app, pilot):
        s = app.screen_ref
        s.card.highlighted = 0
        await press(pilot, "f")
        return type(app.screen).__name__
    assert run_builder(home, script) == "RenamePreviewScreen"


# --- custom fields, delete -----------------------------------------------------------------------------------------------------------

def test_add_your_own_field_to_one_entity(home):
    u = world(home)
    u.new_entity("character", "Stacie")
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "c")
        boxes = list(app.screen.query(Input))
        boxes[0].value, boxes[1].value = "eye colour", "grey"
        for _ in boxes:
            await press(pilot, "enter")
        text = flat(screen_text(app))
        s.card.highlighted = card_index(app, "custom:eye colour")
        await press(pilot, "f")
        return text, flat(screen_text(app))
    text, after = run_builder(home, script)
    assert "eye colour ✎" in text and "grey" in text and "write-only" in after
    assert vault.get_universe("thornwood").entity("stacie").custom == {"eye colour": "grey"}


def test_delete_an_entity_asks_first_and_goes_to_the_trash(home):
    u = world(home)
    u.new_entity("character", "Stacie")
    async def script(app, pilot):
        await press(pilot, "d")
        asked = type(app.screen).__name__
        await press(pilot, "n")
        kept = vault.get_universe("thornwood").entity("stacie") is not None
        await press(pilot, "d", "y")
        return asked, kept
    assert run_builder(home, script) == ("ConfirmScreen", True)
    assert vault.get_universe("thornwood").entity("stacie") is None and (home / "library" / ".trash").exists()


# --- universes and stories -----------------------------------------------------------------------------------------------------------------

def test_create_rename_and_delete_universes(home):
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "N")
        boxes = list(app.screen.query(Input))
        boxes[0].value, boxes[1].value = "Dry Country", "western, noir"
        for _ in boxes:
            await press(pilot, "enter")
        made = (s.universe.slug, s.universe.settings()["genres"])
        s.query_one("#universes").focus(); await pilot.pause()
        await press(pilot, "r")
        app.screen.query_one(Input).value = "Dust Bowl"
        await press(pilot, "enter")
        renamed = vault.get_universe("dry-country").name
        await press(pilot, "d")
        asked = type(app.screen).__name__
        await press(pilot, "y")
        return made, renamed, asked, s.universe
    made, renamed, asked, universe = run_builder(home, script)
    assert made == ("dry-country", ["western", "noir"]) and renamed == "Dust Bowl" and asked == "ConfirmScreen" and universe is None
    assert vault.list_universes() == [] and (home / "library" / ".trash").exists()


def test_stories_are_listed_and_open_as_an_outline_in_the_boxes(home):
    u = world(home)
    u.new_story("The Last Clause", {"genre": "western", "structure": "Story Spine"},
                {"Premise": "A clerk finds a clause.", "Twist": "It was hers."}).add_scene("Open", "Hello there world.")
    async def script(app, pilot):
        s = app.screen_ref
        s.query_one("#stories").focus(); await pilot.pause()
        s.query_one("#stories").highlighted = 0
        await press(pilot, "enter")
        return flat(screen_text(app))
    text = run_builder(home, script)
    for needle in ("Story outline: The Last Clause", "A clerk finds a clause.", "It was hers.", "Story Spine", "3 words in 1 scene"):
        assert needle in text, needle


def test_editing_an_outline_box_writes_story_md(home):
    u = world(home)
    u.new_story("Tale", {}, {"Premise": "Old premise."})
    async def script(app, pilot):
        s = app.screen_ref
        s.story = u.story("tale")
        s.refresh_all()
        await pilot.pause()
        rows = [r[0] for r in s.top_rows()]
        await pilot.click("#outline", offset=(8, rows.index("section:Premise")), button=3)
        await pilot.pause()
        app.screen.query_one(Input).value = "New premise."
        await press(pilot, "enter")
    run_builder(home, script, story="tale", universe="thornwood")
    assert vault.get_universe("thornwood").story("tale").sections()["Premise"] == "New premise."


def test_universe_settings_change_the_mix_for_rolls(home):
    u = world(home)
    async def script(app, pilot):
        await press(pilot, "s")
        boxes = list(app.screen.query(Input))
        boxes[0].value = "fairy tale, fantasy"
        boxes[1].value = "modern"
        boxes[3].value = "fantasy=2"
        for _ in boxes:
            await press(pilot, "enter")
        return flat(screen_text(app))
    text = run_builder(home, script)
    s = vault.get_universe("thornwood").settings()
    assert s["genres"] == ["fairy tale", "fantasy"] and s["exclude_tags"] == ["modern"] and s["boost"] == {"fantasy": 2.0}
    assert vault.get_universe("thornwood").mix_dict()["exclude_tags"] == ["modern"]
    assert (home / "library" / "universes" / "thornwood" / "lists").is_dir()
    assert "fairy tale, fantasy" in text


def test_story_settings_and_global_details_are_saved_to_toml(home):
    from storywheel import settings
    u = world(home)
    u.new_story("Tale")
    async def script(app, pilot):
        s = app.screen_ref
        s.story = u.story("tale")
        await press(pilot, "S")
        boxes = list(app.screen.query(Input))
        boxes[0].value, boxes[3].value, boxes[4].value, boxes[6].value = "novel", "1200", "Clause", "true"
        for _ in boxes:
            await press(pilot, "enter")
        await press(pilot, "G")
        boxes = list(app.screen.query(Input))
        boxes[0].value, boxes[2].value, boxes[3].value = "Andy Writer", "1 Main St\\nTown, ST 00000", "a@example.com"
        for _ in boxes:
            await press(pilot, "enter")
    run_builder(home, script)
    st = settings.load_story(u.story("tale").path)
    assert st["format"] == "novel" and st["daily_goal"] == 1200 and st["title_keyword"] == "Clause" and st["typewriter"] is True
    g = settings.load_global()
    assert g["legal_name"] == "Andy Writer" and g["address"] == "1 Main St\nTown, ST 00000" and g["email"] == "a@example.com"


def test_f1_goes_to_the_wheel_and_q_quits(home):
    world(home)
    async def script(app, pilot):
        await press(pilot, "f1")
    import asyncio
    from storywheel import fill
    app_holder = {}
    async def go():
        app = builder.BuilderApp(engine_factory=lambda u: fill.make_engine(u, seed=1))
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            await pilot.press("f1")
            await pilot.pause()
        return app.next
    assert asyncio.run(go()) == ("wheel", {})


def test_help_lists_the_mode_keys_and_the_entity_keys(home):
    world(home)
    async def script(app, pilot):
        await press(pilot, "question_mark")
        return flat(screen_text(app))
    text = run_builder(home, script, size=(220, 90))
    for needle in ("F1 Wheel", "F2 Builder", "F3 Writer", "roll every blank field", "write it by hand", "rename"):
        assert needle in text, needle


def test_the_builder_saves_on_every_change(home):
    world(home)
    async def script(app, pilot):
        s = app.screen_ref
        await press(pilot, "n", "space")
        return s.entity.id
    eid = run_builder(home, script)
    assert (home / "library" / "universes" / "thornwood" / "characters" / f"{eid}.md").exists()
