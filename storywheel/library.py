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


class Entry:
    __slots__ = ("text", "tags", "kind")

    def __init__(self, text, tags=(), kind=None):
        self.text = text
        self.tags = tuple(norm_tag(t) for t in tags)
        self.kind = kind                      # object, person, place, creature or idea; None if unsaid

    def __repr__(self):
        return f"Entry({self.text!r}, {list(self.tags)})"


class WordList:
    """One JSON file: entries for one slot, plus tags describing their flavor."""

    def __init__(self, id, slot, tags, entries=(), generator=None, markov=0.0):
        self.id = id                          # e.g. "job/frontier-trades"
        self.slot = slot
        self.tags = tuple(norm_tag(t) for t in tags)
        self.entries = list(entries)
        self.generator = generator            # e.g. "faker.city"; None for a plain list
        self.markov = markov                  # share of picks invented by a name maker trained on the entries

    def __repr__(self):
        return f"WordList({self.id!r}, tags={list(self.tags)})"


def _read_list(path, root):
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
    list_kind = doc.get("kind")
    if list_kind is not None and list_kind not in KINDS:
        raise DataError(f'{path}: "kind" should be one of {", ".join(KINDS)}')
    entries = []
    for raw in doc.get("entries", []):
        if isinstance(raw, str):
            entries.append(Entry(raw, kind=list_kind))
        elif isinstance(raw, dict) and "text" in raw:
            kind = raw.get("kind", list_kind)
            if kind is not None and kind not in KINDS:
                raise DataError(f'{path}: entry {raw["text"]!r} has kind {kind!r}; use one of {", ".join(KINDS)}')
            entries.append(Entry(raw["text"], raw.get("tags", []), kind))
        else:
            raise DataError(f'{path}: bad entry {raw!r} (use "text" or {{"text": ..., "tags": [...]}})')
    if not entries and not generator:
        raise DataError(f'{path}: needs "entries" (or a "generator")')
    try:
        markov = float(doc.get("markov", 0))
    except (TypeError, ValueError):
        raise DataError(f'{path}: "markov" should be a number between 0 and 1')
    if markov and not entries:
        raise DataError(f'{path}: "markov" needs entries to learn from')
    return WordList(list_id, slot, tags, entries, generator, markov)


def load_lists(roots):
    """Read every *.json under each root. Later roots replace earlier ones by path."""
    found = {}
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            wl = _read_list(path, root)
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
    return profiles, default, doc.get("_floor"), floors


class Library:
    """Everything loaded from disk: lists by slot, genre profiles, the floor."""

    def __init__(self, lists, profiles, default_profile=None, floor=DEFAULT_FLOOR, floors=None):
        self.lists = lists                                  # id -> WordList
        self.profiles = profiles                            # genre -> {tag: weight}
        self.default_profile = default_profile or {"general": 1.0}
        self.floor = floor                                  # wildcard share for one-off slots
        self.floors = floors or {}                          # slot -> its own (usually lower) share
        self.by_slot = {}
        for wl in lists.values():
            self.by_slot.setdefault(wl.slot, []).append(wl)

    @classmethod
    def load(cls, user_dir=None):
        roots = [DATA / "lists", DATA / "templates"]
        profiles, default, floor, floors = _read_profiles(DATA / "genres.json")
        if user_dir:
            user_dir = Path(user_dir)
            roots += [user_dir / "lists", user_dir / "templates"]
            if (user_dir / "genres.json").exists():
                more, more_default, more_floor, more_floors = _read_profiles(user_dir / "genres.json")
                profiles.update(more)
                default = more_default or default
                floor = more_floor if more_floor is not None else floor
                floors.update(more_floors)
        return cls(load_lists(roots), profiles, default,
                   DEFAULT_FLOOR if floor is None else float(floor), floors)

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
