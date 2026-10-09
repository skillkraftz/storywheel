"""
Saving and loading. Each story is one small JSON file; your universe is one
more. Every save also rewrites the story's markdown file, so it always matches
what you've kept.

Locations: see paths.py (STORYWHEEL_HOME, STORYWHEEL_OUT).
"""
import datetime
import json
import re
from pathlib import Path

from .mix import new_mix, sync_base
from .paths import HOME, OUT
from . import structures
from .steps import STEPS, public, steps_for
from .threads import BEAT_LABELS

STORIES = HOME / "stories"
UNIVERSE = HOME / "universe.json"

HISTORY_LIMIT = 40
SECTION_BREAK = '\n\n---\n\n'


# --- stories ------------------------------------------------------------------------

def new_story():
    now = datetime.datetime.now()
    return {"id": now.strftime("%Y%m%d-%H%M%S"), "created": now.isoformat(timespec="minutes"),
            "step": 0, "kept": {}, "history": {}, "seeds": {}, "universe_mode": "n",
            "mix": new_mix(), "threads": {}, "atoms": {}, "inputs": {}, "steps_v": 2}

def upgrade(story):
    """Bring a story from an older file up to date (v1 files have no mix)."""
    sync_base(story)
    story.setdefault("threads", {})
    story.setdefault("atoms", {})
    story.setdefault("inputs", {})
    if story.get("steps_v") != 2:               # older files predate the structure step
        story["steps_v"] = 2
        if story.get("step", 0) >= 1 or "genre" in story["kept"]:
            story["kept"].setdefault("structure", {"structure": structures.registry()[structures.DEFAULT].label})
            story["step"] = story.get("step", 0) + 1
    return story

def save(story):
    """Write the draft. A draft with nothing kept is not worth a file: it is only written once something is kept
    (or if it already has a file, so that un-keeping everything still saves)."""
    path = STORIES / f"{story['id']}.json"
    if not story["kept"] and not path.exists():
        return None
    STORIES.mkdir(parents=True, exist_ok=True)
    sync_base(story)                            # the mix follows the kept genres
    for key, hist in story["history"].items():
        story["history"][key] = hist[-HISTORY_LIMIT:]
    path.write_text(json.dumps(story, indent=2))
    if story["kept"]:
        return export(story)

def save_draft(story):
    """Write a draft's JSON only (no markdown), for bookkeeping like 'promoted'."""
    STORIES.mkdir(parents=True, exist_ok=True)
    (STORIES / f"{story['id']}.json").write_text(json.dumps(story, indent=2))

def load(story_id):
    return upgrade(json.loads((STORIES / f"{story_id}.json").read_text()))

def all_stories():
    """Newest first."""
    if not STORIES.exists():
        return []
    return [upgrade(json.loads(p.read_text())) for p in sorted(STORIES.glob("*.json"), reverse=True)]

def progress(story):
    """(steps kept, steps in all, finished?): what the Past stories list shows, instead of the step you stopped on."""
    steps = steps_for(story)
    return sum(1 for st in steps if story["kept"].get(st.key)), len(steps), story.get("step", 0) >= len(steps)

def progress_text(story):
    kept, total, done = progress(story)
    return f"{kept}/{total} kept" + (", done" if done else "")

def open_step(story):
    """The step to open a draft on: where you stopped, or (for a finished draft) the last step, never silently the first."""
    n = len(steps_for(story))
    return story.get("step", 0) if story.get("step", 0) < n else n - 1

def cleanup_empty_drafts():
    """Move drafts with nothing kept into HOME/.trash (never delete writing). Returns how many were moved."""
    if not STORIES.exists():
        return 0
    moved = 0
    for p in sorted(STORIES.glob("*.json")):
        try:
            story = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if story.get("kept") or story.get("promoted"):
            continue
        trash = HOME / ".trash"
        trash.mkdir(parents=True, exist_ok=True)
        p.replace(trash / p.name)
        moved += 1
    return moved

def copy_as_new(story):
    """An editable copy of a draft (a promoted one is read-only in the Wheel): same kept pieces, a fresh id, not promoted."""
    import copy
    new = new_story()
    n = 1
    while (STORIES / f"{new['id']}.json").exists():            # (two copies in one second)
        new["id"] = f"{new['id'][:15]}-{n}"
        n += 1
    for key in ("kept", "history", "seeds", "threads", "atoms", "inputs", "mix", "universes", "home", "universe_mode", "step"):
        if key in story:
            new[key] = copy.deepcopy(story[key])
    new["copied_from"] = story["id"]
    return new

