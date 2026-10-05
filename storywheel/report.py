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
_PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z_0-9]*(?::[^{}]*|\|[^{}]*)?\}")   # {x}, {X:req}, {lies|lie}
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
    for wl in library.lists.values():                   # a placeholder nothing can fill would leak into the text
        if wl.is_template:
            from . import frames as _frames
            for e in wl.entries:
                for name in _frames.unknown_names(library, e.text):
                    problems.append((wl.id, e.text, f"nothing can fill {{{name}}}"))
    problems += reframe_problems(library)
    problems += grammar_problems(library)
    problems += sentence_problems(library)
    from . import frames
    problems += frames.lint(library)                    # can every frame be filled?
    return problems


# Sentence-level problems found by reading samples (batch 13): each is a shape that reads wrongly whatever the atoms are.
_FEAR_FEELING = re.compile(r"\b(?:fear|fears|feared|afraid of|dread|dreads|dreaded) \{FEELING")                  # "still fears fear"
_THING_AT_PLACE = re.compile(r"\{(?:THING|PRIZE)[^}]*\} (?:at|from|in|inside|near|out of) \{landmark")          # "wants a music box at the cellar steps"
ANIMALS = {"mule", "horse", "mare", "stallion", "colt", "pony", "donkey", "dog", "hound", "puppy", "cat", "kitten", "raven", "crow", "owl", "wolf", "fox", "hen", "rooster",
           "goat", "sheep", "lamb", "ox", "bull", "cow", "calf", "pig", "hawk", "falcon", "eagle", "bear", "snake", "rat", "mouse", "cattle", "stag", "deer", "hare", "rabbit", "sparrow",
           "dove", "swan", "heron", "toad", "frog", "spider", "bee", "moth", "horses", "dogs", "cats", "ravens", "crows", "wolves", "sheep"}
ENCLOSURE_VERBS = ("locked up", "locks up", "swept", "sweeps", "sealed off", "seals off", "tidied", "dusted", "aired", "boarded up", "boards up", "shut up", "bolted", "barred", "closed up")
ADVERB_ENDINGS = {"twice", "again", "aloud", "quietly", "carefully", "slowly", "quickly", "together", "gently", "silently", "once", "thrice"}
INANIMATE_VERBS = ("opened", "unlocked", "wound", "mended", "polished", "dusted", "cleaned", "burned", "unwrapped", "oiled", "forged", "copied", "sealed", "salted", "locked away",
                   "open", "burn", "mend", "forge", "copy", "restore", "dusts", "polishes", "winds", "opens", "burns", "keeps wrapped", "tucked away", "folded", "stowed away")
VERB_SLOTS = ("act_person", "act_thing", "act_place", "act_event", "act_message", "do_person", "do_thing", "habit_person", "habit_place", "habit_thing")


def sentence_problems(library):
    """Shapes that read badly however they are filled: a fear verb before {FEELING} (the feeling may be fear), a thing or prize said to be at a landmark,
    an animal that is not marked living, an enclosing verb that can take an open place, and a verb that ends in an adverb ("read twice" + object)."""
    out = []
    for wl in library.lists.values():
        if wl.is_template:
            for e in wl.entries:
                if _FEAR_FEELING.search(e.text):
                    out.append((wl.id, e.text, "a fear verb before {FEELING}: the feeling can be fear (\"fears fear\")"))
                if wl.slot == "want" and _THING_AT_PLACE.search(e.text):
                    out.append((wl.id, e.text, "a want placed at a landmark reads as a location (\"a music box at the cellar steps\")"))
            continue
        if wl.generator:
            continue
        for e in wl.entries:
            words = set(re.findall(r"[a-z']+", e.text.lower()))
            if wl.slot == "thing" and (words & ANIMALS) and "living" not in (e.features or ()) and not re.search(r"\b(?:statue|figurine|carving|carved|painting|mask|skull|bone|pelt|hide|feather|egg|nest|shoe|collar|bell|whistle|saddle|blanket|stew|inflatable|pantomime|rocking|stuffed|trap|poison|brand|ledger|oil|cricket|wooden|toy)\b", e.text.lower()):
                out.append((wl.id, e.text, "an animal that is not marked living (verbs for objects would apply to it)"))
            if wl.slot in ("act_place", "habit_place") and e.text.lower().startswith(ENCLOSURE_VERBS):
                obj = set(e.object or ()) | set(wl.object or ()) if hasattr(wl, "object") else set(e.object or ())
                if not obj & {"built", "indoor"}:
                    out.append((wl.id, e.text, "an enclosing verb that does not require a built or indoor place (\"locked up the moor\")"))
            if wl.slot in ("act_thing", "do_thing", "habit_thing") and e.text.lower() in INANIMATE_VERBS:
                obj = set(e.object or ())
                if not obj & {"!living", "paper", "built"}:
                    out.append((wl.id, e.text, "a verb for objects that does not rule out an animal (\"opened a mule\"): give it object !living"))
            if wl.slot in VERB_SLOTS and e.text.split() and e.text.split()[-1].lower() in ADVERB_ENDINGS:
                out.append((wl.id, e.text, "a verb ending in an adverb sits before its object (\"read twice a letter\")"))
    return out


