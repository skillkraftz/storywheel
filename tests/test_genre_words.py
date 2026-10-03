"""Words mode, batch 8: Genre words (browse the generator's lists) and Story words (what a manuscript really uses)."""
import pytest

from dictfixture import build_fixture
from storywheel import dictionary, genrewords, rename, storywords, vault
from storywheel.library import Library


@pytest.fixture(scope="module")
def lib():
    return Library.load()


@pytest.fixture
def index(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    dictionary.forget()
    yield out
    dictionary.forget()


# --- Genre words --------------------------------------------------------------------------------------------------------------------

def test_categories_have_labels_and_every_genre_is_offered(lib):
    labels = dict(genrewords.labels())
    assert labels["First names"] == "first_name" and "Jobs" in labels and "Troubles" in labels and "Title words" in labels
    assert "general" in genrewords.genres(lib) and "fantasy" in genrewords.genres(lib)


def test_rows_come_from_the_chosen_genres_only_and_carry_their_tags(lib):
    fantasy = genrewords.rows(lib, ["fantasy"], "job")
    western = genrewords.rows(lib, ["western"], "job")
    assert fantasy and western
    assert "sellsword" in {r.text for r in fantasy} and "sellsword" not in {r.text for r in western}
    assert all("fantasy" in r.tags for r in fantasy)
    both = genrewords.rows(lib, ["fantasy", "western"], "job")
    assert {r.text for r in both} == {r.text for r in fantasy} | {r.text for r in western}


def test_patterns_are_left_out_of_atom_lists_but_frames_are_shown_whole(lib):
    assert not [r for r in genrewords.rows(lib, ["fantasy"], "place") if "{" in r.text]
    flaws = genrewords.rows(lib, ["fantasy"], "flaw")
    assert any(r.frame and "{" in r.text for r in flaws) and any(not r.frame for r in flaws)


def test_search_narrows_the_rows(lib):
    rows = genrewords.rows(lib, ["fantasy"], "first_name", "ald")
    assert rows and all("ald" in r.text.lower() for r in rows)


def test_more_names_invents_new_names_in_the_genres_style(lib):
    have = {r.text.lower() for r in genrewords.rows(lib, ["fantasy"], "first_name")}
    new = genrewords.more_names(lib, ["fantasy"], "first_name", 10, seed=3)
    assert len(new) >= 6 and not ({n.lower() for n in new} & have)
    assert new == genrewords.more_names(lib, ["fantasy"], "first_name", 10, seed=3)          # a seed gives the same names
    assert genrewords.more_names(lib, ["fantasy"], "job", 5) == []                           # only names have a maker


def test_a_name_becomes_a_character_a_place_a_place_and_a_thing_a_thing(home):
    u = vault.create_universe("U", ["fantasy"])
    msg, e = genrewords.add_to_universe(u, "first_name", "Aldric", "first_name")
    assert e.type == "character" and u.find_by_name("Aldric", "character") and "character" in msg
    msg, e = genrewords.add_to_universe(u, "landmark", "the ruined watchtower", "landmark")
    assert e.type == "place"
    msg, e = genrewords.add_to_universe(u, "thing", "a sword with a name", "thing")
    assert e.type == "thing"
    msg, again = genrewords.add_to_universe(u, "first_name", "Aldric", "first_name")
    assert "already" in msg and len(u.entities("character")) == 1


def test_a_job_goes_on_the_universes_generator_list(home):
    u = vault.create_universe("U", ["fantasy"])
    msg, e = genrewords.add_to_universe(u, "job", "sellsword", "job")
    assert e is None and (u.lists_dir / "job" / "words-added.json").exists() and "job" in msg


# --- Story words ---------------------------------------------------------------------------------------------------------------------

TEXT = ("Stacie rode to Glasswater. The Glass Water road was long. Stacie's dog knew Glasswater well.\n"
        "Stacy waited by the zorbl. A zorbl hummed and the puppy ran. Glasswater slept. Zorbl again.\n")


@pytest.fixture
def world(home, index):
    u = vault.create_universe("U", ["western"])
    s = u.new_story("Tale")
    s.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "manuscript.md").write_text(TEXT, encoding="utf-8")
    u.new_entity("character", "Stacie", {"role": "protagonist"})
    u.new_entity("place", "Glasswater")
    return u, s


def by_text(report, kind=None):
    return {i.text.lower(): i for i in report["items"] if kind is None or i.kind == kind}


def test_names_are_counted_with_where_they_occur(world):
    u, s = world
    names = by_text(storywords.analyze(u, s), "name")
    assert names["stacie"].count >= 2 and names["glasswater"].count == 3
    assert names["glasswater"].where[0]["line"] == 1 and "Glasswater" in names["glasswater"].where[0]["text"]


def test_words_the_dictionary_does_not_know_are_listed_with_counts(world):
    u, s = world
    r = storywords.analyze(u, s)
    unknown = by_text(r, "unknown")
    assert unknown["zorbl"].count == 3
    assert "dog" not in by_text(r) and "puppy" not in by_text(r) and "ran" not in by_text(r)       # known words are not listed
    assert r["words"] > 20 and r["dictionary"]


def test_a_name_written_two_ways_is_flagged(world):
    u, s = world
    variants = by_text(storywords.analyze(u, s), "variant")
    assert "glass water" in variants and variants["glass water"].related == "Glasswater"
    assert variants["glass water"].count == 1


def test_a_near_miss_of_a_name_is_flagged(world):
    u, s = world
    variants = by_text(storywords.analyze(u, s), "variant")
    assert "stacy" in variants and variants["stacy"].related.lower() == "stacie"


def test_adding_to_the_spelling_list_hides_the_word_next_time(world):
    u, s = world
    path, new = storywords.add_to_spelling(u, "Zorbl")
    assert new and path.read_text().splitlines()[:2] == ["Zorbl", "Zorbl's"]
    assert not storywords.add_to_spelling(u, "zorbl")[1]
    assert "zorbl" not in by_text(storywords.analyze(u, s))


def test_the_whole_universe_can_be_read_instead_of_one_story(world):
    u, s = world
    s2 = u.new_story("Other")
    s2.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (s2.manuscript_dir / "manuscript.md").write_text("A zorbl and a blorf.\n", encoding="utf-8")
    one = by_text(storywords.analyze(u, s), "unknown")
    allu = by_text(storywords.analyze(u), "unknown")
    assert "blorf" not in one and allu["blorf"].count == 1 and allu["zorbl"].count == 4


def test_rename_everywhere_works_for_a_word_that_is_not_an_entity(world):
    u, s = world
    stub = type("Stub", (), {"name": "Glass Water", "path": None})()
    matches = rename.find_matches(u, stub, "Glass Water")
    assert len(matches) == 1 and matches[0].kind == "manuscript"
    n = rename.apply_matches(u, stub, "Glass Water", "Glasswater", matches)
    assert n == 1 and "Glass Water" not in (s.manuscript_dir / "manuscript.md").read_text()
