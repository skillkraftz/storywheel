"""Which words your manuscripts already use. A Vocabulary word that appears in any manuscript of any universe is a word you know: it is marked
Known automatically, leaves the lists, and the place where it was used is noted. Forms count (a story that says "lanterns" uses "lantern",
one that says "ran" uses "run")."""
import re

from . import dictionary, vault

WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*[A-Za-z]|[A-Za-z]")
_CACHE = {"sig": None, "map": {}}


def _files():
    out = []
    for u in vault.list_universes():
        for s in u.stories():
            for p in s.files():
                out.append((u, s, p))
    return out


def _signature(files):
    sig = []
    for _u, _s, p in files:
        try:
            st = p.stat()
            sig.append((str(p), st.st_mtime_ns, st.st_size))
        except OSError:
            continue
    return tuple(sig)


def used_map(db=None):
    """{base word: where} for every word of every manuscript: where = {universe, story, scene, line, text, file}. Remembered until a file changes."""
    files = _files()
    sig = _signature(files)
    if sig == _CACHE["sig"]:
        return _CACHE["map"]
    try:
        db = db or dictionary.connect()
    except dictionary.DictionaryMissing:
        db = None
    first = {}                                                                 # surface word -> where (first use)
    for u, s, p in files:
        text = vault.Story._read(s, p)
        scenes = vault.parse_scenes(text)
        for n, line in enumerate(text.split("\n"), 1):
            if vault.marker_label(line.strip()) is not None:
                continue
            for m in WORD.finditer(line):
                w = m.group(0).lower().replace("’", "'")
                if w in first:
                    continue
                scene = next((sc for sc in scenes if sc["start"] <= n <= sc["end"]), None)
                title = (scene["label"] or f"Scene {scenes.index(scene) + 1}") if scene else ""
                a, b = max(0, m.start() - 30), min(len(line), m.end() + 30)
                first[w] = {"universe": u.name, "story": s.title, "scene": title, "line": n, "file": str(p),
                            "text": ("…" if a else "") + line[a:b].strip() + ("…" if b < len(line) else "")}
    out = {}
    for w, where in first.items():
        forms = {w, *dictionary.candidates(w)}
        if db is not None:
            forms.update(x for (x,) in db.execute("select w.w from forms f join words w on w.id = f.word_id where f.form = ?", (w,)))
        for f in forms:
            out.setdefault(f, where)
    _CACHE["sig"], _CACHE["map"] = sig, out
    return out


def find(words, db=None):
    """{word: where} for those of `words` (lowercase) that some manuscript uses."""
    used = used_map(db)
    return {w: used[w] for w in words if w in used}


def describe(where):
    """'The Last Clause (Thornwood), Scene 2, line 12'"""
    if not where:
        return ""
    scene = f", {where['scene']}" if where.get("scene") else ""
    return f"{where['story']} ({where['universe']}){scene}, line {where['line']}"


def auto_known(my, words, db=None):
    """Mark every word of `words` that a manuscript uses as Known (noting where). Returns {word: where} for the ones marked."""
    found = find([w.lower() for w in words], db)
    for w, where in found.items():
        my.mark_known(w, where)
    return found
