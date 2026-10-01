"""
Print the repetition report: are stories assembled from parts, or dealt from a deck?

    python tools/repetition_report.py western "fairy tale" -n 200 --seed 101

Rolls stories in memory (nothing is saved) and lists the entries picked far more
often than their fair share, the most repeated rendered lines, frozen templates
and over-long atoms. See storywheel/report.py.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storywheel.report import build_report, format_report  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("genres", nargs="+")
    ap.add_argument("-n", type=int, default=200, help="stories to roll (default 200)")
    ap.add_argument("--seed", type=int, default=101)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--structure", help="force a story structure (once structures exist)")
    a = ap.parse_args()
    print(format_report(build_report(a.genres, a.n, a.seed, a.top, structure=a.structure), a.top))


if __name__ == "__main__":
    main()
