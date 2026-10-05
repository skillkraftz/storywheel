"""Batch 15: ages and jobs agree, no blank fills anywhere, technology follows the era in every genre, and the repetition report's watch list."""
import collections
import re

import pytest

from storywheel import fill, outline, report, steps, structures, vault
from storywheel.engine import Engine
from storywheel.library import Library
from storywheel.sample import build_story

GENRES = ["western", "fairy tale", "comedy", "fantasy", "mystery", "horror", "sci-fi", "romance", "ghost story", "noir", "thriller",
          "heist", "adventure", "coming-of-age"]
STRUCTURES = ["Story Spine", "Three-Act Outline", "Kishōtenketsu"]


@pytest.fixture(scope="module")
def lib():
    return Library.load()


def stories(genres, n, seed, structure=None):
    """[(story, trace of that story)] for n seeded stories."""
    e = Engine(seed=seed)
    e.trace = []
    out = []
    for _ in range(n):
        before = len(e.trace)
        st = build_story(e, genres, structure=structure) if structure else build_story(e, genres)
        out.append((st, e.trace[before:]))
    return e, out


def texts_of(story):
    k = story["kept"]
    out = []
    for step in ("title", "protagonist", "setting", "premise", "spine", "twist"):
        out += [v for key, v in (k.get(step) or {}).items() if isinstance(v, str) and not key.startswith("_")]
    return out


# --- ages ------------------------------------------------------------------------------------------------------------------------

def test_the_age_rules_are_data(lib):
    assert lib.ages["coming-of-age"] == (13, 19) and lib.ages["_default"] == (20, 80)
    assert steps.band_of(12) == "child" and steps.band_of("15") == "teen" and steps.band_of(45) == "adult" and steps.band_of(66) == "elder"
    assert steps.job_bands(()) == {"adult", "elder"} and steps.job_bands(("teen",)) == {"teen"} and steps.job_bands(("elder",)) == {"elder"}
    assert steps.job_bands(("teen", "adult")) == {"teen", "adult", "elder"}


def test_jobs_say_who_can_do_them(lib):
    def feats(text):
        return next(e.features for wl in lib.by_slot["job"] for e in wl.entries if e.text == text)
    assert "teen" in feats("paperboy") and "teen" in feats("class president") and "adult" not in feats("paperboy")
    for text in ("retired boxer", "retired captain", "retired detective", "retired colonel"):
        assert steps.job_bands(feats(text)) == {"elder"}, text
    every = [e.text for wl in lib.by_slot["job"] if not wl.generator for e in wl.entries if e.text.startswith("retired ")]
    assert every and all(steps.job_bands(feats(t)) == {"elder"} for t in every)
    teen = [e for wl in lib.by_slot["job"] if "coming-of-age" in wl.tags for e in wl.entries]
    assert teen and all("teen" in (e.features or ()) for e in teen)


@pytest.mark.parametrize("genre", GENRES)
def test_a_protagonists_age_is_in_the_genres_range_and_fits_the_job(genre):
    e, rolled = stories([genre], 60, seed=15)
    lo, hi = (13, 19) if genre == "coming-of-age" else (20, 80)
    for st, _trace in rolled:
        p = st["kept"]["protagonist"]
        age = int(p["age"])
        assert lo <= age <= hi, (genre, p["age"], p["job"])
        feats = e.features_of("job", p["job"])
        assert steps.band_of(age) in steps.job_bands(feats), (genre, p["age"], p["job"])


def test_coming_of_age_protagonists_are_teenagers_with_teen_jobs():
    e, rolled = stories(["coming-of-age"], 80, seed=3)
    jobs = collections.Counter(st["kept"]["protagonist"]["job"] for st, _t in rolled)
    assert all(13 <= int(st["kept"]["protagonist"]["age"]) <= 19 for st, _t in rolled)
    assert {"paperboy", "class president", "freshman", "student"} & set(jobs)


def test_a_blend_with_coming_of_age_keeps_the_teenage_range_and_finds_a_job():
    e, rolled = stories(["coming-of-age", "ghost story"], 40, seed=4)
    for st, _t in rolled:
        p = st["kept"]["protagonist"]
        assert 13 <= int(p["age"]) <= 19 and "teen" in steps.job_bands(e.features_of("job", p["job"])), p


