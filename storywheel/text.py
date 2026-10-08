"""Small text polish: articles, plurals, title case, pronouns."""
import re

SMALL_WORDS = {"a", "an", "the", "of", "from", "to", "and", "in", "on", "at",
               "for", "with", "who", "never", "how", "would", "not"}


def plural(w):
    if w.endswith("y") and w[-2:-1] not in "aeiou":
        return w[:-1] + "ies"
    if w.endswith(("s", "x", "z", "ch", "sh")):
        return w + "es"
    return w + "s"


# nouns whose plural ends -ies but whose singular ends -ie (not -y), and a few odd plurals
_IE_WORDS = {"prairie", "movie", "cookie", "zombie", "rookie", "pie", "tie", "lie", "genie", "goodie", "hoodie", "selfie",
             "birdie", "calorie", "brownie", "cutie", "sweetie", "collie", "eerie", "specie", "doggie", "bogie", "newbie"}
_ODD_SINGULAR = {"gallowses": "gallows", "trellises": "trellis", "cactuses": "cactus", "oases": "oasis", "crises": "crisis",
                 "geese": "goose", "wolves": "wolf", "knives": "knife", "leaves": "leaf", "thieves": "thief", "men": "man",
                 "women": "woman", "children": "child", "mice": "mouse", "feet": "foot", "teeth": "tooth"}


def singular(w):
    """Rough singular, so 'the {motif}' reads right: stags -> stag. Possessives ('sorcerer's') and words that are not
    plurals are left alone."""
    if w in _ODD_SINGULAR:
        return _ODD_SINGULAR[w]
    if "'" in w or "’" in w:
        return w
    if w.endswith("ies"):
        return w[:-1] if w[:-1] in _IE_WORDS else w[:-3] + "y"
    if w.endswith(("ches", "shes", "xes", "sses")):
        return w[:-2]
    if w.endswith("uses") and not w.endswith(("ouses", "auses", "ruses")):
        return w[:-2]
    if w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


# Words that start with a vowel but sound like a consonant (a one-armed, a unicorn), and
# words that start with a consonant but sound like a vowel (an hour, an honest).
_CONSONANT_SOUND = r"(?:one|once|uni|use|used|useful|usual|euro|ewe|ubiq)"
_VOWEL_SOUND = r"(?:hour|honest|honor|heir)"


_PARTICLE_WORDS = {"away", "out", "up", "down", "off", "back", "over", "aside", "along", "in", "on"}


def particle_verbs(library):
    """The verb phrases in the library's verb atoms that end in a particle ('traded away', 'locked up'), as
    {phrase}. Only these are moved: 'jumped off it' is not 'jumped it off'."""
    cached = getattr(library, "_particle_verbs", None)
    if cached is None:
        cached = set()
        for slot, lists in library.by_slot.items():
            if slot.split("_")[0] in ("act", "do", "habit"):
                for wl in lists:
                    for e in wl.entries:
                        words = e.text.split()
                        if len(words) >= 2 and words[-1] in _PARTICLE_WORDS:
                            cached.add(e.text)
                            if words[0].endswith("e"):
                                cached.add(" ".join([words[0] + "d"] + words[1:]))
        library._particle_verbs = cached
    return cached


def fix_particles(text, verbs):
    """A particle verb takes a pronoun in the middle: 'traded away it' -> 'traded it away'. (Only it, them and him:
    'her' could be 'picked up her coat'.)"""
    for phrase in verbs:
        if " " in phrase and phrase in text:
            head, _, particle = phrase.rpartition(" ")
            text = re.sub(rf"\b{re.escape(phrase)} (it|them|him)\b(?! of\b)", rf"{head} \1 {particle}", text)
    return text


def fix_articles(text):
    text = re.sub(rf"\b([Aa]) (?=(?!{_CONSONANT_SOUND}\b|{_CONSONANT_SOUND}-|uni)[aeiouAEIOU])", r"\1n ", text)
    text = re.sub(rf"\b([Aa])n (?=(?:{_CONSONANT_SOUND}\b|{_CONSONANT_SOUND}-|uni[a-z]))", r"\1 ", text)
    return re.sub(rf"\b([Aa]) (?={_VOWEL_SOUND})", r"\1n ", text)


def title_case(text):
    return " ".join(w if (i and w.lower() in SMALL_WORDS) else w[:1].upper() + w[1:]
                    for i, w in enumerate(text.split()))


def motif_from(title, fallback):
    """Guess what a title is 'about': the last word before the first connector.
    'The Wonderful Wizard of Oz' -> wizard,  'Grapes From Space' -> grapes.
    `fallback()` supplies a word if the title has none."""
    chunk = []
    for w in title.split():
        w = re.sub(r"'s$", "", w.strip(",.!?:;\"").lower())
        if w in SMALL_WORDS:
            if chunk:
                break
            continue
        chunk.append(w)
    return singular(chunk[-1]) if chunk else fallback()


_OBJECT_WORDS = ("to", "for", "with", "about", "at", "on", "against", "from", "believed", "trusted", "told",
                 "asked", "hired", "followed", "met")


def pronouns(text, first, extra=()):
    """After a character's first mention, use 'their'/'them' instead of repeating
    their name: 'Christina let Christina's mother go' -> 'Christina let their mother go'.
    `extra` are more words that take the character as an object ('betrayed', 'outwitted')."""
    if not first or text.count(first) < 2:
        return text
    i = text.index(first) + len(first)
    head, tail = text[:i], text[i:]
    words = "|".join(re.escape(w) for w in sorted(set(_OBJECT_WORDS) | set(extra), key=len, reverse=True))
    tail = re.sub(rf"\b{re.escape(first)}'s\b", "their", tail)
    tail = re.sub(rf"\b({words}) {re.escape(first)}\b", r"\1 them", tail)
    return head + tail


def implicit(text, first):
    """Text about a character that is shown on their own card: 'Vesna's sister' -> 'their sister'."""
    if not first or first not in text:
        return text
    return pronouns(first + " " + text, first)[len(first) + 1:]


def plural_n(n, noun, plural=None, commas=False):
    """'1 scene', '2 scenes'; give `plural` for an irregular noun ('entity', 'entities'); commas=True writes 1,200."""
    shown = f"{n:,}" if commas else f"{n}"
    return f"{shown} {noun}" if n == 1 else f"{shown} {plural or noun + 's'}"
