"""Fountain, the plain-text screenplay format (https://fountain.io), read the way storywheel needs it.

    parse(text) -> Script(title={key: [lines]}, elements=[Element])

An Element has a `type` and the `line` (1-based) it starts on in the file:

    heading       INT. ATTIC - NIGHT (or a forced ".HEADING"); `number` holds a scene number written as #12#
    action        a paragraph of action, its line breaks kept ("\\n" in text); a forced one starts with "!"
    character     MARA (V.O.) ^   -> name "MARA", ext "(V.O.)", dual True for the second of two side-by-side speeches
    parenthetical (whispering)
    dialogue      the words, line breaks kept
    transition    CUT TO: (uppercase, ending in TO:, alone between blank lines) or a forced "> FADE OUT."
    centered      > THE NEXT MORNING <
    page_break    ===
    section       # Act One   (`level` = the number of #); not printed
    synopsis      = what happens; not printed
    lyrics        ~ a sung line

Notes ([[...]]) and the boneyard (/* ... */) are left out; line numbers still count them. Emphasis (*italic*, **bold**, _underline_) stays in the
text for the renderer. This module is the one reader of a script: the PDF, the Final Draft file, the page estimate, the flip test, the scene list
and the grammar checker's skip list all use it."""
import re
from dataclasses import dataclass, field

HEADING = re.compile(r"^(?:INT|EXT|EST|INT\.?/EXT|I/E|E/I)(?:[. ]|$)", re.I)
SCENE_NUMBER = re.compile(r"\s*#([\w.-]+)#\s*$")
TRANSITION = re.compile(r"^[A-Z0-9 .,'’\-]+TO:$")
EXTENSION = re.compile(r"(\s*\([^)]*\))+\s*$")


@dataclass
class Element:
    type: str
    text: str
    line: int
    name: str = ""            # character: the name without extension
    ext: str = ""             # character: "(V.O.)", "(O.S.)", "(CONT'D)"...
    dual: bool = False        # character (and its speech): the right-hand side of dual dialogue
    level: int = 0            # section: how many #
    number: str = ""          # heading: a scene number written as #12#
    extras: dict = field(default_factory=dict)


@dataclass
class Script:
    title: dict
    elements: list
    body_start: int = 1       # the line the script proper starts on (after the title page)

    def of(self, *types):
        return [e for e in self.elements if e.type in types]

    def headings(self):
        return self.of("heading")

    def characters(self):
        """Character names in the order they first speak."""
        out = []
        for e in self.of("character"):
            if e.name not in out:
                out.append(e.name)
        return out

    def locations(self):
        """Scene locations ("ATTIC" from "INT. ATTIC - NIGHT"), in order of first use."""
        out = []
        for e in self.headings():
            loc = location_of(e.text)
            if loc and loc not in out:
                out.append(loc)
        return out


def location_of(heading):
    """INT. ATTIC - NIGHT -> ATTIC; EXT. HOUSE - GARDEN - DAY -> HOUSE - GARDEN (the last part, the time of day, is left off)."""
    t = re.sub(r"^\.(?!\.)", "", heading.strip())
    t = re.sub(r"^(?:INT\.?/EXT|I/E|E/I|INT|EXT|EST)\.?\s*", "", t, flags=re.I)
    parts = re.split(r"\s+-\s+", t)
    return " - ".join(parts[:-1] if len(parts) > 1 else parts).strip().upper()


def _blank_out(text, pattern):
    """Remove matches of `pattern` but keep their line breaks, so line numbers stay true."""
    return pattern.sub(lambda m: "\n" * m.group(0).count("\n"), text)


BONEYARD = re.compile(r"/\*.*?\*/", re.S)
NOTE = re.compile(r"\[\[.*?\]\]", re.S)


def is_heading(line):
    s = line.strip()
    return (s.startswith(".") and not s.startswith("..") and len(s) > 1) or bool(HEADING.match(s))


def is_upper(s):
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and all(not c.islower() for c in letters)


def is_character_line(s):
    """A character cue on its own (it still needs a blank line before and words after): uppercase, or forced with @."""
    s = s.strip()
    if not s or s.startswith(("!", ">", ".", "#", "=", "~")):
        return False
    if s.startswith("@"):
        return len(s) > 1
    name = EXTENSION.sub("", s.rstrip("^").rstrip())
    return is_upper(name) and not TRANSITION.match(s) and not HEADING.match(s)


def split_cue(s):
    """'@McCLANE (V.O.) ^' -> ('McCLANE', '(V.O.)', True)."""
    s = s.strip()
    dual = s.endswith("^")
    s = s.rstrip("^").strip()
    if s.startswith("@"):
        s = s[1:]
    m = EXTENSION.search(s)
    ext = m.group(0).strip() if m else ""
    name = s[:m.start()].strip() if m else s
    return name, re.sub(r"\)\s*\(", ") (", ext), dual


