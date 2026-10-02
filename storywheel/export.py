"""
Compiling a manuscript and exporting it.

    compile_text(story)         the scenes as one markdown text
    export(story, "docx")       writes <manuscripts>/<Title>/<Title> <date>.docx  (also md, txt, odt, pdf, fountain)

The .docx follows William Shunn's "Proper Manuscript Format" for a short story (shunn.net/format/story.html),
built directly with python-docx:

    US Letter, 1 inch margins, 12 pt Times New Roman (or Courier New: a setting), double-spaced, no extra space
    between paragraphs, a half-inch first-line indent;
    page 1: your legal name, address, email and phone at the top left, "about N words" (rounded to the nearest
    hundred) at the top right; the title centered about halfway down, with "by <byline>" under it;
    pages 2 onwards: a header at the top right, "Surname / Keyword / page number";
    a scene break is a centered "#"; "END" is centered after the last line; *italics* stay italic, **bold** bold.

A novel gets the same pages with each scene file starting a new chapter on a new page (partial). A screenplay is a
clearly marked stub: the manuscript is written out as a .fountain file, unformatted.
.odt and .pdf are made from the .docx with LibreOffice (`soffice`) if it is installed; without it you get a message.
"""
import datetime
import re
import shutil
import subprocess
from pathlib import Path

from . import paths, settings, vault

FORMATS = ("docx", "odt", "pdf", "md", "txt", "fountain")
INDENT_INCHES = 0.5
TITLE_DOWN_POINTS = 4.5 * 72          # the title sits about halfway down the page (the margin is 1 inch)
LINE_POINTS = 13.8                    # one single-spaced line of 12 pt type


class ExportError(Exception):
    pass


# --- the text ---------------------------------------------------------------------------------------------------

def strip_markup(text):
    return text.replace("**", "").replace("*", "")


def normalize(text):
    """A file's text with its scene markers made plain: `* * * Title` becomes `* * *`, and a marker at the very
    start (it only names the first scene) disappears."""
    lines = text.strip("\n").split("\n")
    out, started = [], False
    for line in lines:
        if vault.marker_label(line) is not None:
            if started:
                out.append("* * *")
            continue
        if line.strip():
            started = True
        if started or line.strip():
            out.append(line)
    return "\n".join(out)


def scene_texts(story):
    """[(file name, text)] for each manuscript file, with plain markers."""
    return [(p.name, normalize(p.read_text(encoding="utf-8"))) for p in story.files()]


def one_space(text):
    """Double spaces after a full stop (and !, ?, …, with closing quotes or brackets) become one."""
    return re.sub(r"([.!?…][\"'”’)\]*_]*)[ \t]{2,}(?=\S)", r"\1 ", text)


def paragraphs(text, single_space=False):
    """Blocks of a text: [('scene_break', ''), ('text', 'a paragraph')...]. One line is one paragraph; blank lines mean
    nothing; a marker line is a scene break wherever it is."""
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if vault.marker_label(s) is not None:
            out.append(("scene_break", ""))
        elif s:
            out.append(("text", one_space(s) if single_space else s))
    return out


def compile_text(story):
    """The manuscript as one markdown text (scene files in order, joined by a blank line)."""
    return "\n\n".join(t for _n, t in scene_texts(story) if t.strip())


def plain_text(story):
    """No markup at all: scene breaks are '#', as in a manuscript."""
    blocks = []
    for kind, text in paragraphs(compile_text(story), _one_space(story)):
        blocks.append("#" if kind == "scene_break" else strip_markup(text))
    return "\n\n".join(blocks)


def round_words(n):
    """Shunn: round the word count to the nearest hundred (nearest ten for a very short piece)."""
    if n < 100:
        return max(10, int(n / 10.0 + 0.5) * 10)
    return int(n / 100.0 + 0.5) * 100


def _one_space(story):
    return bool(settings.load_story(story.path).get("export_one_space"))


