"""
The library: your universes, as plain folders of markdown.

    <library>/universes/<universe>/universe.md     name, genres, mix, notes
                                   characters/ places/ things/ groups/ notes/   one .md per entity
                                   stories/<story>/story.md, seed.json, settings.toml, manuscript/, ...
                                   lists/                                       your own atom lists

An entity is a markdown file: fields in the YAML frontmatter, free notes in the body. Its `id` (the file's
name, without .md) never changes, so links by id survive renames; links are stored as ids in link fields.
Deleting moves things to <library>/.trash/ instead of destroying them.
"""
import copy
import datetime
import json
import re
import shutil
from pathlib import Path

from . import frontmatter, paths, schemas

PLACEHOLDER = re.compile(r"^(character|place|thing|group|note)-\d+$")


# --- small helpers ---------------------------------------------------------------------------------

def slugify(text, fallback="untitled"):
    text = re.sub(r"[^a-z0-9]+", "-", (text or "").lower().replace("'", "")).strip("-")
    return text[:60].strip("-") or fallback


def entity_slug(name, type_=""):
    """An entity's id from its name: no leading article, so "a locked box" is `locked-box` and "the sheriff" is `sheriff`
    (a note's name is a title, so it keeps its "The")."""
    if type_ == "note":
        return slugify(name)
    rest = re.sub(r"^(?:a|an|the)\s+", "", (name or "").strip(), flags=re.IGNORECASE)
    return slugify(rest or name)


def root():
    return paths.library_root()


def universes_dir():
    return root() / "universes"


def trash(path):
    """Move a file or folder into <library>/.trash/ (never destroy writing)."""
    path = Path(path)
    if not path.exists():
        return None
    dest_dir = root() / ".trash"
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"{stamp}-{path.name}"
    n = 1
    while dest.exists():
        n += 1
        dest = dest_dir / f"{stamp}-{n}-{path.name}"
    shutil.move(str(path), str(dest))
    return dest


# --- keeping what was read ---------------------------------------------------------------------------------
# Files are read once and remembered until they change on disk (their modification time or size). Our own writes forget
# a file at once; a file changed by the Writer or by another program is noticed by its time. `memo` is for values worked
# out from one or more files (word counts, scenes, a parsed entity); `stamp` says whether any of them has changed.

_MEMO = {}


def stamp(*paths_):
    """What identifies the current contents of files: (mtime, size) for each, None for a missing one."""
    out = []
    for p in paths_:
        try:
            st = Path(p).stat()
            out.append((st.st_mtime_ns, st.st_size))
        except OSError:
            out.append(None)
    return tuple(out)


def memo(key, stamp_, compute):
    """compute() once per (key, stamp_). The value is shared: copy it before changing it."""
    hit = _MEMO.get(key)
    if hit is not None and hit[0] == stamp_:
        return hit[1]
    value = compute()
    _MEMO[key] = (stamp_, value)
    return value


def forget(path):
    """Drop everything remembered about a file we are about to write."""
    prefix = str(path)
    for k in [k for k in _MEMO if k[0] == prefix or (isinstance(k[0], tuple) and prefix in k[0])]:
        _MEMO.pop(k, None)


def _write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)                       # replace in one step: a crash never leaves half a file
    forget(path)


def _unique(base, taken):
    slug, n = base, 1
    while slug in taken:
        n += 1
        slug = f"{base}-{n}"
    return slug


# --- entities ----------------------------------------------------------------------------------------

