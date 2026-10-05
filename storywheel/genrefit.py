"""Genre fit: how well each dictionary word belongs to each genre, worked out once and kept in the dictionary index.

Seeds are the words the generator itself uses for a genre: the atoms of every list tagged with the genre, and the fixed words of its
sentence frames, and a short hand-picked core vocabulary (`data/genre_core.json`, the strongest seeds). Each seed lights up its WordNet meanings (the first meaning most, later ones less), and the glow spreads with a
decaying weight through the meaning's synonyms (they share it), similar-to, also-see, broader and narrower meanings, parts and wholes,
causes and entailments, and, one step, through derivationally related words (storm -> stormy). Words the Moby thesaurus lists beside a
strong seed get a small share. WordNet's subject domains (a meaning "in astronomy") are mapped to genres in `genres.json` (`_domains`)
and give their meanings a fixed share.

The result is three tables in the index:
    lexicon(id, word_id, w, pos, synset_id, zipf)   one row per word and part of speech (n, v, a, r), its first meaning, and how common it is
    fit(genre, word_id, pos, score)                 0..100; absent means no fit
and `meta.fit_stamp`, a hash of everything the result depends on, so it is built again when a genre's lists or the domains change.
Nothing here hides a word: the fit only ranks."""
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict

from . import dictionary

VERSION = 2
KEEP = 0.12                       # scores below this are not stored
DECAY = {"similar": 0.5, "also": 0.4, "hypernym": 0.35, "hyponym": 0.35, "entails": 0.3, "causes": 0.3, "attribute": 0.3,
         "mero_part": 0.25, "mero_substance": 0.25, "mero_member": 0.25, "holo_part": 0.25, "holo_substance": 0.25, "holo_member": 0.25}
DERIVED = 0.45                    # through a derivationally related word
MOBY_SHARE = 0.18                 # of a strong seed's weight, for the words the thesaurus lists beside it
DOMAIN_SHARE = 0.3                # for a meaning that belongs to one of the genre's subject domains (low: the dictionary's subject labels are lumpy, ghost story's were all religion)
CORE_SHARE = 1.0                  # for a word of the genre's hand-picked core vocabulary (data/genre_core.json): the strongest seed there is
SENSE_WEIGHT = (1.0, 0.6, 0.35)   # a seed word lights its first meaning most
RANK_FACTOR = (1.0, 0.8, 0.65, 0.5)   # a word fits a genre less by a meaning that is far down its own list
SKIP_SLOTS = {"first_name", "last_name", "place", "place_stem", "place_end", "close"}
SLOT_POS = {"title_adj": "a", "trait": "a", "job": "n", "thing": "n", "someone": "n", "rival": "n", "landmark": "n", "place_feature": "n",
            "disaster": "n", "message": "n", "title_noun": "n", "vice": "n", "value": "n", "motive": "n", "temptation": "n", "prize": "n",
            **{f"{kind}_{what}": "v" for kind in ("act", "do", "habit") for what in ("person", "thing", "place", "message", "event")}}
OFF_POS = 0.5                     # a seed from a verb list lights its noun meanings half as much, and so on
POS_GROUP = {"n": "n", "v": "v", "a": "a", "s": "a", "r": "r"}
TOKEN = re.compile(r"[a-z][a-z'-]*[a-z]|[a-z]")
STOP = set("""
a about above after again against all almost also always am among an and another any are around as at away back be because been before
being below between both but by came can could did do does done down during each either else even ever every few for from get gets got
had has have having he her here hers him his how however i if in into is it its just like made make many may me might more most much
must my never no nor not now of off often on once one only onto or other our out over own per quite rather said same see she should
since so some such than that the their them then there these they this those though through to too under until up upon us very was we
well were what when where which while who whom whose why will with within without would yet you your
""".split())


FRAME_SHARE = 0.3                 # the fixed words of a sentence frame are scaffolding next to the atoms a genre is made of


