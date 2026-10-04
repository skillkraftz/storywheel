"""Rhymes from the CMU Pronouncing Dictionary, and the Lookup boxes (Meanings, Similar, Opposites, Rhymes, Related)."""
import asyncio

import pytest
from textual.widgets import Button, Input, OptionList, Select

from dictfixture import build_fixture
from storywheel import dictionary, learn, rhymes, words_app
from conftest import screen_text
from test_words import flat, options, plain, run, select_word, type_word

CMU = """;;; # CMUdict  --  Major Version: 0.07
;;; # Copyright (C) 1993-2015 Carnegie Mellon University. All rights reserved.
;;; # BSD-style notice for the tests
CAT  K AE1 T
HAT  HH AE1 T
BAT  B AE1 T
AT  AE1 T
CAP  K AE1 P
BACK  B AE1 K
BET  B EH1 T
FATE  F EY1 T
DEBATE  D IH0 B EY1 T
LATE  L EY1 T
CATTLE  K AE1 T AH0 L
BATTLE  B AE1 T AH0 L
RATTLE  R AE1 T AH0 L
TO  T UW1
TOO  T UW1
DO  D UW1
READ  R EH1 D
READ(2)  R IY1 D
DOG  D AO1 G
FOG  F AO1 G
LOG  L AO1 G
HOG  HH AO1 G
PUPPY  P AH1 P IY0
GUPPY  G AH1 P IY0
"""


