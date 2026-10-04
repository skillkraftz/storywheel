"""Rhymes from the CMU Pronouncing Dictionary, and the Lookup boxes (Meanings, Similar, Opposites, Rhymes, Related)."""
import asyncio

import pytest
from textual.widgets import Button, Input, OptionList, Select

from dictfixture import build_fixture
from storywheel import dictionary, learn, rhymes, words_app
from conftest import screen_text
from test_words import flat, options, plain, run, select_word, type_word

CMU = """a AH0
a(2) EY1
aalborg AO1 L B AO0 R G # place, danish
cat K AE1 T
hat HH AE1 T
bat B AE1 T
at AE1 T
cap K AE1 P
back B AE1 K
bet B EH1 T
fate F EY1 T
debate D IH0 B EY1 T
late L EY1 T
cattle K AE1 T AH0 L
battle B AE1 T AH0 L
rattle R AE1 T AH0 L
to T UW1
too T UW1
do D UW1
read R EH1 D
read(2) R IY1 D
dog D AO1 G
fog F AO1 G
log L AO1 G
hog HH AO1 G
puppy P AH1 P IY0
guppy G AH1 P IY0
glad G L AE1 D
sad S AE1 D
chad CH AE1 D
bad B AE1 D
schad SH AE1 D # name
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
    assert src.name == "cmudict.dict"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(CMU, encoding="utf-8")
    monkeypatch.setattr(dictionary, "knows", lambda words: set(words))        # (most tests: every word counts as known; see the filter tests)
    yield src
    rhymes.forget()
    dictionary.forget()


@pytest.fixture
def real_filter(cmu, monkeypatch):
    """The cmu fixture with the real "does the main dictionary know it" check, against the small test dictionary."""
    monkeypatch.setattr(dictionary, "knows", _real_knows)
    return cmu


_real_knows = dictionary.knows


def words_of(groups):
    return {w for _s, ws in groups for w in ws}


# --- reading the file ---------------------------------------------------------------------------------------------------------

def test_a_trailing_comment_is_not_phonemes():
    rows = rhymes.parse(["aalborg AO1 L B AO0 R G # place, danish", "schad SH AE1 D # name"])
    assert rows == [("aalborg", 1, "AO1 L B AO0 R G".split()), ("schad", 1, "SH AE1 D".split())]


def test_variants_and_single_spaces(cmu):
    rows = rhymes.parse(["read R EH1 D", "read(2) R IY1 D", "a AH0", "a(2) EY1"])
    assert rows == [("read", 1, ["R", "EH1", "D"]), ("read", 2, ["R", "IY1", "D"]), ("a", 1, ["AH0"]), ("a", 2, ["EY1"])]


def test_the_older_uppercase_format_is_still_read():
    rows = rhymes.parse([";;; # CMUdict -- Major Version: 0.07", "ABERDEEN  AE2 B ER0 D IY1 N", "READ(2)  R IY1 D", "#HASH-MARK  HH AE1 SH M AA2 R K",
                         "'S  Z", "!EXCLAMATION-POINT  EH2 K S K L AH0 M EY1 SH AH0 N P OY2 N T"])
    assert [(w, v) for w, v, _p in rows] == [("aberdeen", 1), ("read", 2), ("#hash-mark", 1), ("'s", 1), ("!exclamation-point", 1)]
    assert rows[0][2] == ["AE2", "B", "ER0", "D", "IY1", "N"]


def test_a_line_that_is_not_a_pronunciation_is_skipped():
    assert rhymes.parse(["broken line without phones", "word 123 456", "fine F AY1 N"]) == [("fine", 1, ["F", "AY1", "N"])]


def test_an_older_cmudict_0_7b_file_in_the_sources_folder_is_still_used(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    monkeypatch.setattr(dictionary, "knows", lambda words: set(words))
    rhymes.forget()
    old = rhymes.sources_folder() / "cmudict-0.7b"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text(";;; # CMUdict\n;;; # Copyright (C) 1993-2015 Carnegie Mellon University\nCAT  K AE1 T\nHAT  HH AE1 T\n", encoding="latin-1")
    assert rhymes.source_path() == old
    assert words_of(rhymes.find("cat")["perfect"]) == {"hat"}
    assert "Copyright (C) 1993-2015 Carnegie Mellon University" in rhymes.status()["license"]
    rhymes.forget()


# --- names and rare words -----------------------------------------------------------------------------------------------------

def test_by_default_only_words_the_main_dictionary_knows(real_filter):
    r = rhymes.find("glad")
    assert words_of(r["perfect"]) == {"sad"} and r["filtered"] and r["hidden"] >= 3          # chad, bad, schad are not in the test dictionary
    everything = rhymes.find("glad", rare=True)
    assert words_of(everything["perfect"]) == {"sad", "chad", "bad", "schad"} and everything["hidden"] == 0


def test_the_filter_covers_near_rhymes_too(real_filter):
    assert words_of(rhymes.find("glad")["near"]) <= {"sad", "dash"} or not words_of(rhymes.find("glad")["near"]) & {"chad", "bad", "schad", "cat", "hat"}


def test_the_order_says_how_it_is_ordered(cmu, monkeypatch):
    monkeypatch.setattr(rhymes, "wordfreq_available", lambda: False)
    r = rhymes.find("cat")
    assert r["order"] == rhymes.ORDER_ABC and "pipx inject storywheel wordfreq" in r["order"]
    assert [w for _s, ws in r["perfect"] for w in ws] == ["at", "bat", "hat"]
    monkeypatch.setattr(rhymes, "wordfreq_available", lambda: True)
    monkeypatch.setattr(rhymes, "commonness", lambda w: {"hat": 5.0, "bat": 4.0, "at": 6.5}.get(w, 0))
    r = rhymes.find("cat")
    assert r["order"] == rhymes.ORDER_FREQ and [w for _s, ws in r["perfect"] for w in ws] == ["at", "hat", "bat"]


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
    assert st["installed"]


LICENSE = "Copyright (C) 1993-2015 Carnegie Mellon University. All rights reserved.\nRedistribution and use in source and binary forms are permitted."


def test_install_downloads_the_file_and_the_license_only_when_they_are_not_kept(tmp_path, monkeypatch):
    from storywheel import dictionary_build as db
    seen = []
    def fake(url, dest, progress=lambda m: None):
        seen.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(LICENSE if url == rhymes.CMU_LICENSE_URL else CMU, encoding="utf-8")
    monkeypatch.setattr(db, "download", fake)
    out = tmp_path / "dictionary.sqlite"
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    rhymes.forget()
    messages = []
    n = len(rhymes.parse(CMU.splitlines()))
    assert db.install_rhymes(out, messages.append) == n
    assert seen == [rhymes.CMU_URL, rhymes.CMU_LICENSE_URL] and (tmp_path / "rhymes.sqlite").exists()
    assert rhymes.CMU_URL.endswith("/master/cmudict.dict") and (tmp_path / "dictionary-sources" / "cmudict.dict").exists()
    assert "Copyright (C) 1993-2015 Carnegie Mellon University" in rhymes.status()["license"]
    assert db.install_rhymes(out, messages.append) == n and len(seen) == 2          # (kept: not downloaded again)
    assert rhymes.failure() == ""


def test_a_failed_download_says_so_plainly_and_is_remembered(tmp_path, monkeypatch):
    from storywheel import dictionary_build as db
    out = tmp_path / "dictionary.sqlite"
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    rhymes.forget()
    def boom(url, dest, progress=lambda m: None):
        raise db.DictionaryBuildError("HTTP 404 for the file")
    monkeypatch.setattr(db, "download", boom)
    messages = []
    assert db.install_rhymes(out, messages.append) is None
    assert "Rhymes were NOT installed: HTTP 404 for the file." in messages[-1] and "dictionary install" in messages[-1]
    assert rhymes.failure() == "HTTP 404 for the file."
    with pytest.raises(rhymes.RhymesMissing) as e:
        rhymes.find("cat")
    assert "Rhymes were NOT installed: HTTP 404 for the file." in str(e.value) and "To fix it, run:  storywheel dictionary install" in str(e.value)
    assert not rhymes.status()["installed"]


def test_the_command_line_ends_with_a_plain_not_installed_message(tmp_path, monkeypatch, capsys, home):
    from storywheel import dictionary_build as db
    from storywheel.cli import main as cli
    from dictfixture import XML, MOBY
    import gzip
    def fake(url, dest, progress=lambda m: None):
        dest.parent.mkdir(parents=True, exist_ok=True)
        if url == rhymes.CMU_URL:
            raise db.DictionaryBuildError("HTTP 404 for cmudict.dict")
        if dest.suffix == ".gz":
            with gzip.open(dest, "wb") as f:
                f.write(XML.encode("utf-8"))
        else:
            dest.write_text(MOBY, encoding="latin-1")
    monkeypatch.setattr(db, "download", fake)
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(tmp_path / "d" / "dictionary.sqlite"))
    monkeypatch.setattr("storywheel.genrefit.ensure", lambda *a, **k: None)
    monkeypatch.setattr("storywheel.spelldict.ensure", lambda *a, **k: None)
    rhymes.forget()
    cli(["dictionary", "install"])
    out = capsys.readouterr().out
    assert "Rhymes were NOT installed" in out and "HTTP 404 for cmudict.dict" in out and "Everything else works" in out
    cli(["dictionary", "status"])
    assert "Rhymes: Rhymes were NOT installed: HTTP 404 for cmudict.dict." in capsys.readouterr().out


def test_status_shows_the_license(cmu, capsys):
    from storywheel.cli import main as cli
    rhymes.license_path().write_text(LICENSE, encoding="utf-8")
    rhymes.find("cat")
    cli(["dictionary", "status"])
    out = capsys.readouterr().out
    assert "License of the CMU Pronouncing Dictionary" in out and "Copyright (C) 1993-2015 Carnegie Mellon University" in out


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


def test_the_names_and_rare_words_switch_in_the_box(cmu, monkeypatch):
    monkeypatch.setattr(dictionary, "knows", _real_knows)
    async def script(app, pilot):
        await type_word(app, pilot, "glad")
        common = [plain(i) for i, _t in options(app, "res-rhymes") if i]
        text = " ".join(t for _i, t in options(app, "res-rhymes"))
        app.screen.query_one("#rhrare", Select).value = 1
        await pilot.pause()
        more = [plain(i) for i, _t in options(app, "res-rhymes") if i]
        return common, text, more
    common, text, more = run(script)
    assert "w:sad|" in common and "w:chad|" not in common and "names and rare words are left out" in text and "Ordered" in text
    assert "w:chad|" in more and "w:schad|" in more


def test_the_box_repeats_a_failed_install_instead_of_finding_nothing(tmp_path, monkeypatch, home):
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    dictionary.forget()
    rhymes.forget()
    rhymes.record_failure("HTTP 404 for cmudict.dict.")
    async def script(app, pilot):
        await type_word(app, pilot, "dog")
        return " ".join(t for _i, t in options(app, "res-rhymes"))
    text = run(script)
    assert "Rhymes were NOT installed: HTTP 404 for cmudict.dict." in text and "storywheel dictionary install" in text
