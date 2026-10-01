# storywheel

Roll a story one piece at a time. Keep what clicks, edit what almost works,
and every piece you keep feeds the next roll. Everything you keep lands in a
single markdown file, ready for Obsidian.

## Install

On a Raspberry Pi (or anywhere), from the folder containing `pyproject.toml`:

    pipx install .

No pipx? `sudo apt install pipx` first, or use a virtualenv and `pip install .`

If you want to tinker with the word lists and see changes immediately,
install it editable instead: `pipx install --editable .`

## Use

    storywheel              start a new story
    storywheel list         list your stories
    storywheel resume [N]   pick up where you left off (N from list; default newest)
    storywheel export N --out ~/vault/Stories     copy a story's markdown somewhere
    storywheel sample western "fairy tale" -n 10   print sample stories for a genre mix
    storywheel universe     show what you've saved to your universe
    storywheel universe rm KEY N   remove an entry, e.g.  universe rm spine 1

You go through the steps in order: genre & mood, title, protagonist, setting,
premise, story spine, twist. At each step:

    enter / r   roll again              k        keep it and move on
    f [field]   reroll one field        e [field]  edit a field in place
    E           edit in $EDITOR         w        write your own
    p N         pick earlier roll #N    h        every roll so far (what changed), pick one
    h [field]   every value one field has had, pick one
    u / U       save to / remove from your universe
    b           go back a step
    x           skip this step          q        save and quit
    ?           help

Things carry forward. The title's motif (the thing it's "about") turns up in
the premise, spine and twist. A name or place invented inside a title usually
becomes your protagonist or setting. Genre nudges later steps toward fitting
ideas. If you go back and change something, later steps get the new name or
place swapped in automatically.

Commands work with or without a space: `f 4` and `f4` both reroll field 4.
Rerolling or editing one field also updates other fields in the same item
that mentioned it, so a new landmark changes the rumor about it too.

## Where things live

- Stories: `~/.storywheel/stories/` (one JSON file each)
- Your universe: `~/.storywheel/universe.json`
- Markdown: `~/storywheel/`, rewritten on every keep

Point the markdown straight into your vault so stories show up in Obsidian as
you roll (add this to `~/.bashrc`):

    export STORYWHEEL_OUT=~/path/to/vault/Stories

## Your universe

Press `u` on anything you like and it's saved for future stories. When you
start or resume a story with things in your universe, you'll be asked whether
to pull from it: no, mix it in (about a third of rolls), or only from it.
Characters and settings work best here, since they become recurring people
and places across stories.

## Make it yours

All the words live in JSON files, not Python. Open them, add lines, save.

    storywheel/data/lists/<slot>/<name>.json       word lists (jobs, things, places, ...)
    storywheel/data/templates/<slot>/<name>.json   sentence templates (beats, premises, titles, twists)
    storywheel/data/genres.json                    what each genre favors

Your own lists go in `~/.storywheel/lists/<slot>/` (and templates in
`~/.storywheel/templates/<slot>/`). They are merged with the built-in ones, and
a file at the same path as a built-in one replaces it. That's how you build
your own world over time. Run `pipx install --editable .` to edit the built-in
files and see changes at once.

### A list

    { "_note": "anything you like",
      "slot": "job",
      "tags": ["western", "historical"],
      "entries": ["drover", "saloon keeper", "marshal",
                  {"text": "bounty hunter", "tags": ["noir"]}] }

* `slot` is the kind of thing the list supplies: `job`, `thing`, `someone`,
  `place`, `landmark`, `disaster`, and so on. Many lists can share a slot.
* `tags` describe the list's flavor. Plain strings inherit them. An entry
  written as `{"text": ..., "tags": [...]}` carries its own tags instead.
* A list can say `"generator": "faker.city"` instead of `entries`; it is then
  made up at run time. Built in: `faker.first_name`, `faker.last_name`,
  `faker.city`, `faker.job`, `wonderwords.adjective`, `wonderwords.noun`,
  `wonderwords.verb`. (Faker lists are tagged `modern`.)
* Invented names skip anything under four letters and ordinary dictionary words
  (no "Thistle" or "Bell" from a surname list).
* A list of names can say `"markov": 0.5`: that share of picks is then a new
  name invented by a small Markov-chain name maker trained on the list's own
  entries (so `Calloway, Hollis, Pruitt` can yield `Callis` or `Pruden`); the
  rest are the real entries. Good for name lists with 40+ entries.
* Place names can be built from parts. A `place` entry may contain building
  blocks, e.g. `"{PLACE_ADJ} {PLACE_FEATURE}"` draws from the `place_adj` and
  `place_feature` lists, so a few dozen words make thousands of towns.

### A template

Same shape, in `templates/`. Slots are `title`, `premise`, `twist`, and the
spine beats `once`, `routine`, `inciting`, `reaction`, `escalation`, `climax`,
`resolution`. Inside a template:

* `{UPPERCASE}` is a building block: a fresh draw from the slot of the same
  name every time it appears (`{THING}` draws from the `thing` lists).
  `{ODDITY}` (a random adjective and noun) and `{ALLITERATION}` are built in.
* `{lowercase}` refers to what the story has already kept (`{first}`, `{name}`,
  `{place}`, `{landmark}`, `{motif}`, `{rival}`, ...) and stays the same
  throughout. If the story doesn't have it yet, it's invented on the spot from
  the slot of that name.

Add a line to a block and every template that uses it improves.

### Threads

When a spine beat draws a {THING}, {SOMEONE}, {MESSAGE} or {DISASTER}, the story
remembers it as a **thread**. Later beats can say `{the_thing}`,
`{the_someone}`, `{the_message}` or `{the_disaster}`, which come out as "the
locked box", "the stranger": the same one, now definite. A template that uses a
thread is six times likelier while that thread exists, and never used when it
doesn't, so what "One day" brings in comes back in "Because of that" and "Until
finally". Threads are listed on the spine card, saved in the story file, and
written to the markdown under "Threads".

Rerolling the beat that introduced a thread (`f`) keeps the story straight: if
the new beat brings in a new one of that kind, the thread is updated and every
mention of the old one is swapped; if not, the old one lives on as long as a
later beat still mentions it (that mention turns back into an introduction) and
is retired when none does.

### Motif kinds

A title noun can say what kind of thing it is, so the story doesn't try to
"find the marshal" or "bury the mesa":

    "entries": ["lantern", {"text": "marshal", "kind": "person"},
                {"text": "raven", "kind": "creature"}, {"text": "mesa", "kind": "place"},
                {"text": "curse", "kind": "idea"}]

Kinds are `object` (the default), `person`, `creature`, `place`, `idea`; a whole
list can have a `"kind"` too. In templates, `{the_motif}` is "the lantern" when
the motif is an object, and otherwise falls back to the story's thing (or a fresh
{THING}). Plain `the {motif}` is for places where any kind will do. A person or
creature motif is sometimes offered as a {SOMEONE} ("the marshal rode in").

### Genres, tags and the story mix

`genres.json` gives each genre default weights for tags:

    "western": { "western": 3, "historical": 2, "rural": 1, "general": 1, "modern": 0.2 }

When you keep a genre (or two), their profiles are averaged into **this
story's mix**. Rolling a slot then works in two stages:

1. **Pick a list**, weighted by the mix. A list's weight is the *largest*
   weight among its tags (not the sum, so carrying many tags isn't an
   advantage).
2. **Pick an entry** from it, avoiding recent repeats (nothing comes back until
   about half the list has been used). Plain entries weigh 1; an entry with its
   own tags weighs what those tags weigh in the mix, so a `western` entry is
   much likelier in a western story.

**Wildcard floor:** a list the mix doesn't mention still gets a small slice of
each pick (12%, `_floor` in `genres.json`), so off-genre surprises still turn
up. Slots that repeat all through a story (rival, job, place, names, landmark)
get a lower one, 4%, set per slot under `_floors`, so an off-genre rival doesn't
appear in half the sentences. **Exclusion is absolute:** a tag or list you exclude gets weight
zero and the floor never brings it back. (One exception so rolls never come
up empty: if *every* list for a slot is excluded, the exclusions are ignored
for that slot.)

A genre name that has no profile still works: it becomes a tag with weight 3,
so `steampunk` will favor lists tagged `steampunk`. You can add profiles in
`~/.storywheel/genres.json`.

Each story keeps its own copy of the adjustments (excluded tags, excluded
lists, boosts) in its JSON file under `"mix"`. They never change the genre
profiles, so the next story in the same genre starts from the defaults.

`storywheel/steps.py` holds the step list. Reorder `STEPS` to change the flow,
or add a new `Step` with its own fields.

### Trying a genre mix

    storywheel sample western "fairy tale" -n 10 --seed 1

prints whole stories (title, protagonist, setting, premise, spine, twist) for
that mix without an interactive session and without saving anything. It's the
quickest way to judge a list you've just written. `--seed` makes it repeatable.

Which words belong to which genre is spelled out in `SOURCES.md`, along with
where every list came from and its license.

## Development

    pip install -e '.[dev]'
    pytest

### Building lists

Hand-writing a list straight into `storywheel/data/lists/` is often best. For
broad pools, scripts in `tools/` fetch raw candidates into `data/raw/` (never at
run time); trim them by hand, put the cleaned result in `storywheel/data/lists/`,
and note it in `SOURCES.md`. Check a source's license before using anything from
it. For example, `python tools/fetch_corpora.py` gets two files from the CC0
corpora repository.
