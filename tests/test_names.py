"""Proper names are Title Case; descriptions keep their article and lowercase ("a locked box", "the sheriff")."""
import asyncio

from storywheel import builder, fill, names, promote, vault
from storywheel.cli import main as cli_main


def test_tidy_keeps_descriptions_as_descriptions():
    assert promote.tidy("a locked box") == "a locked box"
    assert promote.tidy("the sheriff") == "the sheriff"
    assert promote.tidy("The Silver Birch Grove") == "The Silver Birch Grove"          # (already a proper name: untouched)
    assert promote.tidy("sheriff") == "sheriff"
    assert promote.tidy("the silver birch grove", proper=True) == "Silver Birch Grove"
    assert promote.titled("the company of the wolf") == "Company of the Wolf"


def test_is_proper():
    assert promote.is_proper("Stacie Anderson") and promote.is_proper("Red Draw")
    assert not promote.is_proper("a locked box") and promote.is_proper("the Hunting Horn") and not promote.is_proper("sheriff")


def test_the_proper_flag_round_trips_through_the_file(home):
    u = vault.create_universe("U")
    a = u.new_entity("character", "Ada Voss")
    a.proper = True
    u.save_entity(a)
    b = u.new_entity("thing", "a locked box")
    b.proper = False
    u.save_entity(b)
    c = u.new_entity("thing", "plain")
    assert "proper: " not in c.path.read_text()
    assert u.entity(a.id).proper is True and u.entity(b.id).proper is False and u.entity(c.id).proper is None
    assert 'proper: "no"' in b.path.read_text() or "proper: no" in b.path.read_text()


def test_promotion_records_names_the_way_they_read(home):
    from test_promote import draft
    from conftest import make_engine
    d = draft(home)
    u = vault.create_universe("U")
    plan = promote.build_plan(d, u, make_engine(home))
    story, _ = promote.apply_plan(plan, u, d)
    ents = {e.id: e for e in u.entities()}
    rival = next(e for e in ents.values() if e.fields.get("role") == "rival")
    assert not rival.name[:1].isupper() and rival.proper is False
    pro = next(e for e in ents.values() if e.fields.get("role") == "protagonist")
    assert pro.name[:1].isupper() and pro.proper is True


def test_a_rolled_thing_keeps_its_wording_and_a_hand_written_name_follows_the_typing(home):
    u = vault.create_universe("U", ["western"])
    t = u.new_entity("thing")
    f = fill.Filler(u, fill.make_engine(u, seed=2))
    value = f.roll(t, "name")
    assert value == value.strip() and f.last_proper == promote.is_proper(value)
    g = u.new_entity("group")
    assert fill.Filler(u, fill.make_engine(u, seed=2)).roll(g, "name").startswith("The ")
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1), universe="u")
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            s = app.screen_ref
            s.entity = s.universe.entity(t.id)
            s._set("name", "a lantern", "Written.")
            low = s.universe.entities("thing")[0]
            first = low.proper
            s.entity = low
            s._set("name", "The Brass Lantern", "Written.")
            return first, [e.proper for e in s.universe.entities("thing")]
    low, after = asyncio.run(go())
    assert low is False and after == [True]


def test_old_wrongly_capitalised_names_are_found_and_fixed_with_a_preview(home, capsys):
    u = vault.create_universe("U", ["western"])
    from storywheel.fill import make_engine
    lib = make_engine(u).library
    thing = next(e.text for wl in lib.by_slot["thing"] if not wl.is_template and not wl.generator for e in wl.entries
                 if not promote.is_proper(e.text) and len(e.text.split()) >= 2)
    old = promote.ARTICLE.sub("", thing).capitalize()
    t = u.new_entity("thing", old)
    ada = u.new_entity("character", "Ada Voss")
    ada.fields["role"] = "protagonist"
    u.save_entity(ada)
    fixes = names.scan(u)
    assert [(f.old, f.new) for f in fixes] == [(old, thing)]
    cli_main(["names", "fix", u.slug])
    out = capsys.readouterr().out
    assert old in out and "Nothing was changed" in out and u.entity(t.id).name == old
    cli_main(["names", "fix", u.slug, "--apply"])
    e = u.entity(t.id)
    assert e.name == thing and e.proper is False and e.id == t.id
    assert names.scan(u) == []
    cli_main(["names", "fix", u.slug])
    assert "already reads right" in capsys.readouterr().out


def test_a_universe_person_called_the_same_as_a_description_is_not_touched(home):
    u = vault.create_universe("U", ["western"])
    c = u.new_entity("character", "Ada Voss")
    c.fields["role"] = "ally"
    u.save_entity(c)
    assert names.scan(u) == []


def test_descriptive_entities_are_not_proper_names_for_the_engine(home):
    u = vault.create_universe("U", ["western"])
    s = u.new_entity("character", "Sheriff Lund")
    s.proper = True
    u.save_entity(s)
    r = u.new_entity("character", "the marshal")
    r.proper = False
    u.save_entity(r)
    from storywheel.engine import Engine
    e = Engine(seed=1)
    e.set_universes([u])
    assert e.proper("the Sheriff Lund rode") == "Sheriff Lund rode"
    assert e.proper("the marshal rode") == "the marshal rode"


def test_ids_drop_a_leading_article_except_for_notes(home):
    u = vault.create_universe("U")
    assert u.new_entity("thing", "a locked box").id == "locked-box"
    assert u.new_entity("character", "the sheriff").id == "sheriff"
    assert u.new_entity("note", "The Dry Years").id == "the-dry-years"
    assert u.new_entity("place", "Red Draw").id == "red-draw"
    assert vault.entity_slug("a") == "a"
