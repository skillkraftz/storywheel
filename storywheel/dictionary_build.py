"""Building the dictionary/thesaurus index (once, from two downloaded files; see `storywheel dictionary install`).

    Open English WordNet (CC BY 4.0), the XML release: definitions, examples, synonyms, antonyms, "kind of".
    Moby Thesaurus II by Grady Ward (public domain, Project Gutenberg #3202, mthesaur.txt): much broader synonym lists.

The index is one SQLite file, so a lookup takes milliseconds and nothing is read at run time but that file. Only the standard
library is used. This is the only part of storywheel that can touch the network, and only when you run `dictionary install`.
"""
import gzip
import io
import json
import re
import shutil
import sqlite3
import urllib.request
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

OEWN_URL = "https://github.com/globalwordnet/english-wordnet/releases/download/2025-edition/english-wordnet-2025.xml.gz"
MOBY_URL = "https://www.gutenberg.org/files/3202/files/mthesaur.txt"
SCHEMA_VERSION = 1

SCHEMA = """
create table meta (key text primary key, value text);
create table words (id integer primary key, w text not null);
create unique index words_w on words (w);
create table forms (form text not null, word_id integer not null);
create index forms_form on forms (form);
create table senses (word_id integer not null, pos text not null, synset_id integer not null, ord integer not null);
create index senses_word on senses (word_id, pos, ord);
create table synsets (id integer primary key, pos text not null, defn text not null, ex text not null,
                      members text not null, hyper text not null, similar text not null);
create table antonyms (word_id integer not null, other_id integer not null);
create index antonyms_word on antonyms (word_id);
create table moby (word_id integer primary key, blob blob not null);
"""


class DictionaryBuildError(Exception):
    pass


def _varint(n, out):
    while n >= 0x80:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    out.append(n)


def pack_ids(ids):
    """Sorted word ids as zlib-compressed varint deltas."""
    out = bytearray()
    prev = 0
    for i in sorted(set(ids)):
        _varint(i - prev, out)
        prev = i
    return zlib.compress(bytes(out), 9)


def unpack_ids(blob):
    data = zlib.decompress(blob)
    ids, prev, shift, cur = [], 0, 0, 0
    for byte in data:
        cur |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
        else:
            prev += cur
            ids.append(prev)
            shift, cur = 0, 0
    return ids


