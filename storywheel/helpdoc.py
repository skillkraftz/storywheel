"""Help, from one source. Every help surface (the help screen in each mode, the Writer's float, Settings > Help, `storywheel help`) reads the
files in `storywheel/data/help/`: one per mode (wheel, builder, writer, settings, words) and topics (universes, structures, genres-and-flavor,
exports, backups, dictionary, grammar, keys), plus `common` for the keys every mode shares.

A help file is plain text:

    # Title
    One paragraph (or two) about what it is for.            <- the introduction
    ## Keys
    ### MainScreen | Everywhere in the Wheel                <- a group: the class that has the bindings | its title in the table
    roll: Roll the step again                               <- action: one-line description (a line indented under it continues it)
    ## Mouse
    - click a field: reroll it
    ## Anything else
    Free text.

The key tables are NOT written in the files. They are made from the real bindings (Textual `BINDINGS` of the mode's screen and its list widgets;
the Writer's configurable shortcuts and fixed keys from keys.py, with the keys as you set them) and merged with the descriptions in the file by
action name. A binding with no description is a bug: `missing_descriptions()` lists them and a test fails on any."""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent / "data" / "help"

MODES = ("wheel", "builder", "writer", "settings", "words")
TOPICS = ("universes", "structures", "genres-and-flavor", "exports", "screenplays", "writing-prose", "backups", "dictionary", "grammar", "keys")

KEY_NAMES = {"question_mark": "?", "slash": "/", "backslash": "\\", "plus": "+", "minus": "-", "equals_sign": "=", "escape": "Esc", "space": "space",
             "enter": "Enter", "tab": "Tab", "comma": ",", "full_stop": ".", "pageup": "PgUp", "pagedown": "PgDn"}

MODULES = {"wheel": "tui", "builder": "builder", "settings": "settings_app", "words": "words_app"}


class Doc:
    def __init__(self, name, title, intro, groups, sections):
        self.name, self.title, self.intro, self.groups, self.sections = name, title, intro, groups, sections


def _read(name):
    path = HERE / f"{name}.md"
    if not path.exists():
        raise KeyError(name)
    return path.read_text(encoding="utf-8")


_CACHE = {}


def load(name):
    """The parsed help file `name`."""
    stamp = (HERE / f"{name}.md").stat().st_mtime_ns if (HERE / f"{name}.md").exists() else 0
    hit = _CACHE.get(name)
    if hit and hit[0] == stamp:
        return hit[1]
    title, intro, groups, sections = name, [], [], []
    current = None                                    # ("intro",) | ("keys",) | ("section", heading, lines)
    group = None
    last_key = None
    for raw in _read(name).splitlines():
        line = raw.rstrip()
        if line.startswith("# ") and current is None:
            title = line[2:].strip()
            current = ("intro",)
            continue
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading.lower() == "keys":
                current = ("keys",)
            else:
                sections.append([heading, []])
                current = ("section", sections[-1])
            continue
        if current and current[0] == "keys":
            if line.startswith("### "):
                cls, _, gtitle = line[4:].partition("|")
                group = {"class": cls.strip(), "title": gtitle.strip() or cls.strip(), "items": {}}
                groups.append(group)
                last_key = None
            elif line.strip() and group is not None:
                if raw[:1] in (" ", "\t") and last_key:
                    group["items"][last_key] += " " + line.strip()
                else:
                    key, sep, desc = line.partition(": ")
                    if sep:
                        last_key = key.strip()
                        group["items"][last_key] = desc.strip()
            continue
        if current and current[0] == "intro":
            intro.append(line)
        elif current and current[0] == "section":
            current[1][1].append(line)
    doc = Doc(name, title, "\n".join(intro).strip(), groups, [(h, "\n".join(ls).strip("\n")) for h, ls in sections])
    _CACHE[name] = (stamp, doc)
    return doc


def names():
    return list(MODES) + list(TOPICS)


def titles():
    """[(name, title, kind)] for the topic list: modes first, then topics."""
    return [(n, load(n).title, "mode" if n in MODES else "topic") for n in names()]


def resolve(word):
    """A help name from what you typed: a mode or topic name, a number of letters of one, or an F-key/mode name. None if unknown."""
    w = (word or "").strip().lower().replace(" ", "-")
    if w in names():
        return w
    alias = {"f1": "wheel", "f2": "builder", "f3": "writer", "f4": "settings", "f5": "words", "genres": "genres-and-flavor", "flavor": "genres-and-flavor",
             "genre": "genres-and-flavor", "export": "exports", "backup": "backups", "dictionaries": "dictionary", "thesaurus": "dictionary",
             "rhymes": "dictionary", "shortcuts": "keys", "universe": "universes", "structure": "structures", "spelling": "grammar",
             "common": "keys", "screenplay": "screenplays", "script": "screenplays", "fountain": "screenplays"}
    if w in alias:
        return alias[w]
    hits = [n for n in names() if n.startswith(w)] if w else []
    return hits[0] if len(hits) == 1 else None


