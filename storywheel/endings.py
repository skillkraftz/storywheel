"""How the story ends: a picked field on the Genre step (never rolled), kept with the genre.

    ENDINGS            any (the default: the story decides), triumph, bittersweet, tragic, open
    of_draft(story)    a Wheel draft's ending key ("any" for an older draft)
    find(text)         an ending key from a key or a label, ignoring case; None if unknown

A climax or resolution template may carry an `"ending"` in its data (a name or a list of names: `{"text": "...", "ending": ["tragic", "open"]}`).
With an ending picked, a template that names others is set aside; an untagged template fits any ending. With "any" nothing is filtered."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Ending:
    key: str
    label: str
    hint: str


ENDINGS = (
    Ending("any", "Any (let the story decide)", "Nothing is held back: climaxes and resolutions of every kind can come up."),
    Ending("triumph", "Triumph", "The protagonist wins, and it holds."),
    Ending("bittersweet", "Bittersweet", "The protagonist wins something and loses something."),
    Ending("tragic", "Tragic", "The protagonist loses, or wins too late."),
    Ending("open", "Open", "The story stops before the question is answered."),
)
BY_KEY = {e.key: e for e in ENDINGS}
DEFAULT = "any"
NAMES = tuple(e.key for e in ENDINGS if e.key != DEFAULT)         # what a template may say in its "ending"


def get(key):
    return BY_KEY.get(str(key or "").strip().lower(), BY_KEY[DEFAULT])


def find(text):
    t = str(text or "").strip().lower()
    for e in ENDINGS:
        if t in (e.key, e.label.lower()):
            return e.key
    return None


def choices():
    """[(label, key)] for a picker."""
    return [(e.label, e.key) for e in ENDINGS]


def of_draft(story):
    key = find((story or {}).get("ending"))
    if key:
        return key
    return find((((story or {}).get("kept") or {}).get("genre") or {}).get("ending")) or DEFAULT