class Entity:
    def __init__(self, type_, id_, fields=None, custom=None, body="", created=None):
        self.type, self.id = type_, id_
        self.fields = dict(fields or {})        # every schema field, by key (links hold ids)
        self.custom = dict(custom or {})        # your own extra fields (write-only)
        self.body = body                        # free-form notes
        self.created = created or datetime.date.today().isoformat()
        self.path = None
        self.proper = None                      # True: a proper name (Title Case); False: a description ("a locked box"); None: not recorded

    @property
    def name(self):
        return self.fields.get("name", "")

    def get(self, key, default=""):
        return self.fields.get(key, default)

    def __repr__(self):
        return f"Entity({self.type}, {self.id!r}, {self.name!r})"

    def clone(self):
        """A copy that can be changed without touching what is remembered."""
        e = Entity(self.type, self.id, {k: (list(v) if isinstance(v, list) else v) for k, v in self.fields.items()},
                   dict(self.custom), self.body, self.created)
        e.path = self.path
        e.proper = self.proper
        return e

    def to_text(self):
        meta = {"id": self.id, "type": self.type}
        if self.proper is not None:
            meta["proper"] = "yes" if self.proper else "no"
        body_key = next((f["key"] for f in schemas.get(self.type)["fields"] if f.get("body")), None)
        for f in schemas.get(self.type)["fields"]:
            if f.get("body"):
                continue
            value = self.fields.get(f["key"], [] if f.get("kind") == "links" else "")
            meta[f["key"]] = value
        if self.custom:
            meta["custom"] = self.custom
        meta["created"] = self.created
        body = self.fields.get(body_key, "") if body_key else self.body
        if body_key and self.body and not body:
            body = self.body
        return frontmatter.dumps(meta, body)

    @classmethod
    def from_text(cls, text, path=None):
        meta, body = frontmatter.loads(text)
        type_ = meta.get("type") or "note"
        try:
            sch = schemas.get(type_)
        except KeyError:
            sch = {"fields": []}
        fields = {}
        for f in sch["fields"]:
            if f.get("body"):
                fields[f["key"]] = body
                continue
            value = meta.get(f["key"], [] if f.get("kind") == "links" else "")
            if f.get("kind") == "links" and isinstance(value, str):
                value = [v.strip() for v in value.split(",") if v.strip()]
            fields[f["key"]] = value if not isinstance(value, (int, float)) else str(value)
        custom = dict(meta.get("custom") or {})
        if type_ == "place" and "season" in custom and not fields.get("season"):
            fields["season"] = custom.pop("season")                       # (older files kept it as a custom field)
        e = cls(type_, meta.get("id") or (Path(path).stem if path else ""), fields, custom,
                "" if any(f.get("body") for f in sch["fields"]) else body, meta.get("created"))
        e.path = Path(path) if path else None
        flag = str(meta.get("proper", "")).strip().lower()
        e.proper = True if flag == "yes" else False if flag == "no" else None
        return e


# --- stories -------------------------------------------------------------------------------------------

