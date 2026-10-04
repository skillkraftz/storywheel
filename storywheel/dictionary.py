"""Look up a word: meanings, similar words and opposite words, offline.

    lookup("running")  ->  {"query", "found", "entries": [...], "suggestions": [...]}

The data is one SQLite file made by `storywheel dictionary install` (see dictionary_build.py): Open English WordNet for meanings,
examples, "kind of" and opposites, Moby Thesaurus II for many more similar words. Inflected forms find their base word
("running" -> "run", "geese" -> "goose"); a word that isn't there comes back with close spellings.
"""
import difflib
import re
import sqlite3

from . import inflect, paths, tools
from .dictionary_build import SCHEMA_VERSION, unpack_ids

POS_NAMES = {"n": "noun", "v": "verb", "a": "adjective", "s": "adjective", "r": "adverb"}
POS_ORDER = ["noun", "verb", "adjective", "adverb"]
NOT_INSTALLED = tools.missing("dictionary", "(one download, about 40 MB)")


OUT_OF_DATE = "The dictionary index is from an older version and the saved sources are missing. To fix it, run:  storywheel dictionary install   (it downloads them again and rebuilds)."


class DictionaryMissing(Exception):
    pass


def index_path():
    import os
    env = os.environ.get("STORYWHEEL_DICTIONARY")
    return __import__("pathlib").Path(env) if env else paths.home() / "dictionary.sqlite"


def installed():
    return index_path().exists()


_CONN = {}


def connect(path=None):
    path = path or index_path()
    key = str(path)
    if key not in _CONN:
        if not __import__("pathlib").Path(path).exists():
            raise DictionaryMissing(NOT_INSTALLED)
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        try:
            version = int(dict(conn.execute("select key, value from meta")).get("schema", 0))
        except (sqlite3.Error, ValueError):
            version = 0
        if version < SCHEMA_VERSION:
            conn.close()
            conn = _rebuild_offline(path)               # (from the kept sources; raises DictionaryMissing if they are not there)
        _CONN[key] = conn
    return _CONN[key]


NOTES = []                       # one-line messages for the screen ("Rebuilt the dictionary index ..."); take them with take_notes()


def take_notes():
    out, NOTES[:] = list(NOTES), []
    return out


def _rebuild_offline(path):
    """The index is from an older format: build it again from the sources kept by `dictionary install`, without the network."""
    from . import dictionary_build
    try:
        counts = dictionary_build.rebuild_from_sources(path)
    except (dictionary_build.DictionaryBuildError, OSError, Exception) as e:
        raise DictionaryMissing(f"{OUT_OF_DATE} (Rebuilding it from the saved sources failed: {e})")
    if counts is None:
        raise DictionaryMissing(OUT_OF_DATE)
    NOTES.append("The dictionary index was from an older version; rebuilt it from the saved sources (no download).")
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)


def forget():
    for c in _CONN.values():
        c.close()
    _CONN.clear()


# --- finding the base word --------------------------------------------------------------------------------------------------------

def candidates(word):
    """Possible base forms of an English word, by the usual endings (best guesses first). Includes the word itself."""
    w = word.lower()
    out = [w]

    def add(x):
        if len(x) >= 2 and x not in out:
            out.append(x)

    if w.endswith("ies"):
        add(w[:-3] + "y"); add(w[:-1])
    if w.endswith("ves"):
        add(w[:-3] + "f"); add(w[:-3] + "fe"); add(w[:-1])
    if w.endswith(("sses", "xes", "zes", "ches", "shes", "oes")):
        add(w[:-2])
    if w.endswith("s") and not w.endswith("ss"):
        add(w[:-1])
    if w.endswith("men"):
        add(w[:-3] + "man")
    if w.endswith("ied"):
        add(w[:-3] + "y")
    if w.endswith("ed"):
        add(w[:-2]); add(w[:-1])
        if len(w) > 4 and w[-3] == w[-4]:
            add(w[:-3])
    if w.endswith("ing"):
        add(w[:-3]); add(w[:-3] + "e")
        if len(w) > 5 and w[-4] == w[-5]:
            add(w[:-4])
        if w.endswith("ying"):
            add(w[:-4] + "ie")
    if w.endswith("ier"):
        add(w[:-3] + "y")
    if w.endswith("iest"):
        add(w[:-4] + "y")
    if w.endswith("er"):
        add(w[:-2]); add(w[:-1])
        if len(w) > 4 and w[-3] == w[-4]:
            add(w[:-3])
    if w.endswith("est"):
        add(w[:-3]); add(w[:-2])
        if len(w) > 5 and w[-4] == w[-5]:
            add(w[:-4])
    if w.endswith("ly"):
        add(w[:-2])
        if w.endswith("ily"):
            add(w[:-3] + "y")
    return out


def clean(word):
    w = (word or "").strip()
    w = re.sub(r"^[^\w]+|[^\w]+$", "", w)
    if w.lower().endswith(("'s", "’s")):
        w = w[:-2]
    return w.replace("’", "'").lower()


