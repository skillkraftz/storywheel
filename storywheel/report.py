"""
Repetition report: are the stories assembled from parts, or dealt from a deck?

Rolls a batch of stories (nothing is saved) and measures:

* the entries picked most often against their fair share. The fair share of an
  entry is its list's picks times its weight over the list's total weight, so
  genre-tagged entries are not blamed for being favored. Anything picked more
  than `factor` times its share is flagged;
* the most repeated rendered lines, with the character's name, the place and
  other story fields blanked out, so "X counted the money twice" shows up as the
  same line wherever it appears;
* frozen templates (fewer than two slots) and over-long atoms (too many words),
  which the lint test also checks.

    python tools/repetition_report.py western "fairy tale" -n 200 --seed 101
"""
import re
from collections import Counter, defaultdict

from .engine import Engine
from .mix import Mix, sync_base
from .sample import build_story
from .steps import public

MAX_ATOM_WORDS = 5
MIN_TEMPLATE_SLOTS = 2
MAX_FIXED_RUN = 6          # a template may not hold more than this many words in a row without a slot
_PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z_0-9]*\}")
# Atoms are reused in many sentences, so they can't know who "their" would mean. Exception:
# losses, which are always things the protagonist lost ("lost their house").
_PRONOUNS = {"they", "them", "their", "theirs", "themselves", "he", "she", "him", "her", "his", "hers"}
_PRONOUN_OK_SLOTS = {"loss"}
# An atom is a noun phrase or a verb, not a clause: no clause punctuation, no clause-making words.
_CLAUSE_PUNCT = re.compile(r"[,;:.!?]")
_CLAUSE_WORDS = {"who", "whom", "whose", "that", "which", "because", "while", "when", "until", "although",
                 "though", "unless", "if", "then", "so"}


def slot_count(text):
    return len(_PLACEHOLDER.findall(text))


def word_count(text):
    return len(_PLACEHOLDER.sub("X", text).split())


def longest_fixed_run(text):
    """The most words in a row that are not slots: the 'frozen' part of a template."""
    return max((len([w for w in part.split() if re.search(r"\w", w)])      # punctuation alone isn't a word
                for part in _PLACEHOLDER.split(text)), default=0)


def lint(library):
    """Problems with the data itself: [(list id, entry text, what is wrong)]."""
    problems = []
    for wl in library.lists.values():
        is_template = wl.is_template
        for e in wl.entries:
            if is_template:
                if slot_count(e.text) < MIN_TEMPLATE_SLOTS:
                    problems.append((wl.id, e.text, f"template has {slot_count(e.text)} slot(s)"))
                run = longest_fixed_run(e.text)
                if run > MAX_FIXED_RUN:
                    problems.append((wl.id, e.text, f"template has {run} fixed words in a row"))
            else:
                n = word_count(e.text)
                if n > MAX_ATOM_WORDS:
                    problems.append((wl.id, e.text, f"atom has {n} words"))
                if _CLAUSE_PUNCT.search(_PLACEHOLDER.sub("X", e.text)):
                    problems.append((wl.id, e.text, "atom contains clause punctuation"))
                words = set(re.findall(r"[a-z']+", e.text.lower()))
                if wl.slot not in _PRONOUN_OK_SLOTS and (_PRONOUNS & words):
                    problems.append((wl.id, e.text, f"atom has a pronoun ({', '.join(sorted(_PRONOUNS & words))})"))
                clause = _CLAUSE_WORDS & words
                if clause:
                    problems.append((wl.id, e.text, f"atom is a clause ({', '.join(sorted(clause))})"))
    return problems


def roll_batch(genres, stories, seed, structure=None, engine=None):
    engine = engine or Engine(seed=seed)
    engine.trace = []
    batches = [build_story(engine, genres, structure=structure) for _ in range(stories)] \
        if structure else [build_story(engine, genres) for _ in range(stories)]
    return engine, batches


def fair_share(engine, genres):
    """{(list id, text): expected fraction of its list's picks}, given the genre mix."""
    story = {"kept": {"genre": {"genre": " / ".join(genres)}}}
    sync_base(story)
    mix = Mix.for_story(story, engine.library)
    weights = mix.weights()
    out = {}
    for wl in engine.library.lists.values():
        if wl.generator or not wl.entries:
            continue
        ws = [mix.entry_weight(e, weights) for e in wl.entries]
        total = sum(ws) or 1.0
        for e, w in zip(wl.entries, ws):
            out[(wl.id, e.text)] = w / total
    return out


