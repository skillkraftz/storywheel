"""A screenplay, laid out and drawn as a PDF (reportlab, Courier Prime bundled), to the usual spec-script standard.

    paginate(text)                    -> [Page]: the script's pages, each a list of Line (what goes where), title page not included
    estimate_pages(text)              -> how many script pages the text makes
    render(text, path, title=..., ...) -> writes the PDF; returns the number of script pages

The standard (Final Draft's margin guide and the usual formatting guides; see REPORT.md, batch 17): US Letter, 12-point Courier (10 characters an
inch, 6 lines an inch), 1.5" left and 1" right margins, the body starting 1" from the top, 55 lines a page. Scene headings and action from 1.5" to
7.5"; character cues at 3.7"; parentheticals from 3.1" to 5.6"; dialogue from 2.5" to 6.0"; transitions right-aligned to 7.5"; page numbers "2."
top right, 0.5" down, from page 2. A speech that does not fit is split between lines of dialogue with (MORE) at the bottom and "NAME (CONT'D)" at
the top of the next page; a scene heading is never the last thing on a page. Sections, synopses and notes are not printed."""
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import fountain

INCH = 72.0
PAGE_W, PAGE_H = 8.5, 11.0
LEFT, RIGHT = 1.5, 7.5
TOP = 1.0
LINE = 12.0                      # points: 6 lines an inch
LINES_PER_PAGE = 55
CHAR = 0.1                       # inches: Courier at 12 points is 10 characters an inch

X = {"heading": 1.5, "action": 1.5, "lyrics": 1.5, "character": 3.7, "parenthetical": 3.1, "dialogue": 2.5, "more": 3.7}
WIDTH = {"heading": 60, "action": 60, "lyrics": 60, "character": 38, "parenthetical": 25, "dialogue": 35, "transition": 20, "centered": 60}
SPACE_BEFORE = {"heading": 2, "action": 1, "character": 1, "transition": 1, "centered": 1, "lyrics": 1}
# dual dialogue: two narrower columns side by side
DUAL = {False: {"character": 2.6, "parenthetical": 2.0, "dialogue": 1.5}, True: {"character": 5.6, "parenthetical": 5.0, "dialogue": 4.5}}
DUAL_WIDTH = {"parenthetical": 20, "dialogue": 28}
MORE = "(MORE)"
CONTD = "(CONT'D)"

FONT_DIR = Path(__file__).parent / "fonts"
FONTS = {(False, False): "CourierPrime", (True, False): "CourierPrime-Bold", (False, True): "CourierPrime-Italic", (True, True): "CourierPrime-BoldItalic"}


# --- runs: text with emphasis ----------------------------------------------------------------------------------------------------

@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


EMPHASIS = re.compile(r"(\\[*_])|(\*\*\*|\*\*|\*|_)")


def runs_of(text):
    """'He *never* came' -> [Run('He '), Run('never', italic=True), Run(' came')]. Unclosed markers are kept as text."""
    out, buf = [], []
    state = {"b": False, "i": False, "u": False}
    tokens = EMPHASIS.split(text)
    # pair up markers first, so a lone * prints as a star
    pieces = []
    k = 0
    while k < len(tokens):
        t = tokens[k]
        if t is None or t == "":
            k += 1
            continue
        pieces.append(t)
        k += 1
    opens = {"***": 0, "**": 0, "*": 0, "_": 0}
    for p in pieces:
        if p in opens:
            opens[p] += 1
    usable = {m: n - n % 2 for m, n in opens.items()}

    def flush():
        if buf:
            out.append(Run("".join(buf), state["b"], state["i"], state["u"]))
            buf.clear()

    for p in pieces:
        if p in ("\\*", "\\_"):
            buf.append(p[1])
        elif p in usable and usable[p] > 0:
            usable[p] -= 1
            flush()
            if p == "***":
                state["b"] = state["i"] = not state["b"]
            elif p == "**":
                state["b"] = not state["b"]
            elif p == "*":
                state["i"] = not state["i"]
            else:
                state["u"] = not state["u"]
        else:
            buf.append(p)
    flush()
    return out


def plain(runs):
    return "".join(r.text for r in runs)