def _open_text(path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rb")
    return open(path, "rb")


def build(oewn_path, moby_path, out_path, progress=lambda msg: None):
    """Write the index to out_path (replacing it). Returns a dict of counts."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.name + ".building")
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(str(tmp))
    db.executescript(SCHEMA)
    ids = {}

    def word_id(w):
        w = w.lower()
        i = ids.get(w)
        if i is None:
            i = ids[w] = len(ids) + 1
        return i

    # --- Open English WordNet ------------------------------------------------------------------------------------------------
    progress("Reading WordNet…")
    synset_ids = {}                                   # "oewn-02086723-n" -> int
    sense_owner = {}                                  # sense id -> (lemma, pos)
    entries = []                                      # (lemma, pos, [(synset key, sense id, [antonym sense ids])], [forms])
    synsets = {}                                      # key -> dict
    with _open_text(oewn_path) as f:
        for event, el in ET.iterparse(f, events=("end",)):
            tag = el.tag
            if tag == "LexicalEntry":
                lemma_el = el.find("Lemma")
                if lemma_el is None:
                    el.clear()
                    continue
                lemma, pos = lemma_el.get("writtenForm"), lemma_el.get("partOfSpeech")
                senses = []
                for s in el.findall("Sense"):
                    ants = [r.get("target") for r in s.findall("SenseRelation") if r.get("relType") == "antonym"]
                    senses.append((s.get("synset"), s.get("id"), ants))
                    sense_owner[s.get("id")] = (lemma, pos)
                entries.append((lemma, pos, senses, [fm.get("writtenForm") for fm in el.findall("Form")]))
                el.clear()
            elif tag == "Synset":
                key = el.get("id")
                rels = {}
                for r in el.findall("SynsetRelation"):
                    rels.setdefault(r.get("relType"), []).append(r.get("target"))
                synsets[key] = {
                    "pos": el.get("partOfSpeech"), "members": (el.get("members") or "").split(),
                    "defn": " ".join(d.text or "" for d in el.findall("Definition")).strip(),
                    "ex": [e.text or "" for e in el.findall("Example")],
                    "hyper": rels.get("hypernym", []), "similar": rels.get("similar", []),
                }
                el.clear()
    if not entries or not synsets:
        raise DictionaryBuildError("That WordNet file has no entries (is it the OEWN .xml or .xml.gz release?).")
    for n, key in enumerate(sorted(synsets), 1):
        synset_ids[key] = n
    progress(f"Writing {len(entries):,} words and {len(synsets):,} meanings…")
    for lemma, pos, senses, forms in entries:
        wid = word_id(lemma)
        for order, (syn, _sid, _ants) in enumerate(senses):
            if syn in synset_ids:
                db.execute("insert into senses values (?,?,?,?)", (wid, pos, synset_ids[syn], order))
        for form in forms:
            f = form.lower()
            if f != lemma.lower():
                db.execute("insert into forms values (?,?)", (f, wid))
    by_synset = {}
    for lemma, pos, senses, _forms in entries:
        for syn, _sid, _a in senses:
            by_synset.setdefault(syn, []).append(lemma)
    for key, s in synsets.items():
        member_ids = ",".join(str(word_id(w)) for w in by_synset.get(key, []))
        db.execute("insert into synsets values (?,?,?,?,?,?,?)", (
            synset_ids[key], s["pos"], s["defn"], "\x1f".join(s["ex"]), member_ids,
            ",".join(str(synset_ids[h]) for h in s["hyper"] if h in synset_ids),
            ",".join(str(synset_ids[h]) for h in s["similar"] if h in synset_ids)))
    pairs = set()
    for lemma, pos, senses, _forms in entries:
        for _syn, _sid, ants in senses:
            for a in ants:
                owner = sense_owner.get(a)
                if owner:
                    pairs.add((word_id(lemma), word_id(owner[0])))
                    pairs.add((word_id(owner[0]), word_id(lemma)))
    db.executemany("insert into antonyms values (?,?)", sorted(pairs))

    # --- Moby Thesaurus II ----------------------------------------------------------------------------------------------------------
    moby_roots = 0
    if moby_path:
        progress("Reading the Moby Thesaurus…")
        with open(moby_path, "rb") as f:
            text = f.read().decode("latin-1")
        for line in text.splitlines():
            line = line.strip()
            if not line or "," not in line:
                continue
            root, *syns = [p.strip() for p in line.split(",")]
            if not root or not syns:
                continue
            db.execute("insert or replace into moby values (?,?)", (word_id(root), pack_ids([word_id(s) for s in syns if s])))
            moby_roots += 1
    db.executemany("insert into words values (?,?)", [(i, w) for w, i in ids.items()])
    meta = {"schema": str(SCHEMA_VERSION), "wordnet": "Open English WordNet 2025 (CC BY 4.0)",
            "moby": "Moby Thesaurus II by Grady Ward (public domain)" if moby_path else ""}
    db.executemany("insert into meta values (?,?)", list(meta.items()))
    db.commit()
    counts = {"words": len(ids), "synsets": len(synsets), "moby_roots": moby_roots}
    db.execute("vacuum")
    db.close()
    tmp.replace(out_path)
    progress("Done.")
    return counts


def download(url, dest, progress=lambda msg: None):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    progress(f"Downloading {url} …")
    try:
        with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
    except OSError as e:
        raise DictionaryBuildError(f"Couldn't download {url}: {e}")
    return dest


def install(out_path, work_dir, progress=lambda msg: None):
    """Download both sources and build the index. The only network use in storywheel, and only when you ask for it."""
    work = Path(work_dir)
    oewn = download(OEWN_URL, work / "oewn.xml.gz", progress)
    moby = download(MOBY_URL, work / "mthesaur.txt", progress)
    counts = build(oewn, moby, out_path, progress)
    shutil.rmtree(work, ignore_errors=True)
    return counts