def author_info(story, g=None, anonymous=False):
    """Who the manuscript is by. 'anonymous' is true when you asked for it or when there is no name to print: then there is
    no contact block, byline or surname (never a placeholder name)."""
    g = g or settings.load_global()
    warnings = []
    legal = g.get("legal_name") or g.get("author_name") or ""
    byline = g.get("author_name") or g.get("legal_name") or ""
    if anonymous:
        return {"lines": [], "byline": "", "surname": "", "legal": "", "anonymous": True}, warnings
    if not legal:
        warnings.append("No author name yet (Settings (F4) > You): exported anonymously, with no name or contact block.")
        return {"lines": [], "byline": "", "surname": "", "legal": "", "anonymous": True}, warnings
    lines = [legal] + [l for l in (g.get("address") or "").split("\n") if l.strip()]
    if not g.get("address"):
        warnings.append("No address yet (Settings (F4) > You): the first page has none.")
    if g.get("email"):
        lines.append(g["email"])
    if g.get("phone"):
        lines.append(g["phone"])
    return {"lines": lines, "byline": byline, "surname": settings.surname(dict(g, legal_name=legal)), "legal": legal,
            "anonymous": False}, warnings


def title_keyword(story, st):
    if st.get("title_keyword"):
        return st["title_keyword"]
    for word in re.findall(r"[A-Za-z0-9']+", story.title):
        if word.lower() not in ("the", "a", "an", "of", "and", "in", "on", "to"):
            return word.capitalize() if word.islower() else word
    return story.title


# --- the .docx --------------------------------------------------------------------------------------------------------

def _runs(paragraph, text, font):
    """Add `text` to a paragraph, turning **bold** and *italic* into real bold and italic runs."""
    pos = 0
    for m in re.finditer(r"\*\*(.+?)\*\*|\*(.+?)\*", text):
        if m.start() > pos:
            paragraph.add_run(text[pos:m.start()])
        run = paragraph.add_run(m.group(1) or m.group(2))
        if m.group(1):
            run.bold = True
        else:
            run.italic = True
        pos = m.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def _set_font(style, name, size_pt):
    from docx.oxml.ns import qn
    from docx.shared import Pt
    style.font.name = name
    style.font.size = Pt(size_pt)
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        from docx.oxml import OxmlElement
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attr), name)


