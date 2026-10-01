"""
Fetch raw candidate word lists from Darius Kazemi's `corpora` repository.

Build-time only; storywheel never touches the network when it runs.
Licence: CC0 (public domain). The repository's README says so:
https://github.com/dariusk/corpora#license

Files land in data/raw/corpora/ unchanged. Nothing there ships with the app:
a human reads them, picks what fits a list, and writes the result into
storywheel/data/lists/. Record what was used in SOURCES.md.

    python tools/fetch_corpora.py                 # the default set below
    python tools/fetch_corpora.py humans/occupations.json  # or name files
"""
import sys
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/dariusk/corpora/master/data/"
OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "corpora"

DEFAULT = [
    "humans/obsolete-occupations.json",   # jobs: charcoal burner, town crier, chapman...
    "mythology/monsters.json",            # fairy-tale folk: troll, hag, selkie...
]


def main(names):
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names or DEFAULT:
        dest = OUT / name.replace("/", "__")
        with urllib.request.urlopen(BASE + name, timeout=30) as r:
            dest.write_bytes(r.read())
        print("fetched", name, "->", dest.relative_to(OUT.parent.parent.parent))


if __name__ == "__main__":
    main(sys.argv[1:])