def find(target=None):
    """Find a story by list number (1 = newest), id, or id prefix. None = newest."""
    stories = all_stories()
    if not stories:
        return None
    if target is None:
        return stories[0]
    if target.isdigit() and int(target) <= len(stories):
        return stories[int(target) - 1]
    matches = [s for s in stories if s["id"].startswith(target)]
    return matches[0] if matches else None

def title_of(story):
    return (story["kept"].get("title") or {}).get("title", "Untitled")


# --- universe -------------------------------------------------------------------------

def load_universe():
    return json.loads(UNIVERSE.read_text()) if UNIVERSE.exists() else {}

def _save_universe(universe):
    HOME.mkdir(parents=True, exist_ok=True)
    UNIVERSE.write_text(json.dumps(universe, indent=2))

def add_to_universe(step_key, fields):
    """Returns (entries for that step, whether this one was newly added)."""
    universe = load_universe()
    entries = universe.setdefault(step_key, [])
    fields = public(fields)
    added = fields not in entries
    if added:
        entries.append(fields)
        _save_universe(universe)
    return len(entries), added

def remove_from_universe(step_key, fields):
    universe = load_universe()
    entries = universe.get(step_key, [])
    if public(fields) in entries:
        entries.remove(public(fields))
        _save_universe(universe)
        return True
    return False

def update_universe_entry(step_key, index, fields):
    """Replace one saved entry's fields. Returns True if there was such an entry."""
    universe = load_universe()
    entries = universe.get(step_key, [])
    if 0 <= index < len(entries):
        entries[index] = public(fields)
        _save_universe(universe)
        return True
    return False

def add_universe_entry(step_key, fields):
    """Add an entry written by hand. Returns (number of entries for that step, whether it was new)."""
    return add_to_universe(step_key, fields)

def remove_universe_entry(step_key, index):
    universe = load_universe()
    entries = universe.get(step_key, [])
    if 0 <= index < len(entries):
        entry = entries.pop(index)
        _save_universe(universe)
        return entry
    return None


# --- markdown -------------------------------------------------------------------------

def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50] or "untitled"

def _picks(story):
    """The Genre step's picked fields that differ from the defaults, as ['Focus: A place', 'Ending: Tragic'] (none for the usual story)."""
    from . import endings, focus
    out = []
    if focus.of_draft(story) != focus.DEFAULT:
        out.append("Focus: " + focus.get(focus.of_draft(story)).label)
    if endings.of_draft(story) != endings.DEFAULT:
        out.append("Ending: " + endings.get(endings.of_draft(story)).label)
    return out


def to_markdown(story):
    kept = story["kept"]
    title = title_of(story)
    genre = kept.get("genre", {})
    motif = kept.get("title", {}).get("motif")

    shape = structures.get((kept.get("structure") or {}).get("structure"))
    front = ["---", f'title: "{title}"']
    if genre:
        front += [f'genre: "{genre.get("genre", "")}"', f'mood: "{genre.get("mood", "")}"']
    if kept.get("structure"):
        front.append(f'structure: "{shape.label}"')
    for pick in _picks(story):
        front.append(f'{pick.split(":")[0].lower()}: "{pick.split(": ", 1)[1]}"')
    if motif:
        front.append(f'motif: "{motif}"')
    front += [f"created: {story['created'][:10]}", "tags: [storywheel]", "---", ""]

    head = [f"# {title}", ""]
    if genre:
        head.append(f"*{genre.get('genre', '')} · {genre.get('mood', '')}*")
    if _picks(story):
        head.append(f"*{' · '.join(_picks(story))}*")
    if motif:
        head.append(f"*Motif: {motif}*")

    sections = ["\n".join(front + head).rstrip()]
    for step in steps_for(story):
        fields = public(kept.get(step.key))
        if not fields or step.key in ("genre", "title", "structure"):
            continue
        if step.key == "spine":
            labels = shape.labels
            body = "\n\n".join((f"**{labels[f]}.** " if shape.show_labels else "") + fields[f]
                                for f in step.fields if f in fields)
        elif step.single:
            body = next(iter(fields.values()))
        else:
            body = "\n".join(f"- **{k.replace('_', ' ').title()}:** {v}" for k, v in fields.items())
        sections.append(f"## {step.label if step.key != 'spine' else shape.label}\n\n{body}")
        if step.key == "spine" and story.get("threads"):
            lines = [f"- **{kind.title()}:** {t['text']} *(introduced: {BEAT_LABELS.get(t['beat'], t['beat'])})*"
                     for kind, t in story["threads"].items()]
            sections.append("## Threads\n\n" + "\n".join(lines))
    return SECTION_BREAK.join(sections) + "\n"

