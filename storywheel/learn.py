"""Words worth learning: not everyday, not obscure. The pool is WordNet's single words; how common each is comes from the
`wordfreq` package (offline; Zipf scale: 7 is "the", 5 is "house", 3.5 is "lantern", 2.7 is "serendipity", 1.2 is "sesquipedalian").

    batch(...)       a fresh set of words (never one already seen), filtered by difficulty, part of speech and subject
    MyWords          what you marked: Known (never offered again) or Learning (your list, with definitions)
"""
import json
import random
import re

from . import dictionary, paths, tools

DIFFICULTY = {          # name: (lowest, highest Zipf frequency)  -- the higher, the more everyday
    "any": (1.5, 3.8), "uncommon": (3.0, 3.8), "rare": (2.3, 3.0), "very rare": (1.5, 2.3),
}
POS = {"noun": ("n",), "verb": ("v",), "adjective": ("a", "s"), "adverb": ("r",)}

# friendly names for WordNet's lexicographer files (the "subject area" of a meaning)
SUBJECT_NAMES = {
    "noun.animal": "Animals", "noun.plant": "Plants", "noun.food": "Food and drink", "noun.body": "The body",
    "noun.person": "People", "noun.group": "Groups and organizations", "noun.artifact": "Things people make",
    "noun.object": "Natural things and places", "noun.location": "Places", "noun.substance": "Materials",
    "noun.cognition": "Thinking and knowing", "noun.communication": "Words, writing and art", "noun.feeling": "Feelings",
    "noun.motive": "Reasons and aims", "noun.event": "Events", "noun.act": "Actions", "noun.phenomenon": "Natural events",
    "noun.process": "Processes", "noun.state": "Conditions", "noun.attribute": "Qualities", "noun.quantity": "Amounts and measures",
    "noun.possession": "Owning and money", "noun.relation": "Relations", "noun.shape": "Shapes", "noun.time": "Time",
    "verb.motion": "Moving", "verb.contact": "Touching and doing", "verb.communication": "Saying and writing",
    "verb.cognition": "Thinking", "verb.emotion": "Feeling", "verb.change": "Changing", "verb.creation": "Making",
    "verb.perception": "Seeing, hearing, sensing", "verb.social": "Social acts", "verb.possession": "Giving and taking",
    "verb.competition": "Competing and fighting", "verb.consumption": "Eating and using", "verb.body": "Body acts",
    "verb.stative": "Being and having", "verb.weather": "Weather", "adj.all": "Describing words", "adv.all": "Adverbs",
}


class WordfreqMissing(Exception):
    pass


MISSING = tools.missing("wordfreq", "(or  pip install wordfreq)")


def zipf(word):
    try:
        from wordfreq import zipf_frequency
    except ImportError:
        raise WordfreqMissing(MISSING)
    return zipf_frequency(word, "en")


def simple_definition(defn, limit=110):
    """One short line from a WordNet gloss: the first clause, without a parenthetical, trimmed."""
    text = re.sub(r"\s*\([^)]*\)", "", defn or "").split(";")[0].strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def subjects(db=None):
    """[(label, key)] for the subject filter: the broad kinds of meaning, then the most used subject areas (law, medicine, music...)."""
    db = db or dictionary.connect()
    present = {lex for (lex,) in db.execute("select distinct lex from synsets where lex != ''")}
    out = [("Any subject", None)]
    out += sorted(((SUBJECT_NAMES[k], k) for k in present if k in SUBJECT_NAMES), key=lambda t: t[0].lower())
    rows = db.execute("select target, count(*) c from rels where kind = 'domain_topic' group by target having c >= 8 order by c desc limit 30").fetchall()
    topics = []
    for target, _c in rows:
        members = dictionary._members(db, target)
        if members:
            topics.append((f"Subject: {members[0]}", f"topic:{target}"))
    return out + sorted(topics, key=lambda t: t[0].lower())


