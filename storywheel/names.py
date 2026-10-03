"""Fixing names that were written in the wrong capitals (older promotions turned "a locked box" into "Locked box").

An entity records whether its name is proper (a person, a town: Title Case) or a description (an object, a role, an unnamed landmark:
lowercase, with the article a sentence uses). Entities made before that was recorded are checked against what the generator knows: if a
name matches an atom in the lists (a thing, a landmark, a rival...) it is that atom's own wording, in the atom's own case.
"""
import re

from . import paths, promote
from .library import Library

SLOTS = ("thing", "someone", "rival", "close", "landmark", "job", "place")


class Fix:
    def __init__(self, entity, new, why):
        self.entity, self.old, self.new, self.why = entity, entity.name, new, why
        self.accepted = True

    def line(self):
        return f"{self.entity.type}: '{self.old}'  ->  '{self.new}'   ({self.why})"


def _atoms(universe):
    from .fill import make_engine
    lib = make_engine(universe).library
    found = {}
    for slot in SLOTS:
        for wl in lib.by_slot.get(slot, []):
            if wl.is_template or wl.generator:
                continue
            for entry in wl.entries:
                key = promote.ARTICLE.sub("", entry.text.strip()).lower()
                if key and key not in found:
                    found[key] = (slot, entry.text.strip())
    return found


def scan(universe):
    """[Fix] for entities whose name isn't recorded as proper or descriptive and looks like a description with a capital letter."""
    atoms = _atoms(universe)
    fixes = []
    for e in universe.entities():
        name = e.name.strip()
        if e.type == "note" or not name or e.proper is not None or promote.ARTICLE.match(name):
            continue
        if e.type == "character" and e.fields.get("role") not in ("rival", "supporting"):
            continue                                        # a protagonist or ally was named by the generator or by hand: a name
        hit = atoms.get(name.lower())
        if hit and not promote.is_proper(hit[1]):
            fixes.append(Fix(e, hit[1], f"the generator's own wording of this {hit[0]}"))
        elif e.type == "thing" and re.fullmatch(r"[A-Z][a-z'-]*(?: [a-z'-]+)+", name):
            fixes.append(Fix(e, promote.described(name), "only the first word had a capital"))
    return fixes


def apply(universe, fixes):
    """Rename the accepted ones (the id stays) and record that they are descriptions. Returns how many."""
    n = 0
    for f in fixes:
        if not f.accepted:
            continue
        e = universe.entity(f.entity.id)
        if e is None:
            continue
        e.fields["name"] = f.new
        e.proper = False
        universe.save_entity(e)
        n += 1
    return n


def mark_rest(universe):
    """Record the remaining unrecorded names: capitalised ones are proper names, the rest descriptions."""
    for e in universe.entities():
        if e.type != "note" and e.proper is None and e.name.strip():
            e.proper = promote.is_proper(e.name)
            universe.save_entity(e)
