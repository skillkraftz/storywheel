"""
Keeping a story consistent when a piece changes.

Editing one field updates other fields in the same item that mention the old
value (a new landmark updates the rumor about it). Changing a kept step swaps
the old values for the new ones across later steps (renaming the protagonist
updates the spine).
"""
import copy
import re

from . import threads as T
from .steps import public, steps_for


def change_pairs(old, new):
    """(old text, new text) pairs for every field that changed, longest first."""
    pairs = []
    for k, ov in public(old).items():
        nv = new.get(k)
        if ov and nv and ov != nv and len(ov) >= 3:
            pairs.append((ov, nv))
            if k == "name" and ov.split()[0] != nv.split()[0]:
                pairs.append((ov.split()[0], nv.split()[0]))
    return sorted(pairs, key=lambda p: -len(p[0]))


def apply_pairs(fields, pairs, skip=()):
    """Swap old values for new ones inside each field's text. Returns the count."""
    count = 0
    for fk, fv in fields.items():
        if fk.startswith("_") or fk in skip:
            continue
        for ov, nv in pairs:
            fv, n = re.subn(r"\b" + re.escape(ov) + r"\b", lambda _m, nv=nv: nv, fv)
            count += n
        fields[fk] = fv
    return count


def substitute(story, i, old, new):
    """After changing step i, swap old names/places/etc. in later steps."""
    pairs = change_pairs(old, new)
    return sum(apply_pairs(story["kept"][s.key], pairs)
               for s in steps_for(story)[i + 1:] if story["kept"].get(s.key))


def with_field(cand, field, value, src=None, settle=True, atoms=None):
    """A copy of a candidate with one field changed. Other fields that mentioned
    the old value get the new one, so a new landmark updates the rumor too.
    Threads travel with the candidate and are re-checked against its new text."""
    new = public(cand)
    old_value, new[field] = new[field], value
    apply_pairs(new, change_pairs({field: old_value}, {field: value}), skip=(field,))
    if src or cand.get("_src") == "edited":
        new["_src"] = src or "edited"
    if "_threads" in cand:
        new["_threads"] = copy.deepcopy(cand["_threads"])
        if settle:
            T.settle(new)
    if "_made" in cand:
        new["_made"] = dict(cand["_made"])
    if "_atoms" in cand:                        # the field changed, so its atoms are now `atoms`
        new["_atoms"] = copy.deepcopy(cand["_atoms"])
        new["_atoms"][field] = atoms or []
    return new


def inherit(new, old):
    """A rewritten candidate (edited whole, written by hand) keeps the old one's threads."""
    if "_threads" in old:
        new["_threads"] = copy.deepcopy(old["_threads"])
        T.settle(new)
    if "_atoms" in old:
        new["_atoms"] = copy.deepcopy(old["_atoms"])
    if "_made" in old:
        new["_made"] = dict(old["_made"])
    return new


def reroll_field(step, engine, story, cand, field):
    """Reroll one field of a candidate; returns the new candidate.

    In a threaded step (the spine), rerolling the beat that introduced a thread
    UPDATES it when the new beat introduces another of that kind (the old text is
    swapped for the new one in the other beats) and otherwise lets it RETIRE once
    no other beat mentions it (see threads.py)."""
    if not step.threads:
        value, _, atoms = step.reroll_value(engine, story, public(cand), field, atoms=cand.get("_atoms"),
                                            made=cand.get("_made"))
        return with_field(cand, field, value, atoms=atoms)
    old = cand.get("_threads", {})
    standing = {k: copy.deepcopy(t) for k, t in old.items() if t["beat"] != field}
    value, introduced, atoms = step.reroll_value(engine, story, public(cand), field, standing,
                                                 atoms=cand.get("_atoms"), made=cand.get("_made"))
    new = with_field(cand, field, value, settle=False, atoms=atoms)
    threads = dict(standing)
    for kind, t in old.items():
        if t["beat"] != field:
            continue
        if kind in introduced:                       # updated: the others follow
            T.swap(new, t, introduced[kind], skip=(field,))
            threads[kind] = introduced[kind]
        else:                                        # may live on in a later beat, or retire
            threads[kind] = t
    for kind, t in introduced.items():
        threads.setdefault(kind, t)
    new["_threads"] = threads
    return T.settle(new)


def carry_threads(story, i, old, new):
    """The spine at step i was replaced; swap changed thread text in later steps."""
    pairs = []
    for kind, t in (old or {}).items():
        n = (new or {}).get(kind)
        if n and n["text"] != t["text"]:
            pairs += T.swap_pairs(t, n)
    pairs.sort(key=lambda p: -len(p[0]))
    count = 0
    for step in steps_for(story)[i + 1:]:
        for key, value in (story["kept"].get(step.key) or {}).items():
            if isinstance(value, str):
                for a, b in pairs:
                    value, n = T.replace_text(value, a, b)
                    count += n
                story["kept"][step.key][key] = value
    return count
