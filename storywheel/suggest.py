"""Suggestions for a story's words, from the dictionary and the genre fit (see `genrefit`). Three lists, each a list of row dicts
(word, pos, definition, mark, fit, note, word_id; a "head" row introduces a group):

    for_story(...)               words that fit the story's genres and are not in its manuscript yet, for one part of speech
    for_entities(...)            words the dictionary relates to your characters' jobs and your things, places and groups
    fresh_alternatives(...)      the story's most overused words, each with replacements that fit the genres

Nothing here changes anything; the rows have the same actions as Genre words (look up, copy, use in the Writer, learn)."""
import re

from . import dictionary, genrefit, learn, overused, wordlists

MAX_ZIPF = 500            # x100: words more everyday than this are not worth suggesting
MIN_FIT = 35
TOKEN = re.compile(r"[a-z][a-z'-]*[a-z]|[a-z]")
POS_OF = {"n": "n", "v": "v", "a": "a", "s": "a", "r": "r"}
RELATIONS = {"synonym": 1.0, "related form": 0.9, "similar": 0.7, "broader": 0.6, "narrower": 0.6, "part or whole": 0.5, "also": 0.4}


def story_genres(universe, story):
    """The genres to suggest for: the story's own (its outline's genre), else the universe's leanings, else none."""
    chosen = []
    if story is not None:
        try:
            meta, _sections = story.load_outline()
            chosen = [g.strip().lower() for g in str(meta.get("genre", "")).replace(",", "/").split("/") if g.strip()]
        except Exception:
            chosen = []
    if not chosen and universe is not None:
        chosen = [g.lower() for g in universe.settings().get("genres", [])]
    return [g for g in chosen if g != "general"]


def used_forms(story, db=None):
    """Every word of the manuscript and the base words it could be a form of (running -> run, ran -> run), lowercase."""
    out = set()
    unique = {tok[0] for tok in overused.tokens(story)}
    try:
        db = db or dictionary.connect()
    except dictionary.DictionaryMissing:
        db = None
    for tok in unique:
        out.add(tok)
        out.update(dictionary.candidates(tok))
        if db is not None:                                                      # irregular forms: ran, geese, better
            for (w,) in db.execute("select w.w from forms f join words w on w.id = f.word_id where f.form = ?", (tok,)):
                out.add(w)
    return out


def _row(db, word, pos, wid, synset, fits, note="", head=False):
    defn = db.execute("select defn from synsets where id = ?", (synset,)).fetchone()
    fit = fits.get(wid, 0)
    return {"word": word, "pos": wordlists.POS_NAMES.get(pos, pos), "definition": learn.simple_definition(defn[0] if defn else ""),
            "fit": fit, "mark": wordlists.marker(fit) if fits else "", "note": note, "word_id": wid, "head": head, "zipf": 0}


def _fits(db, genres, pos=None):
    if not genres or not wordlists.ready(db):
        return {}
    marks = ",".join("?" * len(genres))
    args = list(genres)
    sql = f"select word_id, max(score) from fit where genre in ({marks})"
    if pos:
        sql += " and pos = ?"
        args.append(pos)
    return dict(db.execute(sql + " group by word_id", args))


def _zipf(db):
    """{(word id, pos): zipf x 100} (empty when the index has no lexicon yet)."""
    if not wordlists.ready(db):
        return {}
    return {(w, p): z for w, p, z in db.execute("select word_id, pos, zipf from lexicon")}


# --- 1. for this story -------------------------------------------------------------------------------------------------------------

def for_story(universe, story, pos="a", limit=300, db=None, genres=None):
    """High-fit words of the story's genres that its manuscript does not use yet, in one part of speech."""
    db = db or dictionary.connect()
    genres = genres if genres is not None else story_genres(universe, story)
    if not genres or not wordlists.ready(db):
        return []
    used = used_forms(story, db) if story is not None else set()
    view = wordlists.View(pos, genres, "any", "fit", db=db)
    out, start = [], 0
    while len(out) < limit and start < len(view):
        page = view.page(start, 200)
        start += 200
        if not page:
            break
        for r in page:
            if r["fit"] < MIN_FIT:
                return out
            w = r["word"]
            if " " in w or w in used or r["zipf"] * 100 >= MAX_ZIPF or len(w) < 4:
                continue
            out.append(dict(r, note="fits " + ", ".join(genres), head=False))
            if len(out) >= limit:
                break
    return out


# --- 2. for your characters and places ---------------------------------------------------------------------------------------------

def entity_sources(universe):
    """[(label, text)]: the words that stand for each entity: a character's job, a thing's, place's or group's name."""
    out = []
    for e in universe.entities():
        if e.type == "character":
            job = (e.fields.get("job") or "").strip()
            if job:
                out.append((f"{e.name or 'a character'}, {job}", job))
        elif e.type in ("thing", "place", "group") and (e.name or "").strip():
            out.append((e.name, e.name))
            if e.type == "place" and (e.fields.get("feature") or "").strip():
                out.append((f"{e.name}: {e.fields['feature']}", e.fields["feature"]))
    return out


def _tokens(text):
    return [w.strip("'-") for w in TOKEN.findall((text or "").lower()) if len(w.strip("'-")) >= 3 and w not in genrefit.STOP and w not in ("the", "and")]