class Story:
    """A promoted story: an outline (story.md), settings, and a manuscript of scene files."""

    def __init__(self, universe, slug):
        self.universe, self.slug = universe, slug
        self.path = universe.path / "stories" / slug

    # outline
    @property
    def outline_path(self):
        return self.path / "story.md"

    def load_outline(self):
        """(meta, sections) of story.md, read again only when the file changes. Fresh dicts: change them freely."""
        def read():
            if not self.outline_path.exists():
                return {}, {}
            meta, body = frontmatter.loads(self.outline_path.read_text(encoding="utf-8"))
            return meta, parse_sections(body)
        meta, sections = memo((str(self.outline_path), "outline"), stamp(self.outline_path), read)
        return copy.deepcopy(meta), dict(sections)

    def save_outline(self, meta, sections):
        _write(self.outline_path, frontmatter.dumps(meta, render_sections(meta.get("title", ""), sections)))

    @property
    def meta(self):
        return self.load_outline()[0]

    @property
    def title(self):
        return self.meta.get("title") or self.slug.replace("-", " ").title()

    def sections(self):
        return self.load_outline()[1]

    def set_section(self, heading, text):
        meta, sections = self.load_outline()
        sections[heading] = text.strip("\n")
        self.save_outline(meta, sections)

    def set_meta(self, **changes):
        meta, sections = self.load_outline()
        meta.update(changes)
        self.save_outline(meta, sections)

    # other files
    @property
    def settings_path(self):
        return self.path / "settings.toml"

    @property
    def manuscript_dir(self):
        return self.path / "manuscript"

    @property
    def exports_dir(self):
        return self.path / "exports"

    @property
    def stats_path(self):
        return self.path / "stats.json"

    def scenes(self):
        """Scene files in order: [Path]."""
        if not self.manuscript_dir.is_dir():
            return []
        return sorted(self.manuscript_dir.glob("*.md"))

    def files(self):
        """The manuscript's files in order (one for a short story; one per chapter for a novel)."""
        return self.scenes()

    def scene_list(self):
        """The scenes in order, found by their markers (`* * *` or `* * * Title`) across all the files:
        [{n, title, label, first_line, words, path, line, file}]. `line` is the marker's line (1 for an unmarked first scene)."""
        def build():
            out = []
            for p in self.files():
                for sc in parse_scenes(self._read(p)):
                    n = len(out) + 1
                    out.append({"n": n, "title": sc["label"] or (f"Scene {n}" if n > 1 or sc["marked"] else "Opening"),
                                "label": sc["label"], "first_line": sc["first_line"], "words": sc["words"],
                                "path": str(p), "line": sc["start"], "end": sc["end"], "file": p.name, "marked": sc["marked"]})
            return out
        return [dict(d) for d in memo((str(self.path), "scenes"), self._stamp(), build)]

    def _stamp(self):
        return stamp(*self.files())

    def _read(self, path):
        return memo((str(path), "text"), stamp(path), lambda: Path(path).read_text(encoding="utf-8"))

    def append_scene(self, title="", text=""):
        """A new scene at the end of the manuscript, marked `* * * Title` (in the last file; a first file is made if there is none)."""
        files = self.files()
        if not files:
            self.manuscript_dir.mkdir(parents=True, exist_ok=True)
            target = self.manuscript_dir / "manuscript.md"
            body = (f"* * * {title}\n\n" if title else "") + text
            _write(target, body)
            return {"path": str(target), "line": 1}
        target = files[-1]
        old = target.read_text(encoding="utf-8").rstrip("\n")
        marker = f"* * * {title}".rstrip()
        new = (old + "\n\n" if old else "") + marker + "\n\n" + (text + "\n" if text else "")
        _write(target, new)
        return {"path": str(target), "line": new.count("\n", 0, new.rindex(marker)) + 1}

    def migrate_manuscript(self):
        """Older stories kept one file per scene. A short story now has ONE file (manuscript.md) with a marker line at
        the start of each scene, so the whole thing reads in order. The scene files are moved into a backup folder
        (<story>/.backups/migrated-DATE/) first; a novel keeps one file per chapter. Returns a message, or None."""
        files = self.files()
        from . import settings
        if len(files) <= 1 or str(settings.load_story(self.path).get("format", "short-story")).lower() == "novel":
            return None
        if files == [self.manuscript_dir / "manuscript.md"]:
            return None
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = self.path / ".backups" / f"migrated-{stamp}"
        backup.mkdir(parents=True, exist_ok=True)
        parts = []
        for p in files:
            text = p.read_text(encoding="utf-8").strip("\n")
            shutil.copy2(p, backup / p.name)
            title = re.sub(r"\.md$", "", re.sub(r"^\d+-", "", p.name)).replace("-", " ")
            title = title[:1].upper() + title[1:]
            head, _, rest = text.partition("\n")
            label = marker_label(head)
            if label:                                              # the file already names its scene
                parts.append(text)
            elif label == "":                                      # a plain `* * *` at the top: give it the file's name
                parts.append(f"* * * {title}" + ("\n" + rest if rest else ""))
            else:
                parts.append((f"* * * {title}\n\n" if text else f"* * * {title}\n") + text)
        merged = "\n\n".join(parts).rstrip("\n") + "\n"
        target = self.manuscript_dir / "manuscript.md"
        _write(target, merged)
        for p in files:
            if p != target:
                p.unlink()
        return f"Merged {len(files)} scene files into manuscript.md (the originals are in {backup})."

    def migrate_paragraphs(self):
        """Older manuscripts kept a paragraph as lines joined until a blank line. A paragraph is now one line. Once per story
        (a `.one-line-paragraphs` file says it is done), hard-wrapped paragraphs are joined and blank lines dropped, with the
        old files copied to <story>/.backups/paragraphs-DATE/ first. Returns a message when something changed, else None."""
        flag = self.path / ".one-line-paragraphs"
        if flag.exists() or not self.path.is_dir():
            return None
        changed, total_joined, dropped = [], 0, 0
        files = self.files()
        stamp_ = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = self.path / ".backups" / f"paragraphs-{stamp_}"
        for p in files:
            old = p.read_text(encoding="utf-8")
            new, joined = join_hard_wraps(old)
            if new == old:
                continue
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, backup / p.name)
            blanks = sum(1 for l in old.split("\n")[:-1] if not l.strip())
            dropped += blanks
            total_joined += joined
            _write(p, new)
            changed.append(p.name)
        _write(flag, "one line = one paragraph\n")
        if not changed:
            return None
        parts = []
        if total_joined:
            parts.append(f"joined {total_joined} hard-wrapped paragraph{'s' if total_joined != 1 else ''}")
        if dropped:
            parts.append(f"removed {dropped} blank line{'s' if dropped != 1 else ''}")
        return f"Paragraphs are now one line each: {' and '.join(parts) or 'tidied'} in {', '.join(changed)} (the originals are in {backup})."

    def migrate_quotes(self):
        """Manuscripts keep straight quotes and apostrophes (the spellchecker can't read ’ in "couldn’t"). Once per story (a
        `.straight-quotes` file says so), curly marks in the manuscript files become straight, with the old files copied to
        <story>/.backups/quotes-DATE/ first. Returns a message when something changed, else None."""
        from . import quotes
        flag = self.path / ".straight-quotes"
        if flag.exists() or not self.path.is_dir():
            return None
        changed, total = [], 0
        backup = self.path / ".backups" / f"quotes-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        for p in self.files():
            old = p.read_text(encoding="utf-8")
            n = quotes.count_curly(old)
            if not n:
                continue
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, backup / p.name)
            _write(p, quotes.straighten(old))
            changed.append(p.name)
            total += n
        _write(flag, "straight quotes in the manuscript; the export makes them curly\n")
        if not changed:
            return None
        return (f"Quotes are now straight in the manuscript ({total} curly mark{'s' if total != 1 else ''} changed in {', '.join(changed)}; the "
                f"originals are in {backup}). The export makes them curly again.")

    def seed(self):
        p = self.path / "seed.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def manuscript_text(self):
        return memo((str(self.path), "manuscript"), self._stamp(),
                    lambda: "\n\n".join(self._read(p).strip("\n") for p in self.files()))

    def word_count(self):
        return memo((str(self.path), "words"), self._stamp(), lambda: sum(count_words(self._read(p)) for p in self.scenes()))

    def add_scene(self, title="", text=""):
        """A new manuscript FILE at the end: 03-the-letter.md (a chapter, in a novel; a short story uses append_scene)."""
        self.manuscript_dir.mkdir(parents=True, exist_ok=True)
        n = len(self.scenes()) + 1
        existing = {p.name for p in self.scenes()}
        while any(name.startswith(f"{n:02d}-") for name in existing):
            n += 1
        path = self.manuscript_dir / f"{n:02d}-{slugify(title, 'scene')}.md"
        _write(path, text)
        return path

    def delete(self):
        return trash(self.path)


