"""Genre fit (worked out once and kept in the dictionary index), the long word lists built on it, and the virtual list that shows them."""
import asyncio
import sqlite3
from collections import Counter

import pytest

from dictfixture import ZIPF, build_fixture
from storywheel import dictionary, genrefit, wordlists
from storywheel.library import Entry, Library, WordList
from storywheel.virtuallist import VirtualList


@pytest.fixture
def index(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    monkeypatch.setattr(genrefit, "zipf_function", lambda: (lambda w: ZIPF.get(w, 0.0)))
    dictionary.forget()
    yield out
    dictionary.forget()


def library(**atoms):
    """A small library: {slot-list name: (tags, [texts])}."""
    lists = {}
    for name, (tags, texts, *rest) in atoms.items():
        slot = name.split("_", 1)[0] if rest else "thing"
        lists[name] = WordList(name, rest[0] if rest else slot, tags, [Entry(t) for t in texts], is_template=bool(rest and rest[1]))
    return Library(lists, {"western": {"western": 3}, "fantasy": {"fantasy": 3}, "general": {"general": 1}})


@pytest.fixture
def lib():
    return library(west=(["western"], ["dog", "gallop"]), fant=(["fantasy"], ["wolf", "leaf"]),
                   both=(["western", "fantasy", "general"], ["happy"]))


def built(index, lib):
    return genrefit.build(index, lib)


# --- seeds -------------------------------------------------------------------------------------------------------------------------

def test_seeds_are_the_words_of_a_genres_lists_and_its_frames_a_third_as_much():
    lists = {"thing/west": WordList("thing/west", "thing", ["western"], [Entry("a rusted bell"), Entry("a rusted bell")]),
             "first_name/west": WordList("first_name/west", "first_name", ["western"], [Entry("Abigail")]),
             "premise/west": WordList("premise/west", "premise", ["western"], [Entry("{first} must hunt the lantern")], is_template=True)}
    lib = Library(lists, {"western": {"western": 3}})
    got = genrefit.seed_words(lib)["western"]
    assert got["rusted"] == 2.0 and got["bell"] == 2.0 and "abigail" not in got                  # names are left out
    assert got["hunt"] == pytest.approx(0.3) and "first" not in got and "must" not in got        # frames: fixed words only, no stop words


def test_an_entrys_own_tags_decide_which_genre_it_seeds():
    lists = {"thing/g": WordList("thing/g", "thing", ["general"], [Entry("a lantern", tags=["western"]), Entry("a spoon")])}
    got = genrefit.seed_words(Library(lists, {"western": {"western": 3}}))
    assert "lantern" in got["western"] and "spoon" not in got["western"]


# --- the fit -----------------------------------------------------------------------------------------------------------------------

def test_build_makes_one_lexicon_row_per_word_and_part_of_speech(index, lib):
    counts = built(index, lib)
    db = sqlite3.connect(index)
    rows = db.execute("select w, pos from lexicon").fetchall()
    assert ("dog", "n") in rows and ("run", "v") in rows and ("happy", "a") in rows and ("cheerful", "a") in rows     # (a satellite is an adjective)
    assert len(rows) == len(set(rows)) and counts["words"] == len(rows)
    zipf = dict(db.execute("select w, zipf from lexicon where pos = 'n'"))
    assert zipf["puppy"] == 340


def test_a_seed_lights_its_meaning_and_the_glow_spreads_with_decay(index, lib):
    built(index, lib)
    db = sqlite3.connect(index)
    fit = {(g, w, p): s for g, w, p, s in db.execute("select f.genre, l.w, f.pos, f.score from fit f join lexicon l on l.word_id = f.word_id and l.pos = f.pos")}
    assert fit[("western", "dog", "n")] >= 80                                 # a seed (a word with two meanings points a little less at each)
    assert 0 < fit[("western", "puppy", "n")] < fit[("western", "dog", "n")]    # a narrower word: less
    assert fit[("western", "canine", "n")] < fit[("western", "dog", "n")]       # a broader word: less
    assert ("western", "leaf", "n") not in fit and ("western", "goose", "n") not in fit
    assert fit[("fantasy", "wolf", "n")] >= 85 and ("fantasy", "puppy", "n") not in fit


def test_a_word_every_genre_uses_says_nothing_about_any_of_them(index, lib):
    built(index, lib)
    db = sqlite3.connect(index)
    got = {g: s for g, s in db.execute("select f.genre, f.score from fit f join lexicon l on l.word_id = f.word_id and l.pos = f.pos where l.w = 'happy' and l.pos = 'a'")}
    assert got["western"] < 65 and got["fantasy"] < 65                          # shared by two genres: weighed down, and "general" is no genre


def test_the_thesaurus_neighbours_of_a_strong_seed_get_a_small_share(index, lib):
    built(index, lib)
    db = sqlite3.connect(index)
    hound = db.execute("select f.score from fit f join lexicon l on l.word_id = f.word_id where f.genre = 'western' and l.w = 'hound'").fetchall()
    assert not hound or max(h[0] for h in hound) < 30                           # (not in WordNet's own entries: at most a small share)
    gallop = db.execute("select 1 from lexicon where w = 'gallop'").fetchone()
    assert gallop is None                                                       # a word the dictionary does not know is not invented


def test_subject_domains_light_their_meanings(index, monkeypatch):
    lib = library(west=(["western"], ["dog"]))
    monkeypatch.setattr(genrefit, "domain_names", lambda library: {"western": ["veterinary medicine"], "fantasy": ["veterinary medicine"]})
    built(index, lib)
    db = sqlite3.connect(index)
    fit = {(g, w): s for g, w, s in db.execute("select f.genre, l.w, f.score from fit f join lexicon l on l.word_id = f.word_id and l.pos = f.pos")}
    assert fit[("fantasy", "kennel")] == 70 and fit[("fantasy", "vaccinate")] == 70       # meanings "in veterinary medicine"


def test_the_fit_is_stale_until_built_and_again_when_a_genres_lists_change(index, lib):
    assert genrefit.stale(lib)
    assert "Worked out" in genrefit.ensure(library=lib)
    assert not genrefit.stale(lib) and genrefit.ensure(library=lib) is None
    lib.lists["west"].entries.append(Entry("lasso"))
    assert genrefit.stale(lib)
    assert "Worked out" in genrefit.ensure(library=lib) and not genrefit.stale(lib)


def test_without_a_dictionary_there_is_nothing_to_build(tmp_path, monkeypatch, lib):
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(tmp_path / "none.sqlite"))
    dictionary.forget()
    assert genrefit.ensure(library=lib) is None and not genrefit.stale(lib) and not wordlists.ready()


