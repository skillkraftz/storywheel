"""Rhymes from the CMU Pronouncing Dictionary (cmudict.dict from github.com/cmusphinx/cmudict, Carnegie Mellon University; see SOURCES.md).

The dictionary lists how North American English words are said, as phones ("cat  K AE1 T"; the digit is the stress of a vowel). It is
downloaded with `storywheel dictionary install` and read into a small SQLite file (`rhymes.sqlite`, beside the dictionary index).

    perfect rhyme   the sound from the last stressed vowel to the end is the same, and what comes before it differs (cat / hat, fate / debate)
    near rhyme      the same stressed vowel and a similar ending (cat / cap / back: the endings are all stops), or the same ending after a vowel
                    of the same family (cat / bet)

Words are ordered by how common they are (wordfreq, when installed) and grouped by their number of syllables."""
import re
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1
MAX_NEAR = 300                 # near rhymes shown (the commonest); perfect rhymes are never cut off

CMU_URL = "https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict"
CMU_LICENSE_URL = "https://raw.githubusercontent.com/cmusphinx/cmudict/master/LICENSE"
SOURCE_NAMES = ("cmudict.dict", "cmudict-0.7b")          # the second is the older file; one kept in the sources folder is still used

NOT_INSTALLED = ("The CMU Pronouncing Dictionary isn't installed. Rhymes need it. To fix it, run:  storywheel dictionary install   "
                 "(it downloads it, about 4 MB)")

CLASSES = {}
for _letters, _cls in (("P B T D K G", "s"), ("M N NG", "n"), ("F V TH DH S Z SH ZH HH", "f"), ("CH JH", "a"), ("L R W Y", "l")):
    for _p in _letters.split():
        CLASSES[_p] = _cls
FAMILIES = {}
for _fam in ("IY IH", "EY EH AE", "AA AO AH AW AY", "UW UH OW OY"):
    for _p in _fam.split():
        FAMILIES[_p] = _fam.split()[0]


class RhymesMissing(Exception):
    pass


def index_path():
    from . import dictionary
    return dictionary.index_path().with_name("rhymes.sqlite")


def sources_folder():
    from . import dictionary_build
    return dictionary_build.sources_dir(index_path())


def source_in(folder):
    """The kept CMU file in a sources folder: cmudict.dict, else an older cmudict-0.7b; cmudict.dict is where a download goes."""
    for name in SOURCE_NAMES:
        if (Path(folder) / name).exists():
            return Path(folder) / name
    return Path(folder) / SOURCE_NAMES[0]


def source_path():
    return source_in(sources_folder())


def license_path():
    return sources_folder() / "cmudict.LICENSE"


def error_path():
    return index_path().with_name("rhymes-error.txt")


def failure():
    """Why the last attempt to install rhymes failed (one line), or ''."""
    try:
        return error_path().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def record_failure(reason):
    if reason:
        error_path().write_text(reason + "\n", encoding="utf-8")
    else:
        error_path().unlink(missing_ok=True)


def not_installed_message():
    why = failure()
    if why:
        return (f"Rhymes were NOT installed: {why} To fix it, run:  storywheel dictionary install   (it tries the download again)")
    return NOT_INSTALLED


def installed():
    return index_path().exists() or source_path().exists()


def is_vowel(phone):
    return phone[-1:].isdigit()


def analyze(phones):
    """(syllables, vowel, onset, tail) of a pronunciation (a list of phones), or None for one without a vowel.
    The vowel is the last one with primary stress (else secondary stress, else the last vowel), without its stress digit;
    onset is the consonants just before it; tail is everything after it (stress digits removed)."""
    vowels = [i for i, p in enumerate(phones) if is_vowel(p)]
    if not vowels:
        return None
    pick = None
    for stress in ("1", "2"):
        found = [i for i in vowels if phones[i].endswith(stress)]
        if found:
            pick = found[-1]
            break
    if pick is None:
        pick = vowels[-1]
    start = pick
    while start > 0 and not is_vowel(phones[start - 1]):
        start -= 1
    strip = lambda ph: ph.rstrip("012")
    return len(vowels), strip(phones[pick]), [strip(p) for p in phones[start:pick]], [strip(p) for p in phones[pick + 1:]]