def batch(n=20, difficulty="any", pos=None, subject=None, exclude=(), rng=None, db=None):
    """A fresh set of words worth learning: [{word, pos, definition, zipf, subject}], none in `exclude` (lowercase words).
    Fewer than n come back when the filters run out of words."""
    db = db or dictionary.connect()
    rng = rng or random
    low, high = DIFFICULTY.get(difficulty, DIFFICULTY["any"])
    tags = POS.get(pos or "", ())
    sql = ("select w.w, s.pos, y.defn, y.lex, y.id from senses s join words w on w.id = s.word_id join synsets y on y.id = s.synset_id "
           "where s.ord = 0 and w.w not glob '*[^a-z]*' and length(w.w) >= 4")
    args = []
    if tags:
        sql += " and s.pos in (%s)" % ",".join("?" * len(tags))
        args += list(tags)
    if subject and subject.startswith("topic:"):
        sql += " and y.id in (select synset_id from rels where kind = 'domain_topic' and target = ?)"
        args.append(int(subject[6:]))
    elif subject:
        sql += " and y.lex = ?"
        args.append(subject)
    rows = db.execute(sql, args).fetchall()
    rng.shuffle(rows)
    skip = {w.lower() for w in exclude}
    out, seen = [], set()
    for word, p, defn, lex, _sid in rows:
        if word in skip or word in seen:
            continue
        z = zipf(word)
        if not (low <= z < high):
            continue
        seen.add(word)
        out.append({"word": word, "pos": {"n": "noun", "v": "verb", "a": "adjective", "s": "adjective", "r": "adverb"}.get(p, p),
                    "definition": simple_definition(defn), "zipf": round(z, 1), "subject": SUBJECT_NAMES.get(lex, lex)})
        if len(out) >= n:
            break
    return out


class MyWords:
    """What you decided about words, kept in app storage (vocabulary.json): seen, known and learning."""

    def __init__(self, path=None):
        self.path = path or (paths.home() / "vocabulary.json")
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}
        for key in ("seen", "known"):
            self.data.setdefault(key, [])
        self.data.setdefault("learning", [])
        self.data.setdefault("used", {})                 # word -> where a manuscript used it (marked Known automatically)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # --- the sets -----------------------------------------------------------------------------------------------------------------
    @property
    def seen(self):
        return {w.lower() for w in self.data["seen"]}

    @property
    def known(self):
        return {w.lower() for w in self.data["known"]}

    @property
    def learning(self):
        return list(self.data["learning"])

    def learning_words(self):
        return {e["word"].lower() for e in self.data["learning"]}

    def excluded(self):
        """Words a new batch must not offer: seen, known, or already being learned."""
        return self.seen | self.known | self.learning_words()

    def mark_seen(self, words):
        have = self.seen
        for w in words:
            if w.lower() not in have:
                self.data["seen"].append(w.lower())
                have.add(w.lower())
        self.save()

    def mark_known(self, word, where=None):
        """Known: never offered again and off the Learning list. `where` notes the manuscript that used it (set when it was marked
        automatically): {universe, story, scene, line, text}."""
        self.data["learning"] = [e for e in self.data["learning"] if e["word"].lower() != word.lower()]
        if word.lower() not in self.known:
            self.data["known"].append(word.lower())
        if where:
            self.data["used"][word.lower()] = where
        self.save()

    def used_where(self, word):
        return self.data["used"].get(word.lower())

    def known_entries(self):
        """[{word, where}] for every Known word, those a manuscript used first, then the rest A to Z."""
        used = self.data["used"]
        words = sorted(self.known, key=lambda w: (w not in used, w))
        return [{"word": w, "where": used.get(w)} for w in words]

    def mark_learning(self, word, pos="", definition="", note=""):
        """Add to your list (a word already there is left as it is). Returns True if it was new."""
        self.data["known"] = [w for w in self.data["known"] if w.lower() != word.lower()]
        self.data["used"].pop(word.lower(), None)
        if word.lower() in self.learning_words():
            self.save()
            return False
        self.data["learning"].append({"word": word, "pos": pos, "definition": definition, "note": note})
        self.save()
        return True

    def remove(self, word):
        before = len(self.data["learning"])
        self.data["learning"] = [e for e in self.data["learning"] if e["word"].lower() != word.lower()]
        self.save()
        return before - len(self.data["learning"])

    def add_by_hand(self, word, pos="", definition=""):
        """A word you want to learn that the batches did not offer. Returns "new", "relearn" (it was marked Known) or "have"."""
        had = word.lower() in self.learning_words()
        was_known = word.lower() in self.known
        self.mark_learning(word, pos, definition)
        return "have" if had else ("relearn" if was_known else "new")

    def forget_seen(self):
        self.data["seen"] = []
        self.save()


def fill_definition(entry, db=None):
    """A My words entry with its pos and one-line definition (from the dictionary when it has none)."""
    if entry.get("definition"):
        return entry
    try:
        r = dictionary.lookup(entry["word"], db=db)
    except dictionary.DictionaryMissing:
        return entry
    if r["found"]:
        for e in r["entries"]:
            for part in e["parts"]:
                if part["senses"]:
                    return dict(entry, pos=entry.get("pos") or part["pos"], definition=simple_definition(part["senses"][0]["definition"]))
    return entry
