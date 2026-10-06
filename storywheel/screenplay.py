"""Screenplay stories: a story whose format is "screenplay" keeps its manuscript as one Fountain file, manuscript/script.fountain.

    make_screenplay(story, shape)   marks a story as a screenplay (its format and a page target)
    start_from_outline(story)       writes script.fountain from the outline: a title page, then the beats as Fountain sections and synopses
    append_scene(story, heading)    a new scene heading at the end of the script
    flip_test(text, target)         the problems a reader notices when flipping through a script (see FLIP_RULES)
    title_page(story, anonymous)    the title page the PDF prints (from the story and your details in Settings)

None of the prose rules apply to a script: its blank lines mean something in Fountain, so it is never converted to one line per paragraph,
its scene markers are not rewritten, and it is exported as a script (PDF, .fountain, .fdx), not as prose."""
import re

from . import fountain, settings, structures

DEFAULT_PAGES = 100
SHORT_PAGES = 12
ACTION_LINES = 4             # an action block longer than this (printed lines) slows a reader down
SPEECH_LINES = 10            # a speech longer than this (printed lines of dialogue) is a monologue: worth a look
CAMERA = re.compile(r"\b(we see|we hear|we watch|camera|pan(?:s|ning)? (?:to|across|over)|zoom(?:s|ing)? (?:in|out)|close on|angle on|"
                    r"tracking shot|dolly|crane shot|pov shot|smash cut|insert shot)\b", re.I)


def make_screenplay(story, shape=None):
    from . import formats
    kind = shape.formats[0] if shape is not None and shape.screen and shape.formats else "feature-film"
    formats.apply(story, kind, shape.pages if shape is not None and shape.pages else None)


def target_pages(story):
    """The length the script is aiming at: the story's `target_pages`, else its screen structure's, else 100."""
    st = settings.load_story(story.path)
    try:
        if st.get("target_pages"):
            return int(st["target_pages"])
    except (TypeError, ValueError):
        pass
    meta, _sections = story.load_outline()
    shape = structures.find(meta.get("structure", ""))
    return shape.pages if shape is not None and shape.screen and shape.pages else DEFAULT_PAGES


def author_name():
    g = settings.load_global()
    return str(g.get("author_name") or g.get("legal_name") or "").strip()


def skeleton(story):
    """An empty script: a title page and FADE IN."""
    lines = [f"Title: {story.title}", "Credit: Written by"]
    author = author_name()
    if author:
        lines.append(f"Author: {author}")
    return "\n".join(lines) + "\n\nFADE IN:\n\n"


def outline_fountain(story):
    """The script a story's outline starts: its title page, then each beat as a Fountain section (# Act One, ## its label) with the beat's
    text as a synopsis (= ...). Sections and synopses are not printed: the pages stay empty until you write the scenes under them."""
    from . import outline
    meta, sections = story.load_outline()
    shape = structures.find(meta.get("structure", ""))
    head = skeleton(story).rstrip("\n").replace("\n\nFADE IN:", "")
    out = [head, ""]
    if meta.get("premise") or sections.get("Premise"):
        out += [f"= {outline.plain(meta.get('premise') or sections.get('Premise', ''))}", ""]
    out += ["FADE IN:", ""]
    beats = []
    for key, label, text in outline.rows(story):
        if key.startswith("beat:"):
            beats.append((key, label, text))
    act = None
    for key, label, text in beats:
        b = next((x for x in shape.beats if label == x.label or label.startswith(x.label + " (")), None) if shape is not None else None
        if b is not None and b.act and b.act != act:
            act = b.act
            out += [f"# {act}", ""]
        level = "##" if act else "#"
        out += [f"{level} {label}" if label else f"{level} Beat", "", f"= {text}", ""]
    return "\n".join(out) + "\n"


class ScriptExists(Exception):
    pass


def start_from_outline(story, replace=False):
    """Write manuscript/script.fountain from the outline. An existing script with anything written in it is never replaced unless asked."""
    path = story.script_path
    if path.exists() and not replace:
        script = fountain.parse(path.read_text(encoding="utf-8"))
        if any(e.type not in ("section", "synopsis") for e in script.elements if not (e.type == "action" and e.text.strip() == "FADE IN:")):
            raise ScriptExists(f"{path.name} already has scenes in it; it was left alone.")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():                                            # (replacing: the old file goes to .backups first)
        import datetime, shutil
        keep = story.path / ".backups" / f"script-{datetime.datetime.now():%Y%m%d-%H%M%S}"
        keep.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, keep / path.name)
    path.write_text(outline_fountain(story), encoding="utf-8")
    return path