def keys(vowel, tail):
    key = " ".join([vowel] + tail)
    vkey = vowel + "|" + "".join(CLASSES.get(p, p) for p in tail)
    fkey = FAMILIES.get(vowel, vowel) + "|" + " ".join(tail)
    return key, vkey, fkey


PHONE = re.compile(r"^[A-Z]{1,2}[012]?$")


def parse(lines):
    """[(word, variant, phones list)] from the lines of a cmudict file. Two layouts are read:
        cmudict.dict (now):   lowercase word, "(2)" for variants ("read(2) R IY1 D"), one space, phones, and sometimes a
                              comment ("aalborg AO1 L B AO0 R G # place, danish");
        cmudict-0.7b (older): uppercase, two spaces, ";;;" comment lines.
    A trailing comment is never part of the pronunciation, and a line with anything that is not a phone is skipped."""
    out = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith(";;;"):
            continue
        line = re.sub(r"\s#.*$", "", line)                        # (" # place, danish": the space keeps "#HASH-MARK" safe)
        head, _, rest = line.partition(" ")
        phones = rest.split()
        if not phones or not all(PHONE.match(p) for p in phones):
            continue
        m = re.match(r"^(.*?)(?:\((\d+)\))?$", head)
        word = m.group(1).lower()
        if not re.search(r"[a-z]", word):
            continue
        out.append((word, int(m.group(2) or 1), phones))
    return out


def license_text(lines):
    """The file's own ';;;' header if it has one; else the LICENSE downloaded beside it."""
    head = "\n".join(l[3:].strip() for l in lines if l.startswith(";;;"))[:4000]
    if head:
        return head
    try:
        return license_path().read_text(encoding="utf-8").strip()[:4000]
    except OSError:
        return ""


def build(src, out_path=None):
    """Read a cmudict file into the rhymes index. Returns the number of pronunciations."""
    out_path = Path(out_path or index_path())
    src = Path(src)
    raw = src.read_bytes()
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        lines = raw.decode("latin-1").splitlines()
    tmp = out_path.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(tmp)
    db.executescript("""
        create table meta (key text primary key, value text);
        create table pron (word text not null, variant integer not null, phones text not null, syl integer not null,
                           key text not null, onset text not null, vkey text not null, fkey text not null);
        create index pron_word on pron (word);
        create index pron_key on pron (key);
        create index pron_vkey on pron (vkey);
        create index pron_fkey on pron (fkey);
    """)
    rows = []
    for word, variant, phones in parse(lines):
        a = analyze(phones)
        if a is None:
            continue
        syl, vowel, onset, tail = a
        key, vkey, fkey = keys(vowel, tail)
        rows.append((word, variant, " ".join(phones), syl, key, " ".join(onset), vkey, fkey))
    db.executemany("insert into pron values (?,?,?,?,?,?,?,?)", rows)
    db.executemany("insert into meta values (?,?)", [("schema", str(SCHEMA_VERSION)), ("license", license_text(lines)),
                                                      ("name", "CMU Pronouncing Dictionary (Carnegie Mellon University)")])
    db.commit()
    db.close()
    tmp.replace(out_path)
    forget()
    return len(rows)


_CONN = {}


def forget():
    for c in _CONN.values():
        c.close()
    _CONN.clear()


def connect():
    path = index_path()
    if not path.exists():
        if not source_path().exists():
            raise RhymesMissing(not_installed_message())
        build(source_path(), path)                           # (offline, from the kept source)
    key = str(path)
    if key not in _CONN:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        try:
            version = int(dict(conn.execute("select key, value from meta")).get("schema", 0))
        except (sqlite3.Error, ValueError):
            version = 0
        if version < SCHEMA_VERSION:
            conn.close()
            if not source_path().exists():
                raise RhymesMissing(not_installed_message())
            build(source_path(), path)
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        _CONN[key] = conn
    return _CONN[key]