def _session(home, genre, seed):
    from storywheel import store
    from storywheel.session import Session
    from conftest import make_engine
    st = store.new_story()
    st["kept"]["genre"] = {"genre": genre, "mood": "quiet"}
    from storywheel.mix import sync_base
    sync_base(st)
    s = Session(st, make_engine(home, seed=seed), ratings=None)
    s.enter(next(i for i, step in enumerate(s.steps) if step.key == "protagonist"))
    return s


@pytest.mark.parametrize("genre", ["thriller", "coming-of-age", "ghost story"])
def test_rerolling_age_or_job_alone_keeps_them_agreeing(home, genre):
    s = _session(home, genre, seed=8)
    e = s.engine
    for i in range(12):
        s.reroll_field("age" if i % 2 else "job")
        band = steps.band_of(s.fields["age"])
        assert band in steps.job_bands(e.features_of("job", s.fields["job"])), (s.fields["age"], s.fields["job"])


def test_the_builder_rolls_an_age_that_fits_a_retired_job(home):
    u = vault.create_universe("Old Town", ["thriller"])
    c = u.new_entity("character", "Ada Price", {"job": "retired colonel"})
    f = fill.Filler(u, fill.make_engine(u, seed=2))
    ages = {int(f.roll(c, "age")) for _ in range(15)}
    assert ages and all(a >= 60 for a in ages)
    c.fields["job"] = ""
    c.fields["age"] = "16"
    u2 = vault.create_universe("Young Town", ["coming-of-age"])
    d = u2.new_entity("character", "Bo Hart", {"age": "15"})
    g = fill.Filler(u2, fill.make_engine(u2, seed=3))
    for _ in range(10):
        job = g.roll(d, "job")
        assert "teen" in steps.job_bands(g.engine.features_of("job", job)), job


# --- blank fills -----------------------------------------------------------------------------------------------------------------

BLANK = [(re.compile(r"\S  +\S"), "two spaces"),
         (re.compile(r"\b(?:the|a|an)\s*(?:[,.;:!?]|$)", re.I), "an article followed by nothing"),
         (re.compile(r"\b(?:of|at|with|from|to) (?:the|a|an)?\s*[,.;:!?]", re.I), "a preposition followed by nothing"),
         (re.compile(r"\s[,.;:!?]"), "a space before punctuation"),
         (re.compile(r"\b(the|a|an) (?:the|a|an)\b"), "two articles"),
         (re.compile(r"\[[A-Za-z_]+\]"), "an unfilled slot"),
         (re.compile(r"\{|\}"), "a brace"),
         (re.compile(r"(?:^|\s)'s\b"), "a possessive of nothing"),
         (re.compile(r"^\s*$"), "an empty text")]


def blanks(text):
    return [name for rx, name in BLANK if rx.search(text)]


@pytest.mark.parametrize("structure", STRUCTURES)
@pytest.mark.parametrize("genre", GENRES)
def test_no_rendered_text_has_an_empty_fill(genre, structure):
    _e, rolled = stories([genre], 25, seed=21, structure=structures.get(structure).name)
    bad = [(t, blanks(t)) for st, _tr in rolled for t in texts_of(st) if blanks(t)]
    assert bad == [], bad[:4]


@pytest.fixture
def bare_story(home):
    """A universe whose protagonist has a name only: no rival, no job, no want (a Builder story before much is filled in)."""
    u = vault.create_universe("Thornwood", ["western"])
    u.new_entity("character", "Ann Lowell", {"role": "protagonist", "rival": "", "job": ""})
    return u


@pytest.mark.parametrize("structure", STRUCTURES)
@pytest.mark.parametrize("genre", ["western", "mystery", "horror", "sci-fi", "romance", "heist", "coming-of-age"])
def test_builder_beat_rolls_never_leave_a_blank(bare_story, genre, structure):
    u = bare_story
    shape = structures.get(structure)
    s = u.new_story(f"Tale {genre}", {"structure": shape.label, "genre": genre, "mood": "quiet"},
                    {shape.label: "\n\n".join(f"Beat {i}." for i in range(len(shape.beats)))})
    bad = []
    for seed in range(4):
        filler = fill.Filler(u, fill.make_engine(u, seed=seed))
        for b in shape.beats:
            text = outline.roll_beat(s, u, filler, b, [])
            if blanks(text) or "the  " in text:
                bad.append((b.key, text))
    assert bad == [], bad[:4]