def _page_field(paragraph):
    """A PAGE field, so the header shows the real page number."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    run = paragraph.add_run()
    for kind, text in (("begin", None), (None, " PAGE "), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)


def build_docx(story, path, anonymous=None):
    """Write the manuscript to `path` as a Shunn-format .docx. Returns (words, warnings). `anonymous` (None: the setting)
    leaves out the name, contact block, byline and surname; the header is then "Title / page"."""
    try:
        import docx
        from docx.enum.section import WD_SECTION
        from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: F401
        from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING, WD_TAB_ALIGNMENT
        from docx.shared import Inches, Pt
    except ImportError:
        raise ExportError("The Word export needs the python-docx package (pip install python-docx).")
    st = settings.load_story(story.path)
    if anonymous is None:
        anonymous = bool(st.get("export_anonymous"))
    info, warnings = author_info(story, anonymous=anonymous)
    single = bool(st.get("export_one_space"))
    font = st.get("font") or "Times New Roman"
    novel = str(st.get("format", "short-story")).lower() == "novel"
    scenes = scene_texts(story)
    words = sum(vault.count_words(t) for _n, t in scenes)

    d = docx.Document()
    d.core_properties.title = story.title
    d.core_properties.author = info["byline"]
    section = d.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Inches(1))
    section.header_distance = Inches(0.5)
    section.different_first_page_header_footer = True

    normal = d.styles["Normal"]
    _set_font(normal, font, 12)
    pf = normal.paragraph_format
    pf.space_before = pf.space_after = Pt(0)
    pf.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    pf.widow_control = False

    def para(text="", align=None, indent=False, single=False, before=None, runs=True, keep_next=False):
        p = d.add_paragraph()
        if align is not None:
            p.alignment = align
        f = p.paragraph_format
        if indent:
            f.first_line_indent = Inches(INDENT_INCHES)
        if single:
            f.line_spacing_rule = WD_LINE_SPACING.SINGLE
        if before is not None:
            f.space_before = Pt(before)
        if keep_next:
            f.keep_with_next = True
        if text:
            if runs:
                _runs(p, text, font)
            else:
                p.add_run(text)
        return p

    # page 1: contact block (single spaced), word count at the right of the first line
    block = info["lines"]
    first = para(single=True)
    first.paragraph_format.tab_stops.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.RIGHT)
    first.add_run((block[0] if block else "") + "\t" + f"about {round_words(words):,} words")
    for line in block[1:]:
        para(line, single=True, runs=False)
    # the title (bold unless you turned that off), about halfway down the page, then the byline
    used = max(1, len(block)) * LINE_POINTS
    title_p = para(story.title, WD_ALIGN_PARAGRAPH.CENTER, before=max(24, TITLE_DOWN_POINTS - used), runs=False)
    if st.get("export_title_bold", True) is not False:
        for r in title_p.runs:
            r.bold = True
    if not info["anonymous"]:
        para("by " + info["byline"], WD_ALIGN_PARAGRAPH.CENTER, runs=False)

    # headers: nothing on page 1; "Surname / Title / page" at the top right after that ("Title / page" when anonymous)
    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hp.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    shown = story.title if st.get("export_header", "full") != "keyword" else title_keyword(story, st)
    hp.add_run((f"{info['surname']} / " if info["surname"] else "") + f"{shown} / ")
    _page_field(hp)
    section.first_page_header.paragraphs[0].text = ""

    chapter = 0
    first_block = True
    for name, text in scenes:
        if novel:
            chapter += 1
            p = para(f"Chapter {chapter}", WD_ALIGN_PARAGRAPH.CENTER, before=(0 if chapter == 1 else 0), runs=False)
            p.paragraph_format.page_break_before = chapter > 1
            if chapter > 1:
                p.paragraph_format.space_before = Pt(TITLE_DOWN_POINTS / 3)
        for kind, block_text in paragraphs(text, single):
            if kind == "scene_break":
                para("#", WD_ALIGN_PARAGRAPH.CENTER, runs=False)
            else:
                p = para(block_text, indent=True, before=(24 if first_block and not novel else None))
                first_block = False
    para("END", WD_ALIGN_PARAGRAPH.CENTER, runs=False)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    d.save(str(path))
    return words, warnings


# --- the other formats ---------------------------------------------------------------------------------------------------

def _byline_md(info):
    return "" if info["anonymous"] else f"*by {info['byline']}*\n\n"


def build_md(story, path, anonymous=None):
    st = settings.load_story(story.path)
    info, warnings = author_info(story, anonymous=bool(st.get("export_anonymous")) if anonymous is None else anonymous)
    body = "\n\n".join("* * *" if k == "scene_break" else t for k, t in paragraphs(compile_text(story), _one_space(story)))
    text = f"# {story.title}\n\n{_byline_md(info)}{body}\n"
    Path(path).write_text(text, encoding="utf-8")
    return warnings


def build_txt(story, path, anonymous=None):
    st = settings.load_story(story.path)
    info, warnings = author_info(story, anonymous=bool(st.get("export_anonymous")) if anonymous is None else anonymous)
    by = "" if info["anonymous"] else f"by {info['byline']}\n"
    text = f"{story.title}\n{by}\n{plain_text(story)}\n\nEND\n"
    Path(path).write_text(text, encoding="utf-8")
    return warnings


def build_fountain(story, path):
    info, warnings = author_info(story)
    text = f"Title: {story.title}\nAuthor: {info['byline']}\n\n{compile_text(story)}\n"
    Path(path).write_text(text, encoding="utf-8")
    return warnings + ["Screenplay export is a stub: the manuscript is written out unformatted as a .fountain file."]


MARKER = ".storywheel-story"


def clean_name(text, fallback="Untitled"):
    """A title as a file or folder name: readable, with the characters file systems refuse removed."""
    text = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", text or "")
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or fallback


def story_id(story):
    return f"{story.universe.slug}/{story.slug}"


def export_folder(story):
    """<manuscripts>/<Story Title>/ for this story. A hidden marker in the folder says which story owns it; if another
    story (or nobody we know) owns the folder, the universe's name is added. Never inside or equal to the library."""
    root = paths.manuscripts_root()
    lib = paths.library_root()
    if root == lib or lib in root.parents:
        raise ExportError(f"The manuscripts folder ({paths.tilde(root)}) is inside your library. Choose another in Settings (F4) > Export.")
    me = story_id(story)
    title = clean_name(story.title)
    universe = clean_name(story.universe.name, "Universe")
    candidates = [title, f"{title} ({universe})"] + [f"{title} ({universe}) {n}" for n in range(2, 50)]
    for name in candidates:
        folder = root / name
        if folder == lib or lib in folder.parents or folder in lib.parents:
            continue
        marker = folder / MARKER
        if marker.exists():
            if marker.read_text(encoding="utf-8").strip() == me:
                return folder
            continue
        if not folder.exists() or not any(folder.iterdir()):
            folder.mkdir(parents=True, exist_ok=True)
            marker.write_text(me + "\n", encoding="utf-8")
            return folder
    raise ExportError("Couldn't find a free folder name for this story under " + paths.tilde(root))