def status():
    """{"installed", "license"}: whether rhymes work, and the license text from the downloaded file's own header."""
    try:
        meta = dict(connect().execute("select key, value from meta"))
        lic = meta.get("license", "")
        try:
            lic = license_path().read_text(encoding="utf-8").strip() or lic
        except OSError:
            pass
        return {"installed": True, "name": meta.get("name", ""), "license": lic}
    except (RhymesMissing, sqlite3.Error):
        return {"installed": False, "name": "", "license": ""}


def wordfreq_available():
    try:
        import wordfreq  # noqa: F401
        return True
    except Exception:
        return False


def commonness(word):
    try:
        from wordfreq import zipf_frequency
        return zipf_frequency(word, "en")
    except Exception:
        return 0.0


ORDER_FREQ = "Ordered by how common the word is (wordfreq), commonest first."
ORDER_ABC = "Ordered A to Z (wordfreq isn't installed, so commonness is unknown). To fix it, run:  pipx inject storywheel wordfreq"


def _ordered(found, limit=None, by_frequency=True):
    """found: {word: syllables} -> [(syllables, [words])] by syllables ascending; commonest first (else A to Z)."""
    key = (lambda kv: (-commonness(kv[0]), kv[0])) if by_frequency else (lambda kv: kv[0])
    scored = sorted(found.items(), key=key)
    if limit:
        scored = scored[:limit]
    groups = {}
    for w, syl in scored:
        groups.setdefault(syl, []).append(w)
    return sorted(groups.items())


def find(word, syllables=None, rare=False):
    """Rhymes for a word:
        {"word", "found": bool, "pronunciation": "K AE1 T", "syllables": n,
         "perfect": [(syllables, [words])], "near": [(syllables, [words])], "near_more": number cut off,
         "hidden": names and rare words left out, "filtered": whether the main dictionary was used, "order": a sentence}
    `syllables` limits the rhymes to that many (4 means 4 or more). Unless `rare` is true, only words the main dictionary (WordNet or Moby)
    knows are listed; with `rare` the names and odd spellings in the CMU file are listed too. Raises RhymesMissing when rhymes aren't installed."""
    db = connect()
    w = (word or "").strip().lower()
    mine = db.execute("select phones, syl, key, onset, vkey, fkey from pron where word = ? order by variant", (w,)).fetchall()
    if not mine:
        return {"word": w, "found": False, "pronunciation": "", "syllables": 0, "perfect": [], "near": [], "near_more": 0, "hidden": 0,
                "filtered": False, "order": ""}
    perfect, near = {}, {}
    own_keys = {m[2] for m in mine}
    own_sounds = {(m[2], m[3]) for m in mine}
    for phones, syl, key, onset, vkey, fkey in mine:
        for cw, csyl, ckey, conset in db.execute("select word, syl, key, onset from pron where key = ?", (key,)):
            if cw != w and (ckey, conset) not in own_sounds:           # (the same sound again is the same word, not a rhyme)
                perfect[cw] = csyl
        for cw, csyl, ckey, conset in db.execute("select word, syl, key, onset from pron where vkey = ? or fkey = ?", (vkey, fkey)):
            if cw != w and ckey not in own_keys:
                near[cw] = csyl
    for cw in perfect:
        near.pop(cw, None)

    def limited(d):
        if syllables:
            return {k: v for k, v in d.items() if (v >= syllables if syllables >= 4 else v == syllables)}
        return d
    perfect, near = limited(perfect), limited(near)
    hidden, filtered = 0, False
    if not rare:
        from . import dictionary
        try:
            known = dictionary.knows(set(perfect) | set(near))
            before = len(perfect) + len(near)
            perfect = {k: v for k, v in perfect.items() if k in known}
            near = {k: v for k, v in near.items() if k in known}
            hidden, filtered = before - len(perfect) - len(near), True
        except dictionary.DictionaryMissing:
            pass                                                         # (no main dictionary: nothing to filter by; all are listed)
    by_frequency = wordfreq_available()
    return {"word": w, "found": True, "pronunciation": mine[0][0], "syllables": mine[0][1],
            "perfect": _ordered(perfect, None, by_frequency), "near": _ordered(near, MAX_NEAR, by_frequency),
            "near_more": max(0, len(near) - MAX_NEAR), "hidden": hidden, "filtered": filtered,
            "order": ORDER_FREQ if by_frequency else ORDER_ABC}
