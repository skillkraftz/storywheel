"""Word banks: words you chose while looking around a topic, kept per story or per universe, and saved as a universe atom list
(`<universe>/lists/<slot>/wordbank-....json`) so the Wheel and Builder can roll with them."""
import json
import re
from pathlib import Path

from . import vault
from .library import DATA

BANK = "wordbank.json"


def path_for(universe, story=None):
    return (story.path if story is not None else universe.path) / BANK


def load(universe, story=None):
    """{"name", "words": [{"word", "note"}]} for a story (story given) or the universe."""
    p = path_for(universe, story)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("words", [])
    data.setdefault("name", story.title if story is not None else universe.name)
    return data


def save(universe, data, story=None):
    p = path_for(universe, story)
    p.parent.mkdir(parents=True, exist_ok=True)
    vault._write(p, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return p


def add(universe, words, story=None, note=""):
    """Add words (strings, or (word, note) pairs); returns how many were new."""
    data = load(universe, story)
    have = {w["word"].lower() for w in data["words"]}
    new = 0
    for item in words:
        word, n = (item if isinstance(item, (tuple, list)) else (item, note))
        word = word.strip()
        if word and word.lower() not in have:
            have.add(word.lower())
            data["words"].append({"word": word, "note": n})
            new += 1
    save(universe, data, story)
    return new


def remove(universe, word, story=None):
    data = load(universe, story)
    before = len(data["words"])
    data["words"] = [w for w in data["words"] if w["word"].lower() != word.lower()]
    save(universe, data, story)
    return before - len(data["words"])


def slots():
    """The slots a list can fill (job, thing, place, landmark, someone...), from the built-in lists."""
    return sorted(p.name for p in (DATA / "lists").iterdir() if p.is_dir())


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "words"


def save_as_atom_list(universe, data, slot, name=None):
    """Write the bank as a universe list for `slot`. Atoms are short (five words at most), so longer entries are skipped and
    reported. Returns (path, written count, skipped list)."""
    if slot not in slots():
        raise ValueError(f"'{slot}' is not a slot (known: {', '.join(slots())})")
    entries, skipped = [], []
    for w in data["words"]:
        word = w["word"].strip()
        if len(word.split()) > 5:
            skipped.append(word)
        elif word and word not in entries:
            entries.append(word)
    if not entries:
        raise ValueError("The word bank has nothing to save.")
    genres = [g.lower() for g in universe.settings().get("genres", [])] or ["general"]
    folder = universe.lists_dir / slot
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"wordbank-{slug(name or data.get('name') or 'words')}.json"
    vault._write(path, json.dumps({"_note": f"Made from a word bank in storywheel's Words mode ({data.get('name', '')}).",
                                   "slot": slot, "tags": genres, "entries": entries}, indent=2, ensure_ascii=False) + "\n")
    return path, len(entries), skipped
