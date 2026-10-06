"""
A story's outline as readable rows, and editing one row at a time.

story.md keeps the outline as markdown (a title, then `## Premise`, `## Setting` as `- **Place:** ...` lines, a
`## <Structure>` section with one paragraph per beat, `## Twist`). The Builder shows it as plain text, the way the Wheel
shows "the story so far": no markdown marks, no list dashes, one beat per paragraph, no label repeating what the
sentence already says. Each row can be edited on its own and is written back in the same markdown.
"""
import re

from . import structures

BEAT = re.compile(r"\*\*(.+?)\.\*\*\s*(.*)", re.S)
SETTING = re.compile(r"^\s*-\s*\*\*(.+?):\*\*\s*(.*)$")


def plain(text):
    """Text without markdown marks (for showing)."""
    return text.replace("**", "").replace("__", "")


def is_beat_section(heading):
    return heading in {s.label for s in structures.registry().values()}


def beats(text):
    """[(label or None, text)] for a beats section: one paragraph each; a leading `**Label.**` is the label."""
    out = []
    for para in re.split(r"\n\s*\n", text.strip()):
        para = " ".join(para.split())
        if not para:
            continue
        m = BEAT.match(para)
        out.append((m.group(1), m.group(2)) if m else (None, para))
    return out


def beat_label(heading, i, label, body):
    """What to put beside a beat: its stored label, unless the sentence already says it; else its number."""
    if label and not body.lower().startswith(label.lower().rstrip(".")):
        return label
    return f"{i + 1}."


def blank_beats(shape):
    """A structure's beats section with nothing written yet: each beat's label (or, for a structure whose openers say where you are, the
    opener), one paragraph each, so the Outline shows every beat to fill in."""
    paras = []
    for b in shape.expand({}):
        if shape.show_labels or not b.opening.strip():
            paras.append(f"**{b.label}.**")
        else:
            paras.append(b.opening.strip() + " …")
    return "\n\n".join(paras)


def settings_lines(text):
    return [(m.group(1), m.group(2)) for m in (SETTING.match(l) for l in text.splitlines()) if m]


def rows(story):
    """[(key, label, text)] in reading order."""
    meta, sections = story.load_outline()
    out = [("meta:title", "Title", meta.get("title", "")),
           ("meta:genre", "Genre", " · ".join(x for x in (meta.get("genre"), meta.get("mood")) if x)),
           ("meta:structure", "Structure", meta.get("structure", ""))]
    for heading, text in sections.items():
        if heading == "Setting":
            for name, value in settings_lines(text):
                out.append((f"setting:{name}", name, plain(value)))
        elif is_beat_section(heading):
            for i, (label, body) in enumerate(beats(text)):
                out.append((f"beat:{heading}:{i}", beat_label(heading, i, label, body), plain(body)))
        else:
            out.append((f"section:{heading}", heading, plain(text).replace("\n\n", "\n")))
    return out


def raw(story, key):
    """The text to put in the edit box for a row."""
    meta, sections = story.load_outline()
    kind, _, rest = key.partition(":")
    if kind == "meta":
        return meta.get(rest, "")
    if kind == "section":
        return sections.get(rest, "")
    if kind == "setting":
        return next((v for n, v in settings_lines(sections.get("Setting", "")) if n == rest), "")
    if kind == "beat":
        heading, _, i = rest.rpartition(":")
        items = beats(sections.get(heading, ""))
        return items[int(i)][1] if int(i) < len(items) else ""
    return ""


def save(story, key, text):
    """Write an edited row back into story.md."""
    text = text.strip()
    meta, sections = story.load_outline()
    kind, _, rest = key.partition(":")
    if kind == "meta":
        story.set_meta(**{rest: text})
    elif kind == "section":
        story.set_section(rest, text)
    elif kind == "setting":
        lines = []
        for line in sections.get("Setting", "").splitlines():
            m = SETTING.match(line)
            lines.append(f"- **{m.group(1)}:** {text}" if m and m.group(1) == rest else line)
        story.set_section("Setting", "\n".join(lines))
    elif kind == "beat":
        heading, _, i = rest.rpartition(":")
        items = beats(sections.get(heading, ""))
        i = int(i)
        label = items[i][0]
        items[i] = (label, text)
        story.set_section(heading, "\n\n".join((f"**{l}.** {b}" if l else b) for l, b in items))


# --- repeatable beats (a structure can mark a beat that occurs several times: see structures.py) ------------------------------------------

def parse_repeats(text):
    """'because_2=2,trials=3' -> {'because_2': 2, 'trials': 3}"""
    out = {}
    for part in (text or "").split(","):
        key, _, n = part.strip().partition("=")
        if key and n.strip().isdigit():
            out[key] = int(n)
    return out


def format_repeats(counts, shape):
    return ",".join(f"{k}={n}" for k, n in sorted(counts.items()) if n > shape.beat(k).min)


def beat_plan(story):
    """(structure, [Beat in order, one per paragraph], [(label, text)], heading) for a story whose beats section matches its structure, else None.
    A story promoted before beats could repeat has the minimum of each; one with a single repeatable beat is read from its paragraph count."""
    meta, sections = story.load_outline()
    shape = next((s for s in structures.registry().values() if s.label == meta.get("structure")), None)
    if shape is None or shape.label not in sections:
        return None
    items = beats(sections[shape.label])
    counts = shape.counts(parse_repeats(meta.get("repeats")))
    expanded = shape.expand(counts)
    if len(expanded) != len(items):
        repeatable = shape.repeatable
        extra = len(items) - len(shape.expand({}))
        if len(repeatable) == 1 and extra >= 0 and repeatable[0].min + extra <= repeatable[0].max:
            expanded = shape.expand({repeatable[0].key: repeatable[0].min + extra})
        if len(expanded) != len(items):
            return None
    return shape, expanded, items, shape.label


