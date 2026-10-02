"""
Settings in TOML: global ones in ~/.storywheel/settings.toml (who you are, defaults), and per-story
ones in <story>/settings.toml (format, goals, how the Writer looks).

TOML is read with the standard library where there is one (Python 3.11+) and with a small reader
here otherwise; both understand what is written here: strings, numbers, true/false, and [sections].
"""
import json
import re
from pathlib import Path

from . import paths

# What you are (once, for everything) and defaults for every story. A story can override any of the story ones in its
# own settings.toml. The Settings mode (F4) edits this file.
GLOBAL_DEFAULTS = {
    "author_name": "", "legal_name": "", "surname": "", "address": "", "email": "", "phone": "",
    "font": "Times New Roman", "format": "short-story", "export_format": "docx",
    "daily_goal": 500, "column_width": 72,
    "indent_display": True, "typewriter": False, "invisibles": False, "spellcheck": False,
    "notepad_mode": True, "neovide": False, "writer_font": "", "writer_font_size": 15, "line_spacing": 12,
    "paragraph_spacing": 0,
    "scene_marker": "***",
    "export_title_bold": True, "export_header": "full", "export_anonymous": False, "export_one_space": False,
    "key_italic": "<A-i>", "key_bold": "<A-b>", "key_scene_break": "<A-s>", "key_menu": "<F12>", "key_sidebar": "<F9>",
    "key_peek": "<F8>", "key_builder": "<C-q>", "key_replace": "<C-h>",
    "atom_boost": 1.5,
}
STORY_DEFAULTS = {
    "format": "short-story", "font": "Times New Roman", "column_width": 72, "daily_goal": 500,
    "title_keyword": "", "indent_display": True, "typewriter": False, "invisibles": False,
    "spellcheck": False, "scene_goal": 0,
    "notepad_mode": True, "neovide": False, "writer_font": "", "writer_font_size": 15, "line_spacing": 12,
    "paragraph_spacing": 0,
    "scene_marker": "***",
    "export_title_bold": True, "export_header": "full", "export_anonymous": False, "export_one_space": False,
    "key_italic": "<A-i>", "key_bold": "<A-b>", "key_scene_break": "<A-s>", "key_menu": "<F12>", "key_sidebar": "<F9>",
    "key_peek": "<F8>", "key_builder": "<C-q>", "key_replace": "<C-h>",
}
# story settings that fall back to your global settings
INHERITED = ("format", "font", "column_width", "daily_goal", "indent_display", "typewriter", "invisibles", "spellcheck",
             "notepad_mode", "neovide", "writer_font", "writer_font_size", "line_spacing", "paragraph_spacing",
             "scene_marker", "export_title_bold", "export_header", "export_anonymous", "export_one_space",
             "key_italic", "key_bold", "key_scene_break", "key_menu", "key_sidebar", "key_peek", "key_builder", "key_replace")


def _mini_parse(text):
    data = {}
    target = data
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.fullmatch(r"\[([A-Za-z0-9_.-]+)\]", line)
        if m:
            target = data.setdefault(m.group(1), {})
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip().strip('"'), value.strip()
        if value.startswith('"') or value.startswith("["):
            # strip a trailing comment that follows the closing quote / bracket
            try:
                target[key] = json.loads(value)
                continue
            except ValueError:
                value = re.sub(r"\s+#.*$", "", value)
                try:
                    target[key] = json.loads(value)
                    continue
                except ValueError:
                    pass
        value = re.sub(r"\s+#.*$", "", value)
        if value in ("true", "false"):
            target[key] = value == "true"
        elif re.fullmatch(r"-?\d+", value):
            target[key] = int(value)
        elif re.fullmatch(r"-?\d+\.\d+", value):
            target[key] = float(value)
        elif value.startswith("'") and value.endswith("'"):
            target[key] = value[1:-1]
        else:
            target[key] = value.strip('"')
    return data


def parse_toml(text):
    try:
        import tomllib
        return tomllib.loads(text)
    except ImportError:
        return _mini_parse(text)
    except Exception:                       # a hand-edit slip: read what we can
        return _mini_parse(text)


def _toml_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return json.dumps(v, ensure_ascii=False)          # a JSON string is a valid TOML basic string


def dump_toml(data, header=""):
    lines = [f"# {l}" for l in header.splitlines()] if header else []
    flat = {k: v for k, v in data.items() if not isinstance(v, dict)}
    for k, v in flat.items():
        lines.append(f"{k} = {_toml_value(v)}")
    for k, sub in ((k, v) for k, v in data.items() if isinstance(v, dict)):
        lines += ["", f"[{k}]"] + [f"{kk} = {_toml_value(vv)}" for kk, vv in sub.items()]
    return "\n".join(lines) + "\n"


def _load(path, defaults):
    out = dict(defaults)
    path = Path(path)
    if path.exists():
        try:
            out.update(parse_toml(path.read_text(encoding="utf-8")))
        except OSError:
            pass
    return out


def global_path():
    return paths.home() / "settings.toml"


def load_global():
    return _load(global_path(), GLOBAL_DEFAULTS)


def save_global(values):
    path = global_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    keep = {k: v for k, v in _load(path, {}).items()} if path.exists() else {}     # keys we don't know (library = ...) stay
    merged = dict(GLOBAL_DEFAULTS, **keep)
    merged.update(values)
    path.write_text(dump_toml(merged, "storywheel settings: who you are, and defaults for new stories."),
                    encoding="utf-8")
    return path


def load_story(story_dir):
    """A story's settings: its own file over your global defaults over the built-in ones."""
    g = load_global()
    base = dict(STORY_DEFAULTS)
    for key in INHERITED:
        if key in g and g[key] is not None and (g[key] != "" or key == "writer_font"):
            base[key] = g[key]
    return _load(Path(story_dir) / "settings.toml", base)


def save_story(story_dir, values):
    """Save the story's own settings: only what it sets itself (what it doesn't set follows your defaults)."""
    path = Path(story_dir) / "settings.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    own = _load(path, {}) if path.exists() else {}
    own.update(values)
    path.write_text(dump_toml(own, "this story's settings (anything missing follows your defaults in ~/.storywheel/settings.toml)"),
                    encoding="utf-8")
    return path


def surname(settings):
    """For the manuscript header: an explicit `surname`, else the last word of the author name."""
    if settings.get("surname"):
        return settings["surname"]
    name = (settings.get("legal_name") or settings.get("author_name") or "").split()
    return name[-1] if name else "Author"
