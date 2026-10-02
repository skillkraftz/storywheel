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