def _word_ids(db, text):
    row = db.execute("select id from words where w = ?", (text,)).fetchone()
    return row[0] if row else None


def _has_content(db, wid):
    return bool(db.execute("select 1 from senses where word_id = ? limit 1", (wid,)).fetchone()
                or db.execute("select 1 from moby where word_id = ?", (wid,)).fetchone())


def base_words(db, text):
    """[(word id, word, 'form of' text or None)]: the word itself, then its base forms, each only if the index knows it."""
    found, seen = [], set()

    def take(wid, word, note):
        if wid is not None and wid not in seen and _has_content(db, wid):
            seen.add(wid)
            found.append((wid, word, note))

    take(_word_ids(db, text), text, None)
    for (wid,) in db.execute("select word_id from forms where form = ?", (text,)).fetchall():
        w = db.execute("select w from words where id = ?", (wid,)).fetchone()[0]
        take(wid, w, text)
    for cand in candidates(text)[1:]:
        take(_word_ids(db, cand), cand, text)
    return found


# --- one word ------------------------------------------------------------------------------------------------------------------------

def _word(db, wid):
    row = db.execute("select w from words where id = ?", (wid,)).fetchone()
    return row[0] if row else None


def _ids(csv):
    return [int(i) for i in (csv or "").split(",") if i]


def _members(db, synset_id):
    row = db.execute("select members from synsets where id = ?", (synset_id,)).fetchone()
    return [w for w in (_word(db, i) for i in _ids(row[0] if row else "")) if w]


def _targets(db, synset_id, kind):
    return [t for (t,) in db.execute("select target from rels where synset_id = ? and kind = ?", (synset_id, kind))]


def _members_of(db, synset_ids, skip=()):
    out, seen = [], set(w.lower() for w in skip)
    for sid in synset_ids:
        for w in _members(db, sid):
            if w.lower() not in seen:
                seen.add(w.lower())
                out.append(w)
    return out


def _direct_antonyms(db, wid):
    return [w for (w,) in db.execute("select w from words where id in (select other_id from antonyms where word_id = ?)", (wid,))]


def _entry(db, wid, word, form_of):
    senses = db.execute("select pos, synset_id from senses where word_id = ? order by pos, ord", (wid,)).fetchall()
    groups = {}
    close, seen = [], {word}
    for pos, sid in senses:
        row = db.execute("select defn, ex from synsets where id = ?", (sid,)).fetchone()
        if not row:
            continue
        defn, ex = row
        syns = [m for m in _members(db, sid) if m.lower() != word]
        kind_of = [(_members(db, h) or [""])[0] for h in _targets(db, sid, "hypernym")[:3]]
        types = _members_of(db, _targets(db, sid, "hyponym"), skip=[word])
        has_parts = _members_of(db, [t for k in ("mero_part", "mero_substance", "mero_member") for t in _targets(db, sid, k)])
        part_of = _members_of(db, [t for k in ("holo_part", "holo_substance", "holo_member") for t in _targets(db, sid, k)])
        groups.setdefault(POS_NAMES.get(pos, pos), []).append({
            "definition": defn, "examples": [e for e in ex.split("\x1f") if e], "synonyms": syns,
            "kind_of": [k for k in kind_of if k], "types_of": types, "parts": has_parts, "part_of": part_of})
        for sy in syns:
            if sy.lower() not in seen:
                seen.add(sy.lower())
                close.append(sy)
    # opposites: direct ones, and for adjectives those of the head words the meaning is "similar" to
    ants = _direct_antonyms(db, wid)
    if not ants:
        for pos, sid in senses:
            if pos in ("a", "s"):
                for head in _targets(db, sid, "similar"):
                    for member in _ids((db.execute("select members from synsets where id = ?", (head,)).fetchone() or [""])[0]):
                        for w in _direct_antonyms(db, member):
                            if w not in ants:
                                ants.append(w)
    # indirect opposites: the opposites of each similar word (labelled as such: "sad", because 'glad' is similar to 'happy')
    indirect, known = [], set(a.lower() for a in ants) | {word}
    for sy in close:
        sid_ = _word_ids(db, sy.lower())
        for a in (_direct_antonyms(db, sid_) if sid_ else []):
            if a.lower() not in known:
                known.add(a.lower())
                indirect.append({"word": a, "via": sy})
    # many more similar words from the Moby thesaurus (after the WordNet ones), alphabetical
    moby = db.execute("select blob from moby where word_id = ?", (wid,)).fetchone()
    wide = []
    if moby:
        for i in unpack_ids(moby[0]):
            w = _word(db, i)
            if w and w.lower() not in seen:
                seen.add(w.lower())
                wide.append(w)
    wide.sort(key=str.lower)
    related = {}
    for other, kind in db.execute("select other_id, kind from related where word_id = ?", (wid,)):
        w = _word(db, other)
        if w and w.lower() != word and w not in related.get(kind, []):
            related.setdefault(kind, []).append(w)
    ordered = [{"pos": p, "senses": groups[p]} for p in POS_ORDER if p in groups] + \
              [{"pos": p, "senses": g} for p, g in groups.items() if p not in POS_ORDER]
    return {"word": word, "form_of": form_of, "parts": ordered, "close_synonyms": close, "wide_synonyms": wide,
            "synonyms": close + wide, "antonyms": ants, "indirect_antonyms": indirect, "related_forms": related}


