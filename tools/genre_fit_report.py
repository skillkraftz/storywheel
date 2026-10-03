"""Print the best-fitting words of each genre, to judge the genre fit by eye.

    python tools/genre_fit_report.py                       # the installed dictionary: top 30 adjectives and verbs of every genre
    python tools/genre_fit_report.py --index COPY.sqlite --build --pos n a v --top 40 --genres horror sci-fi

--build works the fit out first (into that index; use a copy). The order is the one the Genre words tab shows: best fit first, then the
more common word. The result is deterministic: no random numbers are used."""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storywheel import dictionary, genrefit  # noqa: E402
from storywheel.library import Library  # noqa: E402
from storywheel import paths  # noqa: E402

NAMES = {"a": "adjectives", "v": "verbs", "n": "nouns", "r": "adverbs"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", help="the dictionary index to read (default: the installed one)")
    ap.add_argument("--build", action="store_true", help="work the genre fit out first")
    ap.add_argument("--pos", nargs="*", default=["a", "v"])
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--genres", nargs="*")
    args = ap.parse_args()
    path = Path(args.index) if args.index else dictionary.index_path()
    if args.build:
        print(genrefit.build(path, Library.load(paths.home()), lambda m: print("  " + m, file=sys.stderr)), file=sys.stderr)
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    genres = args.genres or [g for (g,) in db.execute("select genre from fit group by genre having count(*) > 1000 order by genre")]
    for genre in genres:
        print(f"### {genre}")
        for pos in args.pos:
            rows = db.execute(
                "select l.w, f.score from fit f join lexicon l on l.word_id = f.word_id and l.pos = f.pos "
                "where f.genre = ? and f.pos = ? order by f.score desc, l.zipf desc, l.w limit ?", (genre, pos, args.top)).fetchall()
            print(f"{NAMES[pos]}: " + ", ".join(w for w, _s in rows))
        print()


if __name__ == "__main__":
    main()
