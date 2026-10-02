"""
Promotion: bringing a kept Wheel draft into a universe.

    plan = build_plan(draft, universe)        # what WOULD be created (nothing is written)
    ... show plan.lines(), let the writer switch merges on or off ...
    story, report = apply_plan(plan, universe_or_None, draft)

What the draft becomes (CLAUDE.md has the table): the protagonist is a character with every field;
the rival, a stub character; the town and the landmark are places (the landmark inside the town); the
motif is a thing (an object) or a character (a person or creature); the story's threads are stubs
(someone -> character, thing -> thing, message -> thing, disaster -> note); everything else (title,
genre, mood, structure, premise, setting, beats, twist) is the story's outline, story.md.
"""
import re

from . import structures, vault
from .steps import public

ARTICLE = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)


def tidy(text):
    """'the sheriff' -> 'Sheriff', 'a locked box' -> 'Locked box'."""
    text = ARTICLE.sub("", (text or "").strip())
    return text[:1].upper() + text[1:]


def same_name(a, b):
    return ARTICLE.sub("", (a or "").strip()).lower() == ARTICLE.sub("", (b or "").strip()).lower() and bool((a or "").strip())


class Item:
    def __init__(self, key, type_, name, fields=None, custom=None, body="", links=None, why=""):
        self.key, self.type, self.name = key, type_, name
        self.fields = dict(fields or {})
        self.custom = dict(custom or {})
        self.body = body
        self.links = dict(links or {})          # field -> key of another item (resolved to an id on apply)
        self.why = why                          # "protagonist", "rival", "landmark"...
        self.existing = None                    # an entity with the same name already in the universe
        self.merge = False                      # use that one (fill its blanks) instead of creating a new one

    def line(self):
        if self.existing:
            if self.merge:
                return f"Merge into the existing {self.type} '{self.existing.name}' (blank fields are filled in)"
            return f"Create another {self.type} '{self.name}' (a duplicate of '{self.existing.name}')"
        return f"Create {self.type} '{self.name}'" + (f"  ({self.why})" if self.why else "")


class Plan:
    def __init__(self, draft):
        self.draft = draft
        self.items = []
        self.new_universe_name = None
        self.genres = []
        self.story_title = "Untitled"
        self.meta, self.sections = {}, {}

    def lines(self):
        out = [f"Story: '{self.story_title}' (outline, settings, an empty manuscript)"]
        out += [i.line() for i in self.items]
        if self.new_universe_name:
            out.insert(0, f"New universe '{self.new_universe_name}'"
                       + (f" leaning {' / '.join(self.genres)}" if self.genres else ""))
        return out

    def duplicates(self):
        return [i for i in self.items if i.existing]


def _beat_lines(structure, spine):
    """One paragraph per beat. A structure that shows its labels in the story (Kishotenketsu) keeps them as `**Label.**`;
    one whose beats already open with the label's words (the Story Spine's 'Once upon a time, ...') does not repeat them."""
    labels = {b.key: b.label for b in structure.beats}
    return "\n\n".join((f"**{labels.get(k, k)}.** {v}" if structure.show_labels else v) for k, v in spine.items() if v)


