"""
Markdown files with YAML frontmatter, read and written without a YAML library.

    ---
    id: "stacie-anderson"
    name: "Stacie Anderson"
    age: 34
    members: ["a", "b"]
    custom:
      eye colour: "grey"
    ---
    Free-form notes go here.

Only the shapes storywheel uses are supported: scalars (text, numbers, true/false), flat lists,
and one level of nested key/value ("custom"). Text is written in double quotes (valid YAML, so
Obsidian reads it); hand-written plain values like `age: 34` or `role: rival` are read too.
"""
import json
import re

_KEY = re.compile(r"^([^\s:][^:]*?):(?:\s+(.*))?$")


def _scalar(text):
    text = text.strip()
    if text == "" or text in ("~", "null"):
        return ""
    if text[0] in '"[':
        try:
            return json.loads(text)
        except ValueError:
            pass
    if text[0] == "[":                                  # [a, b] written by hand, unquoted
        inner = text.strip("[]").strip()
        return [x.strip().strip("'\"") for x in inner.split(",")] if inner else []
    if text[0] == "'" and text[-1] == "'":
        return text[1:-1].replace("''", "'")
    if text in ("true", "false"):
        return text == "true"
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def _dump_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def dumps(meta, body=""):
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, dict):
            lines.append(f"{key}:" if value else f"{key}: {{}}")
            for k, v in value.items():
                lines.append(f"  {k}: {_dump_scalar(v)}")
        else:
            lines.append(f"{key}: {_dump_scalar(value)}")
    lines.append("---")
    text = "\n".join(lines) + "\n"
    body = body.strip("\n")
    return text + ("\n" + body + "\n" if body else "")


def loads(text):
    """(meta dict, body) from a markdown file's text. No frontmatter means ({}, whole text)."""
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, text
    meta, current = {}, None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")) and current is not None and isinstance(meta.get(current), dict):
            m = _KEY.match(line.strip())
            if m:
                meta[current][m.group(1).strip()] = _scalar(m.group(2) or "")
            continue
        m = _KEY.match(line)
        if not m:
            continue
        key, rest = m.group(1).strip(), m.group(2)
        if rest is None or rest.strip() == "":
            meta[key] = {}                      # a block follows (or an empty value)
            current = key
        elif rest.strip() == "{}":
            meta[key], current = {}, None
        else:
            meta[key], current = _scalar(rest), None
    for key, value in list(meta.items()):        # an empty block with no children was just an empty value
        if value == {} and key not in ("custom",):
            meta[key] = ""
    return meta, "\n".join(lines[end + 1:]).strip("\n")
