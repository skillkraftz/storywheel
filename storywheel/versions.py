"""Versions: the same story as several stories in different formats (a short story AND a screenplay), in one universe.

    family_of(story)                     the family id in story.md ("" for a story with no versions)
    siblings(story)                      the other stories of the family, in the order they were made
    versions(story)                      the whole family, the story included
    rows(universe)                       the Builder's story list: [{family, title, members: [Story]}], one entry per family
    new_version(story, fmt, ...)         makes a sibling in another (or the same) format; returns (new story, notes)
    prose_to_fountain(text, ...)         a rough start: prose paragraphs as Fountain action
    fountain_to_prose(text)              a rough start: a script's action and dialogue as prose paragraphs

A version is a separate story folder in the same universe. Siblings share a `family` id in story.md (the first story's slug). Content is
COPIED, never synced: editing one outline changes nothing in the other. Characters, places, things, groups and notes belong to the universe,
so every version already shares them. A story with no `family` has no siblings and behaves exactly as before; the source of the first
version gets its `family` written then. Deleting or renaming one version never touches the others (a family is only an id)."""
import shutil
from dataclasses import dataclass

from . import formats, fountain, outline, screenplay, settings, structures, vault

COPY_OPTIONS = ("outline", "notes", "seed", "genres", "structure", "manuscript")
DEFAULT_COPY = ("outline", "notes", "seed", "genres", "structure")           # (the manuscript is the writer's choice, off by default)
COPY_LABELS = {"outline": "Outline sections (premise, setting, twist)", "notes": "Story notes", "seed": "The Wheel draft it came from (seed.json)",
               "genres": "Genres", "structure": "Structure and its beats",
               "manuscript": "The manuscript, as a rough start"}
ROUGH = "Rough start"


class VersionError(Exception):
    pass


# --- families ---------------------------------------------------------------------------------------------------------------------

def family_of(story):
    return str(story.meta.get("family") or "")


def versions(story):
    """The story's whole family in the order the stories were made (just [story] when it has no versions)."""
    fam = family_of(story)
    if not fam:
        return [story]
    found = [s for s in story.universe.stories() if family_of(s) == fam]
    found.sort(key=lambda s: (_number(s), s.slug))
    return found or [story]


def _number(story):
    """Where the story stands in its family: the first story is 1, each version after it has the next number (`version` in story.md)."""
    try:
        return int(story.meta.get("version") or 1)
    except (TypeError, ValueError):
        return 1


def siblings(story):
    return [s for s in versions(story) if s.slug != story.slug]


def rows(universe):
    """The story list, versions together: [{family, title, members}] with a family's stories in one entry, in the order of the first member."""
    out, seen = [], {}
    for s in universe.stories():
        fam = family_of(s)
        if fam and fam in seen:
            seen[fam]["members"].append(s)
            continue
        entry = {"family": fam, "title": s.title, "members": [s]}
        out.append(entry)
        if fam:
            seen[fam] = entry
    for entry in out:
        entry["members"] = versions(entry["members"][0]) if entry["family"] else entry["members"]
    return out


def size_text(story):
    """'1,240 words' or '~12 pages': how big a version is, in its own unit."""
    if story.is_screenplay():
        pages = 0
        try:
            from . import screenplay_pdf
            pages = screenplay_pdf.estimate_pages(story.manuscript_text()) if story.script_path.exists() else 0
        except Exception:                                  # (no reportlab: the words will do)
            pass
        return f"~{pages:g} pages" if pages else f"{story.word_count():,} words"
    return f"{story.word_count():,} words"


def other_version(story, step=1):
    """The next (step 1) or previous (step -1) version of the story, wrapping round; None when it has no siblings."""
    family = versions(story)
    if len(family) < 2:
        return None
    at = next(i for i, s in enumerate(family) if s.slug == story.slug)
    return family[(at + step) % len(family)]


# --- rough conversions ------------------------------------------------------------------------------------------------------------

def prose_to_fountain(text):
    """Prose as Fountain action: one paragraph (one line) per block, a blank line between. A scene break becomes a forced scene heading
    (`.NEW SCENE`, or the break's own title in capitals) for you to rewrite as a real one. Emphasis marks carry over."""
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        label = vault.marker_label(s)
        if label is not None:
            out.append("." + (label.upper() if label else "NEW SCENE"))
        else:
            inner = vault.centered_text(s)
            out.append(f"> {inner} <" if inner else ("!" + s if fountain.is_heading(s) else s))
    return "\n\n".join(out) + ("\n" if out else "")


def _said(text, name):
    t = text.replace("\n", " ").strip()
    if not t:
        return ""
    if t[-1] in ".,":
        t = t[:-1] + ","
    elif t[-1] not in "?!…-—:":
        t += ","
    return f'"{t.replace(chr(34), chr(39))}" {name} said.'


def fountain_to_prose(text):
    """A script's action and dialogue as prose paragraphs, one per line (the manuscript's form). Each scene heading becomes a named scene
    marker (`* * * INT. ATTIC - NIGHT`); a speech becomes `"Words," Name said.`; transitions, parentheticals, sections, synopses and the
    title page are left out."""
    script = fountain.parse(text)
    out, name = [], ""
    for e in script.elements:
        if e.type == "heading":
            out.append(f"* * * {e.text.strip()}")
        elif e.type == "action":
            body = " ".join(e.text.split())
            if body and body != "FADE IN:":
                out.append(body)
        elif e.type == "character":
            name = (e.name or "").strip().title()
        elif e.type == "dialogue":
            line = _said(" ".join(e.text.split()), name or "Someone")
            if line:
                out.append(line)
        elif e.type == "centered":
            out.append(f">{e.text.strip()}<")
    return "\n".join(out) + ("\n" if out else "")