MARKERS = ("***", "* * *", "#")             # the scene breaks that can be chosen in Settings (the first is the default)


def marker_label(line):
    """None if the line is not a scene marker; else the scene's title ('' for a plain break). A line holding only `***`,
    `* * *` or `#` is a break; `* * * Title` (or `*** Title`) is a break that names its scene. `***text***` inside a
    paragraph is bold italic, not a break."""
    s = line.rstrip()
    if s in MARKERS:
        return ""
    m = re.fullmatch(r"\* \* \*\s+(.*)", s) or re.fullmatch(r"\*\*\*\s+([^*\s].*)", s)
    return None if m is None else m.group(1).strip()


def join_hard_wraps(text):
    """The text in the one-line-one-paragraph form: each paragraph on one line, no blank lines, scene markers alone on their
    lines. Lines of a hard-wrapped paragraph (no blank line between them) are joined with a space. Returns (text, joined)
    where `joined` is how many paragraphs were put back together."""
    out, block, joined = [], [], 0
    lines = text.split("\n")
    if not any(not l.strip() and 0 < i < len(lines) - 1 and any(x.strip() for x in lines[:i]) and any(x.strip() for x in lines[i + 1:])
               for i, l in enumerate(lines)):
        return text, 0                    # no blank line between paragraphs: already one paragraph per line

    def flush():
        nonlocal joined
        if block:
            if len(block) > 1:
                joined += 1
            out.append(" ".join(block))
            block.clear()

    for line in text.split("\n"):
        s = line.strip()
        if marker_label(s) is not None:
            flush()
            out.append(s)
        elif s:
            block.append(s)
        else:
            flush()
    flush()
    return "\n".join(out) + ("\n" if out else ""), joined


