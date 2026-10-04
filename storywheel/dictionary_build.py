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
SCHEMA_VERSION = 3

SCHEMA = """
create table meta (key text primary key, value text);
create table words (id integer primary key, w text not null);
create unique index words_w on words (w);
create table forms (form text not null, word_id integer not null);
create index forms_form on forms (form);
create table senses (word_id integer not null, pos text not null, synset_id integer not null, ord integer not null);
create index senses_word on senses (word_id, pos, ord);
create table synsets (id integer primary key, pos text not null, defn text not null, ex text not null,
                      members text not null, hyper text not null, similar text not null, lex text not null default '');
create table rels (synset_id integer not null, kind text not null, target integer not null);
create index rels_synset on rels (synset_id, kind);
create table related (word_id integer not null, other_id integer not null, kind text not null);
create index related_word on related (word_id);
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
                    links = [(r.get("relType"), r.get("target")) for r in s.findall("SenseRelation")
                             if r.get("relType") in ("derivation", "pertainym", "participle")]
                    senses.append((s.get("synset"), s.get("id"), ants, links))
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
                    "hyper": rels.get("hypernym", []), "similar": rels.get("similar", []), "rels": rels,
                    "lex": el.get("lexfile") or "",
                }
                el.clear()
    if not entries or not synsets:
        raise DictionaryBuildError("That WordNet file has no entries (is it the OEWN .xml or .xml.gz release?).")
    for n, key in enumerate(sorted(synsets), 1):
        synset_ids[key] = n
    progress(f"Writing {len(entries):,} words and {len(synsets):,} meanings…")
    for lemma, pos, senses, forms in entries:
        wid = word_id(lemma)
        for order, (syn, _sid, _ants, _links) in enumerate(senses):
            if syn in synset_ids:
                db.execute("insert into senses values (?,?,?,?)", (wid, pos, synset_ids[syn], order))
        for form in forms:
            f = form.lower()
            if f != lemma.lower():
                db.execute("insert into forms values (?,?)", (f, wid))
    by_synset = {}
    for lemma, pos, senses, _forms in entries:
        for syn, _sid, _a, _l in senses:
            by_synset.setdefault(syn, []).append(lemma)
    for key, s in synsets.items():
        member_ids = ",".join(str(word_id(w)) for w in by_synset.get(key, []))
        db.execute("insert into synsets values (?,?,?,?,?,?,?,?)", (
            synset_ids[key], s["pos"], s["defn"], "\x1f".join(s["ex"]), member_ids,
            ",".join(str(synset_ids[h]) for h in s["hyper"] if h in synset_ids),
            ",".join(str(synset_ids[h]) for h in s["similar"] if h in synset_ids), s["lex"]))
    pairs, links = set(), set()
    for lemma, pos, senses, _forms in entries:
        for _syn, _sid, ants, sense_links in senses:
            for a in ants:
                owner = sense_owner.get(a)
                if owner:
                    pairs.add((word_id(lemma), word_id(owner[0])))
                    pairs.add((word_id(owner[0]), word_id(lemma)))
            for kind, target in sense_links:
                owner = sense_owner.get(target)
                if owner and owner[0].lower() != lemma.lower():
                    links.add((word_id(lemma), word_id(owner[0]), kind))
    db.executemany("insert into antonyms values (?,?)", sorted(pairs))
    db.executemany("insert into related values (?,?,?)", sorted(links))
    kept = ("hypernym", "hyponym", "mero_part", "mero_substance", "mero_member", "holo_part", "holo_substance", "holo_member",
            "domain_topic", "has_domain_topic", "also", "attribute", "entails", "causes", "similar")
    rows = []
    for key, s in synsets.items():
        for kind in kept:
            for target in s["rels"].get(kind, []):
                if target in synset_ids:
                    rows.append((synset_ids[key], kind, synset_ids[target]))
    db.executemany("insert into rels values (?,?,?)", rows)

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
    from . import download as dl
    try:
        return dl.fetch(url, dest, progress)
    except dl.DownloadError as e:
        raise DictionaryBuildError(str(e))


def sources_dir(out_path):
    """Where the downloaded sources are kept, next to the index, so a newer index format can be built without the network."""
    return Path(out_path).parent / "dictionary-sources"


def kept_sources(out_path):
    """(oewn path, moby path) if both are kept, else None."""
    work = sources_dir(out_path)
    oewn, moby = work / "oewn.xml.gz", work / "mthesaur.txt"
    return (oewn, moby) if oewn.exists() and oewn.stat().st_size > 0 and moby.exists() and moby.stat().st_size > 0 else None


def rebuild_from_sources(out_path, progress=lambda msg: None):
    """Build the index again from the kept sources, offline. Returns the counts, or None when the sources are not there."""
    kept = kept_sources(out_path)
    if not kept:
        return None
    return build(kept[0], kept[1], out_path, progress)


def install(out_path, work_dir=None, progress=lambda msg: None):
    """Build the index from the sources, downloading only the ones that are missing (the only network use in storywheel, and only when
    you ask for it). The sources are kept."""
    work = Path(work_dir) if work_dir else sources_dir(out_path)
    oewn, moby = work / "oewn.xml.gz", work / "mthesaur.txt"
    if not (oewn.exists() and oewn.stat().st_size > 0):
        download(OEWN_URL, oewn, progress)
    if not (moby.exists() and moby.stat().st_size > 0):
        download(MOBY_URL, moby, progress)
    counts = build(oewn, moby, out_path, progress)
    install_rhymes(out_path, progress)
    return counts


def install_rhymes(out_path, progress=lambda msg: None):
    """The CMU Pronouncing Dictionary for rhymes: download cmudict.dict (and the repository's LICENSE) if they are not kept, then read it into
    rhymes.sqlite. A failure is reported plainly, remembered (the Rhymes box says it too) and does not undo the dictionary. Returns the number
    of pronunciations, or None when rhymes were NOT installed."""
    from . import rhymes
    folder = sources_dir(out_path)
    src = rhymes.source_in(folder)
    try:
        if not (src.exists() and src.stat().st_size > 0):
            src = folder / rhymes.SOURCE_NAMES[0]
            download(rhymes.CMU_URL, src, progress)
        lic = folder / "cmudict.LICENSE"
        if not (lic.exists() and lic.stat().st_size > 0):
            try:
                download(rhymes.CMU_LICENSE_URL, lic, progress)
            except DictionaryBuildError as e:
                progress(f"The CMU license text could not be fetched ({e}); the file's own header is used if it has one.")
        progress("Reading the CMU Pronouncing Dictionary (rhymes)…")
        n = rhymes.build(src, Path(out_path).with_name("rhymes.sqlite"))
        if not n:
            src.unlink(missing_ok=True)                                  # (a bad file must not be kept: the next install fetches it again)
            raise DictionaryBuildError(f"{src.name} had no pronunciations in it.")
        rhymes.record_failure("")
        progress(f"Rhymes ready: {n:,} pronunciations.")
        return n
    except (DictionaryBuildError, OSError, UnicodeError) as e:
        reason = str(e).strip().rstrip(".") + "."
        rhymes.record_failure(reason)
        progress(f"Rhymes were NOT installed: {reason} The dictionary itself is fine; run  storywheel dictionary install  again to retry.")
        return None