def to_plain(story, width=72):
    """The story so far as readable plain text: only what is kept, no markup."""
    import textwrap
    kept = story["kept"]
    if not kept:
        return ""
    shape = structures.get((kept.get("structure") or {}).get("structure"))
    genre = kept.get("genre", {})
    motif = kept.get("title", {}).get("motif")
    out = []
    if kept.get("title"):
        out.append(title_of(story).upper())
    line = " · ".join(x for x in (genre.get("genre"), genre.get("mood"),
                                  shape.label if kept.get("structure") else None) if x)
    if line:
        out.append(line)
    if _picks(story):
        out.append(" · ".join(_picks(story)))
    if motif:
        out.append(f"Motif: {motif}")
    blocks = ["\n".join(out)] if out else []

    def wrap(text, indent="  "):
        return textwrap.fill(text, width, initial_indent=indent, subsequent_indent=indent)

    for step in steps_for(story):
        fields = public(kept.get(step.key))
        if not fields or step.key in ("genre", "title", "structure"):
            continue
        heading = (shape.label if step.key == "spine" else step.label).upper()
        if step.key == "spine":
            labels = shape.labels
            body = "\n\n".join(wrap((f"{labels[f]}. " if shape.show_labels else "") + fields[f])
                                for f in step.fields if f in fields)
        elif step.single:
            body = wrap(next(iter(fields.values())))
        else:
            pad = max(len(k) for k in fields)
            body = "\n".join(textwrap.fill(v, width, initial_indent=f"  {k.replace('_', ' ').capitalize():<{pad}}  ",
                                           subsequent_indent=" " * (pad + 4)) for k, v in fields.items())
        blocks.append(f"{heading}\n{body}")
    return "\n\n".join(blocks)

def _to_trash(path):
    """Move a file into HOME/.trash (a clash gets a number). Returns the new path, or None if there was no such file."""
    path = Path(path)
    if not path.exists():
        return None
    trash = HOME / ".trash"
    trash.mkdir(parents=True, exist_ok=True)
    target, n = trash / path.name, 2
    while target.exists():
        target = trash / f"{path.stem}-{n}{path.suffix}"
        n += 1
    path.replace(target)
    return target


def delete(story):
    """Take a story out of the list: its JSON and its markdown file move to HOME/.trash (nothing is destroyed). Returns the trash folder
    if anything moved (else None). Your universe is untouched."""
    moved = _to_trash(STORIES / f"{story['id']}.json")
    old = story.get("md_path")
    if old and _to_trash(old):
        moved = moved or True
    return (HOME / ".trash") if moved else None

def _focus_key(story):
    from . import focus
    return focus.of_draft(story)


def _ending_key(story):
    from . import endings
    return endings.of_draft(story)


def story_json(story, path=None):
    """Everything an outside program needs about a story, as plain data."""
    kept = story["kept"]
    shape = structures.get((kept.get("structure") or {}).get("structure"))
    genre = kept.get("genre", {})
    return {"id": story.get("id"), "title": title_of(story), "created": story.get("created"),
            "step": story.get("step", 0), "steps": len(steps_for(story)),
            "done": story.get("step", 0) >= len(steps_for(story)),
            "genre": genre.get("genre"), "mood": genre.get("mood"),
            "focus": _focus_key(story), "ending": _ending_key(story),
            "structure": shape.label if kept.get("structure") else None,
            "motif": (kept.get("title") or {}).get("motif"),
            "kept": {k: public(v) for k, v in kept.items()},
            "threads": story.get("threads", {}),
            "text": to_plain(story), "markdown": to_markdown(story) if kept else "",
            "path": str(path) if path else story.get("md_path"),
            "resume": f"storywheel resume {story['id']}" if story.get("id") else None}

def export(story, out_dir=None):
    out = Path(out_dir) if out_dir else OUT
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{_slug(title_of(story))}-{story['id']}.md"
    if out_dir:                                 # one-off copy somewhere else
        path.write_text(to_markdown(story))
        return path
    old = story.get("md_path")
    if old and old != str(path) and Path(old).exists():
        Path(old).unlink()                      # title changed: replace the old file
    path.write_text(to_markdown(story))
    story["md_path"] = str(path)
    (STORIES / f"{story['id']}.json").write_text(json.dumps(story, indent=2))
    return path