def parse_title(lines):
    """The title page (key: value lines at the very top, up to the first blank line) and how many lines it used."""
    title, key, used = {}, None, 0
    if not lines or not re.match(r"^[A-Za-z][A-Za-z ]*:", lines[0]):
        return {}, 0
    for i, line in enumerate(lines):
        if not line.strip():
            used = i + 1
            break
        m = re.match(r"^([A-Za-z][A-Za-z ]*):\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            key = m.group(1).strip().lower()
            title[key] = [m.group(2).strip()] if m.group(2).strip() else []
        elif key is not None:
            title[key].append(line.strip())
        used = i + 1
    return title, used


def parse(text):
    text = (text or "").replace("\r\n", "\n").replace("\t", "    ")
    text = _blank_out(_blank_out(text, BONEYARD), NOTE)
    lines = text.split("\n")
    title, used = parse_title(lines)
    els = []
    i = used
    n = len(lines)

    def blank(k):
        return k < 0 or k >= n or not lines[k].strip()

    while i < n:
        raw = lines[i]
        s = raw.strip()
        if not s:
            i += 1
            continue
        lineno = i + 1
        if re.fullmatch(r"={3,}", s):
            els.append(Element("page_break", "", lineno))
        elif s.startswith("#"):
            level = len(s) - len(s.lstrip("#"))
            els.append(Element("section", s[level:].strip(), lineno, level=level))
        elif s.startswith("=") and not s.startswith("=="):
            els.append(Element("synopsis", s[1:].strip(), lineno))
        elif s.startswith(">") and s.endswith("<"):
            els.append(Element("centered", s[1:-1].strip(), lineno))
        elif s.startswith(">"):
            els.append(Element("transition", s[1:].strip(), lineno))
        elif s.startswith("~"):
            buf = []
            while i < n and lines[i].strip().startswith("~"):          # a verse: lyric lines in a row are one block
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            els.append(Element("lyrics", "\n".join(buf), lineno))
            continue
        elif blank(i - 1) and is_heading(s) and (blank(i + 1) or s.startswith(".")):
            t = s[1:] if s.startswith(".") else s
            num = SCENE_NUMBER.search(t)
            if num:
                t = t[:num.start()]
            els.append(Element("heading", t.strip().upper(), lineno, number=num.group(1) if num else ""))
        elif blank(i - 1) and blank(i + 1) and TRANSITION.match(s):
            els.append(Element("transition", s, lineno))
        elif blank(i - 1) and not blank(i + 1) and is_character_line(s):
            name, ext, dual = split_cue(s)
            els.append(Element("character", s, lineno, name=name, ext=ext, dual=dual))
            i += 1
            buf, start = [], i + 1
            while i < n and lines[i].strip() != "" or (i < n and lines[i] == "  "):
                t = lines[i].strip()
                if t.startswith("(") and t.endswith(")"):
                    if buf:
                        els.append(Element("dialogue", "\n".join(buf), start, dual=dual))
                        buf = []
                    els.append(Element("parenthetical", t, i + 1, dual=dual))
                else:
                    if not buf:
                        start = i + 1
                    buf.append(t)
                i += 1
            if buf:
                els.append(Element("dialogue", "\n".join(buf), start, dual=dual))
            continue
        else:
            buf = []
            while i < n and lines[i].strip():
                t = lines[i].rstrip()
                if not buf and t.lstrip().startswith("!"):
                    t = t.lstrip()[1:]
                buf.append(t)
                i += 1
            els.append(Element("action", "\n".join(buf), lineno))
            continue
        i += 1
    return Script(title, els, used + 1)


# --- what the Writer and the grammar checker need line by line -------------------------------------------------------------------

def line_types(text):
    """{line number: element type} for every line that belongs to an element (title page lines are "title")."""
    script = parse(text)
    lines = (text or "").split("\n")
    out = {k: "title" for k in range(1, script.body_start) if k <= len(lines) and lines[k - 1].strip()}
    for e in script.elements:
        span = max(1, e.text.count("\n") + 1) if e.type in ("action", "dialogue", "lyrics") else 1
        for k in range(e.line, min(len(lines), e.line + span - 1) + 1):
            out[k] = e.type
    return out


NOT_PROSE = ("character", "heading", "transition", "section", "synopsis", "page_break", "title", "centered")


def prose_lines(text):
    """Line numbers whose words the grammar checker may read: action, dialogue, parentheticals and lyrics (never cues, headings, transitions)."""
    return sorted(k for k, t in line_types(text).items() if t not in NOT_PROSE)


def scenes(text):
    """[{n, title, line, section, synopsis, first_line}]: a scene for each heading, with the section it sits under."""
    script = parse(text)
    out, section, sections = [], "", {}
    pending_syn = ""
    for e in script.elements:
        if e.type == "section":
            sections[e.level] = e.text
            for k in list(sections):
                if k > e.level:
                    del sections[k]
            section = " / ".join(sections[k] for k in sorted(sections))
        elif e.type == "synopsis" and out and not out[-1]["synopsis"]:
            out[-1]["synopsis"] = e.text
        elif e.type == "heading":
            out.append({"n": len(out) + 1, "title": e.text, "line": e.line, "section": section, "synopsis": "", "first_line": ""})
        elif out and not out[-1]["first_line"] and e.type in ("action", "dialogue"):
            out[-1]["first_line"] = e.text.split("\n")[0][:80]
    return out


def word_count(text):
    """Words in the script proper (title page, sections, synopses and notes left out)."""
    from .vault import count_words
    script = parse(text)
    return sum(count_words(e.text) for e in script.elements if e.type not in ("section", "synopsis", "page_break"))


def strip_markup(text):
    """*italic*, **bold**, _underline_ and escapes removed, for plain-text uses."""
    t = re.sub(r"\\([*_])", "\x00\\1", text)
    t = re.sub(r"\*{1,3}([^*\n]+?)\*{1,3}", r"\1", t)
    t = re.sub(r"_([^_\n]+?)_", r"\1", t)
    return t.replace("\x00", "")
