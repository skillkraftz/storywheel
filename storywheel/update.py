"""`storywheel update`: bring the installed storywheel up to the version of its source folder, run migrations and rebuild what needs it, and show what
changed.

What is compared is always the INSTALLED version (the running code) with the SOURCE folder's version. The source folder comes from the install itself:
pip records where it installed from in the package's direct_url.json (PEP 610), and an editable install runs straight from its folder.

  * if the source folder has a git remote (the typewriter's checkout pulls from xps:projects/storywheel), it is fetched and fast-forwarded first;
    with no remote (xps) the folder is simply read;
  * if its version differs from the installed one, storywheel is reinstalled from it (pipx; pip for a plain venv); an editable install needs none;
  * then migrations, the dictionary index and the spelling lists are brought up to date in a fresh process.

The Settings "update_remote" is optional: it is only used when the source folder is gone (a temporary clone is made and removed again).
Nothing local is ever overwritten: an unclean checkout with a remote, or a history that has diverged, stops with a message.
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


def installed_version():
    """The version of the code that is running (what is installed)."""
    return __version__


def installed_source():
    """(folder, editable) that this install came from, from pip's direct_url.json; None if pip recorded none (installed from an index or a wheel)."""
    import json
    from importlib import metadata
    from urllib.parse import unquote, urlparse
    try:
        text = metadata.distribution("storywheel").read_text("direct_url.json")
        info = json.loads(text) if text else None
    except (metadata.PackageNotFoundError, ValueError, OSError):
        return None
    if not info or not str(info.get("url", "")).startswith("file:"):
        return None
    return Path(unquote(urlparse(info["url"]).path)), bool((info.get("dir_info") or {}).get("editable"))


def find_source():
    """(folder or None, editable). A folder recorded by the install, else the git checkout the code runs from."""
    found = installed_source()
    if found:
        return found
    here = checkout_dir()
    return (here, True) if here else (None, False)


def is_source(folder):
    return folder is not None and (Path(folder) / "storywheel" / "__init__.py").is_file()


def remotes(repo):
    if not (Path(repo) / ".git").exists():
        return []
    return git(repo, "remote", check=False).stdout.split()


def remote_version(repo):
    """The version in the commit that was just fetched."""
    r = git(repo, "show", "FETCH_HEAD:storywheel/__init__.py", check=False)
    m = VERSION_RE.search(r.stdout or "")
    return m.group(1) if m else None


def fetch_and_forward(repo, say, check_only, remote_setting):
    """Fetch the source folder's remote and fast-forward it. Returns the number of new commits (or, with check_only, how many there are)."""
    names = remotes(repo)
    if not names:
        say(f"{paths.tilde(repo)} has no git remote, so it is only read.")
        return 0
    if git(repo, "status", "--porcelain").stdout.strip():
        raise UpdateError(f"{paths.tilde(repo)} has changes that are not committed, so it was left alone. Commit or stash them first.")
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    source = remote_setting or names[0]                  # (a remote given in Settings goes to git exactly as written: "xps:projects/storywheel" works)
    git(repo, "fetch", "--", source, branch)
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    theirs = git(repo, "rev-parse", "FETCH_HEAD").stdout.strip()
    if head == theirs or git(repo, "merge-base", "--is-ancestor", theirs, head, check=False).returncode == 0:
        return 0
    if git(repo, "merge-base", "--is-ancestor", head, theirs, check=False).returncode != 0:
        raise UpdateError("Your copy and the remote have both changed since they last agreed, so nothing was merged. "
                          f"Look at it with:  git -C {paths.tilde(repo)} log --oneline --graph --all")
    commits = git(repo, "log", "--oneline", f"{head}..{theirs}").stdout.strip().splitlines()
    say(f"{len(commits)} new change(s) {'on' if check_only else 'fetched from'} {source}:")
    for c in commits[:15]:
        say("  " + c)
    if len(commits) > 15:
        say(f"  ... and {len(commits) - 15} more")
    if not check_only:
        git(repo, "merge", "--ff-only", "FETCH_HEAD")
    return len(commits)


def reinstall(folder, say, runner):
    """Install storywheel again from `folder`: with pipx when this is a pipx install, else with pip in the environment that is running."""
    in_pipx = "pipx" in Path(sys.prefix).parts or "pipx" in str(sys.prefix)
    pipx = shutil.which("pipx")
    if in_pipx or pipx:
        if not pipx:
            raise UpdateError(tools.missing("pipx"))
        argv = [pipx, "install", "--force", str(folder)]
    else:
        argv = [sys.executable, "-m", "pip", "install", "--upgrade", str(folder)]
    r = runner(argv, capture_output=True, text=True)
    if r.returncode != 0:
        raise UpdateError(f"{'pipx' if argv[0] == pipx else 'pip'} could not reinstall storywheel: " + (r.stderr or r.stdout).strip()[:300])


def fingerprint(folder):
    """Which code is in the source folder: its commit, plus a hash of any uncommitted changes. None if it is not a git checkout."""
    if not (Path(folder) / ".git").exists():
        return None
    head = git(folder, "rev-parse", "HEAD", check=False)
    if head.returncode != 0:
        return None
    fp = head.stdout.strip()
    diff = git(folder, "diff", "HEAD", check=False).stdout
    if diff.strip():
        import hashlib
        fp += "+" + hashlib.sha1(diff.encode("utf-8", "replace")).hexdigest()[:10]
    return fp


