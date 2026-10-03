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

- `act_climax/comedy`
- `act_climax/general`
- `act_crisis/comedy`
- `act_crisis/general`
- `act_event/comedy`
- `act_event/general`
- `act_incident/comedy`
- `act_incident/general`
- `act_message/comedy`
- `act_message/general`
- `act_midpoint/comedy`
- `act_midpoint/general`
- `act_person/comedy`
- `act_person/general`
- `act_place/comedy`
- `act_place/general`
- `act_resolution/comedy`
- `act_resolution/general`
- `act_setup/comedy`
- `act_setup/general`
- `act_thing/comedy`
- `act_thing/general`
- `act_trials/comedy`
- `act_trials/general`
- `act_turn/comedy`
- `act_turn/general`
- `climax/comedy`
- `deadline/comedy`
- `deadline/general`
- `disaster/comedy`
- `disaster/fairy-tale`
- `disaster/western`
- `do_person/comedy`
- `do_person/general`
- `do_thing/comedy`
- `do_thing/general`
- `era/comedy`
- `era/early-century`
- `era/fairy-tale`
- `era/future`
- `era/modern`
- `era/western`
- `escalation/comedy`
- `feeling/general`
- `first_name/comedy`
- `first_name/fairy-tale`
- `first_name/western`
- `flaw/comedy`
- `habit_person/comedy`
- `habit_person/general`
- `habit_place/comedy`
- `habit_place/general`
- `habit_thing/comedy`
- `habit_thing/general`
- `hiding/comedy`
- `hiding/fairy-tale`
- `hiding/western`
- `inciting/comedy`
- `job/comic-trades`
- `job/fairy-tale-trades`
- `job/frontier-trades`
- `ketsu/comedy`
- `ketsu/general`
- `ki/comedy`
- `ki/general`
- `landmark/comedy`
- `landmark/fairy-tale`
- `landmark/western`
- `last_name/comedy`
- `last_name/fairy-tale`
- `last_name/western`
- `manner/comedy`
- `manner/general`
- `message/comedy`
- `message/fairy-tale`
- `message/western`
- `motive/comedy`
- `motive/general`
- `need/comedy`
- `once/comedy`
- `place/comic-towns`
- `place/fairy-tale-realms`
- `place/western-towns`
- `place_adj/comedy`
- `place_adj/western`
- `place_end/fairy-tale`
- `place_feature/comedy`
- `place_feature/western`
- `place_stem/fairy-tale`
- `premise/comedy`
- `prize/comedy`
- `prize/general`
- `reaction/comedy`
- `resolution/comedy`
- `rival/comedy`
- `rival/fairy-tale`
- `rival/western`
- `routine/comedy`
- `rumor/comedy`
- `secret/comedy`
- `sho/comedy`
- `sho/general`
- `someone/comedy`
- `someone/fairy-tale`
- `someone/western`
- `temptation/comedy`
- `temptation/general`
- `ten/comedy`
- `ten/general`
- `thing/comedy`
- `thing/fairy-tale`
- `thing/western`
- `title/comedy`
- `title/oddity`
- `title_adj/comedy`
- `title_adj/fairy-tale`
- `title_adj/general`
- `title_adj/western`
- `title_noun/comedy`
- `title_noun/fairy-tale`
- `title_noun/general`
- `title_noun/western`
- `trait/comedy-traits`
- `twist/comedy`
- `value/comedy`
- `value/general`
- `vice/comedy`
- `vice/general`
- `want/comedy`

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
`betrayal/*`, `climax/*`, `close/*`, `crime/*`, `disaster/*`, `escalation/*`, `flaw/*`, `hiding/*`, `inciting/*`, `job/*`, `landmark/*`, `loss/*`, `message/*`, `mood/*`, `need/*`, `once/*`, `premise/*`, `reaction/*`, `resolution/*`, `rival/*`, `routine/*`, `rumor/*`, `season/*`, `secret/*`, `someone/*`, `thing/*`, `title/*`, `topic/*`, `trait/*`, `twist/*`, `want/*`, `windfall/*`.
