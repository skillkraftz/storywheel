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
SECTION_BREAK = '\n\n---\n<div style="page-break-after: always;"></div>\n\n'


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
    STORIES.mkdir(parents=True, exist_ok=True)
    sync_base(story)                            # the mix follows the kept genres
    for key, hist in story["history"].items():
        story["history"][key] = hist[-HISTORY_LIMIT:]
    (STORIES / f"{story['id']}.json").write_text(json.dumps(story, indent=2))
    if story["kept"]:
        return export(story)

def load(story_id):
    return upgrade(json.loads((STORIES / f"{story_id}.json").read_text()))

def all_stories():
    """Newest first."""
    if not STORIES.exists():
        return []
    return [upgrade(json.loads(p.read_text())) for p in sorted(STORIES.glob("*.json"), reverse=True)]

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
    if motif:
        front.append(f'motif: "{motif}"')
    front += [f"created: {story['created'][:10]}", "tags: [storywheel]", "---", ""]

    head = [f"# {title}", ""]
    if genre:
        head.append(f"*{genre.get('genre', '')} · {genre.get('mood', '')}*")
    if motif:
        head.append(f"*Motif: {motif}*")

    sections = ["\n".join(front + head).rstrip()]
    for step in steps_for(story):
        fields = public(kept.get(step.key))
        if not fields or step.key in ("genre", "title", "structure"):
            continue
        if step.key == "spine":
            labels = {b.key: b.label for b in shape.beats}
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