def wrap_runs(runs, width):
    """Lines of at most `width` characters, broken between words, each a list of Runs."""
    words = []                                                   # (Run pieces of one word, then the space after)
    cur = []
    for r in runs:
        for part in re.split(r"( )", r.text):
            if part == " ":
                if cur:
                    words.append(cur)
                    cur = []
            elif part:
                cur.append(Run(part, r.bold, r.italic, r.underline))
    if cur:
        words.append(cur)
    lines, line, n = [], [], 0
    for w in words:
        wl = sum(len(p.text) for p in w)
        while wl > width and not line:                           # a word longer than the line: cut it
            text = "".join(p.text for p in w)
            lines.append([Run(text[:width], w[0].bold, w[0].italic, w[0].underline)])
            w = [Run(text[width:], w[0].bold, w[0].italic, w[0].underline)]
            wl = len(w[0].text)
        if line and n + 1 + wl > width:
            lines.append(line)
            line, n = [], 0
        if line:
            line.append(Run(" ", line[-1].bold, line[-1].italic, line[-1].underline and w[0].underline))
            n += 1
        line.extend(w)
        n += wl
    if line:
        lines.append(line)
    return lines or [[Run("")]]


def wrap_text(text, width):
    """Each line of the element's own text wrapped (a line break in the file is kept)."""
    out = []
    for piece in text.split("\n"):
        out += wrap_runs(runs_of(piece), width)
    return out


# --- layout ------------------------------------------------------------------------------------------------------------------------

@dataclass
class Line:
    kind: str                    # heading, action, character, parenthetical, dialogue, transition, centered, more, lyrics, blank
    runs: list = field(default_factory=list)
    x: float = 1.5               # inches from the left edge; for right/center alignment see align
    align: str = "left"          # left, right (to 7.5"), center (between the margins)
    side: str = ""               # dual dialogue: "" or "left"/"right" sharing one row with the other side
    pair: object = None          # dual dialogue: the Line printed beside this one on the same row

    @property
    def text(self):
        return plain(self.runs)


@dataclass
class Block:
    kind: str
    lines: list
    space: int = 1
    keep_next: bool = False      # a heading stays with what follows it
    speech: dict = None          # dialogue: {"cue": Line, "ext": str, "name": str} for splitting with (MORE)/(CONT'D)
    split_at: list = None        # indexes of lines after which the block may be split
    force_page: bool = False


def _lines(kind, text, width, x, align="left"):
    return [Line(kind, runs, x, align) for runs in wrap_text(text, width)]


def _paren_lines(text, width, x):
    """A parenthetical wraps with its later lines one character in (under the text, not the bracket)."""
    first, *rest = wrap_text(text, width)
    lines = [Line("parenthetical", first, x)]
    for runs in rest:
        lines.append(Line("parenthetical", runs, x + CHAR))
    return lines


def _speech(elements, i, dual_side=None):
    """The cue at elements[i] and its parentheticals and dialogue: (lines, split points, next index)."""
    cue = elements[i]
    xs = DUAL[dual_side == "right"] if dual_side else X
    wd = DUAL_WIDTH if dual_side else WIDTH
    lines = [Line("character", runs_of(cue.name + (" " + cue.ext if cue.ext else "")), xs["character"])]
    splits = []
    j = i + 1
    while j < len(elements) and elements[j].type in ("parenthetical", "dialogue"):
        e = elements[j]
        if e.type == "parenthetical":
            lines += _paren_lines(e.text, wd["parenthetical"], xs["parenthetical"])
        else:
            start = len(lines)
            lines += _lines("dialogue", e.text, wd["dialogue"], xs["dialogue"])
            # a split may come after any dialogue line but the last of the speech, and best after a sentence ends
            splits += list(range(start, len(lines) - 1))
        j += 1
    return lines, splits, j


