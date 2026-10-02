"""
Regenerate the list of lists in SOURCES.md.

The prose about outside sources and licenses is kept as written below; the
lists of files are rebuilt from storywheel/data/, so provenance can't go stale.
Lists that already existed at the Stage 1 commit are 'carried over from v1';
generated lists are marked by their "generator"; everything else was written
for this project. Edit the text here, then run:

    python tools/update_sources.py
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from storywheel.library import Library  # noqa: E402

STAGE1 = "cb8da94"

HEAD = """# Sources and licenses

Every list in `storywheel/data/` and where it came from. Update this by running
`python tools/update_sources.py`; `tests/test_content.py` fails if a list file isn't
mentioned here.

Nothing is fetched at run time. Anything mined from outside sources is fetched by a
script in `tools/` into `data/raw/`, trimmed by hand, and only the trimmed result
ships in `storywheel/data/`.

## Outside sources

| Source | License | Used for | Where |
|---|---|---|---|
| [dariusk/corpora](https://github.com/dariusk/corpora) (`humans/obsolete-occupations.json`, `mythology/monsters.json`) | CC0 1.0 public domain. Stated in the repository README ("I have chosen to CC0 license this"). Checked 2026-10-01. | Ideas for jobs and for fairy-tale folk; a short list was picked by hand | `tools/fetch_corpora.py` -> `data/raw/corpora/` |
| [Faker](https://pypi.org/project/Faker/) | MIT | Modern names, cities and jobs, generated at run time | library, not data |
| [wonderwords](https://pypi.org/project/wonderwords/) | MIT | Random dictionary words for the `{ODDITY}` wildcard and wildcard titles; the word list that keeps invented names from being ordinary words | library, not data |
| [Open English WordNet](https://en-word.net/) 2025 edition (`english-wordnet-2025.xml.gz`, github.com/globalwordnet/english-wordnet) | CC BY 4.0 (https://creativecommons.org/licenses/by/4.0). Stated in the file's own header (`license="https://creativecommons.org/licenses/by/4.0"`) and the project page. Checked 2026-10-02. Attribution: shown in `storywheel dictionary status` and on the lookup screens. | Meanings, examples, synonyms, opposites and "kind of" for the dictionary and thesaurus | **Not shipped in the package.** `storywheel dictionary install` downloads it on request (the one network use) and builds `~/.storywheel/dictionary.sqlite`; `storywheel/dictionary_build.py` |
| [wordfreq](https://github.com/rspeer/wordfreq) 3.1.1 (Robyn Speer; PyPI `wordfreq`) | The code is Apache-2.0 (`License: Apache-2.0` in its metadata and LICENSE.txt). Its data files are CC BY-SA 4.0 ("it includes data files that may be redistributed under a Creative Commons Attribution-ShareAlike 4.0 license", from its README), built from public word-frequency sources (Wikipedia, subtitles, news, books, web text, Twitter, Reddit...; the sources' own terms are listed in its README). Checked 2026-10-02. storywheel does not copy or ship the data: it is a dependency, installed by pip/pipx, and only read at run time. Attribution: shown in Words help. | How common each word is (the Zipf scale), to offer words that are neither everyday nor obscure in Words > Vocabulary | a dependency (`wordfreq>=3.0` in pyproject.toml); not in the repository |
| [Moby Thesaurus II](https://www.gutenberg.org/ebooks/3202) by Grady Ward (`mthesaur.txt`, Project Gutenberg #3202) | Public domain: the file's documentation says "Public Domain material by grant from the author, January, 2001". Checked 2026-10-02. | Broader lists of similar words in the thesaurus | Same: downloaded by `storywheel dictionary install`, not shipped |

Roget's Thesaurus (1911) in the Moby download (`roget13a.txt`) was evaluated for "opposite ideas" and **not used**: its category
pairing is not in the data (see BACKLOG.md), and nothing from it is in the program or its data.

Deliberately **not** used from the same repository: `words/spells.json` (fetched, found
to be spells from the Harry Potter books, which doesn't sit well with the CC0 label, and
deleted) and `humans/tolkienCharacterNames.json` (names from a copyrighted work; never
fetched). Check files like these individually before using anything else from corpora.

## Atoms, templates and structures written for this project

Original text. Atoms are short parts (a noun phrase, a verb, a deadline, a prize),
templates are sentence frames with slots that assemble them, and structures
(`data/structures/`: the Story Spine, a three-act outline, kishotenketsu) are ordered
lists of beats that each draw on their own templates. See the README. Names, places and
objects are generic or drawn from folklore and the general stock of the genres; no
passages were copied from any book, film or game. Names are also the training data for
the Markov name maker. Fairy-tale material is written from the shared folklore tradition
(Grimm, Perrault, Andersen and the like are public domain), but not from their text.
The Story Spine is Kenn Adams' teaching format; only its well-known openers are used
here, as the fixed text of one structure. The three-act outline and kishotenketsu are
general, unowned descriptions of story shape.

@@written@@

Of these, `job/fairy-tale-trades` includes nine jobs picked from corpora's
obsolete-occupations list (charcoal burner, town crier, chapman, lamplighter, water
carrier, whipping boy, cup-bearer, plague doctor, ragpicker), and `someone/fairy-tale`
includes creature ideas (troll, hag, selkie, pixie, ogre, goblin, brownie, nymph, dryad)
suggested by corpora's monsters list. Both are CC0.

## Generated at run time (no entries in the file)

@@generated@@

## Carried over from v1

Hand-written by the project owner for v1, moved into JSON in Stage 1, and since
shortened and retagged where they were too long or too specific. Grouped by slot:
@@carried@@.
"""


def main():
    lib = Library.load()
    out = subprocess.run(["git", "ls-tree", "-r", "--name-only", STAGE1], capture_output=True,
                         text=True, cwd=ROOT).stdout
    v1 = {m.group(1) for line in out.splitlines()
          if (m := re.match(r"storywheel/data/(?:lists|templates)/(.+)\.json$", line))}
    generated = sorted(i for i, w in lib.lists.items() if w.generator)
    carried = sorted(i for i in lib.lists if i in v1 and i not in generated)
    written = sorted(i for i in lib.lists if i not in v1 and i not in generated)
    bullets = lambda ids: "\n".join(f"- `{i}`" for i in ids)
    text = (HEAD.replace("@@written@@", bullets(written)).replace("@@generated@@", bullets(generated))
            .replace("@@carried@@", ", ".join(f"`{g}/*`" for g in sorted({i.split('/')[0] for i in carried}))))
    (ROOT / "SOURCES.md").write_text(text)
    print(f"SOURCES.md: {len(written)} written, {len(generated)} generated, {len(carried)} carried over")


if __name__ == "__main__":
    main()
