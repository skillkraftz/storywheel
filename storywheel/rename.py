"""
Renaming an entity, and finding the old name everywhere else.

`find_matches` lists every whole-word use of the old name (possessives like "Stacie's" count) in this
universe's entity files, its story outlines and its manuscripts, with some context. Nothing changes until
`apply_matches` is given the ones you accepted. The entity's id never changes, so links are untouched.
"""
import re
from pathlib import Path

from . import vault


class Match:
    def __init__(self, path, kind, label, index, line_no, context):
        self.path, self.kind, self.label = Path(path), kind, label
        self.index = index                  # the nth match in that file
        self.line_no, self.context = line_no, context
        self.accepted = True

    def __repr__(self):
        return f"Match({self.label}:{self.line_no} #{self.index})"


def _pattern(old):
    # whole word; "Stacie's" (straight or curly apostrophe) matches "Stacie" and keeps its 's
    return re.compile(r"(?<![\w])" + re.escape(old) + r"(?=(?:['’]s)?(?![\w]))")


def _files(universe, entity):
    """(path, kind, label) for everything that may mention a name."""
    out = [(universe.file, "universe", "universe notes")]
    for e in universe.entities():
        out.append((e.path, "entity", f"{e.type}: {e.name or e.id}"))
    for s in universe.stories():
        out.append((s.outline_path, "outline", f"outline: {s.title}"))
        for p in s.files():
            out.append((p, "manuscript", f"manuscript: {s.title} / {p.name}"))
    return [(p, k, l) for p, k, l in out if p and Path(p).exists()]


def _skippable(line, entity, path):
    """The entity's own id and name lines are not text to rewrite (the name is changed separately)."""
    if entity.path and Path(path) == Path(entity.path):
        return line.startswith(("id:", "name:", "created:", "type:"))
    return line.startswith(("id:", "type:", "created:"))


def find_matches(universe, entity, old=None):
    old = (old or entity.name).strip()
    if not old:
        return []
    pat = _pattern(old)
    found = []
    for path, kind, label in _files(universe, entity):
        text = Path(path).read_text(encoding="utf-8")
        index = 0
        for n, line in enumerate(text.split("\n"), 1):
            if _skippable(line, entity, path):
                continue
            for m in pat.finditer(line):
                a, b = max(0, m.start() - 30), min(len(line), m.end() + 30)
                found.append(Match(path, kind, label, index, n, ("…" if a else "") + line[a:b] + ("…" if b < len(line) else "")))
                index += 1
    return found


def apply_matches(universe, entity, old, new, matches):
    """Replace the accepted matches. Returns the number replaced. Files are rewritten whole, one at a time."""
    pat = _pattern(old)
    by_file = {}
    for m in matches:
        if m.accepted:
            by_file.setdefault(m.path, set()).add(m.index)
    total = 0
    for path, wanted in by_file.items():
        lines = Path(path).read_text(encoding="utf-8").split("\n")
        index = 0
        for i, line in enumerate(lines):
            if _skippable(line, entity, path):
                continue
            def repl(m, _wanted=wanted):
                nonlocal index, total
                keep = index not in _wanted
                index += 1
                if keep:
                    return m.group(0)
                total += 1
                return new
            lines[i] = pat.sub(repl, line)
        vault._write(path, "\n".join(lines))
    return total


def rename_entity(universe, entity, new_name, matches=None):
    """Change the name, and rewrite the accepted matches (None = none; the preview decides)."""
    old = entity.name
    entity.fields["name"] = new_name
    universe.save_entity(entity)
    n = apply_matches(universe, entity, old, new_name, matches or [])
    return n
