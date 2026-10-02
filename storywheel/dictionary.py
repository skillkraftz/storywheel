"""Look up a word: meanings, similar words and opposite words, offline.

    lookup("running")  ->  {"query", "found", "entries": [...], "suggestions": [...]}

The data is one SQLite file made by `storywheel dictionary install` (see dictionary_build.py): Open English WordNet for meanings,
examples, "kind of" and opposites, Moby Thesaurus II for many more similar words. Inflected forms find their base word
("running" -> "run", "geese" -> "goose"); a word that isn't there comes back with close spellings.
"""
import difflib
import re
import sqlite3

from . import paths
from .dictionary_build import unpack_ids

POS_NAMES = {"n": "noun", "v": "verb", "a": "adjective", "s": "adjective", "r": "adverb"}
POS_ORDER = ["noun", "verb", "adjective", "adverb"]
NOT_INSTALLED = "The dictionary isn't installed yet. Run:  storywheel dictionary install   (one download, about 40 MB)."


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
        _CONN[key] = conn
    return _CONN[key]


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

def _words(db, id_csv):
    out = []
    for i in (id_csv or "").split(","):
        if i:
            row = db.execute("select w from words where id = ?", (int(i),)).fetchone()
            if row:
                out.append(row[0])
    return out


def _entry(db, wid, word, form_of, limit_similar):
    senses = db.execute("select pos, synset_id from senses where word_id = ? order by pos, ord", (wid,)).fetchall()
    groups = {}
    similar, kinds = [], []
    seen_syn = {word}
    for pos, sid in senses:
        row = db.execute("select defn, ex, members, hyper, similar from synsets where id = ?", (sid,)).fetchone()
        if not row:
            continue
        defn, ex, members, hyper, sim = row
        syns = [m for m in _words(db, members) if m.lower() != word]
        kind_of = []
        for h in (hyper or "").split(",")[:2]:
            if h:
                hm = db.execute("select members from synsets where id = ?", (int(h),)).fetchone()
                if hm:
                    kind_of.append((_words(db, hm[0]) or [""])[0])
        name = POS_NAMES.get(pos, pos)
        groups.setdefault(name, []).append({
            "definition": defn, "examples": [e for e in ex.split("\x1f") if e], "synonyms": syns, "kind_of": [k for k in kind_of if k]})
        for s in syns:
            if s.lower() not in seen_syn:
                seen_syn.add(s.lower())
                similar.append(s)
    # opposites: direct ones, and for adjectives those of the head words the meaning is "similar" to
    ants = [w for (w,) in db.execute("select w from words where id in (select other_id from antonyms where word_id = ?)", (wid,))]
    if not ants:
        for pos, sid in senses:
            if pos in ("a", "s"):
                row = db.execute("select similar from synsets where id = ?", (sid,)).fetchone()
                for h in (row[0] or "").split(",") if row else []:
                    if not h:
                        continue
                    head = db.execute("select members from synsets where id = ?", (int(h),)).fetchone()
                    for mid in _words_ids(db, head[0] if head else ""):
                        for (w,) in db.execute("select w from words where id in (select other_id from antonyms where word_id = ?)", (mid,)):
                            if w not in ants:
                                ants.append(w)
    # many more similar words from the Moby thesaurus (after the WordNet ones)
    moby = db.execute("select blob from moby where word_id = ?", (wid,)).fetchone()
    wide = []
    if moby:
        for i in unpack_ids(moby[0]):
            w = db.execute("select w from words where id = ?", (i,)).fetchone()
            if w and w[0].lower() not in seen_syn and w[0].lower() != word:
                seen_syn.add(w[0].lower())
                wide.append(w[0])
    wide.sort(key=str.lower)
    ordered = [{"pos": p, "senses": groups[p]} for p in POS_ORDER if p in groups] + \
              [{"pos": p, "senses": g} for p, g in groups.items() if p not in POS_ORDER]
    return {"word": word, "form_of": form_of, "parts": ordered, "synonyms": similar + wide[:max(0, limit_similar - len(similar))],
            "more_synonyms": max(0, len(similar) + len(wide) - limit_similar), "close_synonyms": similar, "antonyms": ants}


def _words_ids(db, id_csv):
    return [int(i) for i in (id_csv or "").split(",") if i]


def lookup(word, limit_similar=80, db=None):
    """Everything known about a word. 'found' is False when nothing matched; 'suggestions' then has close spellings."""
    db = db or connect()
    text = clean(word)
    result = {"query": word, "word": text, "found": False, "entries": [], "suggestions": []}
    if not text:
        return result
    for wid, w, note in base_words(db, text):
        result["entries"].append(_entry(db, wid, w, note, limit_similar))
    result["found"] = bool(result["entries"])
    if not result["found"]:
        result["suggestions"] = suggest(db, text)
    return result


def suggest(db, text, n=5):
    like = (text[:1] + "%") if text else "%"
    pool = [w for (w,) in db.execute("select w from words where w like ? and length(w) between ? and ?", (like, len(text) - 2, len(text) + 2))]
    if len(text) > 3:                                             # a wrong first letter is a common slip too
        pool += [w for (w,) in db.execute("select w from words where w like ? and length(w) between ? and ?", ("%" + text[1:], len(text) - 1, len(text) + 1))]
    close = difflib.get_close_matches(text, list(dict.fromkeys(pool)), n=n * 2, cutoff=0.7)
    return sorted(close, key=lambda w: (sorted(w) != sorted(text), -difflib.SequenceMatcher(None, text, w).ratio()))[:n]   # (same letters, swapped, first)


# --- text for screens and the CLI --------------------------------------------------------------------------------------------------------

def card_lines(result, width=78, similar_shown=40):
    """The result as plain text lines (the Wheel/Builder dialog and the CLI use it)."""
    import textwrap
    out = []
    if not result["found"]:
        out.append(f"No entry for '{result['word'] or result['query']}'.")
        if result["suggestions"]:
            out.append("Did you mean: " + ", ".join(result["suggestions"]) + "?")
        return out
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
        if e["synonyms"]:
            shown = e["synonyms"][:similar_shown]
            out += ["", "Similar:"] + textwrap.wrap(", ".join(shown) + (f"  … and {len(e['synonyms']) - len(shown) + e['more_synonyms']} more" if len(e["synonyms"]) > len(shown) or e["more_synonyms"] else ""), width, initial_indent="  ", subsequent_indent="  ")
        if e["antonyms"]:
            out += ["", "Opposite:"] + textwrap.wrap(", ".join(e["antonyms"]), width, initial_indent="  ", subsequent_indent="  ")
        out.append("")
    return out


def status():
    p = index_path()
    if not p.exists():
        return {"installed": False, "path": str(p)}
    db = connect()
    meta = dict(db.execute("select key, value from meta"))
    return {"installed": True, "path": str(p), "size": p.stat().st_size, **meta}