def related_words(db, wid):
    """[(other word id, other word, pos, synset it was reached by, relation)]: what the dictionary says is near this word."""
    senses = db.execute("select synset_id, pos from senses where word_id = ? order by ord limit 4", (wid,)).fetchall()
    out = []
    for syn, pos in senses:
        group = POS_OF.get(pos, pos)
        row = db.execute("select members, hyper, similar from synsets where id = ?", (syn,)).fetchone()
        if not row:
            continue
        members, _hyper, similar = row
        for m in (int(x) for x in members.split(",") if x):
            out.append((m, group, syn, "synonym"))
        for m in _members_of(db, [int(x) for x in similar.split(",") if x]):
            out.append((m, group, syn, "similar"))
        for kind, relation in (("hypernym", "broader"), ("hyponym", "narrower"), ("mero_part", "part or whole"), ("holo_part", "part or whole"),
                               ("mero_member", "part or whole"), ("holo_member", "part or whole"), ("also", "also")):
            targets = [t for (t,) in db.execute("select target from rels where synset_id = ? and kind = ?", (syn, kind))]
            for m in _members_of(db, targets):
                out.append((m, group, syn, relation))
    for other, kind in db.execute("select other_id, kind from related where word_id = ? and kind != 'participle'", (wid,)):
        out.append((other, None, None, "related form"))
    return out


def _members_of(db, synsets):
    ids = []
    for s in synsets:
        row = db.execute("select members from synsets where id = ?", (s,)).fetchone()
        if row:
            ids += [int(x) for x in row[0].split(",") if x]
    return ids


def for_entities(universe, story, limit=300, db=None):
    """Words related, through the dictionary, to the jobs, things, places and groups of the universe, not used in the manuscript yet."""
    db = db or dictionary.connect()
    used = used_forms(story, db) if story is not None else set()
    zipf = _zipf(db)
    words = dict(db.execute("select id, w from words"))
    best = {}
    for label, text in entity_sources(universe):
        sources = set()
        for tok in _tokens(text):
            for wid, w, _note in dictionary.base_words(db, tok):
                sources.add((wid, w))
        for wid, source in sources:
            for other, pos, syn, relation in related_words(db, wid):
                w = words.get(other)
                if not w or w == source or " " in w or "-" in w or len(w) < 4 or w in used or not w.isalpha():
                    continue
                if pos is None:                                                 # a related form: find its first meaning
                    first = db.execute("select synset_id, pos from senses where word_id = ? order by ord limit 1", (other,)).fetchone()
                    if not first:
                        continue
                    syn, pos = first[0], POS_OF.get(first[1], first[1])
                z = zipf.get((other, pos), 0)
                if z >= MAX_ZIPF:
                    continue
                score = RELATIONS[relation] + min(z, 480) / 1000.0
                key = (w, pos)
                if key not in best or score > best[key][0]:
                    best[key] = (score, other, syn, f"{relation} of {source}: {label}")
    rows = []
    for (w, pos), (score, other, syn, note) in sorted(best.items(), key=lambda kv: (-kv[1][0], kv[0][0]))[:limit]:
        row = _row(db, w, pos, other, syn, {}, note)
        row["zipf"] = zipf.get((other, pos), 0) / 100
        rows.append(row)
    return rows


# --- 3. fresh alternatives ---------------------------------------------------------------------------------------------------------

def fresh_alternatives(universe, story, top=12, per=6, db=None, genres=None, min_count=3):
    """For each of the story's most overused words, replacements the dictionary offers, the ones that fit the genres first."""
    db = db or dictionary.connect()
    if story is None:
        return []
    genres = genres if genres is not None else story_genres(universe, story)
    used = used_forms(story, db)
    zipf = _zipf(db)
    words = dict(db.execute("select id, w from words"))
    entity_words = set()
    for e in universe.entities() if universe is not None else []:
        entity_words.update(_tokens(e.name))
    frequent = [f for f in overused.frequent(story, top=top * 3, min_count=min_count) if f["word"] not in entity_words][:top]
    overused_words = {f["word"] for f in frequent} | {form for f in frequent for form in f["forms"]}
    rows = []
    for f in frequent:
        candidates = {}
        for wid, lemma, _note in dictionary.base_words(db, f["word"]):
            fits = _fits(db, genres)
            for other, pos, syn, relation in related_words(db, wid):
                w = words.get(other)
                if relation in ("part or whole", "also", "broader", "related form") or pos is None:
                    continue                                                     # a replacement means the same, or something more specific
                if not w or w == lemma or " " in w or len(w) < 3 or w in overused_words or w in used and zipf.get((other, pos), 0) < 300:
                    continue
                z = zipf.get((other, pos), 0)
                if z >= 600 or z and z < 150:
                    continue
                score = fits.get(other, 0) / 100.0 * 2 + RELATIONS[relation] + min(z, 450) / 1000.0
                key = (w, pos)
                if key not in candidates or score > candidates[key][0]:
                    candidates[key] = (score, other, syn, fits)
        best = sorted(candidates.items(), key=lambda kv: (-kv[1][0], kv[0][0]))[:per]
        head = {"word": f["word"], "pos": "", "definition": f"used {f['count']} times; forms: {', '.join(f['forms'][:4])}", "fit": 0, "mark": "",
                "note": "", "word_id": 0, "head": True, "zipf": 0}
        rows.append(head)
        for (w, pos), (score, other, syn, fits) in best:
            row = _row(db, w, pos, other, syn, fits, f"instead of {f['word']} (×{f['count']})")
            row["zipf"] = zipf.get((other, pos), 0) / 100
            rows.append(row)
    return rows
