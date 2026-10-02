"""Words as universe atoms: one action puts a word on a universe's own list for a slot (job, thing, place...), so the Wheel and Builder
can roll with it. (The old per-story and per-universe 'word banks' were folded into My words by `migrate_banks`.)"""
import json
import re
from pathlib import Path

from . import vault
from .library import DATA

BANK = "wordbank.json"


def path_for(universe, story=None):
    return (story.path if story is not None else universe.path) / BANK


def migrate_banks(my_words):
    """Older versions kept 'word banks' per story and universe. Their words go into My words (note: where they came from) and the
    old file is renamed wordbank.json.migrated (nothing is deleted). Returns how many words were brought over."""
    n = 0
    for u in vault.list_universes():
        places = [(u.path, f"word bank of {u.name}")] + [(s.path, f"word bank of {s.title}") for s in u.stories()]
        for folder, note in places:
            p = Path(folder) / BANK
            if not p.exists():
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for w in data.get("words", []):
                if w.get("word") and my_words.mark_learning(w["word"], note=w.get("note") or note):
                    n += 1
            p.rename(p.with_name(BANK + ".migrated"))
    return n


def slots():
    """The slots a list can fill (job, thing, place, landmark, someone...), from the built-in lists."""
    return sorted(p.name for p in (DATA / "lists").iterdir() if p.is_dir())


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "words"


def add_to_universe_list(universe, word, slot):
    """Add one word to the universe's own list for `slot` (`<universe>/lists/<slot>/words-added.json`), tagged with the universe's
    genres so the Wheel and Builder roll with it. Atoms are five words at most. Returns (path, True if the word was new)."""
    if slot not in slots():
        raise ValueError(f"'{slot}' is not a slot (known: {', '.join(slots())})")
    word = word.strip()
    if not word or len(word.split()) > 5:
        raise ValueError("A list entry is one to five words.")
    folder = universe.lists_dir / slot
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "words-added.json"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        doc = {}
    genres = [g.lower() for g in universe.settings().get("genres", [])] or ["general"]
    doc.setdefault("_note", "Words added in storywheel's Words mode (Add to this universe's word list).")
    doc["slot"] = slot
    doc.setdefault("tags", genres)
    doc.setdefault("entries", [])
    new = word not in doc["entries"]
    if new:
        doc["entries"].append(word)
    vault._write(path, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return path, new