def ensure_script(story):
    """The script file, made (an empty title page and FADE IN) if it is not there yet."""
    path = story.script_path
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(skeleton(story), encoding="utf-8")
    return path


def append_scene(story, heading=""):
    path = ensure_script(story)
    text = path.read_text(encoding="utf-8").rstrip("\n")
    head = (heading or "INT. NEW SCENE - DAY").strip()
    if not fountain.is_heading(head):
        head = "." + head.upper()
    new = text + "\n\n" + head.upper() + "\n\n"
    path.write_text(new, encoding="utf-8")
    return {"path": str(path), "line": new.rstrip("\n").count("\n") + 1}


# --- the flip test --------------------------------------------------------------------------------------------------------------

def flip_test(text, target=None):
    """[{line, kind, message}] in script order: what a reader flipping through notices.
       long-action  an action block of more than ACTION_LINES printed lines
       long-speech  a speech of more than SPEECH_LINES printed lines
       camera       camera directions in a spec script ("we see", "CAMERA", "ANGLE ON"...)
       cut-to       CUT TO: used often (more than once in every five scenes): each one is listed
       length       the page estimate against the target (more than 15% off)"""
    from . import screenplay_pdf as sp
    script = fountain.parse(text)
    out = []
    els = script.elements
    i = 0
    while i < len(els):
        e = els[i]
        if e.type == "action":
            n = len(sp.wrap_text(e.text, sp.WIDTH["action"]))
            if n > ACTION_LINES:
                out.append({"line": e.line, "kind": "long-action", "message": f"Action block of {n} lines (more than {ACTION_LINES}): break it up."})
            for k, line in enumerate(e.text.split("\n")):
                m = CAMERA.search(line)
                if m:
                    out.append({"line": e.line + k, "kind": "camera", "message": f"Camera direction ('{m.group(0)}') in a spec script."})
        elif e.type == "character":
            n, j = 0, i + 1
            while j < len(els) and els[j].type in ("dialogue", "parenthetical"):
                if els[j].type == "dialogue":
                    n += len(sp.wrap_text(els[j].text, sp.WIDTH["dialogue"]))
                j += 1
            if n > SPEECH_LINES:
                out.append({"line": e.line, "kind": "long-speech", "message": f"{e.name} speaks for {n} lines (more than {SPEECH_LINES})."})
        elif e.type == "heading":
            m = CAMERA.search(e.text)
            if m:
                out.append({"line": e.line, "kind": "camera", "message": f"Camera direction ('{m.group(0)}') in a scene heading."})
        i += 1
    cuts = [e for e in els if e.type == "transition" and e.text.upper().startswith("CUT TO")]
    scenes = len(script.headings())
    if cuts and len(cuts) > max(1, scenes // 5):
        for e in cuts:
            out.append({"line": e.line, "kind": "cut-to",
                        "message": f"CUT TO: is used {len(cuts)} times in {scenes} scenes; a new scene heading already says it."})
    if target:
        pages = sp.estimate_pages(text)
        if pages and abs(pages - target) > 0.15 * target:
            word = "long" if pages > target else "short"
            out.append({"line": 1, "kind": "length", "message": f"About {pages:g} pages against a target of {target}: {word}."})
    out.sort(key=lambda d: d["line"])
    return out


# --- the title page ---------------------------------------------------------------------------------------------------------------

def title_page(story, anonymous=False):
    """({title, credit, author, source, contact, date}, warnings) for the PDF: the title centered with "Written by" and your name under it, your
    contact block bottom left (Settings > You), the draft date bottom right. Anonymous (asked for, or no name in Settings): no name, no contact."""
    from .export import author_info
    script = fountain.parse(story.script_path.read_text(encoding="utf-8")) if story.script_path.exists() else None
    tp = script.title if script else {}
    who, warnings = author_info(story, anonymous=anonymous)
    out = {"title": [fountain.strip_markup(t) for t in (tp.get("title") or [story.title])], "credit": "", "author": [],
           "source": [fountain.strip_markup(s) for s in tp.get("source", [])], "contact": [], "date": tp.get("draft date", [])}
    if not who["anonymous"]:
        out["credit"] = (tp.get("credit") or ["Written by"])[0] or "Written by"
        out["author"] = [who["byline"]]
        out["contact"] = who["lines"]
    return out, warnings
