"""Where things live. Override with environment variables:

    STORYWHEEL_HOME  stories, universe and your own lists  (~/.storywheel)
    STORYWHEEL_OUT   where markdown goes, e.g. your vault  (~/storywheel)
    STORYWHEEL_LIBRARY  universes, entities, stories, manuscripts  (~/Writing/storywheel)

HOME and OUT are fixed when the program starts. The library and the functions below read the
environment each time they are called, so tests (and you) can point them somewhere else.
"""
import os
from pathlib import Path

HOME = Path(os.environ.get("STORYWHEEL_HOME", Path.home() / ".storywheel"))
OUT = Path(os.environ.get("STORYWHEEL_OUT", Path.home() / "storywheel"))


def home():
    """App storage: drafts, state.json, settings.toml, ratings, nvim state."""
    return Path(os.environ.get("STORYWHEEL_HOME", Path.home() / ".storywheel"))


def machine_setting(key):
    """A text setting that belongs to this machine: settings.local.toml, else (an older install) settings.toml."""
    import re
    for name in ("settings.local.toml", "settings.toml"):
        try:
            text = (home() / name).read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.search(r'^%s\s*=\s*"((?:[^"\\]|\\.)*)"' % re.escape(key), text, re.M)
        if m and m.group(1).strip():
            return m.group(1).encode().decode("unicode_escape")
    return ""


def library_root():
    """Where universes live: plain folders of markdown you can open in Obsidian.
    STORYWHEEL_LIBRARY wins, then `library = "..."` in ~/.storywheel/settings.toml (the Settings mode, F4), then the default."""
    env = os.environ.get("STORYWHEEL_LIBRARY")
    if env:
        return Path(env)
    value = machine_setting("library")
    return Path(value).expanduser() if value else default_library()


def manuscripts_root():
    """Where exported manuscripts go, one folder per story: STORYWHEEL_MANUSCRIPTS, then `manuscripts_dir = "..."` in
    ~/.storywheel/settings.toml (Settings > Export), then ~/Writing. The library's own layout is not touched."""
    env = os.environ.get("STORYWHEEL_MANUSCRIPTS")
    if env:
        return Path(env).expanduser()
    value = machine_setting("manuscripts_dir")
    return Path(value).expanduser() if value else Path.home() / "Writing"


def tilde(path):
    """A path as it is shown in messages: ~/Writing/... instead of /home/andy/Writing/..."""
    p = str(path)
    h = str(Path.home())
    return "~" + p[len(h):] if p == h or p.startswith(h + os.sep) else p


def default_library():
    return Path.home() / "Writing" / "storywheel"
