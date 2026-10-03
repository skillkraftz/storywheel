"""Story words: the names and the odd words a manuscript actually uses, built from the text itself.

`analyze` reads one story's manuscript (or every story in the universe) and reports
  * names     the universe's entity names, and how often each (and each of its words) is written
  * unknown   words the dictionary does not know and nothing in the universe explains: made-up names, places, jargon, typos
  * variants  things that look like the same name written two ways ("Glasswater" and "Glass Water") or a near-miss of a more common form
with counts and where each occurs. `add_to_spelling` puts a word on the universe's spelling list (the file the Writer reads).
Nothing is changed by looking."""
import difflib
import re
from collections import Counter, defaultdict
from pathlib import Path

from . import dictionary, overused, vault

WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*[A-Za-z]|[A-Za-z]")
MAX_WHERE = 12


class Form:
    """One spelling of a word or name: counted case-insensitively, shown as it is most often written."""
    def __init__(self, key):
        self.key = key
        self.cases = Counter()
        self.where = []
        self.count = 0

    def add(self, text, where):
        self.cases[text] += 1
        self.count += 1
        if len(self.where) < MAX_WHERE:
            self.where.append(where)

    @property
    def text(self):
        return self.cases.most_common(1)[0][0]


class Item:
    def __init__(self, kind, text, count, where, note="", entity=None, related=None):
        self.kind, self.text, self.count, self.where = kind, text, count, where
        self.note, self.entity, self.related = note, entity, related      # related: the form this one probably is (or is a variant of)

    def __repr__(self):
        return f"Item({self.kind}, {self.text!r}, {self.count})"


def strip_possessive(word):
    w = word.replace("’", "'")
    return w[:-2] if w.lower().endswith("'s") else w


def _where(path, line_no, col, line, scene):
    return {"file": str(path), "line": line_no, "col": col, "scene": scene, "text": overused.snippet(line, col)}


def listed_words(universe):
    """Words already on the universe's spelling lists (what you added, and the generated names)."""
    out = set()
    for name in ("en.utf-8.add", "names.utf-8.add"):
        p = universe.path / "spell" / name
        if p.exists():
            out |= {ln.split("/")[0].strip().lower() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()}
    return out


def add_to_spelling(universe, word):
    """Add a word (and its possessive) to the universe's own spelling list. Returns (path, True if it was new)."""
    word = strip_possessive(word.strip())
    folder = universe.path / "spell"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "en.utf-8.add"
    have = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    lowered = {ln.split("/")[0].strip().lower() for ln in have}
    new = word.lower() not in lowered
    if new:
        have += [word, word + "'s"]
        vault._write(path, "\n".join(have) + "\n")
    return path, new


def _known(db, word):
    return bool(dictionary.base_words(db, word))


def _stories(universe, story):
    return [story] if story is not None else universe.stories()


def scan(universe, story=None):
    """({lowercase word: Form}, {lowercase 'word word': Form} for neighbouring capitalized words, total words)."""
    forms, pairs, total = {}, {}, 0
    for st in _stories(universe, story):
        for path in st.files():
            text = vault.Story._read(st, path)
            scenes = vault.parse_scenes(text)
            for n, line in enumerate(text.split("\n"), 1):
                if vault.marker_label(line.strip()) is not None:
                    continue
                scene = next((sc for sc in scenes if sc["start"] <= n <= sc["end"]), None)
                title = (scene["label"] or f"Scene {scenes.index(scene) + 1}") if scene else ""
                prev = None
                for m in WORD.finditer(line):
                    word = strip_possessive(m.group(0))
                    total += 1
                    key = word.lower()
                    here = _where(path, n, m.start(), line, title)
                    forms.setdefault(key, Form(key)).add(word, here)
                    if prev and word[:1].isupper() and prev[0][:1].isupper() and line[prev[1]:m.start()].strip() == "":
                        pk = f"{prev[0].lower()} {key}"
                        pairs.setdefault(pk, Form(pk)).add(f"{prev[0]} {word}", here)
                    prev = (word, m.end())
    return forms, pairs, total


def _compact(text):
    return re.sub(r"[\s'’-]+", "", text.lower())