def _word_ids(db, text):
    row = db.execute("select id from words where w = ?", (text,)).fetchone()
    return row[0] if row else None


def lookup(word, db=None):
    """Everything known about a word. 'found' is False when nothing matched; 'suggestions' then has close spellings."""
    db = db or connect()
    text = clean(word)
    result = {"query": word, "word": text, "found": False, "entries": [], "suggestions": []}
    if not text:
        return result
    for wid, w, note in base_words(db, text):
        result["entries"].append(_entry(db, wid, w, note))
    result["found"] = bool(result["entries"])
    if not result["found"]:
        result["suggestions"] = suggest(db, text)
    # which base word, and which form of it, the looked-up word is (so a replacement can be put in the same form)
    result["base"], result["form_kind"] = text, "base"
    for e in result["entries"]:
        kind = inflect.classify(text, e["word"])
        e["form_kind"] = kind
        if kind not in (None, "base") and result["form_kind"] == "base":
            result["base"], result["form_kind"] = e["word"], kind
    return result


def suggest(db, text, n=5):
    like = (text[:1] + "%") if text else "%"
    pool = [w for (w,) in db.execute("select w from words where w like ? and length(w) between ? and ?", (like, len(text) - 2, len(text) + 2))]
    if len(text) > 3:                                             # a wrong first letter is a common slip too
        pool += [w for (w,) in db.execute("select w from words where w like ? and length(w) between ? and ?", ("%" + text[1:], len(text) - 1, len(text) + 1))]
    close = difflib.get_close_matches(text, list(dict.fromkeys(pool)), n=n * 2, cutoff=0.7)
    return sorted(close, key=lambda w: (sorted(w) != sorted(text), -difflib.SequenceMatcher(None, text, w).ratio()))[:n]   # (same letters, swapped, first)


# --- text for screens and the CLI --------------------------------------------------------------------------------------------------------

def card_lines(result, width=78, **_ignored):
    """The result as plain text lines (the CLI uses it): everything, nothing cut off."""
    import textwrap
    out = []
    if not result["found"]:
        out.append(f"No entry for '{result['word'] or result['query']}'.")
        if result["suggestions"]:
            out.append("Did you mean: " + ", ".join(result["suggestions"]) + "?")
        return out

    def listing(label, words):
        if words:
            out.append("")
            out.append(label)
            out.extend(textwrap.wrap(", ".join(words), width, initial_indent="  ", subsequent_indent="  "))

    for e in result["entries"]:
        title = e["word"] + (f"   (from '{e['form_of']}')" if e["form_of"] else "")
        out += [title, "=" * len(title)]
        for part in e["parts"]:
            out.append(f"{part['pos']}")
            for i, s in enumerate(part["senses"], 1):
                out += textwrap.wrap(f"{i}. {s['definition']}", width, subsequent_indent="   ")
                for ex in s["examples"][:1]:
                    out += textwrap.wrap(f"“{ex}”", width, initial_indent="     ", subsequent_indent="     ")
                if s["kind_of"]:
                    out.append("     a kind of: " + ", ".join(s["kind_of"]))
                if s["synonyms"]:
                    out += textwrap.wrap("similar: " + ", ".join(s["synonyms"]), width, initial_indent="     ", subsequent_indent="       ")
        listing("More similar words:", e["wide_synonyms"])
        listing("Opposite:", e["antonyms"])
        listing("Opposite (indirect, opposites of similar words):", [f"{a['word']} (of {a['via']})" for a in e["indirect_antonyms"]])
        for kind, words in e["related_forms"].items():
            listing(f"Related forms ({kind}):", words)
        out.append("")
    return out


def knows(words):
    """The words (of those given) that the main dictionary has something to say about: an entry in WordNet or Moby, or a form of one
    (plurals, past tenses...). Raises DictionaryMissing when there is no index."""
    db = connect()
    wanted = sorted({w for w in words if w})
    known = set()
    for i in range(0, len(wanted), 400):
        chunk = wanted[i:i + 400]
        marks = ",".join("?" * len(chunk))
        known.update(r[0] for r in db.execute(
            f"select w from words where w in ({marks}) and (id in (select word_id from senses) or id in (select word_id from moby))", chunk))
        known.update(r[0] for r in db.execute(f"select distinct form from forms where form in ({marks})", chunk))
    return known


def status():
    p = index_path()
    if not p.exists():
        return {"installed": False, "path": str(p)}
    db = connect()
    meta = dict(db.execute("select key, value from meta"))
    return {"installed": True, "path": str(p), "size": p.stat().st_size, **meta}