# Phrase shapes that read badly whatever the atoms are (found by scanning hundreds of samples):
_PREP_BEFORE_MANNER = re.compile(r"\b(from|of|to|with|for|at|by|in|on|about|after|over|under|through|before|during|and|but|or|than|as) \{MANNER\b")
_PRIZE_AT_PLACE = re.compile(r"\{PRIZE[^}]*\} (?:at|in|inside|near|from) \{landmark")


def grammar_problems(library):
    """Templates whose wording clashes with whatever fills them: a manner phrase ("in the old tongue") after a preposition
    ("a favor from in the old tongue"), or a prize ("a fortress") said to be at a landmark. A manner that suits only some
    verbs is a restricted feature (speech, carrying, feeling) that a frame has to ask for."""
    out = []
    for wl in library.lists.values():
        if not wl.is_template:
            continue
        for e in wl.entries:
            if _PREP_BEFORE_MANNER.search(e.text):
                out.append((wl.id, e.text, "a manner phrase follows a preposition"))
            if _PRIZE_AT_PLACE.search(e.text):
                out.append((wl.id, e.text, "a prize is placed at a landmark (use a {THING} for something that can be there)"))
    from . import frames
    asked = set()
    for wl in library.lists.values():
        if wl.is_template:
            for e in wl.entries:
                for m in re.finditer(r"\{[A-Z_]+:([^}]*)\}", e.text):
                    asked.update(a.strip().lstrip("!") for r in m.group(1).split(",") for a in r.split("|"))
    for wl in library.lists.values():
        for e in (wl.entries if not wl.is_template else ()):
            for f in frames.RESTRICTED & set(e.features or ()):
                if f not in asked:
                    out.append((wl.id, e.text, f"restricted feature '{f}' that no frame asks for (the atom can never be drawn)"))
    return out


REFRAME_ATOMS = {"motive", "vice", "value", "feeling", "manner"}      # abstractions: no new facts
ESTABLISHED = {"want", "need", "flaw", "secret", "rumor", "rival", "landmark", "motif"}


def reframe_problems(library):
    """Templates for a reframing beat (kishotenketsu's ten) must lean on what the story has
    already established, and introduce no fresh person, object or event."""
    from . import structures
    slots = {b.slot for st in structures.registry().values() for b in st.beats if b.reframe}
    out = []
    for wl in library.lists.values():
        if wl.is_template and wl.slot in slots:
            for e in wl.entries:
                names = [m.group(0).strip("{}").split(":")[0].split("|")[0] for m in _PLACEHOLDER.finditer(e.text)]
                fresh = [n for n in names if n.isupper() and n.lower() not in REFRAME_ATOMS]
                if fresh:
                    out.append((wl.id, e.text, f"reframe template introduces a fresh fact ({', '.join(fresh)})"))
                if not any(n.startswith("the_") or n in ESTABLISHED for n in names):
                    out.append((wl.id, e.text, "reframe template refers to nothing already established"))
    return out


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

    # Frames restrict what a slot may take (only 'stows' verbs go with a hiding place), so the
    # fair share is among the entries that were used at all, not the whole list.
    active = defaultdict(float)
    for (lid, text), n in counts.items():
        active[lid] += shares.get((lid, text), 0.0)
    rows = []
    for (lid, text), n in counts.items():
        share = shares.get((lid, text))
        if not share:
            continue                                     # invented names, generated words
        expected = per_list[lid] * share / (active[lid] or 1.0)
        rows.append((n / expected, n, expected, lid, text))
    # (a rare entry picked 5 times when 1 was expected is noise, not a pattern: it must also be 5 standard deviations above what chance gives: with hundreds of rare entries, 4 flags one by luck about once a run)
    flagged = [r for r in rows if r[0] > factor and r[1] >= min_count and r[1] > r[2] + 5 * r[2] ** 0.5]
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