def _beat_index(key):
    kind, _, rest = key.partition(":")
    if kind != "beat":
        return None
    return int(rest.rpartition(":")[2])


def beat_at(story, key):
    """(beat occurrence, index) for a `beat:` row key, or None."""
    plan = beat_plan(story)
    i = _beat_index(key)
    if plan is None or i is None or i >= len(plan[1]):
        return None
    return plan[1][i], i


def can_add(story, key):
    got = beat_at(story, key)
    if not got:
        return False
    shape, expanded, _items, _h = beat_plan(story)
    base = shape.beat(got[0].key)
    return bool(base and base.repeat and sum(1 for b in expanded if structures.base_key(b.key) == base.key) < base.max)


def can_remove(story, key):
    got = beat_at(story, key)
    if not got:
        return False
    shape, expanded, _items, _h = beat_plan(story)
    base = shape.beat(got[0].key)
    return bool(base and base.repeat and sum(1 for b in expanded if structures.base_key(b.key) == base.key) > base.min)


def _write_beats(story, shape, expanded, items):
    counts = {}
    for b in expanded:
        counts[structures.base_key(b.key)] = counts.get(structures.base_key(b.key), 0) + 1
    repeats = {k: n for k, n in counts.items() if shape.beat(k).repeat}
    story.set_section(shape.label, "\n\n".join((f"**{l}.** {t}" if l else t) for l, t in items))
    story.set_meta(repeats=format_repeats(repeats, shape))


def add_beat(story, key, make_text):
    """Add another of the repeatable beat the row `key` belongs to, after the last of its kind. `make_text(beat, texts)` gives the new
    paragraph (the Builder rolls one with the generator). Returns the new row's key, or None."""
    if not can_add(story, key):
        return None
    shape, expanded, items, heading = beat_plan(story)
    beat = expanded[_beat_index(key)]
    base = shape.beat(beat.key)
    last = max(i for i, b in enumerate(expanded) if structures.base_key(b.key) == base.key)
    n = sum(1 for b in expanded if structures.base_key(b.key) == base.key) + 1
    new_beat = base.instance(n, numbered=shape.show_labels)
    text = make_text(new_beat, [t for _l, t in items]).strip()
    label = new_beat.label if shape.show_labels else None
    expanded = expanded[:last + 1] + [new_beat] + expanded[last + 1:]
    items = items[:last + 1] + [(label, text)] + items[last + 1:]
    _write_beats(story, shape, expanded, items)
    return f"beat:{heading}:{last + 1}"


def remove_beat(story, key):
    """Take out the paragraph of the row `key` (an occurrence of a repeatable beat); later ones are renumbered. Returns True."""
    if not can_remove(story, key):
        return False
    shape, expanded, items, _heading = beat_plan(story)
    i = _beat_index(key)
    base = shape.beat(expanded[i].key)
    expanded = expanded[:i] + expanded[i + 1:]
    items = items[:i] + items[i + 1:]
    n = 0
    for j, b in enumerate(expanded):                              # renumber the labels of what is left of that beat
        if structures.base_key(b.key) == base.key:
            n += 1
            inst = base.instance(n, numbered=shape.show_labels)
            expanded[j] = inst
            if shape.show_labels:
                items[j] = (inst.label, items[j][1])
    _write_beats(story, shape, expanded, items)
    return True


def roll_beat(story, universe, filler, beat, texts):
    """A new paragraph for `beat`, rolled with the generator for this universe and story: the protagonist and setting come from the
    universe's entities, the genre from the outline. (Threads are not carried: in the Builder they are entities.)"""
    from . import steps, store
    from .mix import sync_base
    meta, sections = story.load_outline()
    pseudo = filler._pseudo_story()
    pseudo["kept"] = {"genre": {"genre": meta.get("genre") or " / ".join(universe.settings().get("genres", [])) or "", "mood": meta.get("mood", "")}}
    pseudo["kept"]["structure"] = {"structure": meta.get("structure", "")}
    sync_base(pseudo)
    pro = next((e for e in universe.entities("character") if str(e.fields.get("role", "")).lower() == "protagonist"), None)
    if pro is not None and pro.name:
        kept = {}
        for k in ("name", "age", "job", "trait", "want", "need", "flaw", "secret", "rival"):
            value = str(pro.fields.get(k, "") or "").strip()
            if k == "rival" and value:
                target = universe.resolve(value)                # a link to a character: use its name
                value = target.name if target is not None else value
            if value:
                kept[k] = value                                 # an empty field is left out: a frame that needs it gets a stand-in
        pseudo["kept"]["protagonist"] = kept
    shape = structures.get(meta.get("structure"))
    step = steps.spine_step(shape)
    if "mix" in pseudo and not pseudo["mix"].get("base"):
        pseudo["mix"]["base"] = [g for g in (universe.settings().get("genres") or [])]
    field = shape.beat(beat.key).key
    value, _introduced, _atoms = step.reroll_value(filler.engine, pseudo, {k: "" for k in step.fields}, field, {})
    return value
