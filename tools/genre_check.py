"""One table that checks every genre at once (batch 15): fidelity, repetition (failures and watch items), lint, frame sharing, era and
technology, ages, core vocabulary and neighbors. Prints markdown for REPORT.md.

    python tools/genre_check.py [--stories 200] [--genres "western,noir"]

Run it with STORYWHEEL_HOME and STORYWHEEL_LIBRARY pointing at a temporary folder (CLAUDE.md)."""
import argparse
import difflib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storywheel import genrefit, report, steps                     # noqa: E402
from storywheel import library as lib_mod                          # noqa: E402
from storywheel.engine import Engine                               # noqa: E402
from storywheel.library import Library                             # noqa: E402
from storywheel.mix import Mix, sync_base                          # noqa: E402
from storywheel.sample import build_story                          # noqa: E402

GENRES = ["western", "fairy tale", "comedy", "fantasy", "mystery", "horror", "sci-fi", "romance", "ghost story", "noir", "thriller",
          "heist", "adventure", "coming-of-age"]
FLAVORED = ["first_name", "last_name", "job", "place", "landmark", "thing", "someone", "disaster"]


def frames(lib):
    out = {g: set() for g in GENRES}
    for wl in lib.lists.values():
        if wl.is_template:
            for g in GENRES:
                if g in wl.tags:
                    out[g].update(e.text.strip() for e in wl.entries)
    return out


def sharing(fr, a):
    if not fr[a]:
        return None, None
    worst = max(len(fr[a] & fr[b]) / len(fr[a]) for b in GENRES if b != a and fr[b])
    others = [o for g in GENRES if g != a for o in fr[g]]
    near = 0
    for f in fr[a]:
        for o in others:
            if abs(len(o) - len(f)) > 40:
                continue
            sm = difflib.SequenceMatcher(None, f, o)
            if sm.real_quick_ratio() >= 0.93 and sm.quick_ratio() >= 0.93 and sm.ratio() >= 0.93:
                near += 1
                break
    return worst, near / len(fr[a])


def check(genre, lib, stories):
    e = Engine(seed=2024)
    e.trace = []
    rolled = []
    for _ in range(stories):
        before = len(e.trace)
        st = build_story(e, [genre])
        rolled.append((st, e.trace[before:]))
    story = {"kept": {"genre": {"genre": genre}}}
    sync_base(story)
    mix = Mix.for_story(story, e.library)
    flavor = {t for t, w in mix.weights().items() if w > 0 and t not in ("general", "modern")}
    hits = total = 0
    for slot, _l, tags, _t in e.trace:
        if slot in FLAVORED:
            total += 1
            hits += bool(tags & flavor)
    age_bad = era_bad = 0
    for st, trace in rolled:
        p = st["kept"]["protagonist"]
        if steps.band_of(p["age"]) not in steps.job_bands(e.features_of("job", p["job"])):
            age_bad += 1
        feats = e.features_of("era", st["kept"]["setting"]["era"]) or ()
        kind = "period" if "period" in feats else "modern" if "modern" in feats else None
        if kind:
            banned = "modern" if kind == "period" else "period"
            era_bad += any(banned in (e.features_of(s, t) or ()) for s, _l, _g, t in trace)
    r = report.build_report([genre], stories=stories, seed=101)
    return {"fidelity": hits / max(total, 1), "heavy": len(r["heavy_lines"]), "flagged": r["flagged"], "watch": r["watch"],
            "lint": len([p for p in r["lint"] if p[0].split("/")[-1].startswith(genre.replace(" ", "-"))]),
            "age_bad": age_bad, "era_bad": era_bad}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stories", type=int, default=200)
    ap.add_argument("--genres", default="")
    a = ap.parse_args(argv)
    genres = [g.strip() for g in a.genres.split(",") if g.strip()] or GENRES
    lib = Library.load()
    doc = json.loads((lib_mod.DATA / "genres.json").read_text(encoding="utf-8"))
    core = genrefit.core_words()
    fr = frames(lib)
    rows, watch = [], []
    for g in genres:
        c = check(g, lib, a.stories)
        worst, near = sharing(fr, g)
        lo, hi = Mix({"base": [g], "exclude_tags": [], "exclude_lists": [], "boost": {}}, lib).age_range()
        words = len(core.get(g, {}).get("a", [])) + len(core.get(g, {}).get("v", []))
        rows.append(f"| {g} | {c['fidelity']:.0%} | {c['heavy']} | {len(c['flagged'])} | {len(c['watch'])} | {c['lint']} | "
                    f"{'-' if worst is None else f'{worst:.0%}'} | {'-' if near is None else f'{near:.0%}'} | {lib.tech.get(g, '-')} | "
                    f"{c['era_bad']} | {lo}-{hi} | {c['age_bad']} | {words} | {', '.join(doc['_neighbors'].get(g, [])) or '-'} |")
        watch += [(g, w) for w in c["watch"]]
    print("| Genre | Own material (8 slots) | Lines 5+ times | Repeats (5 SD) | Watch (4-5 SD) | Lint | Most frames shared | Near copies | "
          "Technology | Era breaks | Ages | Age breaks | Core words | Neighbors |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    print("\n".join(rows))
    print()
    print("Watch items (between 4 and 5 standard deviations above chance; not failures):")
    print()
    if not watch:
        print("- none")
    for g, (ratio, n, expected, lid, text) in watch:
        print(f"- {g}: `{lid}` \"{text}\" picked {n} times against {expected:.1f} expected ({ratio:.1f}x)")


if __name__ == "__main__":
    main()
