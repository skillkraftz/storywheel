"""A spelling list made from the dictionary index, so the Writer's spellchecker knows the words of the dictionary and not only Neovim's
built-in English list.

    swdict      every WordNet and Moby word, and the forms storywheel's inflection code can make: plurals and -s, -ed, -ing, -er, -est
    swlenient   a known word plus a common ending or beginning: -ing -ed -er -ers -ly -ness -less -ful, un- re-
                ("gunsmithing" passes). Settings > Writer > "Accept words built from known words".

Neovim reads a word list compiled to `spell/<name>.utf-8.spl` in a folder on its runtimepath, so the lists are written to
`<app storage>/spelllang/` and compiled there by a headless Neovim (a second or two). A stamp records which dictionary index they came from,
and they are rebuilt when it changes.
"""
import json
import re
import sqlite3
import subprocess

from . import dictionary, inflect, paths

VERSION = 1                       # bump when the way the lists are made changes
WORD = re.compile(r"^[a-z][a-z'-]*[a-z]$")


def folder():
    return paths.home() / "spelllang"


def spl_path(name):
    return folder() / "spell" / f"{name}.utf-8.spl"


def _rows(db):
    return db.execute("select w.w, group_concat(distinct s.pos) from words w left join senses s on s.word_id = w.id group by w.id").fetchall()


def _ly(w):
    if w.endswith("y") and len(w) > 2:
        return w[:-1] + "ily"
    if w.endswith("ic"):
        return w + "ally"
    if w.endswith("le") and len(w) > 3 and w[-3] not in "aeiou":
        return w[:-1] + "y"
    return w + "ly"


def _ness(w):
    return (w[:-1] + "iness") if w.endswith("y") and len(w) > 2 else w + "ness"


def _ful_less(w, suffix):
    stem = (w[:-1] + "i") if w.endswith("y") and len(w) > 2 and w[-2] not in "aeiou" else w
    return stem + suffix


def dictionary_words(db):
    """(plain words, lenient words) as sets of lowercase strings."""
    plain, lenient = set(), set()
    for w, pos in _rows(db):
        for part in w.split(" "):
            if WORD.match(part):
                plain.add(part)
        if " " in w or not WORD.match(w) or "'" in w or "-" in w:
            continue
        kinds = set((pos or "").split(","))
        if "s" in kinds:
            kinds.add("a")                            # (a satellite adjective is an adjective)
        if kinds & {"n", "v"}:
            f = inflect.forms_of(w)
            plain.update((f["s"], f["past"], f["pp"], f["ing"]))
        if "a" in kinds and len(w) < 9:
            f = inflect.forms_of(w)
            plain.update(x for x in (f["er"], f["est"]) if " " not in x)
        if not 3 <= len(w) <= 12:
            continue
        if kinds & {"n", "v"}:
            ing = inflect.add_ing(w)
            stem = ing[:-3] if ing.endswith("ing") else w
            lenient.update((ing, inflect.past(w), stem + "er", stem + "ers"))
        if kinds & {"a"}:
            lenient.update((_ly(w), _ness(w)))
        if kinds & {"n"}:
            lenient.update((_ful_less(w, "less"), _ful_less(w, "ful")))
        if kinds & {"a", "v"} and len(w) >= 4:
            lenient.add("un" + w)
        if "v" in kinds and len(w) >= 4:
            lenient.add("re" + w)
    lenient = {x for x in lenient if WORD.match(x)} - plain
    return plain, lenient


def moby_words(db):
    out = set()
    try:
        from .dictionary_build import unpack_ids
        ids = {i: w for i, w in db.execute("select id, w from words")}
        for _wid, blob in db.execute("select word_id, blob from moby"):
            for i in unpack_ids(blob):
                w = ids.get(i, "")
                for part in w.split(" "):
                    if WORD.match(part):
                        out.add(part)
    except (sqlite3.Error, ImportError, ValueError):
        pass
    return out


def stamp_of():
    p = dictionary.index_path()
    st = p.stat()
    return {"version": VERSION, "index": [st.st_mtime_ns, st.st_size]}


def stale():
    """True when the compiled lists are missing or came from another index."""
    try:
        have = json.loads((folder() / "stamp.json").read_text(encoding="utf-8"))
        return have != stamp_of() or not spl_path("swdict").exists() or not spl_path("swlenient").exists()
    except (OSError, ValueError):
        return True


def build(nvim, progress=lambda m: None):
    """Write both lists and compile them with Neovim. Returns {"swdict": n, "swlenient": n}; raises DictionaryMissing without an index."""
    db = dictionary.connect()
    plain, lenient = dictionary_words(db)
    plain |= moby_words(db)
    lenient -= plain
    out = folder()
    (out / "spell").mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, words in (("swdict", plain), ("swlenient", lenient)):
        src = out / f"{name}.txt"
        src.write_text("\n".join(sorted(words)) + "\n", encoding="utf-8")
        progress(f"Compiling {len(words):,} words for the spellchecker ({name})…")
        result = subprocess.run([nvim, "--headless", "-u", "NONE", "-c", f"mkspell! {spl_path(name)} {src}", "-c", "qa!"],
                                capture_output=True, text=True, timeout=300)
        if not spl_path(name).exists():
            raise OSError(f"Neovim could not compile the {name} spelling list: {(result.stderr or result.stdout).strip()[:200]}")
        counts[name] = len(words)
    (out / "stamp.json").write_text(json.dumps(stamp_of()), encoding="utf-8")
    return counts


def ensure(nvim, progress=lambda m: None):
    """Build the lists if they are missing or out of date and a dictionary index exists. Returns a message, or None if nothing was done
    (or nothing could be: no index, no Neovim)."""
    if not nvim or not dictionary.installed():
        return None
    try:
        if not stale():
            return None
        counts = build(nvim, progress)
    except (dictionary.DictionaryMissing, OSError, subprocess.SubprocessError) as e:
        return f"The spelling list from the dictionary could not be built: {e}"
    return f"Built the spelling list from the dictionary ({counts['swdict']:,} words, {counts['swlenient']:,} built from them)."
