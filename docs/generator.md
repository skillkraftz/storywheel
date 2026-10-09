# Writing content for the generator

Moved here from the README (polish 2, ISSUES #22), unchanged except for this heading. It describes the Wheel's data files: atoms, templates, features,
structures, threads and genres. It was last checked against the program in batch 18, not in polish 2; where it disagrees with the files in
`storywheel/data/`, the files are right (CLAUDE.md: the data files are the source of truth). For using storywheel, read [manual.md](manual.md).

## Wheel storage

- Stories: `~/.storywheel/stories/` (one JSON file each)
- Ratings: `~/.storywheel/ratings.json`; recent picks: `~/.storywheel/recent.json`
- Markdown: `~/storywheel/`, rewritten on every keep

Point the markdown straight into your vault so stories show up in Obsidian as
you roll (add this to `~/.bashrc`):

    export STORYWHEEL_OUT=~/path/to/vault/Stories

## Make it yours

Stories are **assembled from parts**, not dealt from a deck of ready-made ideas. Two
kinds of file, both plain JSON:

* **Atoms** (`storywheel/data/lists/<slot>/<name>.json`) are short pieces: a noun
  phrase, a verb, a prize, a deadline, a motive. Five words at most, no full clauses.
* **Templates** (`storywheel/data/templates/<slot>/<name>.json`) are generic sentence
  frames with at least two slots, like `{first} {ACT_PERSON} {SOMEONE} {MANNER}`. A
  template may not hold more than six fixed words in a row, so the ideas come from
  the atoms and not from the frame.

One template with three slots over pools of fifty atoms is over a hundred thousand
sentences. Add atoms freely; they improve every template that uses them. Genre
lives on the atoms (a `western` verb, a `fairy tale` prize), so a template written once
reads right in any genre.

Your own files go in `~/.storywheel/lists/<slot>/`, `~/.storywheel/templates/<slot>/` and
`~/.storywheel/structures/`. They are merged with the built-in ones, and a file at the
same path as a built-in one replaces it. Run `pipx install --editable .` to edit the
built-in files and see changes at once.

`pytest` includes a lint that enforces those rules on every file, so a line that is too
long, a clause where an atom should be, or a frozen template fails the build.

### An atom list

    { "_note": "anything you like",
      "slot": "act_person",
      "tags": ["general"],
      "entries": ["trusted", "lied to", "teamed up with",
                  {"text": "outdrew", "tags": ["western"]}] }

* `slot` is the kind of part: `someone`, `thing`, `message`, `disaster`, `hiding`, `close`,
  `landmark`, verbs (`act_person`, `act_thing`, `act_place`, `act_message`, `act_event` in
  the past tense; `do_thing`, `do_person` in the base form; `habit_thing`, `habit_person`,
  `habit_place` in the present), and abstractions (`prize`, `deadline`, `motive`, `vice`,
  `value`, `temptation`, `feeling`, `manner`, `topic`, `crime`, `loss`). Many lists can share
  a slot. Verbs take their object directly ("trusted" + a person), and atoms never say
  "their" or "them", because they are reused in many sentences.
* `tags` describe the list's flavor. Plain strings inherit them. An entry written as
  `{"text": ..., "tags": [...]}` carries its own tags instead.
* A list can say `"generator": "faker.city"` instead of `entries`; it is then made up
  at run time. Built in: `faker.first_name`, `faker.last_name`, `faker.city`, `faker.job`,
  `wonderwords.adjective`, `wonderwords.noun`, `wonderwords.verb`. (Faker lists are
  tagged `modern`.)
* Invented names skip anything under four letters and ordinary dictionary words
  (no "Thistle" or "Bell" from a surname list).
* A list of names can say `"markov": 0.5`: that share of picks is then a new name
  invented by a small Markov-chain name maker trained on the list's own entries (so
  `Calloway, Hollis, Pruitt` can yield `Callis` or `Pruden`); the rest are the real
  entries. Good for name lists with 40+ entries.
* Place names can be built from parts. A `place` entry may contain slots, e.g.
  `"{PLACE_ADJ} {PLACE_FEATURE}"`, so a few dozen words make thousands of towns.

### A template

    { "slot": "reaction", "tags": ["general"],
      "entries": ["{ACT_PERSON} {SOMEONE} {MANNER}",
                  "made a deal with {SOMEONE} for {PRIZE}",
                  {"text": "saddled up and rode to {landmark} {MANNER}", "tags": ["western"]}] }

* `{UPPERCASE}` is an atom slot: a fresh draw from the slot of the same name every time
  it appears (`{SOMEONE}` draws from the `someone` lists). `{ODDITY}` (a random
  adjective and noun) and `{ALLITERATION}` are built in.