# --- the key tables, from the real bindings ----------------------------------------------------------------------------------

def key_text(binding):
    if binding.key_display:
        return binding.key_display
    return " / ".join(KEY_NAMES.get(k, k) for k in binding.key.split(","))


def _classes(mode):
    """[(class name, class)] of the mode's screen and its list widgets that have their own bindings (dialogs are not listed)."""
    import importlib
    import inspect
    from textual.binding import Binding
    from textual.screen import ModalScreen, Screen
    from textual.widget import Widget
    mod = importlib.import_module("storywheel." + MODULES[mode])
    out = []
    for n, c in inspect.getmembers(mod, inspect.isclass):
        if c.__module__ != mod.__name__ or issubclass(c, ModalScreen) or "BINDINGS" not in c.__dict__ or not issubclass(c, (Screen, Widget)):
            continue
        if any(isinstance(b, Binding) for b in c.__dict__["BINDINGS"]):
            out.append((n, c))
    out.sort(key=lambda nc: (not issubclass(nc[1], Screen), nc[0]))
    return out


def _is_nav(binding):
    return binding.key.split(",")[0] in ("f1", "f2", "f3", "f4", "f5")


def _describe(mode, cls_name, action):
    doc = load(mode)
    for g in doc.groups:
        if g["class"] == cls_name and action in g["items"]:
            return g["items"][action]
    for g in load("common").groups:
        if action in g["items"] or action.split("(")[0] in g["items"]:
            return g["items"].get(action) or g["items"].get(action.split("(")[0])
    return None


def binding_rows(mode):
    """[(group title, [(keys, description or None, action)])] for a Textual mode, from its real bindings. Bindings that share an action are one row;
    F1-F5 are one row."""
    from textual.binding import Binding
    rows, nav_done = [], False
    doc = load(mode)
    for cls_name, cls in _classes(mode):
        items, by_action = [], {}
        for b in cls.__dict__["BINDINGS"]:
            if not isinstance(b, Binding):
                continue
            if _is_nav(b):
                if not nav_done:
                    items.append(("F1 F2 F3 F4 F5", load("common").groups[0]["items"].get("modes"), "modes"))
                    nav_done = True
                continue
            action = b.action
            if action in by_action:
                i = by_action[action]
                keys, d, a = items[i]
                items[i] = (keys + " / " + key_text(b), d, a)
                continue
            by_action[action] = len(items)
            items.append((key_text(b), _describe(mode, cls_name, action), action))
        title = next((g["title"] for g in doc.groups if g["class"] == cls_name), cls_name)
        rows.append((title, items))
    return rows


def writer_rows():
    """The Writer's keys: the configurable shortcuts as you set them, then the fixed ones (keys.py), with the descriptions of writer.md."""
    from . import keys, settings
    doc = load("writer")
    g = settings.load_global()
    descs = {}
    for grp in doc.groups:
        descs.update(grp["items"])
    configurable = [(keys.label(g.get(name) or default), descs.get(name), name) for name, (_label, default) in keys.WRITER_KEYS.items()]
    fixed = [(keys.label(key), descs.get(key), key) for key in keys.RESERVED]
    return [("Shortcuts you can change (Settings > Keys)", configurable), ("Fixed keys", fixed)]


def key_groups(name):
    if name == "writer":
        return writer_rows()
    if name in MODULES:
        return binding_rows(name)
    return []


def missing_descriptions():
    """['wheel: MainScreen roll', ...]: every binding with no one-line description in the help files. Must be empty."""
    out = []
    for mode in MODES:
        for title, items in key_groups(mode):
            for keys_, desc, action in items:
                if not desc:
                    out.append(f"{mode}: {title}: {keys_} ({action})")
    return out


# --- the text -----------------------------------------------------------------------------------------------------------------

