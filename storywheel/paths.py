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


def library_root():
    """Where universes live: plain folders of markdown you can open in Obsidian.
    STORYWHEEL_LIBRARY wins, then `library = "..."` in ~/.storywheel/settings.toml (the Settings mode, F4), then the default."""
    env = os.environ.get("STORYWHEEL_LIBRARY")
    if env:
        return Path(env)
    try:
        import re
        text = (home() / "settings.toml").read_text(encoding="utf-8")
        m = re.search(r'^library\s*=\s*"((?:[^"\\]|\\.)*)"', text, re.M)
        if m and m.group(1).strip():
            return Path(m.group(1).encode().decode("unicode_escape")).expanduser()
    except OSError:
        pass
    return default_library()


def default_library():
    return Path.home() / "Writing" / "storywheel"