def file_stem(story):
    return f"{clean_name(story.title)} {datetime.date.today().isoformat()}"


def unique_stem(folder, stem, exts):
    """The stem, or 'stem -2', 'stem -3'... so that no file of any of the extensions gets overwritten."""
    n = 1
    while True:
        s = stem if n == 1 else f"{stem} -{n}"
        if not any((folder / f"{s}.{e}").exists() for e in exts):
            return s
        n += 1


def convert(path, fmt):
    """Convert a .docx to .odt or .pdf with LibreOffice. Returns the new path."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise ExportError(f"Making a .{fmt} needs LibreOffice ('soffice'), which isn't installed. The .docx was written.")
    out = Path(path).parent
    try:
        res = subprocess.run([soffice, "--headless", "--convert-to", fmt, "--outdir", str(out), str(path)],
                             capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as e:
        raise ExportError(f"LibreOffice failed: {e}")
    target = Path(path).with_suffix("." + fmt)
    if res.returncode != 0 or not target.exists():
        raise ExportError(f"LibreOffice couldn't make the .{fmt}: {res.stderr.strip() or res.stdout.strip()}")
    return target


def export(story, fmt="docx", out_dir=None, anonymous=None):
    """Write the manuscript in a format. Returns {'path', 'format', 'words', 'warnings'}; raises ExportError."""
    fmt = fmt.lower().lstrip(".")
    if fmt not in FORMATS:
        raise ExportError(f"Unknown format '{fmt}'. Choose one of: {', '.join(FORMATS)}")
    if not story.files() or not compile_text(story).strip():
        raise ExportError("The manuscript is empty: write something first.")
    out = Path(out_dir) if out_dir else export_folder(story)
    out.mkdir(parents=True, exist_ok=True)
    exts = {"docx": ["docx"], "odt": ["docx", "odt"], "pdf": ["docx", "pdf"], "md": ["md"], "txt": ["txt"], "fountain": ["fountain"]}[fmt]
    base = out / unique_stem(out, file_stem(story), exts)
    warnings = []
    words = vault.count_words(compile_text(story))
    st = settings.load_story(story.path)
    if str(st.get("format", "")).lower() == "screenplay" and fmt in ("docx", "odt", "pdf"):
        fmt = "fountain"
        warnings.append("This story's format is 'screenplay': exported as a .fountain file instead (screenplay layout is a stub).")
    if fmt == "docx":
        words, warnings = build_docx(story, base.with_suffix(".docx"), anonymous)
        path = base.with_suffix(".docx")
        if str(st.get("format", "")).lower() == "novel":
            warnings.append("Novel layout is partial: chapters start new pages, but Shunn's novel title page is not fully reproduced.")
    elif fmt in ("odt", "pdf"):
        docx_path = base.with_suffix(".docx")
        words, warnings = build_docx(story, docx_path, anonymous)
        path = convert(docx_path, fmt)
    elif fmt == "md":
        path = base.with_suffix(".md")
        warnings = build_md(story, path, anonymous)
    elif fmt == "txt":
        path = base.with_suffix(".txt")
        warnings = build_txt(story, path, anonymous)
    else:
        path = base.with_suffix(".fountain")
        warnings += build_fountain(story, path)
    return {"path": str(path), "shown": paths.tilde(path), "format": fmt, "words": words, "warnings": warnings}