def seed_words(library):
    """{genre: Counter(word -> weight)} from the genre's lists (weight = times used) and frames (a third as much); names are left out."""
    out = defaultdict(Counter)
    for wl in library.lists.values():
        if wl.generator or wl.slot in SKIP_SLOTS:
            continue
        for e in wl.entries:
            tags = e.tags or wl.tags
            text = re.sub(r"\{[^{}]*\}", " ", e.text).lower().replace("’", "'")
            words = [w.strip("'-") for w in TOKEN.findall(text)]
            words = [w for w in words if len(w) >= 3 and w not in STOP]
            for tag in tags:
                if tag in library.profiles and tag != "general":
                    for w in words:
                        out[tag][w] += FRAME_SHARE if wl.is_template else 1.0
    return out


def seed_pos(library):
    """{genre: {word: {pos}}}: the part of speech the list a seed comes from says it is (an adjective list, a verb list...)."""
    out = defaultdict(lambda: defaultdict(set))
    for wl in library.lists.values():
        pos = SLOT_POS.get(wl.slot)
        if not pos or wl.generator or wl.is_template:
            continue
        for e in wl.entries:
            tags = e.tags or wl.tags
            text = re.sub(r"\{[^{}]*\}", " ", e.text).lower().replace("’", "'")
            for w in (x.strip("'-") for x in TOKEN.findall(text)):
                for tag in tags:
                    if tag in library.profiles and tag != "general":
                        out[tag][w].add(pos)
    return out


