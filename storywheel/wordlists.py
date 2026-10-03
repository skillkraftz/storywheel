"""The dictionary's words as long lists for the Words mode's Genre words tab: every lemma of one part of speech, filtered by how
common it is and by a search, ordered by how well it fits the chosen genres (nothing is hidden by genre), by commonness, or A to Z.

`View` holds only the ordered ids of the rows (a few hundred thousand integers); the rows themselves, with their one-line meaning,
are read a page at a time with `page`, so a list of 120,000 nouns costs a fraction of a second to open and nothing to scroll."""
from . import dictionary, genrefit, learn

POS_LABELS = [("Nouns", "n"), ("Verbs", "v"), ("Adjectives", "a"), ("Adverbs", "r")]
POS_NAMES = {"n": "noun", "v": "verb", "a": "adjective", "r": "adverb"}
BANDS = [("Any commonness", "any"), ("Everyday", "everyday"), ("Uncommon", "uncommon"), ("Rare", "rare"), ("Very rare", "very rare")]
BAND_ZIPF = {            # lowest and highest Zipf frequency x 100 (Vocabulary's bands; everyday and very rare are the open ends)
    "everyday": (380, 10_000), "uncommon": (300, 380), "rare": (230, 300), "very rare": (-1, 230),
}
SORTS = [("Genre fit", "fit"), ("Commonness", "common"), ("A to Z", "az")]
MARKERS = ((60, "●●●"), (35, "●●○"), (15, "●○○"))


def marker(score):
    """A small mark for how well a word fits: three levels, blank when it does not."""
    for floor, mark in MARKERS:
        if score >= floor:
            return mark
    return "···"


def ready(db=None):
    try:
        return genrefit.has_tables(db or dictionary.connect())
    except dictionary.DictionaryMissing:
        return False


def has_frequencies(db=None):
    db = db or dictionary.connect()
    return dict(db.execute("select key, value from meta")).get("fit_zipf") == "1"


def genres_with_fit(db=None):
    db = db or dictionary.connect()
    return [g for (g,) in db.execute("select distinct genre from fit order by genre")]


class View:
    def __init__(self, pos="n", genres=(), band="any", sort="fit", query="", db=None):
        self.db = db or dictionary.connect()
        self.pos, self.genres, self.band, self.query = pos, tuple(genres), band, (query or "").strip().lower()
        self.sort = sort if (sort != "fit" or self.genres) else "common"           # without a genre there is nothing to fit
        self.ids, self.fit_of = [], {}
        self._build()

    def _build(self):
        sql, args = "select id, word_id, zipf, w from lexicon where pos = ?", [self.pos]
        if self.band in BAND_ZIPF:
            low, high = BAND_ZIPF[self.band]
            sql += " and zipf >= ? and zipf < ?"
            args += [low, high]
        if self.query:
            sql += " and w like ? escape '\\'"
            args.append("%" + self.query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
        rows = self.db.execute(sql, args).fetchall()
        if self.genres:
            marks = ",".join("?" * len(self.genres))
            self.fit_of = dict(self.db.execute(
                f"select word_id, max(score) from fit where pos = ? and genre in ({marks}) group by word_id", [self.pos, *self.genres]))
        if self.sort == "az":
            rows.sort(key=lambda r: r[3])
        elif self.sort == "common":
            rows.sort(key=lambda r: (-r[2], r[3]))
        else:
            fit = self.fit_of
            rows.sort(key=lambda r: (-fit.get(r[1], 0), -r[2], r[3]))
        self.ids = [r[0] for r in rows]

    def __len__(self):
        return len(self.ids)

    def page(self, start, n):
        """The rows start..start+n-1 as dicts: word, pos, definition, zipf, fit (0..100), mark, word_id."""
        ids = self.ids[start:start + n]
        if not ids:
            return []
        marks = ",".join("?" * len(ids))
        got = {r[0]: r for r in self.db.execute(
            f"select l.id, l.w, l.word_id, l.zipf, y.defn from lexicon l join synsets y on y.id = l.synset_id where l.id in ({marks})", ids)}
        out = []
        for i in ids:
            _id, w, wid, z, defn = got[i]
            fit = self.fit_of.get(wid, 0)
            out.append({"word": w, "pos": POS_NAMES[self.pos], "definition": learn.simple_definition(defn), "zipf": z / 100,
                        "fit": fit, "mark": marker(fit) if self.genres else "", "word_id": wid})
        return out
