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
- `act_climax/fantasy`
- `act_climax/general`
- `act_climax/mystery`
- `act_crisis/comedy`
- `act_crisis/fantasy`
- `act_crisis/general`
- `act_crisis/mystery`
- `act_event/comedy`
- `act_event/fantasy`
- `act_event/general`
- `act_event/mystery`
- `act_incident/comedy`
- `act_incident/fantasy`
- `act_incident/general`
- `act_incident/mystery`
- `act_message/comedy`
- `act_message/fantasy`
- `act_message/general`
- `act_message/mystery`
- `act_midpoint/comedy`
- `act_midpoint/fantasy`
- `act_midpoint/general`
- `act_midpoint/mystery`
- `act_person/comedy`
- `act_person/fantasy`
- `act_person/general`
- `act_person/mystery`
- `act_place/comedy`
- `act_place/fantasy`
- `act_place/general`
- `act_place/mystery`
- `act_resolution/comedy`
- `act_resolution/fantasy`
- `act_resolution/general`
- `act_resolution/mystery`
- `act_setup/comedy`
- `act_setup/fantasy`
- `act_setup/general`
- `act_setup/mystery`
- `act_thing/comedy`
- `act_thing/fantasy`
- `act_thing/general`
- `act_thing/mystery`
- `act_trials/comedy`
- `act_trials/fantasy`
- `act_trials/general`
- `act_trials/mystery`
- `act_turn/comedy`
- `act_turn/fantasy`
- `act_turn/general`
- `act_turn/mystery`
- `climax/comedy`
- `climax/fantasy`
- `climax/mystery`
- `deadline/comedy`
- `deadline/fantasy`
- `deadline/general`
- `deadline/mystery`
- `disaster/comedy`
- `disaster/fairy-tale`
- `disaster/fantasy`
- `disaster/mystery`
- `disaster/western`
- `do_person/comedy`
- `do_person/fantasy`
- `do_person/general`
- `do_person/mystery`
- `do_thing/comedy`
- `do_thing/fantasy`
- `do_thing/general`
- `do_thing/mystery`
- `era/comedy`
- `era/early-century`
- `era/fairy-tale`
- `era/fantasy`
- `era/future`
- `era/modern`
- `era/mystery`
- `era/western`
- `escalation/comedy`
- `escalation/fantasy`
- `escalation/mystery`
- `feeling/general`
- `first_name/comedy`
- `first_name/fairy-tale`
- `first_name/fantasy`
- `first_name/mystery`
- `first_name/western`
- `flaw/comedy`
- `flaw/fantasy`
- `flaw/mystery`
- `habit_person/comedy`
- `habit_person/fantasy`
- `habit_person/general`
- `habit_person/mystery`
- `habit_place/comedy`
- `habit_place/fantasy`
- `habit_place/general`
- `habit_place/mystery`
- `habit_thing/comedy`
- `habit_thing/fantasy`
- `habit_thing/general`
- `habit_thing/mystery`
- `hiding/comedy`
- `hiding/fairy-tale`
- `hiding/fantasy`
- `hiding/mystery`
- `hiding/western`
- `inciting/comedy`
- `inciting/fantasy`
- `inciting/mystery`
- `job/comic-trades`
- `job/fairy-tale-trades`
- `job/fantasy-trades`
- `job/frontier-trades`
- `job/mystery-trades`
- `ketsu/comedy`
- `ketsu/fantasy`
- `ketsu/general`
- `ketsu/mystery`
- `ki/comedy`
- `ki/fantasy`
- `ki/general`
- `ki/mystery`
- `landmark/comedy`
- `landmark/fairy-tale`
- `landmark/fantasy`
- `landmark/mystery`
- `landmark/western`
- `last_name/comedy`
- `last_name/fairy-tale`
- `last_name/fantasy`
- `last_name/mystery`
- `last_name/western`
- `loss/fantasy`
- `manner/comedy`
- `manner/fantasy`
- `manner/general`
- `manner/mystery`
- `message/comedy`
- `message/fairy-tale`
- `message/fantasy`
- `message/mystery`
- `message/western`
- `motive/comedy`
- `motive/fantasy`
- `motive/general`
- `motive/mystery`
- `need/comedy`
- `need/fantasy`
- `need/mystery`
- `once/comedy`
- `once/fantasy`
- `once/mystery`
- `place/comic-towns`
- `place/fairy-tale-realms`
- `place/fantasy-realms`
- `place/mystery-villages`
- `place/western-towns`
- `place_adj/comedy`
- `place_adj/fantasy`
- `place_adj/mystery`
- `place_adj/western`
- `place_end/fairy-tale`
- `place_end/fantasy`
- `place_feature/comedy`
- `place_feature/fantasy`
- `place_feature/mystery`
- `place_feature/western`
- `place_stem/fairy-tale`
- `place_stem/fantasy`
- `premise/comedy`
- `premise/fantasy`
- `premise/mystery`
- `prize/comedy`
- `prize/fantasy`
- `prize/general`
- `prize/mystery`
- `reaction/comedy`
- `reaction/fantasy`
- `reaction/mystery`
- `resolution/comedy`
- `resolution/fantasy`
- `resolution/mystery`
- `rival/comedy`
- `rival/fairy-tale`
- `rival/fantasy`
- `rival/mystery`
- `rival/western`
- `routine/comedy`
- `routine/fantasy`
- `routine/mystery`
- `rumor/comedy`
- `rumor/fantasy`
- `rumor/mystery`
- `secret/comedy`
- `secret/fantasy`
- `secret/mystery`
- `sho/comedy`
- `sho/fantasy`
- `sho/general`
- `sho/mystery`
- `someone/comedy`
- `someone/fairy-tale`
- `someone/fantasy`
- `someone/mystery`
- `someone/western`
- `temptation/comedy`
- `temptation/fantasy`
- `temptation/general`
- `temptation/mystery`
- `ten/comedy`
- `ten/fantasy`
- `ten/general`
- `ten/mystery`
- `thing/comedy`
- `thing/fairy-tale`
- `thing/fantasy`
- `thing/mystery`
- `thing/western`
- `title/comedy`
- `title/fantasy`
- `title/mystery`
- `title/oddity`
- `title_adj/comedy`
- `title_adj/fairy-tale`
- `title_adj/fantasy`
- `title_adj/general`
- `title_adj/mystery`
- `title_adj/western`
- `title_noun/comedy`
- `title_noun/fairy-tale`
- `title_noun/fantasy`
- `title_noun/general`
- `title_noun/mystery`
- `title_noun/western`
- `trait/comedy-traits`
- `trait/fantasy-traits`
- `trait/mystery-traits`
- `twist/comedy`
- `twist/fantasy`
- `twist/mystery`
- `value/comedy`
- `value/fantasy`
- `value/general`
- `value/mystery`
- `vice/comedy`
- `vice/fantasy`
- `vice/general`
- `vice/mystery`
- `want/comedy`
- `want/fantasy`
- `want/mystery`

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