def distance(a, b):
    """Edit distance (insert, delete, change one letter)."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def near_miss(a, b):
    """Could these be the same word spelled two ways? Same first letter, and one slip in a short word or two in a longer one."""
    if a == b or a[:1] != b[:1] or min(len(a), len(b)) < 4:
        return False
    d = distance(a, b)
    return d <= 1 or (d <= 2 and min(len(a), len(b)) >= 5 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.7)


def analyze(universe, story=None, db=None):
    """The report for a story (or the whole universe): {"items": [Item], "words": N, "dictionary": bool}."""
    try:
        db = db or dictionary.connect()
    except dictionary.DictionaryMissing:
        db = None
    forms, pairs, total = scan(universe, story)
    listed = listed_words(universe)
    entities = universe.entities()
    name_to_entity = {}
    entity_words = set()
    for e in entities:
        name = (e.name or "").strip()
        if not name:
            continue
        name_to_entity[name.lower()] = e
        entity_words |= {w.lower() for w in WORD.findall(name)}
    items = []

    # --- names: every entity, with how often it appears (whole name, or any of its words for a person) -----------------------
    counted = {}
    for lname, e in name_to_entity.items():
        full = pairs.get(lname) if " " in lname else forms.get(lname)
        count = full.count if full else 0
        where = list(full.where) if full else []
        if e.type == "character":
            for w in WORD.findall(e.name):
                f = forms.get(w.lower())
                if f and w.lower() not in ("the", "of", "a", "an"):
                    count += f.count if f is not full else 0
                    where += f.where if f is not full else []
        counted[lname] = (count, where[:MAX_WHERE])
        items.append(Item("name", e.name, count, where[:MAX_WHERE], note=e.type, entity=e))

    # --- unknown words: not in the dictionary, not a name, not already on the spelling list ------------------------------------
    unknown = []
    for key, f in forms.items():
        if len(key) < 3 or key in entity_words or key in listed or key in overused.STOPWORDS:
            continue
        if db is not None and _known(db, key):
            continue
        if db is None:
            break
        unknown.append(f)
    unknown.sort(key=lambda f: (-f.count, f.key))
    unknown_keys = {f.key for f in unknown}

    # --- look-alikes -------------------------------------------------------------------------------------------------------------
    compact_to_form = defaultdict(list)       # "glasswater" -> every spelling that squeezes to it (words, pairs, entity names)
    for key, f in forms.items():
        if key in unknown_keys or key in entity_words:
            compact_to_form[_compact(key)].append(("word", f.text, f.count))
    for key, f in pairs.items():
        compact_to_form[_compact(key)].append(("pair", f.text, f.count))
    for lname, e in name_to_entity.items():
        compact_to_form[_compact(lname)].append(("entity", e.name, counted[lname][0]))
    variant_of = {}
    for compact, spellings in compact_to_form.items():
        texts = {s[1].lower() for s in spellings}
        if len(texts) > 1:
            best = max(spellings, key=lambda s: (s[0] == "entity", s[2]))
            for kind, text, count in spellings:
                if text.lower() != best[1].lower():
                    variant_of[text.lower()] = best[1]
    pool = [(f.key, f.count) for f in unknown] + [(w, forms[w].count) for w in entity_words if w in forms]
    pool_words = [w for w, _ in pool]
    count_of = dict(pool)
    for f in unknown:
        if f.key in variant_of:
            continue
        for other in sorted(pool_words, key=lambda w: (w not in entity_words, -count_of[w], w)):
            more = (other in entity_words) or count_of[other] > f.count or (count_of[other] == f.count and other < f.key)
            if more and near_miss(f.key, other):
                variant_of[f.key] = forms[other].text
                break

    for f in unknown:
        rel = variant_of.get(f.key)
        note = f"looks like {rel}" if rel else ""
        items.append(Item("variant" if rel else "unknown", f.text, f.count, f.where, note=note, related=rel))
    for key, f in pairs.items():
        rel = variant_of.get(key)
        if rel:
            items.append(Item("variant", f.text, f.count, f.where, note=f"looks like {rel}", related=rel))
    order = {"variant": 0, "name": 1, "unknown": 2}
    items.sort(key=lambda i: (order[i.kind], -i.count, i.text.lower()))
    return {"items": items, "words": total, "dictionary": db is not None}


def describe(item):
    """A one-line description for a list row."""
    kinds = {"name": "name", "unknown": "not in dictionary", "variant": "look-alike"}
    extra = f"  ({item.note})" if item.note else ""
    return f"{item.text}  ×{item.count}  {kinds[item.kind]}{extra}"