def blocks(text, contd=False):
    """The script as Blocks. `contd`: add an automatic (CONT'D) where a character speaks again after action in the same scene."""
    script = fountain.parse(text)
    els = [e for e in script.elements if e.type not in ("section", "synopsis")]
    if contd:
        for cue in fountain.auto_contd(els):
            cue.ext = (cue.ext + " " + CONTD).strip()
    out = []
    i = 0
    while i < len(els):
        e = els[i]
        if e.type == "page_break":
            out.append(Block("page_break", [], 0, force_page=True))
            i += 1
        elif e.type == "heading":
            text_ = e.text + (f" #{e.number}#" if False else "")
            out.append(Block("heading", _lines("heading", text_, WIDTH["heading"], X["heading"]), SPACE_BEFORE["heading"], keep_next=True))
            i += 1
        elif e.type == "character":
            # dual dialogue: this speech and the next one marked ^ print side by side
            nxt = i + 1
            while nxt < len(els) and els[nxt].type in ("parenthetical", "dialogue"):
                nxt += 1
            if nxt < len(els) and els[nxt].type == "character" and els[nxt].dual and not e.dual:
                left, _s, _j = _speech(els, i, "left")
                right, _s2, j = _speech(els, nxt, "right")
                rows = []
                for k in range(max(len(left), len(right))):
                    a = left[k] if k < len(left) else Line("blank")
                    b = right[k] if k < len(right) else Line("blank")
                    a.side, b.side = "left", "right"
                    a.pair = b
                    rows.append(a)
                out.append(Block("dual", rows, SPACE_BEFORE["character"]))
                i = j
                continue
            lines, splits, j = _speech(els, i)
            out.append(Block("speech", lines, SPACE_BEFORE["character"],
                             speech={"name": e.name, "ext": e.ext, "cue_x": X["character"]}, split_at=splits))
            i = j
        elif e.type == "transition":
            out.append(Block("transition", _lines("transition", e.text.upper(), WIDTH["transition"], RIGHT, "right"), SPACE_BEFORE["transition"]))
            i += 1
        elif e.type == "centered":
            out.append(Block("centered", _lines("centered", e.text, WIDTH["centered"], LEFT, "center"), SPACE_BEFORE["centered"]))
            i += 1
        elif e.type in ("action", "lyrics"):
            kind = e.type
            lines = _lines(kind, e.text, WIDTH[kind], X[kind])
            if kind == "lyrics":
                for ln in lines:
                    ln.runs = [Run(r.text, r.bold, True, r.underline) for r in ln.runs]
            out.append(Block(kind, lines, SPACE_BEFORE[kind], split_at=list(range(1, len(lines) - 2))))
            i += 1
        else:                                                    # a stray parenthetical or dialogue line: print it as action
            out.append(Block("action", _lines("action", e.text, WIDTH["action"], X["action"]), 1))
            i += 1
    return out


@dataclass
class Page:
    lines: list = field(default_factory=list)                    # Line or None (a blank line)

    @property
    def used(self):
        return len(self.lines)


def paginate(text, contd=False):
    """The script's pages: each page a list of lines (None = a blank line), at most LINES_PER_PAGE long."""
    bl = blocks(text, contd)
    pages = [Page()]

    def room():
        return LINES_PER_PAGE - pages[-1].used

    def new_page():
        pages.append(Page())

    i = 0
    while i < len(bl):
        b = bl[i]
        if b.force_page:
            if pages[-1].used:
                new_page()
            i += 1
            continue
        space = b.space if pages[-1].used else 0
        need = space + len(b.lines)
        if b.keep_next and i + 1 < len(bl) and not bl[i + 1].force_page:
            nb = bl[i + 1]
            first_part = min(len(nb.lines), 2 if nb.kind in ("speech", "action") else len(nb.lines))
            need += nb.space + first_part                         # a heading needs at least the start of what follows on its page
        if need <= room() or (not pages[-1].used):
            if b.keep_next and need > room() and pages[-1].used:
                new_page()
                space = 0
            pages[-1].lines += [None] * space + b.lines
            i += 1
            continue
        # it does not fit: split a speech or an action block, else move it to the next page
        avail = room() - space
        if b.kind == "speech" and b.split_at:
            usable = [k for k in b.split_at if k + 1 + 1 <= avail]   # lines 0..k, then (MORE)
            usable = [k for k in usable if k >= 1 and len(b.lines) - (k + 1) >= 1]
            if usable:
                best = max(usable, key=lambda k: (b.lines[k].text.rstrip().endswith((".", "!", "?", "--", "…")), k))
                head = b.lines[:best + 1] + [Line("more", [Run(MORE)], X["character"])]
                ext = b.speech["ext"] if fountain.has_contd(b.speech["ext"]) else (b.speech["ext"] + " " + CONTD).strip()
                cue = Line("character", runs_of(f"{b.speech['name']} {ext}"), b.speech["cue_x"])
                rest = [cue] + b.lines[best + 1:]
                splits = [k - best for k in b.split_at if k > best]
                pages[-1].lines += [None] * space + head
                new_page()
                bl[i] = Block("speech", rest, 0, speech=b.speech, split_at=splits)
                continue
        if b.kind == "action" and len(b.lines) >= 4 and avail >= 2:
            k = min(avail, len(b.lines) - 2)
            if k >= 2:
                pages[-1].lines += [None] * space + b.lines[:k]
                new_page()
                bl[i] = Block("action", b.lines[k:], 0, split_at=list(range(1, len(b.lines) - k - 2)))
                continue
        new_page()
    while len(pages) > 1 and not pages[-1].lines:
        pages.pop()
    # never a heading as the last printed line of a page (the keep rule above handles it; this catches a heading followed by a page break)
    return pages