* `{lowercase}` refers to what the story has already kept (`{first}`, `{name}`, `{place}`,
  `{landmark}`, `{motif}`, `{rival}`, `{want}`, `{need}`, `{flaw}`, `{secret}`...) and stays
  the same throughout. If the story doesn't have it yet, it's invented on the spot from
  the slot of that name. `want`, `need`, `flaw`, `secret` and `rumor` are themselves
  template slots, so even the character's inner life is assembled.
* The template slots are `title`, `premise`, `twist`, `want`, `need`, `flaw`, `secret`,
  `rumor`, and the beats of each structure (below).

### Making sentences make sense: features and frames

Random parts can be grammatical and still meaningless ("enchanted the wicked stepmother",
"the hot springs was built over a black stallion"). So atoms carry a few **features**, and
frames **require** them. The whole vocabulary is small and lives in `storywheel/frames.py`:

| | Feature | Means |
|---|---|---|
| things | `portable` | one person can carry it (the default) |
| | `buryable` | can be buried or hidden underground (the default) |
| | `magic` | magical; for a person, able to do magic |
| | `valuable` | worth money |
| | `living` | an animal: not buried, burned or locked in a box |
| | `bulky` | too big for a pocket or a small hiding place |
| | `paper` | letters, maps, deeds, books: can be forged or copied |
| people | `human` | a person (the default for `someone`) |
| | `creature` | not human: a talking fox, a troll |
| | `friendly`, `threatening` | kindly, or dangerous |
| | `authority` | holds office or power: a sheriff, a queen |
| places | `built`, `natural` | a made structure, or not |
| | `indoor`, `outdoor` | roofed, or open air (the default for landmarks) |
| | `diggable` | has ground something can be buried in |
| disasters | `manmade` | caused by people (a robbery, a feud) |
| | `strikes` | can hit a place (weather, plague, war), unlike "the death of the king" |
| messages | `physical` | something you can hold (the default for messages) |
| prizes | `material`, `social`, `inner` | owned, a standing among people, or not something to be given |
| verbs | `mundane` | an everyday action: what routines are made of |
| | `gentle` | a kind or reconciling act, for endings |
| | `stows`, `trades` | puts something somewhere; gives something up for something |
| manners | `speech`, `carrying`, `feeling` | a spoken manner ("in whispers"), one that needs something in hand ("with drawn steel"), a state of mind ("in silent dread"). Drawn only where a frame asks for it, e.g. `{MANNER:speech}` |
| when | `modern`, `period` | needs present-day technology (a burner phone); belongs to an older time (a telegram). An atom with neither fits any time; a story's era (or, before one is chosen, its genre: noir, western, fairy tale, fantasy and adventure are `period`; thriller, heist and coming-of-age `modern`, in genres.json `_tech`) keeps out the other kind |
| age (jobs) | `child`, `teen`, `adult`, `elder` | who can do the job: a protagonist's age falls in a band the job fits (paperboy and class president are `teen`, "retired ..." is `elder`). A job with none is `adult`, and an adult's job is open to an `elder` too. Each genre's protagonist ages are in genres.json `_ages` (coming-of-age 13 to 19, the rest 20 to 80) |
| anything | `plural` | takes "are" and "were": "the stockyards", "two scarred brothers" |

An atom lists its own features (a list sets defaults for its entries); anything not listed
gets its slot's default:

    {"text": "a black stallion", "features": ["living", "valuable"]}

**Verbs say what they need** of whoever does them and whoever they are done to. Requirements
are lists: `"buryable"` has it, `"!living"` must not, `"magic|authority"` either:

    {"text": "buried",    "object": ["buryable"]}
    {"text": "enchanted", "subject": ["magic"]}
    {"text": "hid",       "object": ["!living"], "features": ["stows"]}

The frame doesn't say which slots those are; the order of the sentence does. A verb's subject
is the nearest person before it who isn't already some other verb's object (the opener's
`{first}` counts) and its object is the next slot after it of the right kind (a person, thing,
place, message or disaster). A hiding place's subject is the thing it hides. So
`{first} {ACT_THING} {THING} {HIDING}` can only ever say "buried a locked box in a hollow
oak", never "buried a mule in a boot".

**Frames can demand features of any slot**, with a colon:

    {THING:buryable}     {CLOSE:human}     {PRIZE:!inner}     {SOMEONE:authority}
    {ACT_THING:mundane}  {landmark:built}  {the_thing:!living}

A frame whose requirement the story can't meet (a `{landmark:built}` frame in a story whose
landmark is a lake) is simply set aside for that story. Character fields are strict this way:
a **want** is something a person could actually get (`{PRIZE:!inner}`), a **need** is an inner
lesson only (`{DO_PERSON:inner}`: forgive, trust, make peace with), a **routine** uses only
`mundane` verbs, and a **secret** is something a person could hide.

