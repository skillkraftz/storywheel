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


SMALL_WORDS = {"of", "the", "and", "de", "del", "la", "le", "von", "van", "der", "du", "on", "in", "at", "to"}


def is_proper(text):
    """Does this text read as a proper name? 'Stacie Anderson', 'Red Draw': yes. 'a locked box', 'the sheriff', 'sheriff': no."""
    text = (text or "").strip()
    rest = ARTICLE.sub("", text)
    return bool(rest) and rest[:1].isupper()                  # "Red Draw", "The Hunting Horn"; not "The sheriff"


def titled(text):
    """A proper name in Title Case, without a leading article ('the silver birch grove' -> 'Silver Birch Grove')."""
    words = ARTICLE.sub("", (text or "").strip()).split()
    return " ".join(w if (w[:1].isupper() or (i and w.lower() in SMALL_WORDS)) else w[:1].upper() + w[1:] for i, w in enumerate(words))


def described(text):
    """A description keeps its article and is lowercase, the way a sentence uses it: 'a locked box', 'the sheriff'."""
    text = (text or "").strip()
    if len(text) > 1 and text[0].isupper() and text[1].islower():
        text = text[0].lower() + text[1:]
    return text


def tidy(text, proper=False):
    """The name an entity gets from generated text. A description stays a description ('a locked box', 'the sheriff'); a proper name
    is Title Case ('Red Draw'). Text that already reads as a proper name is left as it is."""
    if proper:
        return titled(text)
    return (text or "").strip() if is_proper(text) else described(text)


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
        self.proper = is_proper(name) if type_ != "note" else None       # a proper name or a description (see tidy)
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
        self.also = []                          # format keys to also start as: one more version of the story each (see versions.py)

    def lines(self):
        out = [f"Story: '{self.story_title}' (outline, settings, an empty manuscript)"]
        out += [i.line() for i in self.items]
        from . import formats
        out += [f"Also start as {formats.get(k).label.lower()}: a second version of the story, from the same outline (the entities are shared)"
                for k in self.also]
        if self.new_universe_name:
            out.insert(0, f"New universe '{self.new_universe_name}'"
                       + (f" leaning {' / '.join(self.genres)}" if self.genres else ""))
        return out

    def duplicates(self):
        return [i for i in self.items if i.existing]


def _beat_lines(structure, spine):
    """One paragraph per beat. A structure that shows its labels in the story (Kishotenketsu) keeps them as `**Label.**`;
    one whose beats already open with the label's words (the Story Spine's 'Once upon a time, ...') does not repeat them."""
    labels = structure.labels
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

    from . import focus
    person = focus.is_person(focus.of_draft(draft))
    pro = kept.get("protagonist") if person else None                 # (a story about a place or no one makes no protagonist)
    if pro:
        rival_key = None
        if pro.get("rival"):
            r = add(Item("rival", "character", tidy(pro["rival"]), {"role": "rival"}, why="rival"))
            rival_key = r.key
        fields = {k: v for k, v in public(pro).items()}
        fields["role"] = "protagonist"
        fields.pop("rival", None)
        partner, company = fields.pop("partner", ""), fields.pop("company", "")
        add(Item("protagonist", "character", pro.get("name", ""), fields, why="protagonist",
                 links={"rival": rival_key} if rival_key else {}))
        for text, role, why in ((partner, "protagonist", "second lead"),) + tuple((c, "ally", "ensemble") for c in company.split(";")):
            name, _comma, job = (text or "").partition(",")
            if name.strip():
                add(Item(f"{why}:{name.strip()}", "character", name.strip(), {"role": role, "job": job.strip()}, why=why))
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
        note_title = ARTICLE.sub("", text)
        note_title = note_title[:1].upper() + note_title[1:]               # (a note is a title, so it is in sentence case)
        if kind == "someone":
            add(Item(f"thread:{kind}", "character", text, {"role": "supporting"}, why="from the story body"))
        elif kind == "thing":
            add(Item(f"thread:{kind}", "thing", text, {"description": "Appears in the story body."},
                     why="from the story body"))
        elif kind == "message":
            add(Item(f"thread:{kind}", "thing", text, {"description": "A message or document in the story."},
                     why="from the story body"))
        elif kind == "disaster":
            add(Item(f"thread:{kind}", "note", note_title, {"body": f"An event in '{title}': {thread.get('text', '').strip()}."},
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
    from . import formats
    plan.meta["format"] = formats.of_draft(draft)               # (vault.new_story makes it a setting, with the format's usual target)
    if draft.get("repeats"):                                    # repeatable beats the story has more than once (see structures.py)
        plan.meta["repeats"] = ",".join(f"{k}={n}" for k, n in sorted(draft["repeats"].items()))
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
            if item.proper is not None:
                e.proper = item.proper
                universe.save_entity(e)
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
    if plan.also:
        from . import formats, versions
        for key in plan.also:
            if key == formats.of_story(story):
                continue
            extra, _notes = versions.new_version(story, key)
            report.append(f"Created {formats.get(key).label.lower()} version '{extra.slug}' of the story (same outline, same entities).")
    if draft is not None:
        draft["promoted"] = {"universe": universe.slug, "story": story.slug}
    return story, report