def build_plan(draft, universe=None, engine=None, new_universe_name=None):
    """Work out what promotion would create. With an existing universe, same-name entities are found
    (and merging is on by default); nothing is written."""
    kept = draft["kept"]
    plan = Plan(draft)
    title = (kept.get("title") or {}).get("title") or "Untitled"
    plan.story_title = title
    plan.new_universe_name = new_universe_name if universe is None else None
    if universe is None and not plan.new_universe_name:
        plan.new_universe_name = title
    genre = kept.get("genre") or {}
    plan.genres = [g.strip().lower() for g in (genre.get("genre") or "").replace(",", "/").split("/") if g.strip()]
    items = plan.items

    def add(item):
        for other in items:                                  # the same thing twice in one draft is one entity
            if other.type == item.type and same_name(other.name, item.name):
                if item.why and other.why and item.why not in other.why:
                    other.why += f", {item.why}"
                other.fields.update({k: v for k, v in item.fields.items() if v and not other.fields.get(k)})
                return other
        items.append(item)
        return item

    pro = kept.get("protagonist")
    if pro:
        rival_key = None
        if pro.get("rival"):
            r = add(Item("rival", "character", tidy(pro["rival"]), {"role": "rival"}, why="rival"))
            rival_key = r.key
        fields = {k: v for k, v in public(pro).items()}
        fields["role"] = "protagonist"
        fields.pop("rival", None)
        add(Item("protagonist", "character", pro.get("name", ""), fields, why="protagonist",
                 links={"rival": rival_key} if rival_key else {}))
    setting = kept.get("setting")
    if setting:
        town = add(Item("town", "place", setting.get("place", ""),
                        {"kind": "town", "era": setting.get("era", ""), "season": setting.get("season", ""),
                         "rumor": setting.get("rumor", "")}, why="setting"))
        if setting.get("landmark"):
            add(Item("landmark", "place", tidy(setting["landmark"]), {"kind": "landmark"}, links={"parent": town.key},
                     why="landmark"))
    motif = (kept.get("title") or {}).get("motif")
    if motif:
        from .engine import Engine
        kind = (engine or Engine()).motif_kind(motif)
        if kind in ("person", "creature"):
            add(Item("motif", "character", tidy(motif), {"role": "supporting"},
                     body=f"The motif of '{title}'.", why="motif"))
        elif kind == "place":
            add(Item("motif", "place", tidy(motif), {"kind": "wild place"}, body=f"The motif of '{title}'.", why="motif"))
        elif kind != "idea":
            add(Item("motif", "thing", tidy(motif), {"description": f"The motif of '{title}'."}, why="motif"))
    for kind, thread in (draft.get("threads") or {}).items():
        text = tidy(thread.get("text", ""))
        if not text:
            continue
        if kind == "someone":
            add(Item(f"thread:{kind}", "character", text, {"role": "supporting"}, why="from the story body"))
        elif kind == "thing":
            add(Item(f"thread:{kind}", "thing", text, {"description": "Appears in the story body."},
                     why="from the story body"))
        elif kind == "message":
            add(Item(f"thread:{kind}", "thing", text, {"description": "A message or document in the story."},
                     why="from the story body"))
        elif kind == "disaster":
            add(Item(f"thread:{kind}", "note", text, {"body": f"An event in '{title}': {thread.get('text', '').strip()}."},
                     why="event in the story body"))
    if universe is not None:
        for item in items:
            found = universe.find_by_name(ARTICLE.sub("", item.name), item.type) or \
                [e for e in universe.entities(item.type) if same_name(e.name, item.name)]
            if found:
                item.existing, item.merge = found[0], True

    shape = structures.get((kept.get("structure") or {}).get("structure"))
    plan.meta = {"genre": genre.get("genre", ""), "mood": genre.get("mood", ""),
                 "structure": shape.label if kept.get("structure") else "", "motif": motif or "",
                 "promoted_from": draft.get("id", "")}
    sections = {}
    if kept.get("premise"):
        sections["Premise"] = kept["premise"].get("premise", "")
    if setting:
        sections["Setting"] = "\n".join(f"- **{k.replace('_', ' ').title()}:** {v}" for k, v in public(setting).items())
    if kept.get("spine"):
        sections[shape.label] = _beat_lines(shape, kept["spine"])
    if kept.get("twist"):
        sections["Twist"] = kept["twist"].get("twist", "")
    plan.sections = sections
    return plan


def apply_plan(plan, universe=None, draft=None):
    """Write it. Returns (story, report lines). `universe` None means create the plan's new universe."""
    report = []
    if universe is None:
        universe = vault.create_universe(plan.new_universe_name or plan.story_title, plan.genres)
        report.append(f"Created universe '{universe.name}'.")
    elif not universe.settings()["genres"] and plan.genres:
        universe.save_settings(genres=plan.genres)
    ids = {}
    cast = []
    for item in plan.items:
        links = {field: ids[key] for field, key in item.links.items() if key in ids}
        if item.existing and item.merge:
            e = universe.entity(item.existing.id)
            filled = []
            for k, v in {**item.fields, **links}.items():
                if v and not e.fields.get(k):
                    e.fields[k] = v
                    filled.append(k)
            if item.body and not (e.body or e.fields.get("body")):
                e.body = item.body
            universe.save_entity(e)
            report.append(f"Merged into {e.type} '{e.name}'" + (f" (filled {', '.join(filled)})." if filled else "."))
        else:
            e = universe.new_entity(item.type, item.name, {**item.fields, **links})
            e.custom.update(item.custom)
            if item.body and item.type != "note":
                e.body = item.body
            universe.save_entity(e)
            report.append(f"Created {e.type} '{e.name}'.")
        ids[item.key] = e.id
        cast.append(e.id)
    meta = dict(plan.meta, cast=cast)
    story = universe.new_story(plan.story_title, meta, plan.sections, seed=plan.draft)
    report.append(f"Created story '{story.title}'.")
    if draft is not None:
        draft["promoted"] = {"universe": universe.slug, "story": story.slug}
    return story, report
