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

from . import paths, tools

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
        return tools.missing("neovim")
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
    story.migrate_quotes()
    spelling_dir = story.universe.path / "spell"
    try:
        from . import spelling
        spelling.write_names(story, spelling_dir)
    except OSError:
        pass
    try:
        from . import spelldict
        note = spelldict.ensure(nvim_exe())
        if note and note.startswith("The spelling list"):
            print(note, file=sys.stderr)
    except Exception:
        pass
    xdg = nvim_config()
    env = dict(os.environ)
    root = state_root()
    env.update({
        "NVIM_APPNAME": APPNAME,
        "XDG_CONFIG_HOME": str(xdg), "XDG_DATA_HOME": str(root / "data"),
        "XDG_STATE_HOME": str(root / "state"), "XDG_CACHE_HOME": str(root / "cache"),
        "STORYWHEEL_STORY_DIR": str(story.path), "STORYWHEEL_UNIVERSE": story.universe.slug, "STORYWHEEL_SPELL_DIR": str(spelling_dir),
        "STORYWHEEL_SPELLLANG_DIR": str(paths.home() / "spelllang"),
        "STORYWHEEL_STORY": story.slug, "STORYWHEEL_PY": sys.executable,
        "STORYWHEEL_RETURN_FILE": str(return_file),
        "STORYWHEEL_HOME": str(paths.home()), "STORYWHEEL_LIBRARY": str(paths.library_root()),
    })
    for d in ("data", "state", "cache"):
        (root / d).mkdir(parents=True, exist_ok=True)
    return env


def kitty_exe():
    return shutil.which(os.environ.get("STORYWHEEL_KITTY", "kitty"))


def in_kitty():
    """Is storywheel running inside a kitty window? (kitty sets KITTY_WINDOW_ID in every window it makes and TERM=xterm-kitty.)"""
    return bool(os.environ.get("KITTY_WINDOW_ID")) or "kitty" in os.environ.get("TERM", "")


def kitty_command(exe, settings_, argv, title="storywheel: writing"):
    """The kitty command line that opens the Writer in its own window with the writing settings: font, size, line height
    (modify_font cell_height), padding and opacity. The window closes when Neovim does, and it leaves storywheel's own window alone."""
    size = settings_.get("writer_font_size") or 15
    height = max(100, min(300, int(settings_.get("writer_line_height") or 140)))
    padding = max(0, min(200, int(settings_.get("writer_padding") or 0)))
    opacity = float(settings_.get("writer_opacity") or 1.0) if settings_.get("transparent_background", True) else 1.0
    out = [exe, "--class", "storywheel-writer", "--title", title, "-o", f"font_size={size}", "-o", f"modify_font=cell_height {height}%",
           "-o", f"window_padding_width={padding}", "-o", f"background_opacity={max(0.1, min(1.0, opacity))}",
           "-o", "remember_window_size=no", "-o", "confirm_os_window_close=0", "--start-as=maximized"]
    if settings_.get("writer_font"):
        out += ["-o", f"font_family={settings_['writer_font']}"]
    return out + list(argv)


def launch(story, return_file=None):
    """(argv, env, note): how to start the Writer. Inside kitty (and with `writer_kitty` on) it opens in its own kitty window with the
    writing settings; anywhere else it runs in this terminal as it always did. `note` is a plain message when something asked for
    could not be done, else None."""
    from . import settings
    argv, env = command(story, return_file)
    note = None
    st = settings.load_story(story.path)
    if st.get("writer_kitty", True) and in_kitty():
        exe = kitty_exe()
        if exe:
            argv = kitty_command(exe, st, argv, f"storywheel: {story.title}")
            env["STORYWHEEL_GUI"] = "kitty"
        else:
            note = tools.missing("kitty", "The Writer is using this window.")
    return argv, env, note


def kitty_start_note():
    """One line for the start of the program when it is not running in kitty (and the Writer's kitty window is not switched off):
    kitty gives a better Writer, and how to get it. None inside kitty."""
    from . import settings
    if in_kitty() or not settings.load_global().get("writer_kitty", True):
        return None
    return KITTY_NOTE


KITTY_NOTE = ("kitty gives the Writer a better window: its own font, line height and margins (Settings > Writer). "
              "Install it with  sudo apt install kitty  and start storywheel inside it.")


def kitty_note(story):
    """The message to show if the Writer wanted a kitty window but kitty is not installed, else None."""
    return launch(story)[2]


def command(story, return_file=None):
    """(argv, env) to start the Writer on a story. Neovim opens the story's current scene itself."""
    return_file = Path(return_file or (state_root() / "return"))
    argv = [nvim_exe() or "nvim"]
    return argv, environment(story, return_file)


def run(story, scene=None, replace=None):
    """Run the Writer on a story and wait. Returns where the writer asked to go next: 'builder', 'wheel', 'words' or None.
    `replace` ({file, row, start, end, text, new}) is applied before the first screen: the word at that place becomes `new`.
    When the Writer hands a word over (F5), it is left in `run.handover`."""
    import json
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
    if replace:
        env["STORYWHEEL_REPLACE"] = json.dumps(replace)
    data_file = Path(str(return_file) + ".data")
    data_file.unlink(missing_ok=True)
    run.handover = None
    subprocess.call(argv, env=env)
    where = return_file.read_text().strip() if return_file.exists() else ""
    if data_file.exists():
        try:
            run.handover = json.loads(data_file.read_text(encoding="utf-8"))
        except ValueError:
            run.handover = None
        data_file.unlink(missing_ok=True)
    return where or None
