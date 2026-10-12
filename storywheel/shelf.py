"""Every story in the library in one list, across all universes.

    rows(status=None, fmt=None, universe=None)   [{story, universe, universe_name, title, logline, format, format_label, status, size,
                                                   words, edited}] newest edit first
    counts(universe)                             {status: n} for one universe (the collection's header line)
    edited_text(ts)                              "2026-10-12 14:05" for a modification time

The list is for finding and tracking, so it must stay quick with hundreds of stories (a Raspberry Pi 4). Each story's row is worked out once
and remembered (vault.memo) until one of its files changes: the fingerprint is only a stat of story.md, settings.toml, notes.md and the
files in manuscript/, with nothing read or parsed. A refresh with nothing changed parses nothing."""
import datetime
import os
from pathlib import Path

from . import formats, settings, vault, versions


def _fingerprint(story):
    """(stamp, newest modification time) of what a row is made from: nothing is opened, only stat'ed."""
    parts, newest = [], 0.0

    def one(name, st):
        nonlocal newest
        parts.append((name, st.st_mtime_ns, st.st_size))
        newest = max(newest, st.st_mtime)

    for p in (story.outline_path, story.settings_path, story.notes_path):
        try:
            one(p.name, p.stat())
        except OSError:
            parts.append((p.name, None, None))
    try:
        with os.scandir(story.manuscript_dir) as it:
            for e in sorted(it, key=lambda e: e.name):
                if e.is_file() and not e.name.startswith("."):
                    one("m/" + e.name, e.stat())
    except OSError:
        pass
    return tuple(parts), newest


def _row(story, universe_name):
    fmt = formats.of_story(story)
    if story.is_screenplay():
        text = versions.size_text(story)
    else:
        text = f"{story.word_count():,} words"
    return {"story": story, "universe": story.universe.slug, "universe_name": universe_name, "slug": story.slug,
            "title": story.title, "logline": story.logline, "format": fmt, "format_label": formats.get(fmt).short,
            "status": story.status, "size": text, "words": story.word_count()}


def story_row(story, universe_name=None):
    """One story's row, remembered until its files change (or your global settings do: they set a format for stories that name none)."""
    stamp, newest = _fingerprint(story)
    name = universe_name if universe_name is not None else story.universe.name
    key = (str(story.path), "shelfrow", name)
    row = vault.memo(key, (stamp, vault.stamp(settings.global_path())), lambda: _row(story, name))
    return dict(row, edited=newest)


def rows(status=None, fmt=None, universe=None):
    """Every story (in one universe, or in all), newest edit first, optionally only one status and/or one format key."""
    out = []
    unis = [universe] if universe is not None else vault.list_universes()
    for u in unis:
        name = u.name
        for s in u.stories():
            r = story_row(s, name)
            if status and r["status"] != status:
                continue
            if fmt and r["format"] != fmt:
                continue
            out.append(r)
    out.sort(key=lambda r: (-r["edited"], r["universe"], r["slug"]))
    return out


def counts(universe):
    """{status: how many stories} for one universe, every status present."""
    found = {k: 0 for k in vault.STATUSES}
    for r in rows(universe=universe):
        found[r["status"]] += 1
    return found


def edited_text(ts):
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except (OverflowError, OSError, ValueError):
        return ""


def parse_status(text):
    """A status from what was typed (any case), or None."""
    t = str(text or "").strip().lower()
    return t if t in vault.STATUSES else None
