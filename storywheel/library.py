"""
Loading the JSON data: word lists, templates and genre profiles.

Built-in data lives in storywheel/data/. Your own lists go in
~/.storywheel/lists/ (and templates in ~/.storywheel/templates/). They are
merged with the built-in ones; a file with the same path as a built-in one
replaces it.

A list file looks like:

    { "slot": "job", "tags": ["western", "historical"],
      "entries": ["drover", "marshal", {"text": "bounty hunter", "tags": ["noir"]}] }

or, for a generated list, `"generator": "faker.job"` instead of entries.

Atoms can also carry FEATURES (what they are: "buryable", "magic", "human"...) and,
for verbs, requirements on their SUBJECT and OBJECT. See frames.py for the vocabulary:

    {"text": "buried", "object": ["buryable"]}
    {"text": "enchanted", "subject": ["magic"], "object": ["!living"]}
    {"text": "a black stallion", "features": ["living"]}

A list can set defaults for all its entries with "features", "subject" and "object". An entry's own
"features" replace the list's; its "subject" and "object" requirements are added to the list's.
"""
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"
DEFAULT_FLOOR = 0.12


class DataError(Exception):
    pass


def norm_tag(tag):
    return str(tag).strip().lower()


KINDS = ("object", "person", "place", "creature", "idea")


# What an atom is assumed to be when its file doesn't say. Anything else must be declared.
SLOT_FEATURES = {
    "thing": ("portable", "buryable"),
    "someone": ("human",), "close": ("human", "friendly"), "rival": ("human",),
    "landmark": ("outdoor",),
    "message": ("physical",),
}


class Entry:
    __slots__ = ("text", "tags", "kind", "features", "subject", "object")

    def __init__(self, text, tags=(), kind=None, features=None, subject=(), object=()):
        self.text = text
        self.tags = tuple(norm_tag(t) for t in tags)
        self.kind = kind                      # object, person, place, creature or idea; None if unsaid
        self.features = None if features is None else tuple(features)   # what it is; None = unknown (generated)
        self.subject = tuple(subject)         # what a verb needs of its subject
        self.object = tuple(object)           # ... and of its object

    def __repr__(self):
        return f"Entry({self.text!r}, {list(self.tags)})"


class WordList:
    """One JSON file: entries for one slot, plus tags describing their flavor."""

    def __init__(self, id, slot, tags, entries=(), generator=None, markov=0.0, is_template=False):
        self.id = id                          # e.g. "job/frontier-trades"
        self.slot = slot
        self.tags = tuple(norm_tag(t) for t in tags)
        self.entries = list(entries)
        self.generator = generator            # e.g. "faker.city"; None for a plain list
        self.is_template = is_template        # lives under templates/: whole sentences with slots, not atoms
        self.markov = markov                  # share of picks invented by a name maker trained on the entries

    def __repr__(self):
        return f"WordList({self.id!r}, tags={list(self.tags)})"


def _read_list(path, root, is_template=False):
    list_id = path.relative_to(root).with_suffix("").as_posix()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise DataError(f"{path}: not valid JSON ({e})")
    if not isinstance(doc, dict):
        raise DataError(f"{path}: expected a JSON object")
    slot = doc.get("slot") or path.parent.name
    tags = doc.get("tags", [])
    if not isinstance(tags, list):
        raise DataError(f'{path}: "tags" should be a list like ["western", "rural"]')
    generator = doc.get("generator")
    list_features = doc.get("features", SLOT_FEATURES.get(slot, () if not is_template else None))
    list_subject, list_object = doc.get("subject", []), doc.get("object", [])
    list_kind = doc.get("kind")
    if list_kind is not None and list_kind not in KINDS:
        raise DataError(f'{path}: "kind" should be one of {", ".join(KINDS)}')
    entries = []
    for raw in doc.get("entries", []):
        if isinstance(raw, str):
            entries.append(Entry(raw, kind=list_kind, features=list_features,
                                 subject=list_subject, object=list_object))
        elif isinstance(raw, dict) and "text" in raw:
            kind = raw.get("kind", list_kind)
            if kind is not None and kind not in KINDS:
                raise DataError(f'{path}: entry {raw["text"]!r} has kind {kind!r}; use one of {", ".join(KINDS)}')
            entries.append(Entry(raw["text"], raw.get("tags", []), kind,
                                 raw.get("features", list_features),
                                 list(list_subject) + list(raw.get("subject", [])),     # a list's requirements
                                 list(list_object) + list(raw.get("object", []))))      # add to the entry's own
        else:
            raise DataError(f'{path}: bad entry {raw!r} (use "text" or {{"text": ..., "tags": [...]}})')
    if not entries and not generator:
        raise DataError(f'{path}: needs "entries" (or a "generator")')
    from . import frames
    for e in entries:                                   # catch typos in the feature vocabulary
        for problem in frames.check_vocabulary(e):
            raise DataError(f"{path}: {e.text!r}: {problem}")
    try:
        markov = float(doc.get("markov", 0))
    except (TypeError, ValueError):
        raise DataError(f'{path}: "markov" should be a number between 0 and 1')
    if markov and not entries:
        raise DataError(f'{path}: "markov" needs entries to learn from')
    return WordList(list_id, slot, tags, entries, generator, markov, is_template)