def test_the_shipped_genres_have_domains_that_exist_in_wordnet_names():
    lib = Library.load()
    domains = genrefit.domain_names(lib)
    assert domains["sci-fi"] and "astronomy" in domains["sci-fi"] and "law" in domains["mystery"]
    assert set(domains) <= set(lib.profiles)


# --- the lists ---------------------------------------------------------------------------------------------------------------------

def test_markers_have_three_levels_and_a_blank():
    assert [wordlists.marker(s) for s in (100, 60, 59, 35, 20, 15, 14, 0)] == ["●●●", "●●●", "●●○", "●●○", "●○○", "●○○", "···", "···"]


def test_a_view_lists_every_lemma_of_one_part_of_speech(index, lib):
    built(index, lib)
    nouns = wordlists.View("n", sort="az")
    words = [r["word"] for r in nouns.page(0, 100)]
    assert words == sorted(words) and {"dog", "puppy", "goose", "leaf"} <= set(words) and "run" not in words
    assert {r["word"] for r in wordlists.View("v").page(0, 100)} >= {"run", "sprint", "leave", "vaccinate"}
    assert {r["word"] for r in wordlists.View("a").page(0, 100)} >= {"happy", "glad", "cheerful", "doggy"}
    first = nouns.page(0, 3)[0]
    assert first["definition"] and first["pos"] == "noun"


def test_genres_rank_and_never_hide(index, lib):
    built(index, lib)
    everything = wordlists.View("n", sort="az")
    ranked = wordlists.View("n", ["western"], sort="fit")
    assert len(ranked) == len(everything)                                       # nothing is hidden
    top = ranked.page(0, 5)
    assert top[0]["word"] in ("dog", "wretch", "domestic dog") and top[0]["fit"] >= 80 and top[0]["mark"] == "●●●"
    assert [r["fit"] for r in ranked.page(0, 100)] == sorted([r["fit"] for r in ranked.page(0, 100)], reverse=True)
    assert wordlists.View("n", ["fantasy"], sort="fit").page(0, 1)[0]["word"] in ("wolf", "leaf")
    both = wordlists.View("n", ["western", "fantasy"], sort="fit")
    assert {r["word"] for r in both.page(0, 6)} >= {"dog", "wolf"}              # several genres: the best fit to any of them


def test_without_a_genre_there_is_no_fit_marker_and_the_order_is_commonness(index, lib):
    built(index, lib)
    view = wordlists.View("n", [], sort="fit")
    rows = view.page(0, 50)
    assert view.sort == "common" and all(r["mark"] == "" for r in rows)
    zipfs = [r["zipf"] for r in rows]
    assert zipfs == sorted(zipfs, reverse=True)


