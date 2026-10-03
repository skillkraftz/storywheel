"""Every download storywheel makes (the dictionary's sources, LanguageTool) goes through here, so they all behave the same:

  * a normal User-Agent ("storywheel/VERSION"): some sites (languagetool.org) refuse Python's default one with HTTP 403;
  * if a server still refuses (403 and friends), try curl or wget, when one is installed, which many servers accept;
  * a plain message that says what happened and what to do, and never a half-written file left behind.
"""
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from . import __version__

USER_AGENT = f"storywheel/{__version__}"
REFUSED = (401, 403, 406, 429, 451)               # "no" answers worth trying another client for


class DownloadError(Exception):
    pass


def _urllib(url, dest, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def _external(url, dest, timeout):
    """curl or wget, whichever is installed. Returns (tool name, None) on success or (tool name, error text); (None, None) if neither exists."""
    for tool, argv in (("curl", ["curl", "-fsSL", "--max-time", str(max(timeout * 20, 600)), "-o", str(dest), url]),
                       ("wget", ["wget", "-q", "-O", str(dest), url])):
        if shutil.which(tool):
            r = subprocess.run(argv, capture_output=True, text=True)
            if r.returncode == 0 and Path(dest).exists() and Path(dest).stat().st_size > 0:
                return tool, None
            return tool, (r.stderr or r.stdout).strip() or f"exit status {r.returncode}"
    return None, None


def fetch(url, dest, progress=lambda m: None, timeout=60):
    """Download `url` to `dest`. Raises DownloadError with a message fit to show."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    progress(f"Downloading {url} …")
    why = None
    try:
        _urllib(url, part, timeout)
        part.replace(dest)
        return dest
    except urllib.error.HTTPError as e:
        why = f"HTTP {e.code} {e.reason}"
        refused = e.code in REFUSED
    except (OSError, urllib.error.URLError) as e:
        why = str(getattr(e, "reason", e))
        refused = False
    part.unlink(missing_ok=True)
    if refused or "SSL" in why or "certificate" in why.lower():
        tool, err = _external(url, part, timeout)
        if tool and err is None:
            part.replace(dest)
            progress(f"(fetched with {tool}, because the server refused Python's request: {why})")
            return dest
        part.unlink(missing_ok=True)
        if tool:
            raise DownloadError(f"{url} refused the download ({why}), and {tool} could not fetch it either: {err}")
        raise DownloadError(f"{url} refused the download ({why}). Neither curl nor wget is installed to try instead; "
                            "install one (sudo apt install curl) or download the file in a browser and use the --from option.")
    raise DownloadError(f"Couldn't download {url}: {why}")
