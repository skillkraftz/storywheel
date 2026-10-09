"""Story focus: who or what the story is about. A picked field on the Genre step (never rolled), kept with the genre.

    FOCUSES            one protagonist (the default), two leads, an ensemble, a place, no one (a mood piece or vignette)
    of_draft(story)    a Wheel draft's focus key (older drafts have none: one protagonist)
    is_person(key)     does the story have a protagonist? (a place or no one: no)
    find(text)         a focus key from a key or a label, ignoring case; None if unknown

A story with a person at its centre (one, two leads, an ensemble) has the Protagonist step as always; two leads and an ensemble add a
`partner` or a `company` line to it (steps.py), and promotion makes them characters. A story about a place or about no one has no
protagonist: the step is skipped, and the fallback subject stands where `{first}` would (steps.Ctx.subject): the place, or the title's
motif. The frames themselves still tell one arc; see BACKLOG.md for what a real ensemble or a mood piece would need."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Focus:
    key: str
    label: str            # what the picker and the card show
    person: bool          # does the story have a protagonist?
    hint: str


FOCUSES = (
    Focus("one", "One protagonist", True, "The story follows one person's want and need."),
    Focus("two", "Two leads", True, "Two people share the story: the Protagonist step also makes a partner."),
    Focus("ensemble", "An ensemble", True, "A group carries the story: the Protagonist step also makes a company around the lead."),
    Focus("place", "A place", False, "The place is the subject: there is no protagonist, and the story is told about the setting."),
    Focus("none", "No one (a mood piece)", False, "A vignette or mood piece: no protagonist; the title's motif or the place stands in."),
)
BY_KEY = {f.key: f for f in FOCUSES}
DEFAULT = "one"


def get(key):
    return BY_KEY.get(str(key or "").strip().lower(), BY_KEY[DEFAULT])


def find(text):
    t = str(text or "").strip().lower()
    for f in FOCUSES:
        if t in (f.key, f.label.lower()):
            return f.key
    return None


def choices():
    """[(label, key)] for a picker."""
    return [(f.label, f.key) for f in FOCUSES]


def of_draft(story):
    """A draft's focus key: the one chosen for it, else the one its kept genre step records, else one protagonist."""
    key = find((story or {}).get("focus"))
    if key:
        return key
    return find((((story or {}).get("kept") or {}).get("genre") or {}).get("focus")) or DEFAULT


def is_person(key):
    return get(key).person
