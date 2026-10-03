"""
A universe's entities as atoms for the generator, and as whole-step candidates for the Wheel.

    characters  ->  `someone`, `close`, `rival` atoms (their full names) and `first_name` / `last_name`
    places      ->  `place` (towns and regions) and `landmark` (landmarks, buildings, wild places)
    things      ->  `thing`

Each list is tagged `universe:<slug>`; the story's mix boosts that tag by the universe's `atom_boost`, so the
world's own people and places turn up often without crowding out everything else.
"""
from .library import Entry, WordList
from .promote import ARTICLE


def tag(universe):
    return f"universe:{universe.slug}"


def _thing_text(name):
    if ARTICLE.match(name):
        return name
    return f"the {name}" if name[:1].isupper() else f"a {name}"


def build_lists(universe):
    """WordLists for one universe, ids like 'universe:thornwood/someone'. Empty slots are left out."""
    t = tag(universe)
    chars, places, things = universe.entities("character"), universe.entities("place"), universe.entities("thing")
    by_slot = {s: [] for s in ("someone", "close", "rival", "first_name", "last_name", "place", "landmark", "thing")}
    for c in chars:
        name = c.name.strip()
        if not name:
            continue
        by_slot["someone"].append(Entry(name, kind="person", features=("human",)))
        by_slot["close"].append(Entry(name, kind="person", features=("human", "friendly")))
        by_slot["rival"].append(Entry(name, kind="person", features=("human",)))
        parts = name.split()
        by_slot["first_name"].append(Entry(parts[0]))
        if len(parts) > 1:
            by_slot["last_name"].append(Entry(parts[-1]))
    for p in places:
        name = p.name.strip()
        if not name:
            continue
        kind = p.fields.get("kind") or "town"
        if kind in ("landmark", "building", "wild place"):
            text = name if ARTICLE.match(name) else f"the {name}"
            by_slot["landmark"].append(Entry(text, kind="place", features=("outdoor",) if kind != "building" else ("built",)))
        else:
            by_slot["place"].append(Entry(name, kind="place", features=("outdoor",)))
    for th in things:
        name = th.name.strip()
        if name:
            feats = tuple(f.strip() for f in str(th.fields.get("features", "")).split(",") if f.strip()) or ("portable", "buryable")
            by_slot["thing"].append(Entry(_thing_text(name), kind="object", features=feats))
    return [WordList(f"universe:{universe.slug}/{slot}", slot, [t], entries) for slot, entries in by_slot.items() if entries]


GROUPS = (("character", "Characters", "protagonist"), ("place", "Places", "setting"), ("thing", "Things", None))


def named(universe, type_):
    """The universe's named entities of one type (a blank, unnamed one is not shown or counted anywhere)."""
    return [e for e in universe.entities(type_) if e.name.strip()]


def counts_text(universe):
    """'3 characters · 2 places · 2 things': the same numbers the Wheel's panel groups show."""
    parts = []
    for type_, label, _step in GROUPS:
        n = len(named(universe, type_))
        parts.append(f"{n} {label.lower() if n != 1 else label.lower().rstrip('s')}")
    return " · ".join(parts)


def step_candidates(universe, step_key):
    """Whole-step candidates from a universe: protagonist <- characters, setting <- places.
    Each is the dict of fields that step uses (blank ones are filled by an ordinary roll when it is used)."""
    out = []
    if step_key == "protagonist":
        for c in universe.entities("character"):
            if not c.name.strip():
                continue
            f = {"name": c.name}
            for k in ("age", "job", "trait", "want", "need", "flaw", "secret"):
                f[k] = c.fields.get(k, "")
            rival = universe.resolve(c.fields.get("rival"))
            f["rival"] = rival.name if rival else (c.fields.get("rival") or "")
            out.append((c, f))
    elif step_key == "setting":
        for p in universe.entities("place"):
            if not p.name.strip() or (p.fields.get("kind") in ("landmark", "building")):
                continue
            landmark = ""
            for other in universe.entities("place"):
                if other.fields.get("parent") == p.id and other.name:
                    landmark = other.name if ARTICLE.match(other.name) else f"the {other.name}"
                    break
            landmark = landmark or p.fields.get("feature", "")
            f = {"place": p.name, "era": p.fields.get("era", ""), "season": p.fields.get("season", ""),
                 "landmark": landmark, "rumor": p.fields.get("rumor", "")}
            out.append((p, f))
    return out


def save_piece(universe, step_key, label, fields):
    """Save a piece from the Wheel into a universe: a protagonist becomes a character, a setting a place (its landmark
    a place inside it), anything else a note. An entity with the same name is filled in, not duplicated.
    Returns (entity, message)."""
    from . import promote
    if step_key == "protagonist":
        type_, name, data = "character", fields.get("name", ""), dict(fields, role="protagonist")
        rival = data.pop("rival", "")
    elif step_key == "setting":
        type_, name = "place", fields.get("place", "")
        data = {"kind": "town", "era": fields.get("era", ""), "season": fields.get("season", ""), "rumor": fields.get("rumor", "")}
        rival = ""
    else:
        type_, name = "note", f"{label}: {next(iter(fields.values()))[:40]}"
        data = {"body": "\n\n".join(f"**{k.replace('_', ' ').title()}.** {v}" for k, v in fields.items())}
        rival = ""
    found = universe.find_by_name(name, type_)
    if found:
        e = found[0]
        for k, v in data.items():
            if v and not e.fields.get(k):
                e.fields[k] = v
        universe.save_entity(e)
        return e, f"'{name}' is already in {universe.name}; its blank fields were filled in."
    e = universe.new_entity(type_, name, data)
    if rival:
        e.fields["rival"] = rival
    if type_ != "note":
        e.proper = promote.is_proper(name)
    universe.save_entity(e)
    if step_key == "setting" and fields.get("landmark"):
        landmark = universe.new_entity("place", promote.tidy(fields["landmark"]), {"kind": "landmark", "parent": e.id})
        landmark.proper = promote.is_proper(landmark.name)
        universe.save_entity(landmark)
    return e, f"Saved '{name}' to {universe.name} as a {type_}."
