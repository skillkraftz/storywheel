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

A beat with `"repeat": {"min": 1, "max": 4}` can occur that many times in a row (the Story Spine's "Because of that", the Three-Act's rising
action): the writer adds or removes one in the Wheel and in the Builder's outline. The first one keeps the beat's key, later ones are
`key__2`, `key__3`...; min is at least 1.

A screen structure (`"screen": true`, with `"pages"`: its usual length) is for a screenplay: each beat may name its `"act"`, which becomes a
section (`# Act One`) when the script is started from the outline. A story on a screen structure is a screenplay. Screen structures are never
picked at random; you choose one. `"formats"` says which formats a structure fits (formats.py: short-story, novel, feature-film,
short-film); it defaults to the two prose formats, or for a screen structure to feature-film. The pickers offer only the structures that fit.

A beat with `"reframe": true` (kishotenketsu's *ten*) may only reinterpret something already
established in the story: its templates may use threads and the story's own fields, never a fresh
person, object or event.

`show_labels` puts each beat's label in front of its text in the output; the
Story Spine doesn't need it because its openers already say where you are.
"""
import json
from pathlib import Path

DATA = Path(__file__).parent / "data" / "structures"
DEFAULT = "story-spine"


class StructureError(Exception):
    pass


SEP = "__"


def base_key(key):
    """'because_2__3' -> 'because_2'"""
    return key.split(SEP)[0]


def instance_key(base, n):
    return base if n <= 1 else f"{base}{SEP}{n}"


def instance_number(key):
    return int(key.split(SEP)[1]) if SEP in key else 1


class Beat:
    def __init__(self, key, slot, label, opening="", closing=".", reframe=False, repeat=None, act=""):
        self.key, self.slot, self.label = key, slot, label
        self.act = act                # a screen structure's act ("Act One"): the script's top-level section
        self.opening, self.closing = opening, closing
        self.reframe = reframe        # may only reinterpret what is already established (see report.lint)
        self.repeat = repeat          # (min, max) when the beat can occur several times in a row, else None

    @property
    def min(self):
        return self.repeat[0] if self.repeat else 1

    @property
    def max(self):
        return self.repeat[1] if self.repeat else 1

    def instance(self, n, numbered=False):
        """This beat as its nth occurrence (key because_2__2); later ones are numbered in their label when the structure shows labels."""
        if n <= 1:
            return self
        label = f"{self.label} ({n})" if numbered else self.label
        return Beat(instance_key(self.key, n), self.slot, label, self.opening, self.closing, self.reframe, None, self.act)


class BeatLabels(dict):
    """beat key -> label; an occurrence key such as because_2__3 answers with its beat's label."""

    def __missing__(self, key):
        base = base_key(key)
        if base != key and base in self:
            return self[base]
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


class Structure:
    def __init__(self, name, label, blurb, beats, show_labels=False, order=100, screen=False, pages=0, formats=None):
        self.name, self.label, self.blurb = name, label, blurb
        self.beats, self.show_labels, self.order = beats, show_labels, order
        self.screen = screen          # a screen structure: a story built on it is a screenplay (and it is never picked at random)
        self.pages = pages            # a screen structure's usual length in pages (the target a new script starts with)
        self.formats = tuple(formats or (("feature-film",) if screen else ("short-story", "novel")))     # the formats it fits

    @property
    def keys(self):
        return [b.key for b in self.beats]

    @property
    def labels(self):
        return BeatLabels({b.key: b.label for b in self.beats})

    def beat(self, key):
        """The beat a key belongs to (an occurrence key finds its beat), or None."""
        base = base_key(key)
        return next((b for b in self.beats if b.key == base), None)

    @property
    def repeatable(self):
        return [b for b in self.beats if b.repeat and b.max > b.min]

    def counts(self, repeats=None):
        """{beat key: how many times it occurs} for the repeatable beats, from a story's `repeats` (missing = the minimum, kept within min and max)."""
        repeats = repeats or {}
        out = {}
        for b in self.beats:
            if b.repeat:
                out[b.key] = max(b.min, min(b.max, int(repeats.get(b.key, b.min) or b.min)))
        return out

    def expand(self, repeats=None):
        """The beats in order, each repeatable beat as many times as `repeats` says."""
        counts = self.counts(repeats)
        out = []
        for b in self.beats:
            for n in range(1, counts.get(b.key, 1) + 1):
                out.append(b.instance(n, numbered=self.show_labels))
        return out


def _read(path):
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        beats = []
        for b in doc["beats"]:
            rep_ = b.get("repeat")
            repeat = (max(1, int(rep_.get("min", 1))), max(1, int(rep_.get("max", 1)))) if rep_ else None
            if repeat and repeat[1] < repeat[0]:
                raise StructureError(f"{path}: beat {b['key']} has a repeat maximum below its minimum")
            beats.append(Beat(b["key"], b.get("slot", b["key"]), b.get("label", b["key"]),
                              b.get("opening", ""), b.get("closing", "."), bool(b.get("reframe")), repeat, b.get("act", "")))
        keys = [b.key for b in beats]
        if not beats or len(set(keys)) != len(keys):
            raise StructureError(f"{path}: needs at least one beat, and beat keys must be unique")
        name = doc.get("name") or path.stem
        return Structure(name, doc.get("label", name), doc.get("blurb", ""), beats, bool(doc.get("show_labels")),
                         doc.get("order", 100), bool(doc.get("screen")), int(doc.get("pages", 0) or 0),
                         [str(f).lower() for f in doc.get("formats") or []])
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


def prose():
    """The structures a story can be rolled into at random (screen structures are chosen on purpose)."""
    return [s for s in registry().values() if not s.screen]


def get(text):
    """Like find, but an unknown or missing name gives the Story Spine."""
    return find(text) or registry()[DEFAULT]


def beat_labels():
    return BeatLabels({b.key: b.label for s in registry().values() for b in s.beats})
