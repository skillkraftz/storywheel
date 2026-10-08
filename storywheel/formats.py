"""What a story is written as: its format, chosen from a list (never typed), and what follows from it.

    FORMATS                   the four choices: short story, novel, screenplay (feature film), screenplay (short film)
    structures_for(key)       the structures that fit a format (a screen structure names its formats; the others fit prose)
    of_story(story)           a promoted story's format key, from its settings (and its structure, for older scripts)
    of_draft(draft)           a Wheel draft's format key
    apply(story, key, target) saves a story's format and target length in its settings.toml
    target(story)             (number, unit): the length the story aims at, in words for prose and pages for a script

A story's settings.toml keeps `format` as short-story, novel or screenplay (what the Writer and the export read); a screenplay also keeps
`script_kind` (feature-film or short-film) and `target_pages`, prose keeps `target_words`. A Wheel draft keeps the key itself (`format`)."""
from dataclasses import dataclass

from . import settings, structures


@dataclass(frozen=True)
class Format:
    key: str              # short-story, novel, feature-film, short-film
    label: str            # what the pickers show
    setting: str          # what settings.toml's `format` holds: short-story, novel or screenplay
    unit: str             # "words" or "pages"
    target: int           # the usual length, the target a new story starts with


FORMATS = (
    Format("short-story", "Short story", "short-story", "words", 5000),
    Format("novel", "Novel", "novel", "words", 80000),
    Format("feature-film", "Screenplay (feature film)", "screenplay", "pages", 110),
    Format("short-film", "Screenplay (short film)", "screenplay", "pages", 12),
)
BY_KEY = {f.key: f for f in FORMATS}
DEFAULT = "short-story"
SCRIPT_KINDS = ("feature-film", "short-film")


def get(key):
    """The Format for a key (an unknown or empty key is the default, short story)."""
    return BY_KEY.get(str(key or "").strip().lower(), BY_KEY[DEFAULT])


def known(key):
    return str(key or "").strip().lower() in BY_KEY


def find(text):
    """A format key from a key or a label ("Short story", "short-film", "Screenplay (feature film)"), ignoring case; None if unknown."""
    t = str(text or "").strip().lower()
    for f in FORMATS:
        if t in (f.key, f.label.lower()):
            return f.key
    return None


def is_script(key):
    return get(key).setting == "screenplay"


def choices():
    """[(label, key)] for a picker."""
    return [(f.label, f.key) for f in FORMATS]


def structures_for(key):
    """The structures a story of this format can be built on, in the order they are offered."""
    key = get(key).key
    return [s for s in structures.registry().values() if key in s.formats]


def fits(structure, key):
    return structure is not None and get(key).key in structure.formats


def default_structure(key):
    found = structures_for(key)
    return found[0] if found else None


def from_setting(fmt, kind="", structure_text=""):
    """A format key from what settings.toml says (format, script_kind) and the story's structure: a script with no kind recorded is a short
    film when its structure is the short film's, else a feature."""
    fmt = str(fmt or "").strip().lower()
    if fmt in ("short-story", "novel"):
        return fmt
    if fmt in SCRIPT_KINDS:                                     # (a format key written where the setting belongs)
        return fmt
    if fmt == "screenplay" or (structures.find(structure_text or "") is not None and structures.find(structure_text).screen):
        kind = str(kind or "").strip().lower()
        if kind in SCRIPT_KINDS:
            return kind
        shape = structures.find(structure_text or "")
        if shape is not None and shape.screen and shape.formats:
            return shape.formats[0]
        return "feature-film"
    return DEFAULT


def global_default():
    """The format a new story starts as: your default in Settings (a screenplay there means a feature film)."""
    g = settings.load_global()
    return from_setting(g.get("format", DEFAULT), g.get("script_kind", ""))


def of_story(story):
    st = settings.load_story(story.path)
    meta, _sections = story.load_outline()
    return from_setting(st.get("format"), st.get("script_kind"), meta.get("structure", ""))


def of_draft(draft):
    """A Wheel draft's format: the one chosen for it, else what its kept structure implies, else your default."""
    key = str((draft or {}).get("format") or "")
    if known(key):
        return key.lower()
    text = (((draft or {}).get("kept") or {}).get("structure") or {}).get("structure", "")
    shape = structures.find(text or "")
    if shape is not None and shape.screen:
        return from_setting("screenplay", "", text)
    return global_default()


def apply(story, key, target=None):
    """Save a story's format (and its target length: words for prose, pages for a script; the format's usual length when not given)."""
    f = get(key)
    try:
        target = int(target) if target not in (None, "") else f.target
    except (TypeError, ValueError):
        target = f.target
    values = {"format": f.setting}
    if f.unit == "pages":
        values.update(script_kind=f.key, target_pages=max(1, target))
    else:
        values.update(target_words=max(0, target))
    settings.save_story(story.path, values)


def target(story):
    """(number, unit) the story aims at: target_words for prose, target_pages for a script (0 words: no target set)."""
    f = get(of_story(story))
    st = settings.load_story(story.path)
    if f.unit == "pages":
        from . import screenplay
        return screenplay.target_pages(story), "pages"
    try:
        return int(st.get("target_words") or 0), "words"
    except (TypeError, ValueError):
        return 0, "words"


def parse_target(text):
    """A target typed in a box: digits (commas and spaces allowed) -> int; anything else -> None."""
    t = str(text or "").replace(",", "").replace(" ", "").strip()
    return int(t) if t.isdigit() else None