def normalize(line, story):
    """Blank out the parts of a rendered line that are supposed to differ."""
    k = story["kept"]
    names = []
    p = k.get("protagonist", {})
    if p.get("name"):
        names += [p["name"], p["name"].split()[0], p["name"].split()[-1]]
    s = k.get("setting", {})
    names += [s.get(f) for f in ("place", "landmark") if s.get(f)]
    for n in sorted(set(filter(None, names)), key=len, reverse=True):
        line = re.sub(re.escape(n) + r"(?:'s)?", "X", line)
    return line


def build_report(genres, stories=200, seed=101, top=15, factor=3.0, min_count=5, structure=None):
    engine, batch = roll_batch(genres, stories, seed, structure)
    shares = fair_share(engine, genres)
    counts = Counter((lid, text) for _slot, lid, _tags, text in engine.trace)
    per_list = Counter()
    for (lid, _t), n in counts.items():
        per_list[lid] += n

    rows = []
    for (lid, text), n in counts.items():
        share = shares.get((lid, text))
        if not share:
            continue                                     # invented names, generated words
        expected = per_list[lid] * share
        rows.append((n / expected, n, expected, lid, text))
    flagged = [r for r in rows if r[0] > factor and r[1] >= min_count]
    flagged.sort(reverse=True)

    lines = Counter()
    where = {}
    for story in batch:
        for step_key in ("premise", "spine", "twist"):
            for key, text in public(story["kept"].get(step_key) or {}).items():
                norm = normalize(text, story)
                lines[norm] += 1
                where[norm] = f"{step_key}.{key}"
    repeated = [(n, t, where[t]) for t, n in lines.most_common(top) if n >= 2]

    problems = lint(engine.library)
    return {"engine": engine, "stories": stories, "genres": genres, "seed": seed,
            "picks": len(engine.trace), "rows": rows, "flagged": flagged,
            "top_entries": sorted((r for r in rows if len(engine.library.lists[r[3]].entries) >= 15),
                                  key=lambda r: -r[1])[:top],
            "heavy_lines": [(t, n) for t, n in lines.items() if n >= 5],
            "lines_total": sum(lines.values()),
            "repeated": repeated, "lint": problems}


def format_report(r, top=15):
    out = [f"Repetition report: {' / '.join(r['genres'])}, {r['stories']} stories, seed {r['seed']}, "
           f"{r['picks']} picks", ""]
    heavy = r["heavy_lines"]
    out.append(f"Headline: {len(heavy)} distinct rendered lines appear 5+ times "
               f"({sum(n for _t, n in heavy)} of {r['lines_total']} lines); "
               f"{len(r['flagged'])} entries picked over 3x their fair share")
    out.append("")
    out.append("Most picked entries in lists of 15+ (count, multiple of fair share, list):")
    for ratio, n, expected, lid, text in r["top_entries"][:top]:
        flag = "  <-- over 3x" if ratio > 3 and n >= 5 else ""
        out.append(f"  {n:4d}  {ratio:5.1f}x  {lid:28s} {text[:60]}{flag}")
    out += ["", f"Entries over 3x their fair share (and picked 5+ times): {len(r['flagged'])}"]
    for ratio, n, expected, lid, text in r["flagged"][:top]:
        out.append(f"  {ratio:5.1f}x  {n:4d} vs {expected:5.1f} expected  {lid}  {text[:56]}")
    out += ["", "Most repeated rendered lines (names and places blanked, 2+ times):"]
    for n, text, where in r["repeated"]:
        out.append(f"  {n:4d}x  [{where}] {text[:90]}")
    if not r["repeated"]:
        out.append("  (none)")
    frozen = [p for p in r["lint"] if "slot" in p[2] or "fixed words" in p[2]]
    long_atoms = [p for p in r["lint"] if p[2].startswith("atom")]
    out += ["", f"Frozen templates (fewer than {MIN_TEMPLATE_SLOTS} slots, or {MAX_FIXED_RUN}+ fixed words in a row): {len(frozen)}"]
    by_list = Counter(p[0] for p in frozen)
    out += [f"  {lid}: {n}" for lid, n in by_list.most_common(12)]
    out += [f"Atoms that are too long or are clauses (more than {MAX_ATOM_WORDS} words, punctuation, clause words): {len(long_atoms)}"]
    by_list = Counter(p[0] for p in long_atoms)
    out += [f"  {lid}: {n}" for lid, n in by_list.most_common(12)]
    return "\n".join(out)