def count_words(text):
    """Words in some prose: runs of non-space characters that hold a letter or digit. Scene marker lines (`* * *`,
    `* * * Title`) are not prose and are not counted. The Writer counts the same way."""
    return sum(1 for line in text.split("\n") if marker_label(line) is None
               for w in line.split() if re.search(r"\w", w))


def parse_scenes(text):
    """Scenes in a file by their markers: [{start, end, label, marked, first_line, words}] (lines are 1-based).
    A marker at the very start names the first scene (it is not a break); text before the first marker is a scene of its own."""
    lines = text.split("\n")
    scenes = []
    for i, line in enumerate(lines, 1):
        label = marker_label(line)
        if label is not None:
            scenes.append({"start": 1 if not scenes else i, "label": label, "marked": True})
        elif line.strip() and not scenes:
            scenes.append({"start": 1, "label": "", "marked": False})
    for k, sc in enumerate(scenes):
        sc["end"] = (scenes[k + 1]["start"] - 1) if k + 1 < len(scenes) else len(lines)
        block = lines[sc["start"] - 1:sc["end"]]
        sc["first_line"] = next((l.strip() for l in block if l.strip() and marker_label(l) is None), "")
        sc["words"] = count_words("\n".join(block))
    return scenes


def parse_sections(body):
    """{heading: text} from '## Heading' blocks (the '# Title' line is ignored)."""
    sections, current, buf = {}, None, []
    for line in body.split("\n"):
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip("\n")
            current, buf = line[3:].strip(), []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip("\n")
    return sections


def render_sections(title, sections):
    out = [f"# {title}"] if title else []
    for heading, text in sections.items():
        out += ["", f"## {heading}", "", text.strip("\n")]
    return "\n".join(out).strip("\n")


# --- universes ---------------------------------------------------------------------------------------------

def _global_boost():
    from . import settings
    try:
        return float(settings.load_global().get("atom_boost") or 1.5)
    except (TypeError, ValueError):
        return 1.5


