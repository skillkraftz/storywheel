"""`storywheel update`: pull the newest storywheel from a git remote, reinstall only if the version changed, run migrations, rebuild what
needs it (the dictionary index from its kept sources, the spelling lists), and show what changed.

Where the code comes from:
  * run from a git checkout (an editable install, or `pipx install --editable`): that checkout is updated in place;
  * otherwise the remote in Settings (`update_remote`) is cloned to ~/.storywheel/source and storywheel is reinstalled from it with pipx.
Nothing local is ever overwritten: an unclean checkout or a history that has diverged stops with a message.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__, paths, settings, tools

PACKAGE = Path(__file__).resolve().parent
VERSION_RE = re.compile(r'__version__\s*=\s*"([^"]+)"')


class UpdateError(Exception):
    pass


def git(repo, *args, check=True):
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        raise UpdateError(tools.missing("git"))
    if check and r.returncode != 0:
        raise UpdateError((r.stderr or r.stdout).strip() or f"git {' '.join(args)} failed")
    return r


def checkout_dir():
    """The git working tree this code is running from, or None (a normal pipx install lives in site-packages)."""
    top = PACKAGE.parent
    return top if (top / ".git").exists() else None


def version_in(repo):
    try:
        m = VERSION_RE.search((Path(repo) / "storywheel" / "__init__.py").read_text(encoding="utf-8"))
        return m.group(1) if m else None
    except OSError:
        return None


def changelog_since(repo, installed):
    """The CHANGELOG.md entries newer than `installed`, as text."""
    try:
        text = (Path(repo) / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    out = []
    for block in re.split(r"(?m)^(?=## )", text):
        m = re.match(r"## (\d+(?:\.\d+)*)", block)
        if m and _key(m.group(1)) > _key(installed):
            out.append(block.strip())
    return "\n\n".join(out)


def _key(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "0"))


def source_dir(remote):
    """The checkout to update. A clone in ~/.storywheel/source when this isn't running from one."""
    here = checkout_dir()
    if here:
        return here, True
    if not remote:
        raise UpdateError("There is no git remote to update from. Set one in Settings (F4) > Sync, or run  storywheel setup.")
    clone = paths.home() / "source"
    if not (clone / ".git").exists():
        clone.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["git", "clone", remote, str(clone)], capture_output=True, text=True)
        if r.returncode != 0:
            raise UpdateError(f"Could not clone {remote}: {(r.stderr or r.stdout).strip()}")
    return clone, False


def update(say=print, check_only=False, runner=subprocess.run):
    """Returns a short status word: 'up-to-date', 'updated' or 'available' (check_only)."""
    remote = (settings.load_global().get("update_remote") or "").strip()
    repo, editable = source_dir(remote)
    if git(repo, "status", "--porcelain").stdout.strip():
        raise UpdateError(f"{paths.tilde(repo)} has changes that are not committed, so it was left alone. Commit or stash them first.")
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    fetch_from = remote or "origin"
    git(repo, "fetch", fetch_from, branch)
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    theirs = git(repo, "rev-parse", "FETCH_HEAD").stdout.strip()
    installed = __version__
    if head == theirs or git(repo, "merge-base", "--is-ancestor", theirs, head, check=False).returncode == 0:
        say(f"Already up to date (storywheel {installed}).")
        return "up-to-date"
    if git(repo, "merge-base", "--is-ancestor", head, theirs, check=False).returncode != 0:
        raise UpdateError("Your copy and the remote have both changed since they last agreed, so nothing was merged. "
                          f"Look at it with:  git -C {paths.tilde(repo)} log --oneline --graph --all")
    commits = git(repo, "log", "--oneline", f"{head}..{theirs}").stdout.strip().splitlines()
    say(f"{len(commits)} new change(s):")
    for c in commits[:15]:
        say("  " + c)
    if len(commits) > 15:
        say(f"  ... and {len(commits) - 15} more")
    if check_only:
        return "available"
    git(repo, "merge", "--ff-only", "FETCH_HEAD")
    new = version_in(repo) or installed
    notes = changelog_since(repo, installed)
    if _key(new) != _key(installed):
        say(f"Version {installed} -> {new}.")
        if notes:
            say("\n" + notes + "\n")
        if not editable:
            pipx = shutil.which("pipx")
            if not pipx:
                raise UpdateError(tools.missing("pipx"))
            say("Reinstalling…")
            r = runner([pipx, "install", "--force", str(repo)], capture_output=True, text=True)
            if r.returncode != 0:
                raise UpdateError("pipx could not reinstall storywheel: " + (r.stderr or r.stdout).strip()[:300])
        else:
            say("(This is a checkout installed in place, so the new code is already in use.)")
    else:
        say(f"Version {installed} is unchanged, so storywheel was not reinstalled.")
    # migrations and rebuilds run in a fresh process: the new code, not the code that is running now
    r = runner([sys.executable, "-m", "storywheel", "post-update"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        say(line)
    return "updated"


def post_update(say=print):
    """What a new version may need: migrations, the dictionary index and the spelling lists."""
    from . import dictionary, migrate, spelldict, writer
    lines = migrate.migrate_universe_json() + migrate.migrate_manuscripts() + migrate.migrate_exports()
    for line in lines:
        say("  " + line)
    if dictionary.installed():
        try:
            dictionary.connect()                            # rebuilds an older index from the kept sources
            for note in dictionary.take_notes():
                say("  " + note)
        except dictionary.DictionaryMissing as e:
            say("  " + str(e))
        note = spelldict.ensure(writer.nvim_exe())
        if note:
            say("  " + note)
    say("  Migrations and rebuilds are done." if True else "")
