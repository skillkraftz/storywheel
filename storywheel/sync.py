"""Syncing your writing between machines (one used at a time) with Syncthing. storywheel does not sync anything itself; it makes sure
everything worth syncing can live under ONE folder, keeps what belongs to one machine out, and shows the conflicts Syncthing makes.

The sync folder (default ~/Writing) holds:

    <sync>/storywheel/       the library: universes, entities, stories, manuscripts          (setting: library)
    <sync>/<Title>/          exported manuscripts                                             (setting: manuscripts_dir)
    <sync>/.storywheel/      your settings.toml, ratings, vocabulary, recent picks, your own lists/structures/genres/entities, Wheel drafts
    <sync>/.stignore         what Syncthing must leave out

`storywheel sync link FOLDER` moves those app files into `<sync>/.storywheel/` and leaves a symbolic link in ~/.storywheel for each, so
the program finds them where it always did. Stays on each machine (never synced): Neovim's state, the dictionary index and its sources,
the compiled spelling lists, where you left off (state.json), and settings.local.toml (folders, Neovide, fonts).
"""
import datetime
import difflib
import os
import re
import shutil
from pathlib import Path

from . import paths, settings, tools, vault

SHARED = ("settings.toml", "ratings.json", "vocabulary.json", "recent.json", "genres.json", "lists", "structures", "stories", "entities")
DATA = ".storywheel"
STIGNORE = """// storywheel: things that belong to one machine, or are temporary, stay out of the sync
(?d).DS_Store
.~lock.*
*.swp
*.building
spelllang
nvim
dictionary.sqlite
dictionary-sources
state.json
settings.local.toml
"""
CONFLICT = re.compile(r"^(?P<stem>.+)\.sync-conflict-(?P<when>\d{8}-\d{6})(?:-(?P<device>[A-Z0-9]+))?(?P<ext>\.[^.]+)?$")
SKIP_DIRS = {".git", ".stfolder", ".stversions", "node_modules"}


def sync_folder():
    value = settings.load_global().get("sync_folder") or ""
    return Path(value).expanduser() if value else None


def syncthing_installed():
    return shutil.which("syncthing") is not None


# --- linking the shared app files into the sync folder ------------------------------------------------------------------------------------

def plan(folder):
    """[(name, what)] for each shared item: what linking would do to it."""
    folder, home = Path(folder).expanduser(), paths.home()
    out = []
    for name in SHARED:
        src, dst = home / name, folder / DATA / name
        if src.is_symlink() and src.resolve() == dst.resolve():
            out.append((name, "already linked"))
        elif src.exists() and dst.exists():
            out.append((name, "the copy in the sync folder is kept; yours is set aside in ~/.storywheel/.pre-sync/"))
        elif src.exists() or src.is_symlink():
            out.append((name, "moved into the sync folder and linked"))
        elif dst.exists():
            out.append((name, "linked to the copy in the sync folder"))
        else:
            out.append((name, "nothing yet"))
    return out


def link(folder):
    """Move the shared app files into <folder>/.storywheel and link them back. Never overwrites: if both places have one, the sync
    folder's copy is used and this machine's is set aside. Returns lines to show."""
    folder = Path(folder).expanduser()
    home = paths.home()
    data = folder / DATA
    data.mkdir(parents=True, exist_ok=True)
    lines = []
    for name in SHARED:
        src, dst = home / name, data / name
        if src.is_symlink():
            if src.resolve() == dst.resolve():
                continue
            src.unlink()                                                    # linked somewhere else before: point it here
        if src.exists():
            if dst.exists():
                aside = home / ".pre-sync"
                aside.mkdir(exist_ok=True)
                shutil.move(str(src), str(aside / name))
                lines.append(f"{name}: the sync folder already had one, so it is used; yours is in {paths.tilde(aside / name)}")
            else:
                shutil.move(str(src), str(dst))
                lines.append(f"{name}: moved into the sync folder")
        elif not dst.exists():
            continue
        else:
            lines.append(f"{name}: linked to the copy in the sync folder")
        os.symlink(dst, src, target_is_directory=dst.is_dir())
    ignore = folder / ".stignore"
    if not ignore.exists():
        ignore.write_text(STIGNORE, encoding="utf-8")
        lines.append(f"wrote {paths.tilde(ignore)} (what Syncthing leaves out)")
    settings.save_global({"sync_folder": str(folder)})
    return lines or ["Everything was already linked."]


