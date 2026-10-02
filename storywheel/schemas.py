"""Entity schemas: what fields a character, place, thing, group or note has. Data in data/entities/*.json
(and your own in ~/.storywheel/entities/ replace or add types by file name)."""
import json

from . import paths
from .library import DATA

TYPES = ("character", "place", "thing", "group", "note")


_CACHE = {}


def _roots():
    return (DATA / "entities", paths.home() / "entities")


def _signature():
    """The schema folders' own change times: adding or replacing a schema file changes them (a file edited in place is
    picked up the next time the program starts)."""
    out = []
    for root in _roots():
        try:
            out.append((str(root), root.stat().st_mtime_ns))
        except OSError:
            out.append((str(root), None))
    return tuple(out)


def load():
    """{type: schema dict}, built-in then yours. Read once; read again if a schema folder changes. Treat as read-only."""
    sig = _signature()
    if _CACHE.get("sig") == sig:
        return _CACHE["found"]
    found = {}
    for root in _roots():
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            found[doc["type"]] = doc
    _CACHE.update(sig=sig, found=found)
    return found


def get(type_):
    schemas = load()
    if type_ not in schemas:
        raise KeyError(f"no entity type '{type_}' (known: {', '.join(schemas)})")
    return schemas[type_]


def field_keys(type_):
    return [f["key"] for f in get(type_)["fields"]]


def field_spec(type_, key):
    return next((f for f in get(type_)["fields"] if f["key"] == key), None)


def can_roll(spec):
    """Does the generator know how to fill this field?"""
    fill = spec.get("fill") or {}
    return not fill.get("write") and bool(fill)
