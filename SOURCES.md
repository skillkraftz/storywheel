# Sources and licenses

Every list in `storywheel/data/` and where it came from. Update this when you add
or change a list; `tests/test_content.py` fails if a list file isn't mentioned here.

Nothing is fetched at run time. Anything mined from outside sources is fetched by a
script in `tools/` into `data/raw/`, trimmed by hand, and only the trimmed result
ships in `storywheel/data/`.

## Outside sources

| Source | License | Used for | Where |
|---|---|---|---|
| [dariusk/corpora](https://github.com/dariusk/corpora) (`humans/obsolete-occupations.json`, `mythology/monsters.json`) | CC0 1.0 public domain. Stated in the repository README ("I have chosen to CC0 license this"). Checked 2026-10-01. | Ideas for jobs and for fairy-tale folk; a short list was picked by hand | `tools/fetch_corpora.py` -> `data/raw/corpora/` |
| [Faker](https://pypi.org/project/Faker/) | MIT | Modern names, cities and jobs, generated at run time | library, not data |
| [wonderwords](https://pypi.org/project/wonderwords/) | MIT | Random dictionary words for the `{ODDITY}` wildcard and wildcard titles | library, not data |

Deliberately **not** used from the same repository: `words/spells.json` (fetched, found
to be spells from the Harry Potter books, which doesn't sit well with the CC0 label, and
deleted) and `humans/tolkienCharacterNames.json` (names from a copyrighted work; never
fetched). Check files like these individually before using anything else from corpora.

## Hand-written for the western / fairy tale slice

Written for this project, original text. Names, places and objects are generic or
drawn from folklore and the general stock of the genres; no passages were copied from
any book, film or game. Names are also the training data for the Markov name maker.
Fairy-tale material is written from the shared folklore tradition (Grimm, Perrault,
Andersen and the like are public domain), but not from their text.

- `disaster/fairy-tale`
- `disaster/western`
- `era/fairy-tale`
- `era/western`
- `first_name/fairy-tale`
- `first_name/western`
- `hiding/fairy-tale`
- `hiding/western`
- `job/fairy-tale-trades`
- `job/frontier-trades`
- `landmark/fairy-tale`
- `landmark/western`
- `last_name/fairy-tale`
- `last_name/western`
- `message/fairy-tale`
- `message/western`
- `place/fairy-tale-realms`
- `place/western-towns`
- `place_adj/western`
- `place_end/fairy-tale`
- `place_feature/western`
- `place_stem/fairy-tale`
- `rival/fairy-tale`
- `rival/western`
- `rumor/fairy-tale`
- `rumor/western`
- `someone/fairy-tale`
- `someone/western`
- `thing/fairy-tale`
- `thing/western`
- `title/fairy-tale`
- `title/general`
- `title/oddity`
- `title/western`
- `title_adj/fairy-tale`
- `title_adj/general`
- `title_adj/western`
- `title_noun/fairy-tale`
- `title_noun/general`
- `title_noun/western`

Of these, `job/fairy-tale-trades` includes nine jobs picked from corpora's
obsolete-occupations list (charcoal burner, town crier, chapman, lamplighter, water
carrier, whipping boy, cup-bearer, plague doctor, ragpicker), and `someone/fairy-tale`
includes creature ideas (troll, hag, selkie, pixie, ogre, goblin, brownie, nymph, dryad)
suggested by corpora's monsters list. Both are CC0.

## Generated at run time (no entries in the file)

- `adj/dictionary`
- `first_name/faker`
- `job/faker-jobs`
- `last_name/faker`
- `noun/dictionary`
- `place/faker-cities`
- `verb/dictionary`

## Carried over from v1

Hand-written by the project owner for v1 and moved into JSON in Stage 1. Grouped by slot.

- `betrayal/*`\n- `change/*`\n- `climax/*`\n- `close/*`\n- `crime/*`\n- `deal/*`\n- `disaster/*`\n- `era/*`\n- `errand/*`\n- `escalation/*`\n- `flaw/*`\n- `hiding/*`\n- `inciting/*`\n- `job/*`\n- `landmark/*`\n- `loss/*`\n- `message/*`\n- `mood/*`\n- `need/*`\n- `once/*`\n- `premise/*`\n- `reaction/*`\n- `resolution/*`\n- `rival/*`\n- `rival_move/*`\n- `routine/*`\n- `rumor/*`\n- `sacrifice/*`\n- `season/*`\n- `secret/*`\n- `someone/*`\n- `thing/*`\n- `topic/*`\n- `trait/*`\n- `twist/*`\n- `want/*`\n- `windfall/*`\n