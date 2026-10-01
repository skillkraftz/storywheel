"""
Threads: the things and people a story's spine introduces, so later beats can
pick them up again.

When a spine beat draws a building block of one of the THREAD_KINDS (say
{THING} comes out as "a locked box"), the story remembers it as a thread:

    story["threads"] = {"thing": {"text": "a locked box", "beat": "one_day"}, ...}

Later beats can then say {the_thing}, which comes out as "the locked box": the
same box, now definite. Templates that use {the_...} are preferred while that
thread exists, and impossible while it doesn't.

Rerolling the beat that introduced a thread keeps the story consistent:

* if the new beat introduces a new one of that kind, the thread is UPDATED and
  the old text is swapped for the new everywhere it was mentioned;
* if it doesn't, the old thread is kept for as long as some other beat still
  mentions it (that beat becomes the introduction), and RETIRED when none does.

Everything here works on plain dicts, so it is easy to test.
"""
import re

THREAD_KINDS = ("thing", "someone", "message", "disaster")
PREFERRED = 6.0            # how much likelier a template that uses a live thread is

_REF = re.compile(r"\{the_(%s)\}" % "|".join(THREAD_KINDS))

BEAT_LABELS = {"once": "Once upon a time", "every_day": "Every day", "one_day": "One day",
               "because_1": "Because of that", "because_2": "Because of that",
               "until_finally": "Until finally", "ever_since": "Ever since then"}


def definite(text):
    """'a locked box' -> 'the locked box'. Names and plurals are left alone."""
    return re.sub(r"^(?:a|an) ", "the ", text, flags=re.IGNORECASE)


def refs(template):
    """The thread kinds a template refers to with {the_...}."""
    return set(_REF.findall(template))


def weight(template, available):
    """Factor for picking a template: 1 if it uses no threads, PREFERRED if every
    thread it uses exists, 0 if one is missing."""
    used = refs(template)
    if not used:
        return 1.0
    return PREFERRED if used <= set(available) else 0.0


def intro_forms(t):
    """How a thread's text can read where it is introduced. The sentence's own
    pronoun pass can turn "Amanda's first love" into "their first love", so a thread
    may carry that as "shown" too."""
    return [t["text"]] + ([t["shown"]] if t.get("shown") and t["shown"] != t["text"] else [])


def all_forms(t):
    """Every way the thread can read anywhere: introduced, or mentioned again."""
    forms = intro_forms(t)
    return forms + [d for d in (definite(f) for f in forms) if d not in forms]


def replace_text(text, old, new):
    """Case-insensitive replace that keeps a sentence-initial capital: ("The locked
    box was a fake", "the locked box", "the pistol") -> "The pistol was a fake"."""
    def repl(m):
        return new[:1].upper() + new[1:] if m.group(0)[:1].isupper() else new
    return re.subn(re.escape(old), repl, text, flags=re.IGNORECASE)


def swap_pairs(old, new):
    """(old form, new form) pairs for replacing one thread by another, longest first."""
    n_forms = intro_forms(new)
    pairs = []
    for i, form in enumerate(intro_forms(old)):
        repl = n_forms[min(i, len(n_forms) - 1)]
        pairs += [(form, repl)]
        if definite(form) != form:
            pairs.append((definite(form), definite(repl)))
    return sorted(set(pairs), key=lambda p: -len(p[0]))


def swap(fields, old, new, skip=()):
    """Replace thread `old` with thread `new` (dicts) in each text field. Returns the count."""
    count = 0
    pairs = swap_pairs(old, new)
    for key, value in fields.items():
        if key.startswith("_") or key in skip or not isinstance(value, str):
            continue
        for a, b in pairs:
            value, n = replace_text(value, a, b)
            count += n
        fields[key] = value
    return count


def settle(cand):
    """Bring a candidate's threads in line with its text, in place.

    Each thread's beat becomes the first beat that mentions it. If it is only
    mentioned as "the X" (its introduction was rerolled away), that first
    mention turns back into "a X" so it reads as an introduction. A thread no
    beat mentions any more is retired."""
    threads = cand.get("_threads")
    if not threads:
        return cand
    kept = {}
    for kind, t in threads.items():
        intro = intro_forms(t)
        for name, value in cand.items():
            if name.startswith("_") or not isinstance(value, str):
                continue
            low = value.lower()
            if any(f.lower() in low for f in intro):
                kept[kind] = dict(t, beat=name)
                break
            hit = next((definite(f) for f in intro if definite(f) != f and definite(f).lower() in low), None)
            if hit:
                cand[name] = replace_text(value, hit, intro[0])[0]
                kept[kind] = dict(t, beat=name)
                break
    cand["_threads"] = kept
    return cand


def verify(thread, beat_text, first):
    """Check a freshly recorded thread against the finished beat. Returns the thread
    (with "shown" set if the pronoun pass reworded it) or None if it can't be found."""
    if thread["text"] in beat_text:
        return thread
    if first:
        shown = thread["text"].replace(f"{first}'s", "their")
        if shown in beat_text:
            return dict(thread, shown=shown)
    return None


def describe(threads):
    """'thing: a jar of teeth (One day) · someone: ...' for display."""
    return " · ".join(f"{kind}: {t['text']} ({BEAT_LABELS.get(t['beat'], t['beat'])})"
                      for kind, t in threads.items())
