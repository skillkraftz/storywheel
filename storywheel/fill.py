"""
Filling an entity's fields with the generator.

A field's schema says how it is filled (data/entities/*.json, "fill"):
    {"step": "protagonist", "field": "job"}   what the Wheel's step makes for that field
    {"slot": "thing", "format": "The {x} Co"}  an atom list
    {"link": "character"}                      may point at a real entity of that type
    {"write": true}                            write only
The roll uses the universe's mix, the entity's other fields (a character's need is made knowing
their flaw), and the universe's existing entities (a rival may be an existing character).
"""
import random

from . import paths, promote, schemas
from .engine import Engine
from .library import Library
from .steps import steps_for

LINK_CHANCE = 0.6          # how often a field that CAN link to an existing entity does


class NothingToLink(Exception):
    """A link-only field (owner, leader, parent) and no entity of that type exists yet."""


def is_blank(value):
    return value in ("", None, [])


def make_engine(universe=None, seed=None, ratings=None):
    """An engine for rolling in a universe: its own lists folder (if any) is merged in."""
    extra = [universe.lists_dir] if universe is not None and universe.lists_dir.is_dir() else []
    lib = Library.load(paths.home(), extra)
    return Engine(seed=seed, library=lib, user_dir=paths.home(), ratings=ratings)


class Filler:
    def __init__(self, universe, engine=None, rng=None):
        self.universe = universe
        self.engine = engine or make_engine(universe)
        self.rng = rng or self.engine.rng
        self.last_atoms = []               # [[slot, text], ...] the last roll drew (what a rating needs to know)

    # --- context --------------------------------------------------------------------------------------

    def _pseudo_story(self):
        """The thing the generator reads its mix and kept values from: a story-shaped dict."""
        return {"kept": {}, "seeds": {}, "atoms": {}, "threads": {}, "history": {}, "inputs": {},
                "mix": self.universe.mix_dict(), "universe_mode": "n"}

    def _context(self, entity, spec):
        """The entity's other filled fields, named the way the Wheel's step names them."""
        fill = spec["fill"]
        rest = {}
        for other in schemas.get(entity.type)["fields"]:
            f = other.get("fill") or {}
            if other["key"] == spec["key"] or f.get("step") != fill.get("step"):
                continue
            value = entity.fields.get(other["key"])
            if is_blank(value):
                continue
            if other.get("kind") == "link":
                target = self.universe.resolve(value)
                value = target.name if target else value
            rest[f["field"]] = value
        return rest

    # --- rolling -----------------------------------------------------------------------------------------

    def roll(self, entity, key):
        """A new value for one field (not applied). Raises NothingToLink for a link-only field with nothing to link."""
        spec = schemas.field_spec(entity.type, key)
        fill = (spec or {}).get("fill") or {}
        self.last_atoms = []
        if not spec or fill.get("write") or not fill:
            raise ValueError(f"'{key}' is write-only")
        link = fill.get("link")
        if link:
            others = [e for e in self.universe.entities(link) if e.id != entity.id]
            if others and (not (fill.get("step") or fill.get("slot")) or self.rng.random() < LINK_CHANCE):
                current = entity.fields.get(key)
                fresh = [e for e in others if e.id != current] or others
                return self.rng.choice(fresh).id
            if not (fill.get("step") or fill.get("slot")):
                raise NothingToLink(f"There is no {schemas.get(link)['label'].lower()} in this universe to link to yet.")
        if fill.get("step"):
            from .steps import step_by_key
            story = self._pseudo_story()
            step = step_by_key(fill["step"], story)
            value, _t, atoms = step.reroll_value(self.engine, story, self._context(entity, spec), fill["field"])
            self.last_atoms = [list(a) for a in atoms]
            return value
        if fill.get("slot"):
            from .mix import Mix
            mix = Mix(self.universe.mix_dict(), self.engine.library)
            ratings = self.engine.ratings
            bias = (lambda e: ratings.atom_bias(fill["slot"], e.text, ())) if ratings is not None else None     # ratings change rolls here too
            wl, entry = self.engine.pick_item(fill["slot"], mix, bias=bias)
            self.last_atoms = [[fill["slot"], entry.text]]
            text = promote.tidy(entry.text) if spec["key"] == "name" else entry.text
            if fill.get("format"):
                text = fill["format"].replace("{x}", entry.text.split()[-1].capitalize())
            return text
        raise ValueError(f"don't know how to fill '{key}'")

    def roll_blank(self, entity):
        """Roll every blank field the generator can fill, in schema order. Returns the keys that were filled."""
        done = []
        for spec in schemas.get(entity.type)["fields"]:
            if not schemas.can_roll(spec) or not is_blank(entity.fields.get(spec["key"])):
                continue
            try:
                entity.fields[spec["key"]] = self.roll(entity, spec["key"])
                done.append(spec["key"])
            except NothingToLink:
                continue
        return done

    def reroll_all(self, entity):
        """Roll every rollable field again (the caller has already asked 'are you sure?')."""
        for spec in schemas.get(entity.type)["fields"]:
            if schemas.can_roll(spec):
                entity.fields[spec["key"]] = [] if spec.get("kind") == "links" else ""
        return self.roll_blank(entity)