def record_path():
    return paths.home() / "installed-source.json"


def recorded():
    """What was installed last time we know of: {"fingerprint", "version", "folder"} or {}."""
    import json
    try:
        data = json.loads(record_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def record_install(folder, fp, version=None):
    """Remember which source commit is installed now, so the next update notices fixes committed without a version bump."""
    import json
    if fp is None:
        record_path().unlink(missing_ok=True)
        return
    record_path().parent.mkdir(parents=True, exist_ok=True)
    record_path().write_text(json.dumps({"fingerprint": fp, "version": version or version_in(folder), "folder": str(folder)}), encoding="utf-8")


def short(fp):
    return (fp or "")[:7] + ("+changes" if fp and "+" in fp else "")


def record_current(say=print):
    """`storywheel update --record`: say that the installed code is what the source folder holds now (after installing by hand)."""
    folder, _editable = find_source()
    if not is_source(folder):
        raise UpdateError("There is no source folder to record.")
    fp = fingerprint(folder)
    record_install(folder, fp)
    say(f"Recorded the installed source: {paths.tilde(folder)} at {short(fp) or 'a folder that is not a git checkout'}.")


def update(say=print, check_only=False, runner=subprocess.run):
    """Returns 'up-to-date', 'updated', or (check_only) 'available'."""
    remote_setting = (settings.load_global().get("update_remote") or "").strip()
    folder, editable = find_source()
    temporary = None
    if not is_source(folder):
        if not remote_setting:
            where = f" ({paths.tilde(folder)})" if folder else ""
            raise UpdateError(f"The folder storywheel was installed from{where} is not there any more, and no update remote is set. "
                              "Set one in Settings (F4) > Updates (a git URL, or user@computer:path/storywheel), or reinstall from a checkout.")
        import tempfile
        temporary = Path(tempfile.mkdtemp(prefix="storywheel-update-"))
        say(f"The folder storywheel was installed from is gone; cloning {remote_setting} for this update.")
        r = subprocess.run(["git", "clone", "--", remote_setting, str(temporary / "storywheel")], capture_output=True, text=True)
        if r.returncode != 0:
            shutil.rmtree(temporary, ignore_errors=True)
            raise UpdateError(f"Could not clone {remote_setting}: {(r.stderr or r.stdout).strip()}")
        folder, editable = temporary / "storywheel", False
    try:
        installed = installed_version()
        fetched = 0 if temporary else fetch_and_forward(folder, say, check_only, remote_setting)
        source_version = version_in(folder)
        source_fp = fingerprint(folder)
        if check_only and fetched:
            source_version = remote_version(folder) or source_version
            fetch_head = git(folder, "rev-parse", "FETCH_HEAD", check=False).stdout.strip()
            source_fp = fetch_head or source_fp
        if not source_version:
            raise UpdateError(f"{paths.tilde(folder)} has no storywheel/__init__.py with a version in it.")
        installed_fp = recorded().get("fingerprint")
        have = f" (commit {short(installed_fp)})" if installed_fp else " (which commit is not recorded)"
        there = f" (commit {short(source_fp)})" if source_fp else ""
        say(f"Installed: {installed}{have}. Source {paths.tilde(folder)}: {source_version}{there}.")
        newer, older = _key(source_version) > _key(installed), _key(source_version) < _key(installed)
        if older:
            say("The source is older than what is installed, so nothing was changed.")
            return "up-to-date"
        # the same version number can still be different code: fixes committed without a bump must reach an installed copy too
        recommit = (not newer) and (not editable) and source_fp is not None and source_fp != installed_fp
        if not newer and not recommit:
            if editable and fetched and not check_only:
                say("This install runs straight from that folder; the fetched changes are already in use.")
                _post(runner, say)
                return "updated"
            say("Already up to date.")
            return "up-to-date"
        notes = changelog_since(folder, installed) if newer else ""
        if recommit:
            say("Same version number, but " + (f"the source is at commit {short(source_fp)}, not {short(installed_fp)}." if installed_fp else
                "storywheel does not know which commit is installed, so it reinstalls once to record it."))
        if check_only:
            say("An update is available. Run  storywheel update  to install it.")
            if notes:
                say("\n" + notes + "\n")
            return "available"
        if notes:
            say("\n" + notes + "\n")
        if editable:
            say("This install runs straight from that folder, so the new code is already in use.")
        else:
            say("Reinstalling.")
            reinstall(folder, say, runner)
            record_install(folder, source_fp, source_version)
        _post(runner, say)
        return "updated"
    finally:
        if temporary:
            shutil.rmtree(temporary, ignore_errors=True)


def _post(runner, say):
    """Migrations and rebuilds run in a fresh process: the new code, not the code that is running now."""
    r = runner([sys.executable, "-m", "storywheel", "post-update"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        say(line)


def post_update(say=print):
    """What a new version may need: migrations, the dictionary index and the spelling lists."""
    from . import dictionary, genrefit, migrate, spelldict, writer
    lines = migrate.migrate_universe_json() + migrate.migrate_manuscripts() + migrate.migrate_exports() + migrate.migrate_sync_links() + migrate.migrate_settings()
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
        note = genrefit.ensure()
        if note:
            say("  " + note)
    say("  Migrations and rebuilds are done." if True else "")
