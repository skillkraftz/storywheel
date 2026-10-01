# Sources and licenses

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

- `act_climax/general`
- `act_crisis/general`
- `act_event/general`
- `act_incident/general`
- `act_message/general`
- `act_midpoint/general`
- `act_person/general`
- `act_place/general`
- `act_resolution/general`
- `act_setup/general`
- `act_thing/general`
- `act_trials/general`
- `act_turn/general`
- `deadline/general`
- `disaster/fairy-tale`
- `disaster/western`
- `do_person/general`
- `do_thing/general`
- `era/fairy-tale`
- `era/western`
- `feeling/general`
- `first_name/fairy-tale`
- `first_name/western`
- `habit_person/general`
- `habit_place/general`
- `habit_thing/general`
- `hiding/fairy-tale`
- `hiding/western`
- `job/fairy-tale-trades`
- `job/frontier-trades`
- `ketsu/general`
- `ki/general`
- `landmark/fairy-tale`
- `landmark/western`
- `last_name/fairy-tale`
- `last_name/western`
- `manner/general`
- `message/fairy-tale`
- `message/western`
- `motive/general`
- `place/fairy-tale-realms`
- `place/western-towns`
- `place_adj/western`
- `place_end/fairy-tale`
- `place_feature/western`
- `place_stem/fairy-tale`
- `prize/general`
- `rival/fairy-tale`
- `rival/western`
- `sho/general`
- `someone/fairy-tale`
- `someone/western`
- `temptation/general`
- `ten/general`
- `thing/fairy-tale`
- `thing/western`
- `title/oddity`
- `title_adj/fairy-tale`
- `title_adj/general`
- `title_adj/western`
- `title_noun/fairy-tale`
- `title_noun/general`
- `title_noun/western`
- `value/general`
- `vice/general`

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

Hand-written by the project owner for v1, moved into JSON in Stage 1, and since
shortened and retagged where they were too long or too specific. Grouped by slot:
`betrayal/*`, `climax/*`, `close/*`, `crime/*`, `disaster/*`, `era/*`, `escalation/*`, `flaw/*`, `hiding/*`, `inciting/*`, `job/*`, `landmark/*`, `loss/*`, `message/*`, `mood/*`, `need/*`, `once/*`, `premise/*`, `reaction/*`, `resolution/*`, `rival/*`, `routine/*`, `rumor/*`, `season/*`, `secret/*`, `someone/*`, `thing/*`, `title/*`, `topic/*`, `trait/*`, `twist/*`, `want/*`, `windfall/*`.
