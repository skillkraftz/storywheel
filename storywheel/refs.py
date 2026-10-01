"""
Keeping a story consistent when a piece changes.

Editing one field updates other fields in the same item that mention the old
value (a new landmark updates the rumor about it). Changing a kept step swaps
the old values for the new ones across later steps (renaming the protagonist
updates the spine).
"""
import re

from .steps import STEPS, public


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
               for s in STEPS[i + 1:] if story["kept"].get(s.key))


def with_field(cand, field, value, src=None):
    """A copy of a candidate with one field changed. Other fields that mentioned
    the old value get the new one, so a new landmark updates the rumor too."""
    new = public(cand)
    old_value, new[field] = new[field], value
    apply_pairs(new, change_pairs({field: old_value}, {field: value}), skip=(field,))
    if src or cand.get("_src") == "edited":
        new["_src"] = src or "edited"
    return new