def load_lists(roots):
    """Read every *.json under each root. Later roots replace earlier ones by path."""
    found = {}
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            wl = _read_list(path, root, root.name == "templates")
            found[wl.id] = wl
    return found


def _read_profiles(path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    profiles = {}
    for name, weights in doc.items():
        if not name.startswith("_"):
            profiles[name.strip().lower()] = {norm_tag(t): float(w) for t, w in weights.items()}
    default = {norm_tag(t): float(w) for t, w in doc.get("_default", {}).items()}
    floors = {slot: float(f) for slot, f in doc.get("_floors", {}).items()}
    neighbors = {name.strip().lower(): [norm_tag(t) for t in tags] for name, tags in doc.get("_neighbors", {}).items()}
    return profiles, default, doc.get("_floor"), floors, neighbors


class Library:
    """Everything loaded from disk: lists by slot, genre profiles, the floor."""

    def __init__(self, lists, profiles, default_profile=None, floor=DEFAULT_FLOOR, floors=None, neighbors=None):
        self.lists = lists                                  # id -> WordList
        self.profiles = profiles                            # genre -> {tag: weight}
        self.default_profile = default_profile or {"general": 1.0}
        self.floor = floor                                  # wildcard share for one-off slots
        self.floors = floors or {}                          # slot -> its own (usually lower) share
        self.neighbors = neighbors or {}                    # genre -> tags of the genres whose lists the floor may draw from
        self.own_slots = {}                                 # genre -> slots where the floor is off (only its own and the general lists)
        self.tech = {}                                      # genre -> "modern" or "period": the technology its stories assume
        self.ages = {}                                      # genre -> (youngest, oldest) protagonist; "_default" for the rest
        self.by_slot = {}
        for wl in lists.values():
            self.by_slot.setdefault(wl.slot, []).append(wl)

    @classmethod
    def load(cls, user_dir=None, extra_roots=()):
        """Built-in data, then your own in user_dir, then `extra_roots` (a universe's own lists folder)."""
        roots = [DATA / "lists", DATA / "templates"]
        profiles, default, floor, floors, neighbors = _read_profiles(DATA / "genres.json")
        if user_dir:
            user_dir = Path(user_dir)
            roots += [user_dir / "lists", user_dir / "templates"]
            if (user_dir / "genres.json").exists():
                more, more_default, more_floor, more_floors, more_neighbors = _read_profiles(user_dir / "genres.json")
                profiles.update(more)
                default = more_default or default
                floor = more_floor if more_floor is not None else floor
                floors.update(more_floors)
                neighbors.update(more_neighbors)
        roots += [Path(r) for r in extra_roots]
        lib = cls(load_lists(roots), profiles, default,
                  DEFAULT_FLOOR if floor is None else float(floor), floors, neighbors)
        docs = [json.loads((DATA / "genres.json").read_text(encoding="utf-8"))]
        if user_dir and (Path(user_dir) / "genres.json").exists():
            docs.append(json.loads((Path(user_dir) / "genres.json").read_text(encoding="utf-8")))
        for doc in docs:
            lib.own_slots.update({k.strip().lower(): list(v) for k, v in doc.get("_own_slots", {}).items()})
            lib.tech.update({k.strip().lower(): v for k, v in doc.get("_tech", {}).items()})
            lib.ages.update({k.strip().lower(): (int(v[0]), int(v[1])) for k, v in doc.get("_ages", {}).items() if not k.startswith("_note")})
        return lib

    def replace_lists(self, prefix, new_lists):
        """Swap every list whose id starts with `prefix` for `new_lists` (used for universe atoms)."""
        for list_id in [i for i in self.lists if i.startswith(prefix)]:
            del self.lists[list_id]
        for wl in new_lists:
            self.lists[wl.id] = wl
        self.by_slot = {}
        for wl in self.lists.values():
            self.by_slot.setdefault(wl.slot, []).append(wl)

    @property
    def genre_names(self):
        return list(self.profiles)

    def has_slot(self, slot):
        return slot in self.by_slot

    def all_tags(self):
        tags = set()
        for wl in self.lists.values():
            tags.update(wl.tags)
            for e in wl.entries:
                tags.update(e.tags)
        for p in self.profiles.values():
            tags.update(p)
        return sorted(tags)