def unlink():
    """Turn the links back into real files in ~/.storywheel (copies; the sync folder is left as it is)."""
    home, lines = paths.home(), []
    for name in SHARED:
        src = home / name
        if src.is_symlink():
            target = src.resolve()
            src.unlink()
            if target.is_dir():
                shutil.copytree(target, src)
            elif target.exists():
                shutil.copy2(target, src)
            lines.append(f"{name}: copied back")
    settings.save_global({"sync_folder": ""})
    return lines or ["Nothing was linked."]


def where_to_look():
    """Folders searched for conflicts: the sync folder, or else the library, the manuscripts folder and the app storage."""
    f = sync_folder()
    roots = [f] if f else [paths.library_root(), paths.manuscripts_root(), paths.home()]
    seen, out = set(), []
    for r in roots:
        try:
            key = Path(r).resolve()
        except OSError:
            continue
        if key not in seen and Path(r).is_dir():
            seen.add(key)
            out.append(Path(r))
    return out


# --- conflicts ---------------------------------------------------------------------------------------------------------------------------

class Conflict:
    def __init__(self, path):
        self.path = Path(path)
        m = CONFLICT.match(self.path.name)
        self.original = self.path.with_name(m.group("stem") + (m.group("ext") or ""))
        self.when = datetime.datetime.strptime(m.group("when"), "%Y%m%d-%H%M%S")
        self.device = m.group("device") or ""

    @property
    def id(self):
        return str(self.path)

    def text(self, which):
        p = self.original if which == "mine" else self.path
        try:
            return p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def words(self, which):
        t = self.text(which)
        return vault.count_words(t) if t is not None else None

    def summary(self):
        mine = "missing" if not self.original.exists() else (f"{self.words('mine'):,} words" if self.words("mine") is not None else "a binary file")
        other = f"{self.words('other'):,} words" if self.words("other") is not None else "a binary file"
        return f"{self.original.name}: yours {mine}; the other copy {other} ({self.when:%Y-%m-%d %H:%M})"


def find_conflicts(roots=None):
    out = []
    for root in roots or where_to_look():
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if ".sync-conflict-" in name and CONFLICT.match(name):
                    out.append(Conflict(Path(dirpath) / name))
    return sorted(out, key=lambda c: str(c.path))


def diff(conflict, context=2, limit=80):
    """The differences between your file and the other copy as lines: '-' yours only, '+' the other copy only."""
    a, b = conflict.text("mine"), conflict.text("other")
    if b is None or (conflict.original.exists() and a is None):
        return ["(a binary file: there is nothing to compare line by line)"]
    lines = list(difflib.unified_diff((a or "").splitlines(), b.splitlines(), "yours", "the other copy", lineterm="", n=context))
    if not lines:
        return ["The two copies are identical."]
    return lines[:limit] + ([f"... {len(lines) - limit} more lines"] if len(lines) > limit else [])


def keep(conflict, which):
    """Keep one copy. "mine": your file stays, the other copy goes to the trash. "other": the other copy takes your file's place
    and your file goes to the trash. Nothing is destroyed (the library's .trash holds the loser). Returns a message."""
    if which == "mine":
        vault.trash(conflict.path)
        return f"Kept yours. The other copy of {conflict.original.name} is in the trash."
    if conflict.original.exists():
        vault.trash(conflict.original)
    conflict.original.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(conflict.path), str(conflict.original))
    return f"Kept the other copy of {conflict.original.name}. Yours is in the trash."


def status():
    f = sync_folder()
    linked = [n for n in SHARED if (paths.home() / n).is_symlink()]
    return {"folder": str(f) if f else "", "linked": linked, "syncthing": syncthing_installed(),
            "conflicts": len(find_conflicts()), "library_inside": bool(f and _inside(paths.library_root(), f)),
            "manuscripts_inside": bool(f and _inside(paths.manuscripts_root(), f))}


def _inside(path, folder):
    try:
        Path(path).resolve().relative_to(Path(folder).expanduser().resolve())
        return True
    except ValueError:
        return False


STEPS = ("To keep your writing in step on two computers (only one used at a time):\n"
         "  1. Install Syncthing on both:  {install}\n"
         "  2. Run Syncthing on each (it opens a page in your browser at http://127.0.0.1:8384) and add the other as a device.\n"
         "  3. Share the folder {folder} between them (on the second machine, accept it and pick the same place).\n"
         "  4. On the second machine run:  storywheel setup   and give the same folder; it links your settings and lists into it.\n"
         "  Close storywheel on one machine and let Syncthing finish (its page says 'Up to Date') before opening it on the other.")


def steps_text(folder):
    return STEPS.format(install=tools.TOOLS["syncthing"][2], folder=paths.tilde(folder))
