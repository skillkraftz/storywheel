"""
Story structures: the shape of a story's body, as data.

A structure is an ordered list of beats. Each beat has a key, a label, the
template slot it draws from, and optionally a fixed opener ("Once upon a time, ")
and a closing. The templates behind a beat are ordinary template lists built
from the same atoms as everything else, so a new structure is a JSON file in
storywheel/data/structures/ (or ~/.storywheel/structures/) plus template lists
for its beats.

    { "name": "kishotenketsu", "label": "Kishōtenketsu", "blurb": "...",
      "show_labels": true, "order": 3,
      "beats": [ {"key": "ki", "label": "Ki (introduction)", "slot": "ki"}, ... ] }

`show_labels` puts each beat's label in front of its text in the output; the
Story Spine doesn't need it because its openers already say where you are.
"""
import json
from pathlib import Path

DATA = Path(__file__).parent / "data" / "structures"
DEFAULT = "story-spine"


class StructureError(Exception):
    pass


class Beat:
    def __init__(self, key, slot, label, opening="", closing="."):
        self.key, self.slot, self.label = key, slot, label
        self.opening, self.closing = opening, closing


class Structure:
    def __init__(self, name, label, blurb, beats, show_labels=False, order=100):
        self.name, self.label, self.blurb = name, label, blurb
        self.beats, self.show_labels, self.order = beats, show_labels, order

    @property
    def keys(self):
        return [b.key for b in self.beats]


def _read(path):
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        beats = [Beat(b["key"], b.get("slot", b["key"]), b.get("label", b["key"]),
                      b.get("opening", ""), b.get("closing", ".")) for b in doc["beats"]]
        keys = [b.key for b in beats]
        if not beats or len(set(keys)) != len(keys):
            raise StructureError(f"{path}: needs at least one beat, and beat keys must be unique")
        name = doc.get("name") or path.stem
        return Structure(name, doc.get("label", name), doc.get("blurb", ""), beats, bool(doc.get("show_labels")),
                         doc.get("order", 100))
    except (ValueError, KeyError, TypeError) as e:
        raise StructureError(f"{path}: {e!r} (see structures.py for the format)")


def load(user_dir=None):
    """name -> Structure, from the built-in ones then the user's own (which can replace them)."""
    found = {}
    for root in (DATA, Path(user_dir) / "structures" if user_dir else None):
        if root and root.is_dir():
            for path in sorted(root.glob("*.json")):
                s = _read(path)
                found[s.name] = s
    # by "order" (the default first), then by name
    order = sorted(found, key=lambda n: (n != DEFAULT, found[n].order, n))
    return {n: found[n] for n in order}


_registry = None


def registry():
    global _registry
    if _registry is None:
        from . import paths
        _registry = load(paths.HOME)
    return _registry


def find(text):
    """A structure by name or label, ignoring case, or None."""
    t = (text or "").strip().lower()
    for s in registry().values():
        if t in (s.name.lower(), s.label.lower()):
            return s
    return None


def get(text):
    """Like find, but an unknown or missing name gives the Story Spine."""
    return find(text) or registry()[DEFAULT]


def beat_labels():
    return {b.key: b.label for s in registry().values() for b in s.beats}