class Universe:
    def __init__(self, slug):
        self.slug = slug
        self.path = universes_dir() / slug

    # --- its own file
    @property
    def file(self):
        return self.path / "universe.md"

    def _meta(self):
        if not self.file.exists():
            return {}, ""
        return frontmatter.loads(self.file.read_text(encoding="utf-8"))

    @property
    def name(self):
        return self._meta()[0].get("name") or self.slug.replace("-", " ").title()

    @property
    def notes(self):
        return self._meta()[1]

    def settings(self):
        """genres, exclude_tags, exclude_lists, boost, atom_boost, notes."""
        meta, body = self._meta()
        return {"name": meta.get("name") or self.name, "genres": list(meta.get("genres") or []),
                "exclude_tags": list(meta.get("exclude_tags") or []), "exclude_lists": list(meta.get("exclude_lists") or []),
                "boost": {k: float(v) for k, v in (meta.get("boost") or {}).items()},
                "atom_boost": float(meta.get("atom_boost") or _global_boost()), "atom_boost_own": bool(meta.get("atom_boost")),
                "notes": body, "created": meta.get("created", "")}

    def save_settings(self, **changes):
        """Save changes. `atom_boost` pins this universe's own boost; `atom_boost=None` goes back to your default (F4)."""
        s = self.settings()
        if "atom_boost" in changes:
            s["atom_boost_own"] = changes["atom_boost"] is not None
            if changes["atom_boost"] is None:
                changes = {k: v for k, v in changes.items() if k != "atom_boost"}
        s.update(changes)
        meta = {"name": s["name"], "genres": s["genres"], "exclude_tags": s["exclude_tags"],
                "exclude_lists": s["exclude_lists"], "boost": s["boost"],
                "created": s["created"] or datetime.date.today().isoformat()}
        if s["atom_boost_own"]:
            meta["atom_boost"] = s["atom_boost"]
        _write(self.file, frontmatter.dumps(meta, s["notes"]))

    def mix_dict(self):
        """This universe's mix in the same shape a story's mix has, for the generator."""
        s = self.settings()
        return {"base": [g.lower() for g in s["genres"]], "exclude_tags": list(s["exclude_tags"]),
                "exclude_lists": list(s["exclude_lists"]), "boost": dict(s["boost"])}

    @property
    def lists_dir(self):
        return self.path / "lists"

    # --- entities
    def _dir(self, type_):
        return self.path / schemas.get(type_)["folder"]

    def _entities_shared(self, type_=None):
        """The universe's entities, each read from disk only when its file has changed. The objects are SHARED: for looking,
        not for changing (entities() and entity() hand out copies)."""
        found = []
        for t in ([type_] if type_ else [t for t in schemas.load()]):
            folder = self._dir(t)
            if folder.is_dir():
                for p in sorted(folder.glob("*.md")):
                    def read(p=p):
                        return Entity.from_text(p.read_text(encoding="utf-8"), p)
                    try:
                        found.append(memo((str(p), "entity"), stamp(p), read))
                    except OSError:
                        continue
        return found

    def entities(self, type_=None):
        return [e.clone() for e in self._entities_shared(type_)]

    def entity(self, id_):
        for e in self._entities_shared():
            if e.id == id_:
                return e.clone()
        return None

    def find_by_name(self, name, type_=None):
        want = (name or "").strip().lower()
        return [e.clone() for e in self._entities_shared(type_) if e.name.strip().lower() == want and want]

    def _all_ids(self):
        return {e.id for e in self._entities_shared()}

    def new_entity(self, type_, name="", fields=None):
        """A new entity, saved at once. With no name it is blank (and gets a placeholder id like character-1)."""
        taken = self._all_ids()
        if name:
            id_ = _unique(entity_slug(name, type_), taken)
        else:
            n = 1
            while f"{type_}-{n}" in taken:
                n += 1
            id_ = f"{type_}-{n}"
        e = Entity(type_, id_, {f["key"]: ([] if f.get("kind") == "links" else "") for f in schemas.get(type_)["fields"]})
        e.fields.update(fields or {})
        if name:
            e.fields["name"] = name
        self.save_entity(e)
        return e

    def save_entity(self, e):
        """Write the entity. A placeholder id (character-1) becomes a real one the first time it has a name;
        links to it are rewritten, so nothing breaks."""
        if PLACEHOLDER.match(e.id) and e.name.strip():
            old = e.id
            new = _unique(entity_slug(e.name, e.type), self._all_ids() - {old})
            if new != old:
                old_path = self._dir(e.type) / f"{old}.md"
                e.id = new
                _write(self._dir(e.type) / f"{new}.md", e.to_text())
                if old_path.exists():
                    old_path.unlink()
                self.relink(old, new)
                e.path = self._dir(e.type) / f"{new}.md"
                return e
        e.path = self._dir(e.type) / f"{e.id}.md"
        _write(e.path, e.to_text())
        return e

    def delete_entity(self, e):
        """Move to the trash, and clear links that pointed at it."""
        trash(e.path or self._dir(e.type) / f"{e.id}.md")
        self.unlink(e.id)

    # --- links
    def link_fields(self, e):
        """[(key, kind)] of the entity's fields that hold ids."""
        return [(f["key"], f["kind"]) for f in schemas.get(e.type)["fields"] if f.get("kind") in ("link", "links")]

    def relink(self, old, new):
        for e in self.entities():
            changed = False
            for key, kind in self.link_fields(e):
                v = e.fields.get(key)
                if kind == "link" and v == old:
                    e.fields[key], changed = new, True
                elif kind == "links" and isinstance(v, list) and old in v:
                    e.fields[key], changed = [new if x == old else x for x in v], True
            if changed:
                _write(e.path, e.to_text())

    def unlink(self, id_):
        for e in self.entities():
            changed = False
            for key, kind in self.link_fields(e):
                v = e.fields.get(key)
                if kind == "link" and v == id_:
                    e.fields[key], changed = "", True
                elif kind == "links" and isinstance(v, list) and id_ in v:
                    e.fields[key], changed = [x for x in v if x != id_], True
            if changed:
                _write(e.path, e.to_text())

    def resolve(self, value, type_=None):
        """The entity a link field's value names (an id), or None if it's just text."""
        if not value or not isinstance(value, str):
            return None
        e = next((x for x in self._entities_shared() if x.id == value), None)
        return e if e and (type_ is None or e.type == type_) else None

    def links_from(self, e):
        """[(label, target entity or text)] this entity points at."""
        out = []
        for f in schemas.get(e.type)["fields"]:
            if f.get("kind") not in ("link", "links"):
                continue
            values = e.fields.get(f["key"]) or ([] if f["kind"] == "links" else "")
            for v in (values if isinstance(values, list) else [values]):
                if v:
                    out.append((f["label"], self.resolve(v) or v))
        return out

    def links_to(self, e):
        """[(label, entity)] of entities that point at this one."""
        out = []
        known = schemas.load()
        for other in self._entities_shared():
            if other.id == e.id:
                continue
            for f in known[other.type]["fields"] if other.type in known else ():
                v = other.fields.get(f["key"])
                if f.get("kind") == "link" and v == e.id or f.get("kind") == "links" and isinstance(v, list) and e.id in v:
                    out.append((f["label"], other))
        return out

    def appearances(self, e):
        """Stories that mention this entity: by name in the outline or manuscript, or recorded at promotion."""
        found = []
        for s in self.stories():
            stamp_ = stamp(s.outline_path, *s.files())
            if memo((str(s.path), "appears", e.id, e.name), stamp_, lambda s=s: self._mentions(s, e)):
                found.append(s)
        return found

    @staticmethod
    def _mentions(s, e):
        pat = re.compile(r"(?<![\w])" + re.escape(e.name) + r"(?:'s|’s)?(?![\w])", re.IGNORECASE) if e.name else None
        meta, sections = s.load_outline()
        recorded = e.id in (meta.get("cast") or [])
        text = "\n".join(sections.values()) + "\n" + s.manuscript_text()
        return bool(recorded or (pat and pat.search(text)))

    # --- stories
    def stories(self):
        folder = self.path / "stories"
        return [Story(self, p.name) for p in sorted(folder.iterdir()) if p.is_dir()] if folder.is_dir() else []

    def story(self, slug):
        s = Story(self, slug)
        return s if s.path.is_dir() else None

    def new_story(self, title, meta=None, sections=None, seed=None):
        taken = {s.slug for s in self.stories()}
        slug = _unique(slugify(title, "story"), taken)
        s = Story(self, slug)
        s.path.mkdir(parents=True, exist_ok=True)
        m = {"id": slug, "title": title, "universe": self.slug, "created": datetime.date.today().isoformat()}
        m.update(meta or {})
        s.save_outline(m, sections or {})
        _write(s.path / ".one-line-paragraphs", "one line = one paragraph\n")      # (new stories already follow the rule)
        _write(s.path / ".straight-quotes", "straight quotes in the manuscript; the export makes them curly\n")
        if seed is not None:
            _write(s.path / "seed.json", json.dumps(seed, indent=2))
        return s

    def delete(self):
        return trash(self.path)


# --- universes: listing and creating --------------------------------------------------------------------------

def list_universes():
    base = universes_dir()
    if not base.is_dir():
        return []
    return [Universe(p.name) for p in sorted(base.iterdir()) if p.is_dir() and not p.name.startswith(".")]


def get_universe(slug):
    u = Universe(slug)
    return u if u.path.is_dir() else None


def create_universe(name, genres=(), notes=""):
    taken = {u.slug for u in list_universes()}
    u = Universe(_unique(slugify(name, "universe"), taken))
    u.path.mkdir(parents=True, exist_ok=True)
    u.save_settings(name=name, genres=[g.lower() for g in genres], notes=notes)
    for t in schemas.load():
        u._dir(t).mkdir(exist_ok=True)
    (u.path / "stories").mkdir(exist_ok=True)
    return u


def rename_universe(universe, new_name):
    """Changes the universe's name (its folder, and so every link, stays as it is)."""
    universe.save_settings(name=new_name)
    return universe
