"""Quotation marks. Manuscripts keep STRAIGHT quotes and apostrophes (' and "): Neovim's spellchecker treats ’ as a letter that is not
part of the word, so "couldn’t" looks misspelled. The export turns them into curly ones (setting export_curly_quotes, default on)."""
import re

CURLY = {"‘": "'", "’": "'", "‚": "'", "‛": "'", "“": '"', "”": '"', "„": '"', "‟": '"'}
_STRAIGHT = re.compile("[‘’‚‛“”„‟]")

# a leading apostrophe that is an apostrophe (an elision), not an opening single quote
ELISIONS = ("em", "til", "tis", "twas", "twere", "cause", "round", "bout", "n", "neath", "nother", "tain't", "cept", "fraid", "kay", "sup")
OPENERS = " \t\n([{—–-/“‘\""
MARKS = "*_"                                                         # markdown italics/bold do not count as text for context


def straighten(text):
    """Curly quotes and apostrophes -> straight."""
    return _STRAIGHT.sub(lambda m: CURLY[m.group(0)], text)


def count_curly(text):
    return len(_STRAIGHT.findall(text))


def _before(text, i):
    """The character before position i, looking through italic/bold marks."""
    j = i - 1
    while j >= 0 and text[j] in MARKS:
        j -= 1
    return text[j] if j >= 0 else ""


def _after(text, i):
    j = i + 1
    while j < len(text) and text[j] in MARKS:
        j += 1
    return text[j:j + 12]


def smarten(text):
    """Straight quotes and apostrophes -> curly, by context: an apostrophe inside a word or closing a quote is ’, a quote that follows
    a space, a bracket or a dash (or starts the text) opens: “ or ‘. Leading elisions ('em, 'til) and decades ('90s) keep ’."""
    out = []
    for i, ch in enumerate(text):
        if ch not in "'\"":
            out.append(ch)
            continue
        prev, nxt = _before(text, i), _after(text, i)
        opening = prev == "" or prev in OPENERS
        if ch == '"':
            out.append("“" if opening else "”")
        else:
            if opening and not nxt[:1].isspace() and nxt != "":
                low = nxt.lower()
                if re.match(r"\d\d", nxt) or any(re.match(re.escape(e) + r"\b", low) for e in ELISIONS):
                    out.append("’")
                else:
                    out.append("‘")
            else:
                out.append("’")
    return "".join(out)
