"""A spelling word list per universe: the names of its characters, places, things and groups, and the proper nouns in a story's outline,
written where the Writer's spellchecker can read them (`<universe>/spell/names.utf-8.add`). Words you add yourself with "Add to
Dictionary" go to `<universe>/spell/en.utf-8.add`, which is never overwritten."""
import re
from pathlib import Path

from . import vault

WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*[A-Za-z]|[A-Za-z]")
SKIP = {"The", "A", "An", "And", "But", "Or", "Of", "In", "On", "At", "To", "For", "With", "As", "By", "From", "He", "She", "It", "They",
        "We", "You", "I", "His", "Her", "Their", "Its", "Our", "My", "Your", "This", "That", "These", "Those", "Once", "Every", "One", "Until",
        "Because", "Then", "When", "While", "After", "Before", "If", "So", "Not", "No", "Yes", "What", "Who", "Why", "How", "Where"}


def name_words(universe):
    out = set()
    for e in universe.entities():
        for field in ("name",):
            for w in WORD.findall(e.fields.get(field, "") or ""):
                out.add(w.replace("’", "'"))
    return out


def outline_words(story):
    """Capitalized words in the story's outline that do not start a sentence: very likely proper nouns."""
    out = set()
    try:
        meta, sections = story.load_outline()
    except Exception:
        return out
    for text in list(sections.values()) + [str(meta.get("title", ""))]:
        for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
            words = WORD.findall(sentence)
            for i, w in enumerate(words):
                if w[0].isupper() and i > 0 and w not in SKIP and not w.isupper():
                    out.add(w.replace("’", "'"))
    return out


def write_names(story, folder):
    """Write the universe's name list (the Writer reads it; Vim needs the plural/possessive forms spelled out). Returns the path."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    words = name_words(story.universe) | outline_words(story)
    lines = set()
    for w in words:
        lines.add(w)
        if not w.endswith("'s"):
            lines.add(w + "'s")                      # (possessives: Vim does not guess them for an added word)
    path = folder / "names.utf-8.add"
    new = "\n".join(sorted(lines, key=str.lower)) + ("\n" if lines else "")
    if not path.exists() or path.read_text(encoding="utf-8") != new:
        vault._write(path, new)
    return path