def test_commonness_bands_use_the_vocabulary_bands(index, lib):
    built(index, lib)
    def words(band):
        return {r["word"] for r in wordlists.View("n", band=band, sort="az").page(0, 100)}
    assert "tail" in words("everyday") and "dog" in words("everyday")             # 4.6 and 5.2
    assert words("uncommon") >= {"puppy", "goose"} and "tail" not in words("uncommon")         # 3.4, 3.7 (wolf, 3.9, is everyday)
    assert "kennel" in words("rare") and "canine" in words("rare")                # 2.6 and 2.8
    assert "wretch" in words("very rare") and "kennel" not in words("very rare")


def test_search_filters_the_list_and_literal_characters_are_safe(index, lib):
    built(index, lib)
    assert {r["word"] for r in wordlists.View("n", query="dog", sort="az").page(0, 50)} >= {"dog", "domestic dog"}
    assert wordlists.View("n", query="zzz").page(0, 5) == []
    assert len(wordlists.View("n", query="%")) == 0 and len(wordlists.View("n", query="_")) == 0       # (not wildcards)


def test_pages_are_read_a_few_rows_at_a_time(index, lib):
    built(index, lib)
    view = wordlists.View("n", sort="az")
    assert len(view.page(2, 3)) == 3 and view.page(len(view), 5) == [] and len(view.page(len(view) - 1, 5)) == 1


# --- the virtual list --------------------------------------------------------------------------------------------------------------

from rich.text import Text
from textual.app import App


class ListApp(App):
    def __init__(self, count):
        super().__init__()
        self.count = count
        self.log_rows = []

    def compose(self):
        yield VirtualList(id="v")

    def on_mount(self):
        v = self.query_one(VirtualList)
        v.set_source(self.count, lambda start, n: [f"row {i}" for i in range(start, min(start + n, self.count))],
                     lambda row, selected, width: Text(("> " if selected else "  ") + row))

    def on_virtual_list_highlighted(self, e):
        self.log_rows.append(e.index)

    def on_virtual_list_selected(self, e):
        self.log_rows.append(("open", e.index))


def drive(count, script, size=(80, 20)):
    async def go():
        app = ListApp(count)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot, app.query_one(VirtualList))
    return asyncio.run(go())


def test_a_huge_list_opens_by_reading_one_page():
    async def script(app, pilot, v):
        await pilot.pause()
        return v.fetches, v.virtual_size.height, v.current()
    fetches, height, current = drive(500_000, script)
    assert height == 500_000 and fetches <= 2 and current == "row 0"


def test_keys_move_the_cursor_and_scroll_it_into_view():
    async def script(app, pilot, v):
        await pilot.press("down", "down")
        a = v.cursor
        await pilot.press("pagedown")
        b = v.cursor
        await pilot.press("end")
        c, top = v.cursor, v.scroll_offset.y
        await pilot.press("home")
        d, top0 = v.cursor, v.scroll_offset.y
        await pilot.press("up")
        return a, b, c, top, d, top0, v.cursor, v.fetches
    a, b, c, top, d, top0, after_up, fetches = drive(100_000, script)
    assert a == 2 and 18 <= b <= 22 and c == 99_999 and top >= 99_999 - 19 and d == 0 and top0 == 0 and after_up == 0
    assert fetches <= 6                                                         # (never the whole list)


def test_enter_and_a_double_click_open_a_row_and_a_click_selects_it():
    async def script(app, pilot, v):
        v.focus()
        await pilot.pause()
        await pilot.click(VirtualList, offset=(5, 3))
        await pilot.pause()
        picked = v.cursor
        await pilot.press("enter")
        await pilot.pause()
        return picked, app.log_rows
    picked, log = drive(1000, script)
    assert picked == 3 and ("open", 3) in log and 3 in log


def test_the_cursor_row_is_marked_and_rows_are_rendered_on_demand():
    async def script(app, pilot, v):
        await pilot.press("down")
        lines = ["".join(seg.text for seg in v.render_line(y)) for y in range(4)]
        return lines
    lines = drive(50, script)
    assert lines[0].startswith("  row 0") and lines[1].startswith("> row 1") and lines[2].startswith("  row 2")


def test_an_empty_list_has_no_cursor_and_keys_do_nothing():
    async def script(app, pilot, v):
        await pilot.press("down", "end", "enter")
        return v.cursor, v.current(), app.log_rows
    assert drive(0, script) == (None, None, [])