def sections(name):
    """[(heading, body)] of a help page: About (the introduction), Keys (made from the bindings), then the file's own sections."""
    doc = load(name)
    out = []
    if doc.intro:
        out.append(("About", doc.intro))
    groups = key_groups(name)
    if groups:
        lines = []
        for title, items in groups:
            lines.append(title)
            width = min(22, max([len(k) for k, _d, _a in items] + [4]))
            for k, d, _a in items:
                lines.append(f"  {k.ljust(width)}  {d or '(no description yet)'}")
            lines.append("")
        out.append(("Keys", "\n".join(lines).rstrip()))
    out.extend((h, b) for h, b in doc.sections)
    return out


# --- tabs (batch 18): the help screens and the Writer's float show a page as tabs --------------------------------------------------

KEY_SECTIONS = ("Keys", "Mouse")
SCRIPT_FORMATS = ("screenplay", "feature-film", "short-film")


def _short_title(name):
    title = load(name).title
    return title[4:] if title.startswith("The ") else title


def _topic_sections():
    """Every topic page as one section each (its introduction, then its own sections), for the Topics tab."""
    out = []
    for t in TOPICS:
        doc = load(t)
        parts = []
        for heading, body in sections(t):
            parts += ([body] if heading == "About" else [heading, "~" * len(heading), body])
        out.append((doc.title, "\n\n".join(parts)))
    return out


def tabs(name, fmt=None):
    """[(tab title, [(heading, body)])]: how a help page is shown as tabs.

    The Writer: the guide to the story's format (Screenplay, or Writing prose for a short story or a novel), Writing basics, Keys, Export.
    A mode: its guide (the introduction and its own sections), Keys (and Mouse), Topics (every topic page). A topic page is one tab."""
    page = sections(name)
    keys_ = [(h, b) for h, b in page if h in KEY_SECTIONS]
    rest = [(h, b) for h, b in page if h not in KEY_SECTIONS]
    if name == "writer":
        script = str(fmt or "").lower() in SCRIPT_FORMATS
        guide = "screenplays" if script else "writing-prose"
        return [("Screenplay" if script else "Writing prose", sections(guide)), ("Writing basics", rest), ("Keys", keys_),
                ("Export", sections("exports"))]
    if name in MODES:
        return [(_short_title(name), rest), ("Keys", keys_), ("Topics", _topic_sections())]
    return [(load(name).title, page)]


def tab_text(secs, width=None, query=""):
    """(text, matches): a tab's sections as plain text; with a query only the sections containing every word of it."""
    words = [w for w in (query or "").lower().split() if w]
    parts, found = [], 0
    for heading, body in secs:
        if words and not all(w in f"{heading} {body}".lower() for w in words):
            continue
        found += 1
        parts += [heading, "-" * len(heading), wrap(body, width), ""]
    if words and not found:
        parts += [f"Nothing in this tab matches “{query}”. Try another tab, or Settings > Help, which searches every page."]
    return "\n".join(parts).rstrip() + "\n", found


def wrap(body, width):
    """Wrap a page's paragraphs to a width; table rows (indented) keep their key column."""
    import textwrap
    if not width:
        return body
    out = []
    for line in body.splitlines():
        if not line.strip() or len(line) <= width:
            out.append(line)
        elif line.startswith("  "):
            m = re.match(r"^(\s+\S.*?\s{2,})\S", line)
            hang = len(m.group(1)) if m else len(line) - len(line.lstrip()) + 2
            out.extend(textwrap.wrap(line, width, subsequent_indent=" " * min(hang, 30), break_long_words=False))
        else:
            out.extend(textwrap.wrap(line, width, break_long_words=False))
    return "\n".join(out)


def text(name, width=None):
    """The whole page as plain text (the command line, the Writer's float); `width` wraps it."""
    doc = load(name)
    parts = [doc.title, "=" * len(doc.title), ""]
    for heading, body in sections(name):
        parts += [heading, "-" * len(heading), wrap(body, width), ""]
    return "\n".join(parts).rstrip() + "\n"


def search(query):
    """[(name, heading, snippet)] of every section (of every page) whose text contains all the words of the query, best matches first."""
    words = [w for w in re.split(r"\s+", (query or "").lower().strip()) if w]
    if not words:
        return []
    hits = []
    for n in names():
        title = load(n).title
        for heading, body in sections(n):
            hay = f"{title} {heading} {body}".lower()
            if all(w in hay for w in words):
                score = sum(hay.count(w) for w in words) + (5 if all(w in heading.lower() or w in title.lower() for w in words) else 0)
                first = next((l.strip() for l in body.splitlines() if any(w in l.lower() for w in words)), body.splitlines()[0] if body else "")
                hits.append((score, n, heading, first[:100]))
    hits.sort(key=lambda h: -h[0])
    return [(n, h, s) for _sc, n, h, s in hits]
