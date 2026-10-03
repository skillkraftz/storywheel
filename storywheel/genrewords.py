"""The "From the Wheel" lists of the Genre words tab: the generator's own short lists (first and last names, jobs, places, things) by genre,
to borrow from. (The long lists of nouns, verbs, adjectives and adverbs are `wordlists`.)

`rows` lists the entries of the chosen genres, each with its genre tags; `more_names` invents new names with the same Markov name
maker the generator uses; `add_to_universe` turns a name into a character, a place into a place, a thing into a thing, or puts any
word on the universe's own generator list. Nothing here changes the built-in data."""
import random
from collections import namedtuple

from . import markov, vault, wordbank

# (key, label, atom slots, frame slots, entity type a word of it becomes). Frames are whole phrases such as a flaw or a want.
CATEGORIES = [
    ("first_name", "First names", ("first_name",), (), "character"),
    ("last_name", "Last names", ("last_name",), (), "character"),
    ("job", "Jobs", ("job",), (), None),
    ("place", "Places", ("place", "landmark"), (), "place"),
    ("thing", "Things", ("thing",), (), "thing"),
]
NAME_CATEGORIES = {"first_name", "last_name"}
GENERAL = "general"

Row = namedtuple("Row", "text tags list_id slot frame")


def category(key):
    return next(c for c in CATEGORIES if c[0] == key)


def labels():
    return [(c[1], c[0]) for c in CATEGORIES]


def genres(library):
    """The genres you can browse: every profile, plus 'general' (the neutral lists)."""
    return sorted(library.profiles) + [GENERAL]


def genre_tags(genre):
    return {genre.strip().lower()}


def _wanted(chosen):
    out = set()
    for g in chosen:
        out |= genre_tags(g)
    return out


def rows(library, chosen, key, query=""):
    """The entries of `chosen` genres in a category, alphabetical, each with the genre tags it carries. `query` keeps rows containing it.
    Patterns that need other slots filled ("{PLACE_ADJ} {PLACE_FEATURE}") are left out of atom lists."""
    _key, _label, atom_slots, frame_slots, _etype = category(key)
    want, q = _wanted(chosen), (query or "").strip().lower()
    out, seen = [], set()
    for frame, slots in ((False, atom_slots), (True, frame_slots)):
        for slot in slots:
            for wl in library.by_slot.get(slot, []):
                if wl.generator or wl.id.startswith("universe"):
                    continue
                for e in wl.entries:
                    tags = e.tags or wl.tags
                    if want and not (want & set(tags)):
                        continue
                    if not frame and "{" in e.text:
                        continue
                    if q and q not in e.text.lower():
                        continue
                    if (slot, e.text) in seen:
                        continue
                    seen.add((slot, e.text))
                    out.append(Row(e.text, tuple(tags), wl.id, slot, frame))
    out.sort(key=lambda r: (r.text.lower(), r.slot))
    return out


def tag_label(tags, chosen=()):
    """The genre tags of a row, shortest first, the chosen genres leading."""
    mine = [t for t in tags if t in {c.lower() for c in chosen}]
    rest = [t for t in tags if t not in mine]
    return ", ".join(mine + rest)


def more_names(library, chosen, key, n=12, seed=None, reject=()):
    """New names for a name category, invented by the name maker trained on the chosen genres' names (the same maker the generator uses).
    Returns [] if there are too few names to learn from."""
    if key not in NAME_CATEGORIES:
        return []
    training = [r.text for r in rows(library, chosen, key) if " " not in r.text and r.text.isalpha()]
    if len(training) < 12:
        return []
    maker = markov.NameMaker(training)
    rng = random.Random(seed)
    out = []
    for _ in range(n * 6):
        name = maker.make(rng, reject=reject)
        if name and name.capitalize() not in out:
            out.append(name.capitalize())
        if len(out) >= n:
            break
    return out


def entity_type(key, row_slot=None):
    """The kind of entity a word of this category becomes, or None (then it goes on the generator list)."""
    et = category(key)[4]
    if et == "note":
        return None
    return et


def add_to_universe(universe, key, text, slot):
    """Add a word to a universe. A name becomes a character, a place a place, a thing a thing (new, with that name); anything else
    goes on the universe's own generator list for its slot. Returns (what happened in words, entity or None)."""
    etype = entity_type(key)
    if etype:
        existing = universe.find_by_name(text, etype)
        if existing:
            return f"{text} is already a {etype} in {universe.name}.", existing[0]
        fields = {}
        if etype == "character":
            fields["role"] = "supporting"
        e = universe.new_entity(etype, text, fields)
        return f"Made a {etype}, {text}, in {universe.name}.", e
    path, new = wordbank.add_to_universe_list(universe, text, slot)
    return (f"Added {text} to {universe.name}'s '{slot}' list." if new else f"{text} was already on the '{slot}' list."), None
