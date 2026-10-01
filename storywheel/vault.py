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


def _write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)                       # replace in one step: a crash never leaves half a file


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

    @property
    def name(self):
        return self.fields.get("name", "")

    def get(self, key, default=""):
        return self.fields.get(key, default)

    def __repr__(self):
        return f"Entity({self.type}, {self.id!r}, {self.name!r})"

    def to_text(self):
        meta = {"id": self.id, "type": self.type}
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
        e = cls(type_, meta.get("id") or (Path(path).stem if path else ""), fields, meta.get("custom") or {},
                "" if any(f.get("body") for f in sch["fields"]) else body, meta.get("created"))
        e.path = Path(path) if path else None
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
        if not self.outline_path.exists():
            return {}, {}
        meta, body = frontmatter.loads(self.outline_path.read_text(encoding="utf-8"))
        return meta, parse_sections(body)

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

    def seed(self):
        p = self.path / "seed.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def manuscript_text(self):
        return "\n\n".join(p.read_text(encoding="utf-8").strip("\n") for p in self.scenes())

    def word_count(self):
        return sum(len(p.read_text(encoding="utf-8").split()) for p in self.scenes())

    def add_scene(self, title="", text=""):
        """A new scene file at the end: 03-the-letter.md."""
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
                "atom_boost": float(meta.get("atom_boost", 3.0) or 3.0), "notes": body,
                "created": meta.get("created", "")}

    def save_settings(self, **changes):
        s = self.settings()
        s.update(changes)
        meta = {"name": s["name"], "genres": s["genres"], "exclude_tags": s["exclude_tags"],
                "exclude_lists": s["exclude_lists"], "boost": s["boost"], "atom_boost": s["atom_boost"],
                "created": s["created"] or datetime.date.today().isoformat()}
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

    def entities(self, type_=None):
        found = []
        for t in ([type_] if type_ else [t for t in schemas.load()]):
            folder = self._dir(t)
            if folder.is_dir():
                for p in sorted(folder.glob("*.md")):
                    try:
                        found.append(Entity.from_text(p.read_text(encoding="utf-8"), p))
                    except OSError:
                        continue
        return found

    def entity(self, id_):
        for e in self.entities():
            if e.id == id_:
                return e
        return None

    def find_by_name(self, name, type_=None):
        want = (name or "").strip().lower()
        return [e for e in self.entities(type_) if e.name.strip().lower() == want and want]

    def _all_ids(self):
        return {e.id for e in self.entities()}

    def new_entity(self, type_, name="", fields=None):
        """A new entity, saved at once. With no name it is blank (and gets a placeholder id like character-1)."""
        taken = self._all_ids()
        if name:
            id_ = _unique(slugify(name), taken)
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
            new = _unique(slugify(e.name), self._all_ids() - {old})
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
        e = self.entity(value)
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
        for other in self.entities():
            if other.id == e.id:
                continue
            for f in schemas.get(other.type)["fields"]:
                v = other.fields.get(f["key"])
                if f.get("kind") == "link" and v == e.id or f.get("kind") == "links" and isinstance(v, list) and e.id in v:
                    out.append((f["label"], other))
        return out

    def appearances(self, e):
        """Stories that mention this entity: by name in the outline or manuscript, or recorded at promotion."""
        found = []
        pat = re.compile(r"(?<![\w])" + re.escape(e.name) + r"(?:'s|’s)?(?![\w])", re.IGNORECASE) if e.name else None
        for s in self.stories():
            meta, sections = s.load_outline()
            recorded = e.id in (meta.get("cast") or [])
            text = "\n".join(sections.values()) + "\n" + s.manuscript_text()
            if recorded or (pat and pat.search(text)):
                found.append(s)
        return found

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
