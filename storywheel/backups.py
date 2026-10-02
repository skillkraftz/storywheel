"""Backups of a story's manuscript: the Writer's rolling copies, and the copies made before a conversion or a restore. Browse them, read a
preview, and restore one (the current version is copied aside first, so a restore can itself be undone).

    <story>/.backups/2026-10-02/1530-manuscript.md       rolling: made while you write (a copy every 15 minutes at most, 30 days kept)
    <story>/.backups/migrated-20261002-153000/...        the scene files, before they were merged into one manuscript
    <story>/.backups/paragraphs-.../  quotes-.../         before paragraphs were put one to a line / quotes made straight
    <story>/.backups/restore-.../                         what was there before a restore
"""
import datetime
import re
import shutil
from pathlib import Path

from . import vault

KINDS = {"rolling": "while writing", "migrated": "before scenes were merged", "paragraphs": "before paragraphs were joined",
         "quotes": "before quotes were made straight", "restore": "before a restore"}
ROLLING = re.compile(r"^(\d{4})-(.+)$")
STAMPED = re.compile(r"^(migrated|paragraphs|quotes|restore)-(\d{8})-(\d{6})$")


def _entry(story, root, path, kind, when):
    rel = path.relative_to(root).as_posix()
    name = ROLLING.match(path.name).group(2) if kind == "rolling" and ROLLING.match(path.name) else path.name
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    return {"id": rel, "kind": kind, "what": KINDS[kind], "when": when.strftime("%Y-%m-%d %H:%M"), "file": name,
            "words": vault.count_words(text), "path": str(path), "_sort": when}


def list_backups(story):
    """Every backup of the story's manuscript files, newest first: [{id, kind, what, when, file, words, path}]."""
    root = story.path / ".backups"
    out = []
    if not root.is_dir():
        return out
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        m = STAMPED.match(folder.name)
        if m:
            when = datetime.datetime.strptime(m.group(2) + m.group(3), "%Y%m%d%H%M%S")
            for f in sorted(folder.iterdir()):
                if f.is_file():
                    out.append(_entry(story, root, f, m.group(1), when))
        elif re.fullmatch(r"\d{4}-\d\d-\d\d", folder.name):
            day = datetime.datetime.strptime(folder.name, "%Y-%m-%d")
            for f in sorted(folder.iterdir()):
                r = ROLLING.match(f.name)
                if f.is_file() and r:
                    when = day.replace(hour=int(r.group(1)[:2]), minute=int(r.group(1)[2:]))
                    out.append(_entry(story, root, f, "rolling", when))
    out.sort(key=lambda e: e["_sort"], reverse=True)
    for e in out:
        e.pop("_sort")
    return out


def find(story, backup_id):
    for e in list_backups(story):
        if e["id"] == backup_id:
            return e
    return None


def preview(entry, lines=14, width=100):
    """The first lines of what the backup holds (and how it differs in size from the file now, in the second return value)."""
    try:
        text = Path(entry["path"]).read_text(encoding="utf-8")
    except OSError:
        return "(can't read this backup)"
    shown = [l[:width] + ("…" if len(l) > width else "") for l in text.split("\n") if l.strip()][:lines]
    return "\n".join(shown)


def restore(story, backup_id):
    """Put a backup back as its manuscript file. What was there is copied to .backups/restore-DATE/ first. Returns
    {"restored": file name, "kept": path of the copy of the version that was replaced (or None), "words": words now}."""
    e = find(story, backup_id)
    if e is None:
        raise ValueError(f"There is no backup '{backup_id}'.")
    target = story.manuscript_dir / e["file"]
    kept = None
    if target.exists():
        when = datetime.datetime.now()
        while (story.path / ".backups" / f"restore-{when.strftime('%Y%m%d-%H%M%S')}").exists():
            when += datetime.timedelta(seconds=1)                   # (two restores in one second keep separate copies)
        folder = story.path / ".backups" / f"restore-{when.strftime('%Y%m%d-%H%M%S')}"
        folder.mkdir(parents=True, exist_ok=True)
        kept = folder / target.name
        shutil.copy2(target, kept)
    story.manuscript_dir.mkdir(parents=True, exist_ok=True)
    text = Path(e["path"]).read_text(encoding="utf-8")
    vault._write(target, text)
    return {"restored": target.name, "kept": str(kept) if kept else None, "words": vault.count_words(text)}
