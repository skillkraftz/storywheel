"""Optional grammar checking with a LOCAL LanguageTool server (https://languagetool.org). Off by default; nothing runs unless you turn it on.

    storywheel grammar install [--from FILE.zip]   download LanguageTool (about 200 MB) or unpack a zip you copied over
    storywheel grammar status                      Java, version, memory, whether the server is running
    storywheel grammar start | stop                what the Writer does for you when grammar checking is turned on or off

The Writer (sw/grammar.lua) talks to the server over HTTP on 127.0.0.1 only. It is LanguageTool's free (open source) rule set, not the
Premium rules of the Google Docs extension, and the large n-gram data is not used.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from . import paths, settings, tools

DOWNLOAD_URL = "https://languagetool.org/download/LanguageTool-stable.zip"
DEFAULT_PORT = 18081
MIN_JAVA = 11
SERVER_CLASS = "org.languagetool.server.HTTPServer"

from .grammar_categories import CATEGORIES, CATEGORY_DEFAULTS  # noqa: E402

HELP_NOTE = ("This is the local LanguageTool: its free rules, not the Premium rules of the Google Docs extension, and without the large n-gram "
             "data (so some confused-word checks that need it are missing).")


class GrammarError(Exception):
    pass


# --- where things are ------------------------------------------------------------------------------------------------------------------

def install_dir():
    return Path(os.environ.get("STORYWHEEL_LANGUAGETOOL", paths.home() / "languagetool"))


def server_jar():
    """The languagetool-server.jar of the installed copy, or None."""
    base = install_dir()
    if not base.is_dir():
        return None
    found = sorted(base.glob("*/languagetool-server.jar")) + sorted(base.glob("languagetool-server.jar"))
    return found[-1] if found else None


def version():
    jar = server_jar()
    if not jar:
        return None
    m = re.search(r"LanguageTool-([0-9][0-9.]*)", str(jar.parent.name))
    return m.group(1) if m else (jar.parent.name or "unknown")


def pid_path():
    return paths.home() / "languagetool.pid"


def log_path():
    return paths.home() / "languagetool.log"


# --- the settings, turned into what the server wants -------------------------------------------------------------------------------------

def config(g=None):
    """Everything the Writer needs: the server's URL, the categories and rules to switch off, the language, the pause."""
    g = g or settings.load_global()
    off_cats = [cid for key, cid, _l, on, _h in CATEGORIES if not bool(g.get(key, on))]
    off_rules = [r.strip() for r in re.split(r"[,\s]+", str(g.get("grammar_off_rules") or "")) if r.strip()]
    port = int(g.get("grammar_port") or DEFAULT_PORT)
    if port == DEFAULT_PORT and os.environ.get("STORYWHEEL_GRAMMAR_PORT"):         # (tests: a real server of yours on the usual port must not be used)
        port = int(os.environ["STORYWHEEL_GRAMMAR_PORT"])
    return {"url": f"http://127.0.0.1:{port}", "port": port, "disabledCategories": ",".join(off_cats), "disabledRules": ",".join(off_rules),
            "language": g.get("grammar_language") or "en-US", "pause_ms": int(g.get("grammar_pause_ms") or 1500),
            "memory_mb": int(g.get("grammar_memory_mb") or 512)}


def turn_off_rule(rule):
    g = settings.load_global()
    rules = [r for r in re.split(r"[,\s]+", str(g.get("grammar_off_rules") or "")) if r]
    if rule not in rules:
        rules.append(rule)
    settings.save_global({"grammar_off_rules": ",".join(rules)})
    return rules


# --- Java and memory ---------------------------------------------------------------------------------------------------------------------

def java_exe():
    return shutil.which(os.environ.get("STORYWHEEL_JAVA", "java"))


def java_version(exe=None):
    """The major version of Java (17, 21...), or None."""
    exe = exe or java_exe()
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r'version "(\d+)(?:\.(\d+))?', r.stderr + r.stdout)
    if not m:
        return None
    major = int(m.group(1))
    return int(m.group(2)) if major == 1 and m.group(2) else major          # "1.8.0" is Java 8


def memory_mb():
    """(total, available) MB from /proc/meminfo, or (None, None)."""
    try:
        info = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines() if ":" in line)
        get = lambda k: int(info[k].split()[0]) // 1024
        return get("MemTotal"), get("MemAvailable")
    except (OSError, KeyError, ValueError):
        return None, None


def status():
    cfg = config()
    total, avail = memory_mb()
    need = cfg["memory_mb"] + 250                           # the heap plus Java itself
    java = java_version()
    out = {"java": java_exe() or "", "java_version": java, "java_ok": bool(java and java >= MIN_JAVA), "installed": server_jar() is not None,
           "version": version(), "path": str(install_dir()), "running": running(), "url": cfg["url"], "memory_limit_mb": cfg["memory_mb"],
           "memory_needed_mb": need, "memory_total_mb": total, "memory_available_mb": avail, "problems": []}
    if not out["java"]:
        out["problems"].append(tools.missing("java"))
    elif not out["java_ok"]:
        out["problems"].append(f"Java {java or 'of unknown version'} is too old: LanguageTool needs Java {MIN_JAVA} or newer. To fix it, run:  sudo apt install default-jre-headless")
    if not out["installed"]:
        out["problems"].append("LanguageTool isn't installed. To fix it, run:  storywheel grammar install   (or  storywheel grammar install --from FILE.zip)")
    if avail is not None and avail < need:
        out["problems"].append(f"Only {avail} MB of memory is free and LanguageTool wants about {need} MB ({cfg['memory_mb']} MB heap + Java). "
                               "Close something, or lower the limit in Settings > Grammar.")
    return out