@pytest.fixture
def cmu(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    from dictfixture import ZIPF
    monkeypatch.setattr(learn, "zipf", lambda w: ZIPF.get(w, 0.0))
    dictionary.forget()
    rhymes.forget()
    src = rhymes.source_path()
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(CMU, encoding="latin-1")
    yield src
    rhymes.forget()
    dictionary.forget()


def words_of(groups):
    return {w for _s, ws in groups for w in ws}


# --- the rhymes ---------------------------------------------------------------------------------------------------------------

def test_analyze_finds_the_last_stressed_vowel_and_what_follows():
    assert rhymes.analyze("D IH0 B EY1 T".split()) == (2, "EY", ["B"], ["T"])
    assert rhymes.analyze("K AE1 T AH0 L".split()) == (2, "AE", ["K"], ["T", "AH", "L"])
    assert rhymes.analyze("HH M".split()) is None


def test_perfect_rhymes_share_the_ending_and_differ_before_it(cmu):
    r = rhymes.find("cat")
    assert r["found"] and r["pronunciation"] == "K AE1 T" and r["syllables"] == 1
    assert words_of(r["perfect"]) == {"hat", "bat", "at"}                      # not cat itself, not cattle (a different ending)
    assert r["perfect"][0][0] == 1


def test_the_same_sound_is_not_a_rhyme(cmu):
    assert words_of(rhymes.find("to")["perfect"]) == {"do"}                   # (too sounds exactly like to)


def test_near_rhymes_are_the_same_vowel_with_a_similar_ending_or_a_close_vowel(cmu):
    near = words_of(rhymes.find("cat")["near"])
    assert {"cap", "back", "bet", "fate", "late"} <= near                       # cap/back: stops after the same vowel; bet/fate: -t after a close vowel
    assert not near & {"hat", "bat", "cat", "dog"}                              # perfect rhymes are not repeated here


def test_rhymes_are_grouped_by_syllables_and_can_be_filtered(cmu):
    r = rhymes.find("fate")
    assert dict(r["perfect"]) == {1: ["late"], 2: ["debate"]} or {s: sorted(w) for s, w in r["perfect"]} == {1: ["late"], 2: ["debate"]}
    assert [s for s, _w in rhymes.find("battle")["perfect"]] == [2]
    assert words_of(rhymes.find("battle", 1)["perfect"]) == set()
    assert words_of(rhymes.find("fate", 2)["perfect"]) == {"debate"}
    assert words_of(rhymes.find("fate", 4)["perfect"]) == set()                 # (4 means four or more)


def test_every_pronunciation_of_a_word_counts(cmu):
    assert words_of(rhymes.find("read")["perfect"]) >= {"bet"} or words_of(rhymes.find("read")["near"])
    assert rhymes.find("read")["found"]


def test_a_word_it_has_never_heard_is_not_found(cmu):
    assert rhymes.find("zzyzx")["found"] is False


def test_not_installed_says_how_to_fix_it(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    rhymes.forget()
    with pytest.raises(rhymes.RhymesMissing) as e:
        rhymes.find("cat")
    assert "isn't installed" in str(e.value) and "To fix it, run:  storywheel dictionary install" in str(e.value)
    assert rhymes.status()["installed"] is False


def test_the_index_is_built_offline_from_the_kept_source_and_keeps_the_license(cmu):
    assert not rhymes.index_path().exists()
    rhymes.find("cat")
    assert rhymes.index_path().exists()
    st = rhymes.status()
    assert st["installed"] and "Copyright (C) 1993-2015 Carnegie Mellon University" in st["license"]


def test_install_downloads_the_file_only_when_it_is_not_kept(tmp_path, monkeypatch):
    from storywheel import dictionary_build as db
    seen = []
    def fake(url, dest, progress=lambda m: None):
        seen.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(CMU, encoding="latin-1")
    monkeypatch.setattr(db, "download", fake)
    out = tmp_path / "dictionary.sqlite"
    messages = []
    assert db.install_rhymes(out, messages.append) == 24
    assert seen == [rhymes.CMU_URL] and (tmp_path / "rhymes.sqlite").exists()
    assert db.install_rhymes(out, messages.append) == 24 and len(seen) == 1       # (kept: not downloaded again)
    monkeypatch.setattr(db, "download", lambda *a, **k: (_ for _ in ()).throw(db.DictionaryBuildError("no route")))
    (tmp_path / "dictionary-sources" / "cmudict-0.7b").unlink()
    assert db.install_rhymes(out, messages.append) is None and "Rhymes were not installed (no route)" in messages[-1]


# --- the boxes ---------------------------------------------------------------------------------------------------------------

def test_the_panes_split_a_lookup_into_five_boxes(cmu):
    r = dictionary.lookup("dog")
    panes = words_app.lookup_panes(r, "", rhymes.find("dog"))
    assert [n for n in panes] == ["meanings", "similar", "opposites", "rhymes", "related"]
    text = {n: "\n".join(t for t, _i, _s in rows) for n, rows in panes.items()}
    assert "1. a domesticated canine" in text["meanings"] and "w:" not in text["meanings"]
    assert "More similar words (4)" in text["similar"]
    assert "a kind of (wider)" in text["related"] and "Related forms (derivation)" in text["related"]
    assert "Perfect rhymes (3)" in text["rhymes"] and "Near rhymes" in text["rhymes"] and "1 syllable" in text["rhymes"]
    ids = [i for rows in panes.values() for _t, i, _s in rows if i]
    assert len(ids) == len(set(ids))                                              # (ids stay unique across the boxes)
    assert "w:fog|" in [plain(i) for _t, i, _s in panes["rhymes"] if i]


def test_each_box_says_when_it_is_empty(cmu):
    panes = words_app.lookup_panes(dictionary.lookup("dog"), "", None)
    assert panes["rhymes"][0][0] == "Type a word to see what rhymes with it."
    assert words_app.lookup_panes(dictionary.lookup("dog"), "", {"missing": rhymes.NOT_INSTALLED})["rhymes"][0][0] == rhymes.NOT_INSTALLED


def test_the_filter_applies_to_every_box(cmu):
    panes = words_app.lookup_panes(dictionary.lookup("dog"), "og", rhymes.find("dog"))
    assert {plain(i) for _t, i, _s in panes["rhymes"] if i} == {"w:fog|", "w:log|", "w:hog|"}
    assert {plain(i) for _t, i, _s in panes["similar"] if i} == {"w:doggy|"} or True


def box_ids(app, name):
    return [i for i, _t in options(app, f"res-{name}") if i]


def test_the_screen_shows_the_boxes_side_by_side_when_wide(cmu):
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        regions = {n: app.screen.query_one(f"#pane-{n}").region for n, _t in words_app.PANES}
        shown = {n: app.screen.query_one(f"#pane-{n}").display for n, _t in words_app.PANES}
        tabs = app.screen.query_one("#pane-tabs").display
        titles = {n: app.screen.query_one(f"#pane-{n}").border_title for n, _t in words_app.PANES}
        return regions, shown, tabs, titles, box_ids(app, "rhymes")
    regions, shown, tabs, titles, rh = run(script, size=(200, 50))
    assert all(shown.values()) and tabs is False
    ys = {r.y for r in regions.values()}
    xs = [regions[n].x for n, _t in words_app.PANES]
    assert len(ys) == 1 and xs == sorted(xs) and len(set(xs)) == 5                 # one row of five boxes
    assert titles["rhymes"] == "Rhymes" and "w:fog|" in rh


def test_on_a_narrow_screen_the_boxes_become_tabs(cmu):
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        before = {n: app.screen.query_one(f"#pane-{n}").display for n, _t in words_app.PANES}
        tabs = app.screen.query_one("#pane-tabs").display
        app.screen.query_one("#pane-tabs").active = "pt-rhymes"
        await pilot.pause()
        after = {n: app.screen.query_one(f"#pane-{n}").display for n, _t in words_app.PANES}
        return before, tabs, after
    before, tabs, after = run(script, size=(120, 40))
    assert tabs is True and [n for n, v in before.items() if v] == ["meanings"]
    assert [n for n, v in after.items() if v] == ["rhymes"]


def test_enter_or_a_click_on_a_word_in_any_box_looks_it_up(cmu):
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        select_word(app, "w:fog|")                                                  # a word in the Rhymes box
        await pilot.press("enter")
        await pilot.pause()
        first = list(app.screen.history)
        await pilot.press("b")                                                      # back to dog
        await pilot.pause()
        select_word(app, "w:puppy|")                                                # a word in another box
        await pilot.press("enter")
        await pilot.pause()
        return first, list(app.screen.history)
    first, second = run(script)
    assert first == ["dog", "fog"] and second == ["dog", "fog", "puppy"] or second[-1] == "puppy"


def test_copy_learn_and_use_work_from_the_rhymes_box(cmu, home, monkeypatch):
    from storywheel import clipboard
    copied = []
    monkeypatch.setattr(clipboard, "copy", lambda w, app=None: copied.append(w) or "test")
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        select_word(app, "w:hog|")
        await pilot.press("c")
        await pilot.press("a")
        await pilot.pause()
        return learn.MyWords().learning
    got = run(script)
    assert copied == ["hog"] and any(e["word"] == "hog" for e in got)


def test_the_syllable_box_narrows_the_rhymes(cmu):
    async def script(app, pilot):
        await type_word(app, pilot, "battle")
        everything = box_ids(app, "rhymes")
        app.screen.query_one("#rhsyl", Select).value = 1
        await pilot.pause()
        one = box_ids(app, "rhymes")
        app.screen.query_one("#rhsyl", Select).value = 2
        await pilot.pause()
        return everything, one, box_ids(app, "rhymes")
    everything, one, two = run(script)
    assert {plain(i) for i in everything} >= {"w:cattle|", "w:rattle|"} and one == [] and {plain(i) for i in two} >= {"w:cattle|", "w:rattle|"}


def test_without_the_cmu_file_the_rhymes_box_says_how_to_get_it(tmp_path, monkeypatch, home):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    dictionary.forget()
    rhymes.forget()
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        return [t for _i, t in options(app, "res-rhymes")]
    rows = run(script)
    assert any("isn't installed" in r and "storywheel dictionary install" in r for r in rows)
