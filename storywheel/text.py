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


def singular(w):
    """Rough singular, so 'the {motif}' reads right: stags -> stag."""
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith(("ches", "shes", "xes", "sses")):
        return w[:-2]
    if w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


# Words that start with a vowel but sound like a consonant (a one-armed, a unicorn), and
# words that start with a consonant but sound like a vowel (an hour, an honest).
_CONSONANT_SOUND = r"(?:one|once|uni|use|used|useful|usual|euro|ewe|ubiq)"
_VOWEL_SOUND = r"(?:hour|honest|honor|heir)"


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