# --- installing ----------------------------------------------------------------------------------------------------------------------------

def _safe_extract(zf, dest):
    dest = Path(dest).resolve()
    for member in zf.namelist():
        target = (dest / member).resolve()
        if dest != target and dest not in target.parents:
            raise GrammarError(f"The zip holds a path outside its folder ({member}); it was not unpacked.")
    zf.extractall(dest)


def install(from_file=None, progress=lambda m: None, url=DOWNLOAD_URL):
    """Unpack LanguageTool into the install folder, from FILE.zip or by downloading it (the only network use of this feature)."""
    tmp = None
    if from_file:
        src = Path(from_file).expanduser()
        if not src.is_file():
            raise GrammarError(f"There is no file {src}.")
    else:
        from . import download as dl
        src = tmp = paths.home() / "languagetool-download.zip"
        try:
            dl.fetch(url, src, lambda m: progress(m.replace(" …", " (about 200 MB) …")))
        except dl.DownloadError as e:
            tmp.unlink(missing_ok=True)
            raise GrammarError(f"{e}  On a machine without internet, or if the download keeps failing, get LanguageTool-stable.zip another way and run:  "
                               "storywheel grammar install --from LanguageTool-stable.zip")
    try:
        if not zipfile.is_zipfile(src):
            raise GrammarError(f"{src} is not a zip file.")
        with zipfile.ZipFile(src) as zf:
            if not any(n.endswith("languagetool-server.jar") for n in zf.namelist()):
                raise GrammarError("That zip has no languagetool-server.jar, so it is not LanguageTool.")
            stage = install_dir().parent / (install_dir().name + ".new")
            shutil.rmtree(stage, ignore_errors=True)
            stage.mkdir(parents=True)
            progress("Unpacking…")
            _safe_extract(zf, stage)
        old = install_dir()
        if old.exists():
            stop()
            shutil.rmtree(old)
        stage.replace(old)
    finally:
        if tmp and tmp.exists():
            tmp.unlink()
    return version()


# --- the server ------------------------------------------------------------------------------------------------------------------------------

def _http(url, data=None, timeout=3):
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def responding(url=None):
    try:
        _http((url or config()["url"]) + "/v2/languages", timeout=2)
        return True
    except (OSError, urllib.error.URLError):
        return False


def running():
    return responding()


def server_command(cfg=None):
    cfg = cfg or config()
    override = os.environ.get("STORYWHEEL_LT_CMD")             # tests (and tinkerers) can start a different server: {port} is filled in
    if override:
        return override.replace("{port}", str(cfg["port"])).split()
    jar = server_jar()
    if not jar:
        raise GrammarError("LanguageTool isn't installed. To fix it, run:  storywheel grammar install   (or  storywheel grammar install --from FILE.zip)")
    java = java_exe()
    if not java:
        raise GrammarError(tools.missing("java"))
    v = java_version(java)
    if v is not None and v < MIN_JAVA:
        raise GrammarError(f"Java {v} is too old: LanguageTool needs Java {MIN_JAVA} or newer. To fix it, run:  sudo apt install default-jre-headless")
    return [java, f"-Xmx{cfg['memory_mb']}m", "-cp", str(jar), SERVER_CLASS, "--port", str(cfg["port"])]


def start(wait=60):
    """Start the server (if it is not already answering) and wait until it is ready. Returns the URL."""
    cfg = config()
    if responding(cfg["url"]):
        return cfg["url"]
    cmd = server_command(cfg)
    log_path().parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path(), "ab")
    proc = subprocess.Popen(cmd, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    pid_path().write_text(str(proc.pid))
    end = time.time() + wait
    while time.time() < end:
        if proc.poll() is not None:
            pid_path().unlink(missing_ok=True)
            tail = log_path().read_text(errors="replace")[-300:].strip()
            raise GrammarError(f"The LanguageTool server stopped right away. {tail}")
        if responding(cfg["url"]):
            return cfg["url"]
        time.sleep(0.3)
    stop()
    raise GrammarError(f"The LanguageTool server did not answer within {wait} seconds (a Raspberry Pi can need a minute; "
                       "see ~/.storywheel/languagetool.log).")


def stop():
    """Stop the server storywheel started. Returns True if there was one."""
    try:
        pid = int(pid_path().read_text().strip())
    except (OSError, ValueError):
        return False
    pid_path().unlink(missing_ok=True)
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return False
    end = time.time() + 5
    while time.time() < end:
        try:
            os.kill(pid, 0)
        except OSError:
            break
        time.sleep(0.1)
    return True


# --- per-story ignored items ---------------------------------------------------------------------------------------------------------------------

def ignore_path(story_dir):
    return Path(story_dir) / "grammar-ignore.json"


def ignored(story_dir):
    try:
        data = json.loads(ignore_path(story_dir).read_text(encoding="utf-8"))
        return [d for d in data if isinstance(d, dict) and "rule" in d]
    except (OSError, ValueError):
        return []


def forget_ignored(story_dir):
    p = ignore_path(story_dir)
    n = len(ignored(story_dir))
    p.unlink(missing_ok=True)
    return n