def core_words():
    """{genre: {"a": [adjectives], "v": [verbs]}} from data/genre_core.json (single lowercase words)."""
    from . import library as lib_mod
    try:
        doc = json.loads((lib_mod.DATA / "genre_core.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {g.strip().lower(): {k: [w for w in str(v.get(k, "")).lower().split() if w] for k in ("a", "v")}
            for g, v in doc.items() if not g.startswith("_") and isinstance(v, dict)}


NUMBER_WORDS = set("""zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty
fifty sixty seventy eighty ninety hundred thousand million billion trillion twoscore threescore fourscore third fourth fifth sixth seventh eighth ninth tenth
eleventh twelfth twentieth thirtieth fortieth fiftieth hundredth thousandth""".split())
ROMAN = re.compile(r"^(?=[ivxlcdm]+$)m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$")


def is_browsable(word, zipf=0):
    """Should a dictionary word be offered for browsing and given a genre fit? No numbers or number words made only of numerals ("fifty-four",
    "twoscore", "thirty-first"; "one-eyed" is a word), no Roman numerals the frequency data does not know ("xl", "xiv"), nothing under three letters,
    and no unknown fragment ("liv": a short word the frequency data has never met)."""
    w = (word or "").lower()
    if len(w) < 3 or re.search(r"[^a-z' -]", w):
        return False
    parts = [p for p in re.split(r"[- ]", w) if p]
    if not parts or all(p in NUMBER_WORDS for p in parts) or (len(parts) > 1 and parts[-1] in ("first", "second") and all(p in NUMBER_WORDS for p in parts[:-1])):
        return False
    if zipf <= 150 and ROMAN.match(w):
        return False                                             # ("mix" and "dim" are Roman numerals too, but people use them)
    if zipf == 0 and len(w) <= 4 and " " not in w and "-" not in w:
        return False
    return True


def domain_names(library):
    """{genre: [subject domain words]} from genres.json `_domains` (read again from the file: the library keeps only profiles)."""
    from . import library as lib_mod
    try:
        doc = json.loads((lib_mod.DATA / "genres.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {k.strip().lower(): [w.lower() for w in v] for k, v in (doc.get("_domains") or {}).items()}
    return out


def stamp(library, db):
    """A hash of what the fit is built from: the seed words, the domains, the code version and the index it is built on."""
    h = hashlib.sha1()
    h.update(f"{VERSION}".encode())
    for genre, words in sorted(seed_words(library).items()):
        h.update(genre.encode())
        h.update(",".join(f"{w}:{n:.1f}" for w, n in sorted(words.items())).encode())
    h.update(json.dumps(domain_names(library), sort_keys=True).encode())
    h.update(json.dumps(core_words(), sort_keys=True).encode())
    for genre, hints in sorted(seed_pos(library).items()):
        h.update(f"{genre}:" .encode() + ",".join(f"{w}{''.join(sorted(p))}" for w, p in sorted(hints.items())).encode())
    try:
        meta = dict(db.execute("select key, value from meta"))
        h.update(f"{meta.get('schema')}|{db.execute('select count(*) from words').fetchone()[0]}".encode())
    except sqlite3.Error:
        pass
    return h.hexdigest()[:20]


def has_tables(db):
    try:
        return bool(db.execute("select 1 from sqlite_master where name = 'lexicon'").fetchone()
                    and db.execute("select 1 from sqlite_master where name = 'fit'").fetchone())
    except sqlite3.Error:
        return False


def stale(library=None, db=None):
    """True when the fit tables are missing or were built from other genre material."""
    from .library import Library
    from . import paths
    try:
        db = db or dictionary.connect()
    except dictionary.DictionaryMissing:
        return False
    if not has_tables(db):
        return True
    library = library or Library.load(paths.home())
    have = dict(db.execute("select key, value from meta")).get("fit_stamp")
    return have != stamp(library, db)


def zipf_function():
    try:
        from wordfreq import zipf_frequency
    except ImportError:
        return None
    return lambda w: zipf_frequency(w, "en")


def _rows_for_lexicon(db, zipf):
    first = {}
    for wid, pos, syn, order in db.execute("select word_id, pos, synset_id, ord from senses order by word_id, ord"):
        key = (wid, POS_GROUP.get(pos, pos))
        if key not in first:
            first[key] = syn
    words = dict(db.execute("select id, w from words"))
    out = []
    for (wid, pos), syn in first.items():
        w = words.get(wid, "")
        if not w or re.search(r"[^a-z' -]", w):
            continue                                             # digits and symbols are not words to browse
        z = int(round(100 * zipf(w))) if zipf else 0
        if not is_browsable(w, z if zipf else 1):
            continue                                             # numbers, number words, fragments, anything under three letters
        out.append((wid, w, pos, syn, z))
    out.sort(key=lambda r: (r[2], r[1]))
    return out


def _graph(db):
    """{synset: [(neighbor, weight)]}, members of each synset, and derivation links by word."""
    adj = defaultdict(list)
    for syn, kind, target in db.execute("select synset_id, kind, target from rels"):
        w = DECAY.get(kind)
        if w:
            adj[syn].append((target, w))
    members = {}
    for sid, csv in db.execute("select id, members from synsets"):
        members[sid] = [int(x) for x in csv.split(",") if x]
    deriv = defaultdict(list)
    for wid, other, _kind in db.execute("select word_id, other_id, kind from related"):
        deriv[wid].append(other)
    return adj, members, deriv


def _spread(seed_scores, adj, members, deriv, sense_of, hops=2):
    """Synset scores after spreading `seed_scores` {synset: score}. Each hop multiplies by the edge's weight; a synset keeps its best score."""
    score = dict(seed_scores)
    frontier = dict(seed_scores)
    for hop in range(hops):
        nxt = {}
        for syn, s in frontier.items():
            if s < 0.28 and hop:                                       # only strong lights are carried a second step
                continue
            for target, w in adj.get(syn, ()):
                v = s * w
                if v >= KEEP and v > score.get(target, 0.0):
                    score[target] = nxt[target] = v
            if hop == 0:
                for m in members.get(syn, ()):
                    for other in deriv.get(m, ()):
                        for osyn in sense_of.get(other, ())[:2]:
                            v = s * DERIVED
                            if v >= KEEP and v > score.get(osyn, 0.0):
                                score[osyn] = nxt[osyn] = v
        frontier = nxt
    return score


def _domain_synsets(db, domains):
    """{genre: {synset}} for meanings whose subject domain (or a narrower one) is one of the genre's domain words."""
    word_ids = {w: i for w, i in db.execute("select w, id from words")}
    by_topic = defaultdict(list)
    for syn, target in db.execute("select synset_id, target from rels where kind = 'domain_topic'"):
        by_topic[target].append(syn)
    narrower = defaultdict(list)
    for syn, target in db.execute("select synset_id, target from rels where kind = 'hyponym'"):
        narrower[syn].append(target)
    out = {}
    for genre, names in domains.items():
        topics = set()
        for name in names:
            wid = word_ids.get(name)
            if wid is None:
                continue
            for (syn,) in db.execute("select synset_id from senses where word_id = ?", (wid,)):
                if syn in by_topic or syn in narrower:
                    topics.add(syn)
        wide = set(topics)
        for t in topics:
            wide.update(narrower.get(t, ()))
        got = set()
        for t in wide:
            got.update(by_topic.get(t, ()))
        out[genre] = got
    return out


def build(path, library, progress=lambda m: None, zipf=None):
    """Write lexicon, fit and the stamp into the index at `path`. Takes a minute or two on the full dictionary."""
    zipf = zipf if zipf is not None else zipf_function()
    ro = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        progress("Reading the dictionary…")
        material = seed_words(library)
        hints = seed_pos(library)
        domains = domain_names(library)
        core = core_words()
        lexicon = _rows_for_lexicon(ro, zipf)
        browsable = {(wid, pos) for wid, _w, pos, _s, _z in lexicon}
        adj, members, deriv = _graph(ro)
        sense_of = defaultdict(list)
        for wid, syn, order in ro.execute("select word_id, synset_id, ord from senses order by word_id, ord"):
            sense_of[wid].append(syn)
        sense_pos = dict(ro.execute("select id, pos from synsets"))
        rank, seen_pos = {}, Counter()                                      # how far down a word's list of meanings (of that part of speech) a synset is
        for wid, syn, pos in ro.execute("select s.word_id, s.synset_id, s.pos from senses s order by s.word_id, s.ord"):
            key = (wid, POS_GROUP.get(pos, pos))
            rank[(wid, syn)] = seen_pos[key]
            seen_pos[key] += 1
        dfs = Counter()
        for g, words in material.items():
            dfs.update(set(words))
        n_genres = max(len(material), 1)
        moby_cache = {}
        domain_syns = _domain_synsets(ro, {g: domains.get(g, []) for g in set(material) | set(domains)})
        rows = []
        for genre in sorted(set(material) | set(domain_syns) | set(core)):
            progress(f"Working out which words fit {genre}…")
            seeds = defaultdict(float)
            strong = {}
            for word, count in material.get(genre, {}).items():
                df = dfs[word]
                weight = (1.0, 0.6, 0.3)[df - 1] if df <= 3 else 0.0           # a word every genre uses says nothing about this one
                weight *= min(1.0, 0.6 + 0.4 * count)                          # a frame's scaffolding word counts for less than an atom
                if weight <= 0:
                    continue
                for (wid, _w, _note) in dictionary.base_words(ro, word):
                    senses = sense_of.get(wid, ())
                    poly = 1.0 / (1.0 + 0.15 * (len(senses) - 1))              # a word with thirty meanings points at none of them
                    want = hints.get(genre, {}).get(word, ())
                    for order, syn in enumerate(senses[:3]):
                        fits = not want or POS_GROUP.get(sense_pos.get(syn, ""), "") in want
                        v = weight * poly * SENSE_WEIGHT[order] * (1.0 if fits else OFF_POS)
                        if v > seeds[syn]:
                            seeds[syn] = v
                    strong[wid] = max(strong.get(wid, 0.0), weight * poly)
            for syn in domain_syns.get(genre, ()):
                if DOMAIN_SHARE > seeds[syn]:
                    seeds[syn] = DOMAIN_SHARE
            core_best = {}                                          # (word id, pos) -> 1.0: the hand-picked words themselves
            for pos, words in core.get(genre, {}).items():
                for word in words:
                    for (wid, _w, _note) in dictionary.base_words(ro, word):
                        mine = [syn for syn in sense_of.get(wid, ()) if POS_GROUP.get(sense_pos.get(syn, ""), "") == pos][:3]
                        for order, syn in enumerate(mine):
                            seeds[syn] = max(seeds[syn], CORE_SHARE * (1.0, 0.7, 0.45)[order])
                        if mine:
                            core_best[(wid, pos)] = CORE_SHARE
                            strong[wid] = max(strong.get(wid, 0.0), CORE_SHARE)
            score = _spread(dict(seeds), adj, members, deriv, sense_of)
            best = {}                                               # (word id, pos) -> score
            for syn, s in score.items():
                pos = POS_GROUP.get(sense_pos.get(syn, ""), "")
                for m in members.get(syn, ()):
                    key = (m, pos)
                    v = s * RANK_FACTOR[min(rank.get((m, syn), 0), len(RANK_FACTOR) - 1)]     # the word's own first meaning counts most
                    if v > best.get(key, 0.0):
                        best[key] = v
            best.update({k: max(v, best.get(k, 0.0)) for k, v in core_best.items()})
            for wid, weight in strong.items():
                if weight < 0.6:
                    continue
                if wid not in moby_cache:
                    blob = ro.execute("select blob from moby where word_id = ?", (wid,)).fetchone()
                    moby_cache[wid] = _unpack(blob[0]) if blob else []
                share = MOBY_SHARE * weight
                for other in moby_cache[wid]:
                    for syn in sense_of.get(other, ())[:1]:
                        key = (other, POS_GROUP.get(sense_pos.get(syn, ""), ""))
                        if share > best.get(key, 0.0):
                            best[key] = share
            for (wid, pos), s in best.items():
                if s >= KEEP and pos and (wid, pos) in browsable:
                    rows.append((genre, wid, pos, int(round(min(s, 1.0) * 100))))
        meta_schema = dict(ro.execute("select key, value from meta")).get("schema")
    finally:
        ro.close()
    progress(f"Saving {len(rows):,} genre scores and {len(lexicon):,} words…")
    rw = sqlite3.connect(str(path))
    try:
        rw.executescript("""
        drop table if exists lexicon; drop table if exists fit;
        create table lexicon (id integer primary key, word_id integer not null, w text not null, pos text not null,
                              synset_id integer not null, zipf integer not null);
        create index lexicon_pos_w on lexicon (pos, w);
        create table fit (genre text not null, word_id integer not null, pos text not null, score integer not null);
        create index fit_genre on fit (genre, word_id);
        """)
        rw.executemany("insert into lexicon (word_id, w, pos, synset_id, zipf) values (?,?,?,?,?)",
                       [(wid, w, pos, syn, z) for wid, w, pos, syn, z in lexicon])
        rw.executemany("insert into fit values (?,?,?,?)", rows)
        rw.execute("insert or replace into meta values ('fit_stamp', ?)", (stamp(library, rw),))
        rw.execute("insert or replace into meta values ('fit_zipf', ?)", ("1" if zipf else "0",))
        rw.commit()
    finally:
        rw.close()
    dictionary.forget()
    return {"words": len(lexicon), "scores": len(rows), "schema": meta_schema}


def _unpack(blob):
    from .dictionary_build import unpack_ids
    return unpack_ids(blob)


def ensure(progress=lambda m: None, library=None):
    """Build the fit if it is missing or out of date and a dictionary exists. Returns a message, or None when nothing was needed or possible."""
    from .library import Library
    from . import paths
    if not dictionary.installed():
        return None
    try:
        library = library or Library.load(paths.home())
        if not stale(library):
            return None
        counts = build(dictionary.index_path(), library, progress)
    except (dictionary.DictionaryMissing, OSError, sqlite3.Error) as e:
        return f"The genre fit of the words could not be built: {e}"
    return f"Worked out which of {counts['words']:,} dictionary words fit each genre ({counts['scores']:,} scores)."
