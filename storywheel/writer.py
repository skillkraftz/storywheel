"""
The Writer: Neovim, set up as a full-screen writing room (config shipped in storywheel/nvim/).

    nvim_config()      where the config lives (installed or linked under ~/.storywheel/nvim/ on first run)
    command(story)     the argv + environment to run Neovim on a story
    run(story)         run it, and say where the writer wants to go next ("builder", "wheel" or None)

Neovim runs with NVIM_APPNAME=storywheel-writer and its own XDG folders under ~/.storywheel/nvim/, so it never
touches a personal Neovim setup. The Lua side gets story details from `storywheel story show ... --json`.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import paths

APPNAME = "storywheel-writer"
PACKAGE_CONFIG = Path(__file__).parent / "nvim"
MIN_NVIM = (0, 10)


class WriterError(Exception):
    pass


def nvim_exe():
    return shutil.which(os.environ.get("STORYWHEEL_NVIM", "nvim"))


def nvim_version(exe=None):
    exe = exe or nvim_exe()
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10).stdout
        first = out.splitlines()[0]                                   # NVIM v0.11.6
        nums = first.split("v")[1].split("-")[0].split(".")
        return tuple(int(n) for n in nums[:3])
    except (OSError, IndexError, ValueError, subprocess.SubprocessError):
        return None


def check():
    """A plain message if the Writer can't run here, else None."""
    exe = nvim_exe()
    if not exe:
        return "Neovim isn't installed (the Writer needs Neovim 0.10 or newer: install it with your package manager)."
    version = nvim_version(exe)
    if version is None or version < MIN_NVIM:
        have = ".".join(map(str, version)) if version else "unknown"
        return f"The Writer needs Neovim 0.10 or newer; this is {have}."
    return None


def state_root():
    return paths.home() / "nvim"


def nvim_config():
    """The config folder Neovim will use as XDG_CONFIG_HOME/<APPNAME>: a link to the package's, or a copy where
    links aren't possible. Returns the XDG_CONFIG_HOME folder."""
    xdg = state_root() / "config"
    target = xdg / APPNAME
    xdg.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        if Path(os.readlink(target)) == PACKAGE_CONFIG:
            return xdg
        target.unlink()
    elif target.exists():
        if (target / ".copied-from").exists():          # a copy (where links weren't possible): keep it current
            _refresh_copy(target)
        return xdg
    try:
        target.symlink_to(PACKAGE_CONFIG, target_is_directory=True)
    except OSError:
        shutil.copytree(PACKAGE_CONFIG, target)
        (target / ".copied-from").write_text(str(PACKAGE_CONFIG))
    return xdg


def _refresh_copy(target):
    shutil.rmtree(target)
    shutil.copytree(PACKAGE_CONFIG, target)
    (target / ".copied-from").write_text(str(PACKAGE_CONFIG))


def environment(story, return_file):
    story.migrate_manuscript()
    story.migrate_paragraphs()
    xdg = nvim_config()
    env = dict(os.environ)
    root = state_root()
    env.update({
        "NVIM_APPNAME": APPNAME,
        "XDG_CONFIG_HOME": str(xdg), "XDG_DATA_HOME": str(root / "data"),
        "XDG_STATE_HOME": str(root / "state"), "XDG_CACHE_HOME": str(root / "cache"),
        "STORYWHEEL_STORY_DIR": str(story.path), "STORYWHEEL_UNIVERSE": story.universe.slug,
        "STORYWHEEL_STORY": story.slug, "STORYWHEEL_PY": sys.executable,
        "STORYWHEEL_RETURN_FILE": str(return_file),
        "STORYWHEEL_HOME": str(paths.home()), "STORYWHEEL_LIBRARY": str(paths.library_root()),
    })
    for d in ("data", "state", "cache"):
        (root / d).mkdir(parents=True, exist_ok=True)
    return env


def neovide_exe():
    return shutil.which(os.environ.get("STORYWHEEL_NEOVIDE", "neovide"))


def launch(story, return_file=None):
    """(argv, env, note): how to start the Writer, honoring the neovide setting. `note` is a plain message when
    Neovide was asked for but isn't installed (the terminal is used instead), else None."""
    from . import settings
    argv, env = command(story, return_file)
    note = None
    if settings.load_story(story.path).get("neovide"):
        exe = neovide_exe()
        if exe:
            argv = [exe, "--no-fork"]                 # wait for the window to close, like the terminal Neovim does
            env["STORYWHEEL_GUI"] = "neovide"
        else:
            note = ("Neovide isn't installed, so the Writer opened in the terminal. "
                    "Install Neovide, or turn 'Use Neovide' off in Settings (F4).")
    return argv, env, note


def neovide_note(story):
    """The message to show if Neovide is wanted but not installed, else None."""
    return launch(story)[2]


def command(story, return_file=None):
    """(argv, env) to start the Writer on a story. Neovim opens the story's current scene itself."""
    return_file = Path(return_file or (state_root() / "return"))
    argv = [nvim_exe() or "nvim"]
    return argv, environment(story, return_file)


def run(story, scene=None):
    """Run the Writer on a story and wait. Returns where the writer asked to go next: 'builder', 'wheel', or None."""
    problem = check()
    if problem:
        raise WriterError(problem)
    story.manuscript_dir.mkdir(parents=True, exist_ok=True)
    return_file = state_root() / "return"
    state_root().mkdir(parents=True, exist_ok=True)
    return_file.write_text("")
    argv, env, note = launch(story, return_file)
    run.note = note
    if scene:                                   # open at this scene: "<file>:<line>"
        env["STORYWHEEL_SCENE"] = f"{scene['path']}:{scene.get('line', 1)}"
    subprocess.call(argv, env=env)
    where = return_file.read_text().strip() if return_file.exists() else ""
    return where or None
