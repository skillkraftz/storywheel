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


def added_words(universe):
    """[(slot, word)] on the universe's own 'words added' lists, by slot."""
    out = []
    folder = universe.lists_dir
    if not folder.is_dir():
        return out
    for slot_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        path = slot_dir / "words-added.json"
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out += [(slot_dir.name, w) for w in doc.get("entries", [])]
    return out


def remove_added(universe, slot, word):
    """Take a word off the universe's 'words added' list for a slot (the file goes when the list is empty). Returns True if it was there."""
    path = universe.lists_dir / slot / "words-added.json"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    before = len(doc.get("entries", []))
    doc["entries"] = [w for w in doc.get("entries", []) if w != word]
    if len(doc["entries"]) == before:
        return False
    if doc["entries"]:
        vault._write(path, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    else:
        vault.forget(path)
        path.unlink()
    return True


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
