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

    storywheel              start a new story (a full-screen app)
    storywheel --plain      the same, with a simple prompt instead of the app
    storywheel list         list your stories
    storywheel show [N]     print a story as plain text
    storywheel resume [N]   pick up where you left off (N from list; default newest)
    storywheel export N --out ~/vault/Stories     copy a story's markdown somewhere
    storywheel sample western "fairy tale" -n 10   print sample stories for a genre mix
    storywheel report       the worst-rated lines and the frames that produced them
    storywheel universe     show what you've saved to your universe
    storywheel universe rm KEY N   remove an entry, e.g.  universe rm spine 1

`list`, `show`, `export` and `sample` take `--json` (one JSON document on stdout, nothing
else) so another program, such as a Neovim plugin, can drive the engine. Each story has
`id`, `title`, `genre`, `mood`, `structure`, `kept` (every kept step's fields), `text`
(plain text), `markdown`, `path`, `step`/`steps`/`done` and `resume`. `storywheel show 1
--json`, `storywheel sample western -n 3 --seed 1 --json` and `storywheel list --json` are
the three shapes; a seeded `sample` is repeatable. `show` exits 1 with `{"error": ...}`
when there is no such story.

### The app

It is meant for a full-screen desktop terminal (it needs room for three columns).

    +--------------+--------------------------+----------------------+
    | Steps        |  card: the candidate     | The story so far     |
    |  ✓ Genre     |    name  Wade Hollis ▲▼  |  ● Spine was built   |
    |  ● Spine     |    job   drover      ▲▼  |    on a stand-in ... |
    |  ▶ Premise   |  [Roll][Keep][Back]...   |                      |
    | Universe     +--------------------------+  THE LANTERN OF ...  |
    |  ▶ Setting   |  History: every roll     |  PROTAGONIST         |
    | Past stories |   #1 ... #2 job: ...     |    Name  Wade ...    |
    +--------------+--------------------------+----------------------+
     space Roll  k Keep  q Quit  ? Help  f Field  e Edit  ...  c Copy story

**Left:** the steps, your universe, and your past stories. **Middle:** the card and its
history. **Right:** the story so far, kept content only, as plain text, with problems
listed at the top.

Step markers: `✓` kept, `–` skipped, `▶` current, `·` still to do, **yellow `●`**
kept but built on a stand-in or on something that has since changed, **red `✗`** it
refers to something that no longer exists (say the protagonist was skipped after the
body was kept). Click a flagged step, or press Enter on it, to go there; the right
column says what is wrong.

The card shows the current candidate; up and down select a field. The history lists
every roll of the step and what changed in each; Tab moves between the lists, and Enter
on a history row picks that one. Select a field and press `h` and the history becomes
**that field's own history**, so you can bring an old value back without losing the rest
(`h` again returns to every roll).

    space / enter   roll again          k      keep it and move on
    f               reroll the field    e      edit the field in place
    E               edit in $EDITOR     w      write your own
    + / -           like / dislike      u / U  save to / remove from your universe
    h               history             m      the mix editor
    v               universe panel      enter  reroll the selected field
    c               copy the story so far to the clipboard, as plain text
    b               go back a step      x      skip this step
    q               quit (asks)         ?      help

**Past stories** (bottom left): Enter opens one (the story you leave is saved), `d`
deletes one after asking, `p` / `s` send its protagonist / setting to your universe.
Buttons do the same.

**Quitting:** `q` asks "Keep this story or delete it?". Keep saves it; after the app
closes it prints the story as plain text, then the markdown path and the command to
resume it. Delete removes the story and its markdown file (your universe is untouched).

**Clipboard:** `c` copies the story so far, as plain text, with `wl-copy`, `xclip`,
`xsel`, `pbcopy` or `clip.exe` (whichever the machine has), else through the terminal's
own clipboard escape (OSC 52).

You go through the steps in order: genre & mood, structure, title, protagonist,
setting, premise, story body, twist. Things carry forward. The title's motif (the
thing it's "about") turns up in the premise, body and twist. A name or place invented
inside a title usually becomes your protagonist or setting. Genre nudges later steps
toward fitting ideas. If you go back and change something, later steps get the new
name or place swapped in automatically. Rerolling or editing one field also updates
other fields in the same item that mentioned it, so a new landmark changes the rumor
about it too.

### Stand-ins and stale candidates

The sidebar lets you jump ahead. If you roll a step before the ones it builds on are
kept (the story body before the protagonist, say), it invents **stand-ins** (a first
name, a job, a place) and the card says so. Each candidate remembers which earlier
fields it was built from. When you later keep those steps, a candidate built on a
stand-in shows a banner, "Built for Mark; your protagonist is now Stacie Anderson",
with **Update** (`a`: swap the kept values into a copy), **Reroll**, and **Ignore** (dismiss the banner; the candidate stays as it is).
Stale rows in the history are marked. A single-field reroll always uses what you have
kept, never an old stand-in. If you keep a step that was built on a stand-in and then
keep the real one, the kept text is updated for you.

### The mouse

The app has the mouse (over SSH too, in most terminals). On the card:

    click a field        reroll just that field (like f)
    right-click a field  edit it in place (like e)
    scroll over a field  step through that field's earlier values
    click ▲ or ▼         rate that line (like + and -)

Enter on a highlighted field rerolls that field, the same as a click; space rolls the
whole step. A row of buttons under the card does Roll, Keep, Back, Skip and Mix. Click a
step to jump to it and a history row to pick it. While the app has the mouse, select
text in the terminal by holding **Shift** while you drag (some terminals use Alt, or
Option on a Mac).

### The universe panel

The bottom half of the left column holds your universe, grouped by kind (Protagonist,
Setting, ...); Enter or a click opens and closes a group. `v` moves the keyboard there.

    enter / click an entry   preview it
      in the preview:  enter or u = use in this story,  e = edit,  d = delete (asks first)
    n or [+ New]             write a new entry from scratch, in that kind's fields
    t or [Use: ...]          for this story: no / mix it in / only from the universe

"Use in this story" adds the entry as a new candidate for its step (jumping there if you
are elsewhere). Nothing is kept until you press `k`, and kept steps never change. Blank
boxes in a hand-written entry are filled in with an ordinary roll when it is used.

### The mix editor

Press `m` for this story's mix: every tag with its genre default, your boost, and its
weight now, and (Tab) every list. `e` excludes a tag or list, `+`/`-` boost or soften a
tag, `0` clears a boost, `r` resets to the genre defaults. **It edits this story only**
and says so on screen: the genre profiles never change, and it affects future rolls,
not what you have kept.

### Ratings

Press `+` or `-` on a line (the selected field; on a one-field step, the whole thing).
A ▲ or ▼ marks it. Each rating is saved in `~/.storywheel/ratings.json` with the frame
(template) and atoms that produced the line. Over time the tool leans away from what
keeps getting `-`, gently: one dislike is no evidence at all; a frame, or a pair of
atoms ("buried" + "a mule"), with a net score of -2 is drawn a fifth less often, and so
on down to a floor of 25%, never to zero. A single atom is only touched at net -3, and
less. Press the same key again to clear a rating. `storywheel report` lists the
worst-rated lines, the frames that produced them (and how far each is down-weighted),
and the atom pairs that keep getting `-`. A seeded `storywheel sample` ignores ratings,
so it stays repeatable.

### The plain prompt

`storywheel --plain` (also used automatically when there is no terminal, as in a
pipe) is the original prompt loop. It works on a dumb terminal over a slow link:

    enter / r   roll again              k        keep it and move on
    f [field]   reroll one field        e [field]  edit a field in place
    E           edit in $EDITOR         w        write your own
    + / - [field]  like / dislike       p N      pick earlier roll #N
    h           every roll so far (what changed), pick one
    h [field]   every value one field has had, pick one
    u / U       save to / remove from your universe
    b           go back a step
    x           skip this step          q        save and quit
    ?           help

Commands work with or without a space: `f 4` and `f4` both reroll field 4.

## Where things live

- Stories: `~/.storywheel/stories/` (one JSON file each)
- Your universe: `~/.storywheel/universe.json`
- Ratings: `~/.storywheel/ratings.json`; recent picks: `~/.storywheel/recent.json`
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
templates, built from the same atoms. Three ship in `storywheel/data/structures/`:

* **Story Spine**: Once upon a time, Every day, One day, Because of that (twice), Until
  finally, Ever since then. The fixed openers are the only frozen text anywhere.
* **Three-Act Outline**: setup, inciting incident, first turn; rising action, midpoint,
  crisis; climax, resolution.
* **Kishōtenketsu**: introduction, development, a surprising turn, reconciliation. No
  conflict required.

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
same check runs in the test suite.

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