**Agreement**: `{is}`, `{was}`, `{has}` and `{does}` agree with the noun before them ("the
stockyards **were** built over..."), and `{lies|lie}` picks its first form for a singular
subject, the second for a plural one. Present-tense verbs take only singular subjects.

The solver fills the nouns first, then picks verbs that fit the nouns it got, and starts
over when a verb has nothing to fit. **`pytest` checks every frame in the data**: each
slot can be satisfied by at least 3 atoms, and at least half of all draws succeed first time,
so a restriction can never starve a slot. A further test re-verifies every choice the
solver makes across thousands of real stories.

A **reframing** beat (kishotenketsu's *ten*) goes further: it may only reinterpret something
already established, so its templates use threads and the story's own fields, never a fresh
person, object or event.

### Nothing repeats

* **Within a story, no atom is used twice.** Each kept step records the atoms it used;
  later steps and rerolls avoid them (and a reroll avoids what the rest of its own item
  uses). Only if a list truly runs out does the rule relax.
* **Across sessions, recent picks are remembered** in `~/.storywheel/recent.json`: an
  entry isn't offered again until about half its list has been used, even next week.
  (`storywheel sample` never reads or writes it, so a seed always means the same stories.)

### Structures

A story's body is shaped by a **structure**: an ordered list of beats, each with its own
templates, built from the same atoms. Ten prose structures ship in `storywheel/data/structures/` (and two screen ones):

* **Story Spine**: Once upon a time, Every day, One day, Because of that (twice), Until
  finally, Ever since then. The fixed openers are the only frozen text anywhere.
* **Three-Act Outline**: setup, inciting incident, first turn; rising action, midpoint,
  crisis; climax, resolution.
* **Kishōtenketsu**: introduction, development, a surprising turn, reconciliation. No
  conflict required.
* **Save the Cat** (15 beats), **Hero's Journey** (12), **Seven-Point** (7): for a novel.
* **Freytag's Pyramid**: the tragic shape, for a short story or a novel.
* **Single Moment** (3 beats), **Circular Story** (it returns to its opening image) and **In Medias Res**: for flash fiction and
  short stories.

`"formats"` in the file says which formats offer a structure (`flash`, `short-story`, `novel`, `feature-film`, `short-film`); without it a
structure fits the short story and the novel. The pickers and a random roll offer only the ones that fit the draft's format.

In a session, the **Structure** step comes right after Genre & mood; roll to see another,
`k` to keep. Changing it later rolls the story body again. `storywheel sample` picks one
at random per story; force one with `--structure three-act`.

A structure is a small file, so you can add your own:

    { "name": "five-beats", "label": "Five Beats", "blurb": "One line about its shape.",
      "show_labels": true, "order": 4,
      "beats": [ {"key": "hook", "slot": "five_hook", "label": "The hook"},
                 {"key": "dig", "slot": "five_dig"}, ... ] }

Each beat's `slot` names a template list (`templates/five_hook/*.json`). A beat may also
have an `"opening"` ("Once upon a time, ") and a `"closing"` (default `"."`).

**Reuse a slot before you write one.** The `act_*` slots are whole sentences with no opener (`act_setup`, `act_incident`, `act_turn`,
`act_trials`, `act_midpoint`, `act_crisis`, `act_climax`, `act_resolution`), `ki`, `ketsu` and `ten` are quiet ones, and `theme`, `debate`,
`reward`, `opening_image`, `echo` and `in_the_thick` came with batch 21. Name them in the beats of the new structure, as `feature-film.json`
and `save-the-cat.json` do. Beat keys must be unique across every structure (prefix them: `stc_`, `hj_`). Write a new slot only when nothing
fits, and give it a `general.json` (`"tags": ["general"]`): a genre with no file of its own for a slot falls back to the general frames, so
every genre renders. Add genre files later, as for any slot.

**Endings.** A climax or resolution frame may say which endings it is for: `{"text": "...", "ending": ["tragic", "open"]}` (names from
triumph, bittersweet, tragic, open; a string works for one). An untagged frame fits any ending. With an ending picked on the Genre step, a
frame for other endings is never drawn, and a beat whose slot has frames for the picked ending draws from those alone six times in ten
(`steps.ENDING_SHARE`), because the genre files carry no ending and would drown them out. Tag more frames, and write more of them, to give an
ending more variety; `tests/test_endings.py` asks for at least three frames of each ending in each of the five climax and resolution slots.

**Focus.** A story whose focus is a place or no one has no protagonist (`storywheel/focus.py`). Frames that read `{name}`, `{last}`, `{age}`,
`{job}`, `{trait}`, `{want}`, `{need}`, `{flaw}`, `{secret}` or `{rival}` are set aside for it, and so are `{first}'s` and any title that says
`{first}`; `{first}` becomes "everyone in {place}" (a place) or "someone" (no one). A frame meant to work for such a story should use only
`{first}`, `{place}`, `{landmark}`, `{season}` and the atoms.

**Repeatable beats.** A beat can say it may occur several times in a row, with a minimum (at least 1) and a maximum:
`{"key": "because_2", "slot": "escalation", "label": "Because of that", "repeat": {"min": 1, "max": 4}}`. The Story Spine's
second "Because of that" (up to 4), the Three-Act's rising action (up to 4) and Kishōtenketsu's development (up to 3) do. In the Wheel,
on the story body, `A` (or the +Beat button) adds another of the beat under the cursor, rolled to follow the others and free to reuse the
threads in play, and `X` (-Beat) takes one out; later ones move up, a thread nobody mentions any more retires, and the step's history starts
again because its shape changed. Keeping stores how many there are (`repeats` in the draft); promotion writes it to `story.md`
(`repeats: because_2=2`). In the Builder, on the outline, `A` and `X` do the same to the beat under the cursor (the new one is rolled
with the generator for the universe and its protagonist). The extra beats are keyed `because_2__2`, `because_2__3`...

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

**Neighbors:** the floor is not spread evenly over every other genre. `_neighbors` in `genres.json` names, for each genre, the
tags of the genres next door (fantasy: mythological, adventure; romance: comedy, domestic, coming-of-age, historical...). The floor's
share goes to untagged lists and lists of neighboring genres; genres that are not neighbors get a tenth of it between them, and where
a slot has no neighbor lists at all the floor shrinks to that tenth. So a fantasy story gets no insurance adjuster, and a comedy no
dragon's blood. A genre with no `_neighbors` entry keeps the even floor.

**Frames are the genre's own.** Neighbors and the floor lend pieces (people, things, places, names, verbs), never frames: a story's titles,
premises, twists and beats come only from its own genres' frames and the general ones (a general frame tagged for another genre is left out).
So a mystery can meet a thriller's courier, but it is never titled like a thriller.

**People fit the protagonist's age.** Close people and passing characters can say which protagonists they fit, with the same age bands as
jobs (`child`, `teen`, `adult`, `elder`): a coming-of-age protagonist has a coach, a best friend and a first crush, never a spouse or a best
customer, and is never visited by an old flame.

**Moods** lean the same way: each mood in `lists/mood/general.json` is tagged with the genres it suits ("absurd" is comedy's, "eerie"
is horror's), so "comedy · eerie" is rare. **Era and season agree**: an era that names a season ("the week before Christmas") sets it
(`data/seasons.json` lists the words).

**Written genres:** western, fairy tale, comedy, fantasy, mystery, horror, sci-fi, romance, ghost story, noir, thriller, heist, adventure and coming-of-age have their own
names, jobs, places, things, people, troubles, title words and frames for every beat.

A genre name that has no profile still works: it becomes a tag with weight 3,
so `steampunk` will favor lists tagged `steampunk`. You can add profiles in
`~/.storywheel/genres.json`.

Each story keeps its own copy of the adjustments (excluded tags, excluded
lists, boosts) in its JSON file under `"mix"`. They never change the genre
profiles, so the next story in the same genre starts from the defaults.

`storywheel/steps.py` holds the step list (`steps_for`). Reorder it to change the flow,
or add a new `Step` with its own fields.

### Trying a genre mix

    storywheel sample western "fairy tale" -n 10 --seed 1

prints whole stories (title, protagonist, setting, premise, spine, twist) for
that mix without an interactive session and without saving anything. It's the
quickest way to judge a list you've just written. `--seed` makes it repeatable.

Which words belong to which genre is spelled out in `SOURCES.md`, along with
where every list came from and its license.

### Is it assembled, or dealt?

    python tools/repetition_report.py western "fairy tale" -n 200 --seed 101

rolls 200 stories in memory and reports the entries picked far more often than their
fair share, the rendered lines seen again and again (names blanked out), and any
frozen templates or over-long atoms. A healthy run has no line seen five times. The
same check runs in the test suite. An entry 5 standard deviations above chance (and 3x its
share, 5+ picks) is a failure; one between 4 and 5 is listed as "watch", so a real repeat
is seen before it grows.

    python tools/genre_check.py

checks all fourteen genres at once and prints a markdown table: how much of a story comes
from the genre's own material, repeats and watch items, lint, how many frames it shares
with another genre (identical, and 93% alike), its technology and whether any story broke
it, its protagonists' age range and whether any job broke it, its core vocabulary and its
neighbors.