def test_builder_character_rolls_never_leave_a_blank(bare_story):
    u = bare_story
    c = u.new_entity("character", "Bea Moss", {})
    f = fill.Filler(u, fill.make_engine(u, seed=5))
    for _ in range(6):
        for key in ("age", "job", "trait", "want", "need", "flaw", "secret"):
            text = f.roll(c, key)
            assert not blanks(text), (key, text)


def test_an_empty_kept_field_is_treated_as_missing():
    e = Engine(seed=1)
    story = {"kept": {"genre": {"genre": "western"}, "protagonist": {"name": "Ann Lowell", "rival": "", "job": "  "}}, "seeds": {}, "atoms": {}}
    from storywheel.mix import sync_base
    sync_base(story)
    c = steps.Ctx(e, story)
    assert c["rival"].strip() and c["job"].strip()


# --- technology and era ----------------------------------------------------------------------------------------------------------

def era_kind(e, st):
    feats = e.features_of("era", (st["kept"].get("setting") or {}).get("era", "")) or ()
    return "period" if "period" in feats else "modern" if "modern" in feats else None


@pytest.mark.parametrize("genre", GENRES)
def test_a_period_era_never_gets_modern_things_jobs_or_messages(genre):
    e, rolled = stories([genre], 60, seed=31)
    for st, trace in rolled:
        kind = era_kind(e, st)
        if kind is None:
            continue
        banned = "modern" if kind == "period" else "period"
        wrong = [(slot, text) for slot, _l, _t, text in trace if banned in (e.features_of(slot, text) or ())]
        assert wrong == [], (genre, st["kept"]["setting"]["era"], wrong[:4])


@pytest.mark.parametrize("genre", ["western", "fairy tale", "fantasy", "noir", "adventure"])
def test_period_genres_only_land_in_period_eras(genre):
    e, rolled = stories([genre], 40, seed=32)
    assert all(era_kind(e, st) == "period" for st, _t in rolled)


@pytest.mark.parametrize("genre", ["thriller", "heist", "coming-of-age"])
def test_modern_leaning_genres_mostly_land_in_modern_eras(genre):
    e, rolled = stories([genre], 80, seed=33)
    kinds = collections.Counter(era_kind(e, st) for st, _t in rolled)
    assert kinds["modern"] / len(rolled) >= 0.6, kinds


def test_the_same_era_in_two_lists_never_disagrees_about_technology(lib):
    seen = collections.defaultdict(set)
    for wl in lib.by_slot["era"]:
        for e in wl.entries:
            seen[e.text.lower()].add(tuple(sorted(f for f in (e.features or ()) if f in ("modern", "period"))))
    assert {t: v for t, v in seen.items() if len(v) > 1} == {}


def test_faker_jobs_count_as_modern():
    from storywheel import engine as engine_mod
    assert engine_mod.GENERATED_FEATURES["faker.job"] == ("modern",)


# --- repetition report -----------------------------------------------------------------------------------------------------------

def test_the_report_keeps_a_watch_list_between_4_and_5_standard_deviations():
    assert report.FAIL_SD == 5 and report.WATCH_SD == 4
    r = report.build_report(["western"], stories=40, seed=7)
    assert "watch" in r
    for ratio, n, expected, _lid, _text in r["watch"]:
        assert expected + 4 * expected ** 0.5 < n <= expected + 5 * expected ** 0.5
    assert "Watch (4 to 5 standard deviations" in report.format_report(r)


# --- every genre is complete (Part C) --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("genre", GENRES)
def test_every_genre_has_a_profile_neighbors_a_core_vocabulary_and_an_age_range(lib, genre):
    import json
    from storywheel import genrefit, library as lib_mod
    from storywheel.mix import Mix
    doc = json.loads((lib_mod.DATA / "genres.json").read_text(encoding="utf-8"))
    assert lib.profiles[genre][genre] >= 3
    assert doc["_neighbors"].get(genre), genre
    words = genrefit.core_words()[genre]
    assert len(words["a"]) + len(words["v"]) >= 40
    lo, hi = Mix({"base": [genre], "exclude_tags": [], "exclude_lists": [], "boost": {}}, lib).age_range()
    assert 13 <= lo < hi <= 80
    eras = [e for wl in lib.by_slot["era"] if genre in wl.tags for e in wl.entries]
    assert len(eras) >= 4
    if lib.tech.get(genre):
        other = "modern" if lib.tech[genre] == "period" else "period"
        assert sum(other not in (e.features or ()) for e in eras) / len(eras) >= 0.7, genre      # (a genre's eras mostly match its technology)