# --- making a version ---------------------------------------------------------------------------------------------------------------

def _copy_manuscript(src, dst):
    """Copies the source's manuscript into the new story as a rough start. Returns a sentence about what was done ('' if there was nothing)."""
    a, b = formats.is_script(formats.of_story(src)), formats.is_script(formats.of_story(dst))
    files = src.files()
    if not files or not any(p.read_text(encoding="utf-8").strip() for p in files):
        return "The manuscript was empty, so there was nothing to copy."
    dst.manuscript_dir.mkdir(parents=True, exist_ok=True)
    if not a and not b:
        for p in files:
            shutil.copy2(p, dst.manuscript_dir / p.name)
        return f"{ROUGH}: the manuscript was copied as it is ({len(files)} file{'s' if len(files) != 1 else ''}); it is a separate copy now."
    if not a and b:
        body = prose_to_fountain(src.manuscript_text())
        head = screenplay.skeleton(dst).rstrip("\n").replace("\n\nFADE IN:", "")
        note = f"[[{ROUGH}: converted from the prose of \"{src.title}\". Every paragraph is action. Rewrite it as scenes, action and dialogue.]]"
        vault._write(dst.script_path, f"{head}\n\n{note}\n\nFADE IN:\n\n{body}")
        return f"{ROUGH}: the prose was written into script.fountain as action. Rewrite it as scenes, action and dialogue."
    if a and not b:
        prose = fountain_to_prose(src.script_path.read_text(encoding="utf-8"))
        if formats.of_story(dst) == "novel":
            dst.add_scene(src.title, prose)
        else:
            vault._write(dst.manuscript_dir / "manuscript.md", prose)
        return f"{ROUGH}: the script's action and dialogue became prose paragraphs. Expect to rewrite them."
    shutil.copy2(src.script_path, dst.script_path)
    return f"{ROUGH}: the script was copied as it is; it is a separate copy now."


def new_version(story, fmt, title=None, copy=DEFAULT_COPY, target=None):
    """A sibling of `story` in the format `fmt` (a key from formats.FORMATS), in the same universe and family. `copy` says what is copied
    from COPY_OPTIONS. Returns (new story, [notes]). Nothing in `story` changes except that it joins the family when it had none."""
    if not formats.known(fmt):
        raise VersionError(f"Unknown format '{fmt}'. Choose one of: {', '.join(f.key for f in formats.FORMATS)}")
    copy = set(copy or ())
    bad = copy - set(COPY_OPTIONS)
    if bad:
        raise VersionError(f"Unknown thing to copy: {', '.join(sorted(bad))}. Choose from: {', '.join(COPY_OPTIONS)}")
    universe = story.universe
    title = (title or story.title).strip() or story.title
    meta, sections = story.load_outline()
    family = family_of(story) or story.slug
    notes = []

    new_meta = {k: v for k, v in meta.items() if k not in ("id", "title", "universe", "created", "family", "format", "target")}
    if "genres" not in copy:
        new_meta.pop("genre", None)
    new_sections = {}
    shape = structures.find(meta.get("structure", ""))
    beat_heads = [h for h in sections if outline.is_beat_section(h)]
    if "outline" in copy:
        new_sections.update({h: t for h, t in sections.items() if h not in beat_heads})
    if "structure" in copy:
        new_sections.update({h: sections[h] for h in beat_heads})
    else:
        for k in ("structure", "repeats"):
            new_meta.pop(k, None)
        shape = None
    if "structure" in copy and shape is not None and not formats.fits(shape, fmt):
        fit = formats.default_structure(fmt)
        if fit is not None:                                   # the old beats stay as they are; the new format's beats are blank, to map by hand
            new_sections[fit.label] = outline.blank_beats(fit)
            new_meta["structure"] = fit.label
            new_meta.pop("repeats", None)
            notes.append(f"{shape.label} doesn't fit {formats.get(fmt).label}: its beats were copied as they are, and {fit.label} was added with "
                         "blank beats for you to fill in.")
    new_meta["family"] = family
    new_meta["version"] = str(max(_number(s) for s in versions(story)) + 1)
    new_meta["format"] = formats.get(fmt).key
    if target is not None:
        new_meta["target"] = target

    taken = {s.slug for s in universe.stories()}
    base = vault.slugify(title, "story")
    slug = base
    if slug in taken:
        slug = f"{base}-{formats.get(fmt).key}"
    if slug in taken:
        slug = None                                             # (new_story numbers it)
    seed = story.seed() if "seed" in copy else None
    new = universe.new_story(title, new_meta, new_sections, seed=seed, slug=slug)
    if family_of(story) != family:
        story.set_meta(family=family)
    if "notes" in copy and story.notes.strip():
        new.save_notes(story.notes)
    if "manuscript" in copy:
        notes.append(_copy_manuscript(story, new))
    return new, notes


def create_versions(story, keys, copy=DEFAULT_COPY):
    """One version for each format key (used by promotion). Returns [(new story, notes)]."""
    return [new_version(story, k, copy=copy) for k in keys]
