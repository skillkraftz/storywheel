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

GLOBAL_DEFAULTS = {
    "author_name": "", "legal_name": "", "address": "", "email": "", "phone": "",
    "font": "Times New Roman", "format": "short-story", "daily_goal": 500, "column_width": 72,
}
STORY_DEFAULTS = {
    "format": "short-story", "font": "Times New Roman", "column_width": 72, "daily_goal": 500,
    "title_keyword": "", "indent_display": True, "typewriter": False, "invisibles": False,
    "spellcheck": False, "scene_goal": 0,
}


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
    merged = dict(GLOBAL_DEFAULTS, **{k: v for k, v in values.items() if k in GLOBAL_DEFAULTS or True})
    path.write_text(dump_toml(merged, "storywheel settings: who you are, and defaults for new stories."),
                    encoding="utf-8")
    return path


def load_story(story_dir):
    """A story's settings: its own file over your global defaults over the built-in ones."""
    g = load_global()
    base = dict(STORY_DEFAULTS)
    for key in ("format", "font", "column_width", "daily_goal"):
        if key in g and g[key] not in ("", None):
            base[key] = g[key]
    return _load(Path(story_dir) / "settings.toml", base)


def save_story(story_dir, values):
    path = Path(story_dir) / "settings.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_toml(dict(STORY_DEFAULTS, **values), "this story's settings"), encoding="utf-8")
    return path


def surname(settings):
    """For the manuscript header: an explicit `surname`, else the last word of the author name."""
    if settings.get("surname"):
        return settings["surname"]
    name = (settings.get("legal_name") or settings.get("author_name") or "").split()
    return name[-1] if name else "Author"