def estimate_pages(text):
    pages = paginate(text)
    if len(pages) == 1 and not pages[0].lines:
        return 0
    full = len(pages) - 1
    return round(full + pages[-1].used / LINES_PER_PAGE, 1)


# --- drawing ----------------------------------------------------------------------------------------------------------------------

_registered = False


def _register_fonts():
    global _registered
    if _registered:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    files = {"CourierPrime": "CourierPrime-Regular.ttf", "CourierPrime-Bold": "CourierPrime-Bold.ttf",
             "CourierPrime-Italic": "CourierPrime-Italic.ttf", "CourierPrime-BoldItalic": "CourierPrime-BoldItalic.ttf"}
    for name, f in files.items():
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / f)))
    _registered = True


def _draw_runs(c, runs, x_pt, baseline):
    for r in runs:
        if not r.text:
            continue
        font = FONTS[(r.bold, r.italic)]
        c.setFont(font, 12)
        c.drawString(x_pt, baseline, r.text)
        w = len(r.text) * CHAR * INCH
        if r.underline and r.text.strip():
            c.setLineWidth(0.6)
            c.line(x_pt, baseline - 1.5, x_pt + w, baseline - 1.5)
        x_pt += w


def _draw_line(c, ln, row):
    baseline = (PAGE_H - TOP) * INCH - row * LINE - 9.0          # the top of the text sits on the line; 9pt down to the baseline
    if ln is None:
        return
    if ln.pair is not None and ln.pair.kind != "blank":            # dual dialogue: the right-hand side of this row
        _draw_runs(c, ln.pair.runs, ln.pair.x * INCH, baseline)
    if ln.kind == "blank":
        return
    width = len(ln.text) * CHAR * INCH
    if ln.align == "right":
        x = RIGHT * INCH - width
    elif ln.align == "center":
        x = (LEFT + RIGHT) / 2 * INCH - width / 2
    else:
        x = ln.x * INCH
    _draw_runs(c, ln.runs, x, baseline)


def _title_page(c, tp):
    """Title centered a third of the way down, "Written by" and the author under it; the contact block bottom left; the draft date bottom right."""
    _register_fonts()
    def centered(text, row, bold=False):
        w = len(text) * CHAR * INCH
        c.setFont(FONTS[(bold, False)], 12)
        c.drawString(PAGE_W / 2 * INCH - w / 2, PAGE_H * INCH - TOP * INCH - row * LINE - 9.0, text)
    row = 21                                                     # about 3.5" from the top of the page
    for line in tp.get("title") or []:
        centered(line, row)
        row += 1
    row += 1
    if tp.get("credit"):
        centered(tp["credit"], row)
        row += 2
    for a in tp.get("author") or []:
        centered(a, row)
        row += 1
    if tp.get("source"):
        row += 1
        for s in tp["source"]:
            centered(s, row)
            row += 1
    contact = tp.get("contact") or []
    c.setFont(FONTS[(False, False)], 12)
    for k, line in enumerate(contact):
        c.drawString(LEFT * INCH, TOP * INCH + (len(contact) - 1 - k) * LINE + 3, line)
    for k, line in enumerate(tp.get("date") or []):
        w = len(line) * CHAR * INCH
        c.drawString(RIGHT * INCH - w, TOP * INCH + 3 + k * LINE, line)


def render(text, path, title_page=None, contd=False):
    """Write the script as a PDF. `title_page` = {title: [lines], credit: str, author: [lines], source: [lines], contact: [lines], date: [lines]}
    or None for no title page. Returns the number of script pages."""
    from reportlab.pdfgen import canvas
    _register_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=(PAGE_W * INCH, PAGE_H * INCH))
    tp = title_page or {}
    c.setTitle(" ".join(tp.get("title") or []) or "Screenplay")
    if tp.get("author"):
        c.setAuthor(" ".join(tp["author"]))
    if title_page:
        _title_page(c, title_page)
        c.showPage()
    pages = paginate(text, contd)
    for n, page in enumerate(pages, start=1):
        if n > 1:
            label = f"{n}."
            c.setFont(FONTS[(False, False)], 12)
            c.drawString(RIGHT * INCH - len(label) * CHAR * INCH, (PAGE_H - 0.5) * INCH - 9.0, label)
        for row, ln in enumerate(page.lines):
            _draw_line(c, ln, row)
        c.showPage()
    c.save()
    return len(pages)
