"""Entity schemas: what fields a character, place, thing, group or note has. Data in data/entities/*.json
(and your own in ~/.storywheel/entities/ replace or add types by file name)."""
import json

from . import paths
from .library import DATA

TYPES = ("character", "place", "thing", "group", "note")


def load():
    """{type: schema dict}, built-in then yours."""
    found = {}
    for root in (DATA / "entities", paths.home() / "entities"):
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            found[doc["type"]] = doc
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
