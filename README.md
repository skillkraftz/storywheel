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
each pick (12%, set by `_floor` in `genres.json`), so off-genre surprises
still turn up. **Exclusion is absolute:** a tag or list you exclude gets weight
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

## Development

    pip install -e '.[dev]'
    pytest
