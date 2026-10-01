# storywheel — project brief

storywheel is a terminal tool for beating writer's block. You build a story one
piece at a time: roll a piece, reroll until something clicks, edit it if you
have a better idea, keep it, and move on. Each kept piece feeds the rolls that
come after it. The output is one markdown file per story, ready for Obsidian.

The owner is a writer, not a power user of this tool. It should feel like
spinning a wheel, not filling in a form. It runs on a Raspberry Pi, usually
over SSH, so it must stay light, fast, and fully offline at run time.

A working v1 exists (the `storywheel/` package in this repo). It proved the
core loop works and that the output can be genuinely useful. v2 keeps every v1
behavior described under "Behavior to keep" and fixes what testing exposed.


## Why v2: what testing showed

The engine works; the data is the problem. Genre barely influences anything.
Only a few lists carry genre tags, and everything else ignores genre: titles
come from wonderwords picking random dictionary words (a western fairy tale
got "Absent Giraffes" after 21 rolls), and names, jobs and towns come from
Faker, which produces modern American people. A "western / fairy tale" story
gets a management consultant named Kayla in Juliefurt.

Whole-sentence lists repeated quickly. v1 fixed this with building-block
templates (see below), which works well and should carry over.

The scrolling terminal output is hard to use. Long sessions scroll endlessly
and history is hard to browse. v2 needs a real TUI.


## Core design: lists, tags, genre profiles, and the story mix

All content lives in JSON data files, not Python. Four ideas carry the design.

A **slot** is a kind of thing a template needs: `name`, `job`, `place`,
`landmark`, `thing`, `someone`, `disaster`, `title_noun`, and so on. Every
placeholder in a template names a slot.

A **list** is one JSON file that supplies entries for one slot and carries
tags describing its flavor. For example, `lists/job/frontier-trades.json` has
slot `job` and tags `western, historical`, while
`lists/thing/mythological-artifacts.json` has slot `thing` and tags
`fantasy, mythological`. Many lists can supply the same slot.

A **genre profile** gives default weights to tags. The `fantasy` profile might
weight `fantasy` 3, `mythological` 2, `medieval` 2, `modern` 0.2. Profiles
are the "preset links" between genres and lists, and they ship with the app in
`data/genres.json`.

The **story mix** is what actually drives rolling for one story. When genres
are kept, their profiles are blended (equal weight by default) into the
story's mix. The user can then adjust that mix for this story only: exclude a
tag, exclude one specific list, boost something, or reset to defaults. These
adjustments are saved inside the story's JSON file and never change the
genre profiles. Turning off `mythological` in one fantasy story does nothing
to the next fantasy story, which starts from the defaults again.

Picking an entry for a slot works in two stages. First pick a list, weighted
by the story mix: a list's weight comes from its tags (sum or max of matching
tag weights; choose one and document it). Then pick an entry from that list,
avoiding recent repeats (v1's "no repeat until about half the list is used"
rule).

Two rules keep this from becoming a closed box. **Wildcard floor:** any list
the mix doesn't mention still gets a small floor weight (start around 10–15%
of total pick probability, configurable), so off-genre surprises still happen
occasionally. **Exclusion is absolute:** a tag or list the user excluded gets
weight zero, ignoring the floor. The user said it plainly: "if I'm tired of
mythological stuff, I can exclude it for that story."

Entries can optionally carry their own tags as `{"text": "...", "tags": [...]}`
for the rare entry that's more specific than its list. Plain strings inherit
their list's tags.

A sketch of the data shapes (adjust as needed, but keep them simple and
hand-editable):

```json
// data/lists/job/frontier-trades.json
{ "slot": "job", "tags": ["western", "historical"],
  "entries": ["drover", "saloon keeper", "marshal", "assayer", "stagecoach driver"] }

// data/genres.json
{ "western": { "western": 3, "historical": 2, "rural": 1, "modern": 0.2 },
  "fantasy": { "fantasy": 3, "mythological": 2, "medieval": 2, "modern": 0.2 } }

// inside a story file
"mix": { "base": ["western", "fairy tale"],
         "exclude_tags": ["mythological"], "exclude_lists": [],
         "boost": { "frontier": 1.5 } }
```

Users can add their own lists in `~/.storywheel/lists/`, which are merged with
the built-in ones. That's how someone builds their own world over time.


## Templates and building blocks (keep from v1)

Story beats, premises, titles and twists are templates, also stored as JSON
with tags. Uppercase placeholders like `{SOMEONE}`, `{THING}` or `{DISASTER}`
are building blocks, drawn fresh at every occurrence. Lowercase placeholders
like `{first}`, `{place}` or `{motif}` refer to what the story has already
kept and stay consistent. One template with three blocks yields thousands of
sentences; this is what made v1 rerolls feel open. In v2, blocks are just
slots, so they automatically draw from genre-weighted lists.

Titles must become genre-aware too. Replace wonderwords dictionary picks with
title templates whose slots draw from genre lists (`title_noun`, `title_adj`,
places, names). Keep `{ODDITY}` (random adjective + noun from a general
dictionary) as a deliberate occasional wildcard, not the default.

Names should come from genre name lists. A small Markov-chain generator
trained on each name list is a good way to get endless names that sound right
for the genre without repeating. Faker can remain one tagged source among
many (tag `modern`).


## Behavior to keep from v1

These all work in v1 and should survive the rewrite.

The step flow is ordered and forward-only: genre & mood, title, protagonist,
setting, premise, story spine (Once upon a time / Every day / One day /
Because of that ×2 / Until finally / Ever since then), twist. Later steps
read what earlier steps kept; earlier steps never need reworking. The step
order is defined in one place so it's easy to change.

At each step the user can roll again, keep, reroll a single field, edit a
field in place (pre-filled with the current text), edit the whole item in
`$EDITOR`, write their own, pick any earlier candidate, skip the step, go back
a step, and save and quit at any point. Rerolls avoid repeating anything in
that step's history.

Rerolling or editing one field updates other fields in the same item that
mention the old value (a new landmark updates the rumor about it). Going back
and changing a kept step swaps the old values into the new ones across later
steps (renaming the protagonist updates the spine).

The title produces a **motif**, the thing it's "about," which later steps
reuse. Names or places invented inside a title are saved as **seeds**, so the
first protagonist or setting roll tends to reuse them; rerolls ignore seeds.

The **universe** is a cross-story pool the user curates by saving pieces they
like (`u` to add, `U` to remove, plus a CLI `universe rm`). On starting or
resuming a story, if the universe isn't empty, ask whether to pull from it:
no, mix it in (about a third of rolls), or only from it. Characters and
settings are the natural universe items.

Small text polish that matters: a/an correction, rough singularizing of the
motif, using "their"/"them" after a character's first mention in a sentence,
and treating `f1` the same as `f 1`.

Storage is one JSON file per story in `~/.storywheel/stories/`, the universe
in `~/.storywheel/universe.json`, both overridable with `STORYWHEEL_HOME`.
Every keep rewrites the story's markdown file in `STORYWHEEL_OUT` (default
`~/storywheel/`): YAML frontmatter (title, genre, mood, motif, created, tags),
then sections separated by `---` plus
`<div style="page-break-after: always;"></div>` so it reads well in Obsidian
and prints with page breaks. If the title changes, the old file is replaced.

CLI commands remain: `storywheel` (new story), `list`, `resume [N]`,
`export N --out DIR`, `universe`, `universe rm KEY N`.


## The TUI (Textual)

Use Textual. It runs well over SSH and on a Pi. One screen, no scrolling back.
Suggested layout: a sidebar listing the seven steps with kept/skipped/current
markers, where any step can be selected to jump there; a main card showing the
current candidate, with fields selectable by arrow keys; and a history panel
listing every candidate for the step (showing what changed between rolls, as
v1's `h` does), browsable and selectable with the arrow keys. Selecting a
field and pressing a key should show that field's own history so an old value
can be brought back without losing the rest.

Keep the single-key feel from v1: space or enter to roll, `k` keep, `f` reroll
field, `e` edit field inline, `E` external editor, `w` write your own, `u`/`U`
universe, `b` back, `x` skip, `q` save and quit, `?` help. Show the keys in a
footer.

Add a **mix editor** screen for the current story: every tag (and, expanded,
every list) with its current weight, toggles to exclude, a way to boost, and
"reset to genre defaults." It edits only this story's mix and should say so on
screen. Changing the mix affects future rolls only; kept pieces don't change.

The plain v1-style prompt loop can stay as a fallback (`storywheel --plain`)
for dumb terminals, but it's optional.


## Building the content

Gather word lists at build time with scripts in `tools/`, never at run time.
Scripts write raw candidates to `data/raw/`; a human trims them; the cleaned
results go in `data/lists/` and ship with the package. Good sources, all to be
checked for licensing before anything is committed:

- Darius Kazemi's `corpora` repository (public-domain JSON lists made for text
  generators: occupations, objects, creatures, mythology, and more).
- WordNet via NLTK, for every word under a category (kinds of weapons,
  vehicles, buildings, occupations).
- The Datamuse API, for words associated with a seed term like "frontier" or
  "starship," useful for seeding a list.
- Public-domain books from Project Gutenberg (fairy tales, early westerns,
  early science fiction), mined for genre nouns and names with a
  part-of-speech tagger.

Target at least the 14 genres v1 offers (mystery, romance, horror, western,
sci-fi, comedy, fairy tale, heist, ghost story, coming-of-age, noir,
thriller, fantasy, adventure) plus cross-cutting tags like `modern`,
`historical`, `rural`, `urban`, `mythological`, `domestic`. Quality beats
volume: 40 good entries in a list are worth more than 400 noisy ones.


## Build plan

Work in stages, each one usable and tested before the next.

**Stage 1: data model and engine.** Move all v1 pools into JSON lists and
templates. Implement slots, tags, genre profiles, the story mix with
per-story overrides, weighted list picking with the wildcard floor and hard
exclusions, and no-repeat entry picking. Keep the v1 prompt interface working
on top of the new engine. Done when v1's behavior is preserved and tests pass.

**Stage 2: genre content.** Write the `tools/` scripts, build and curate
lists and name sets for every genre, and make titles and names genre-driven.
Done when a "western / fairy tale" story, rolled 200 times in a test, draws
the large majority of its names, jobs, places and objects from matching tags
(pick a threshold, around 80%), and the rest come from the wildcard floor.

**Stage 3: the Textual TUI**, including the mix editor and history panel.

**Stage 4: polish** from real use.


## Constraints and conventions

Python 3.9+, installable with `pipx install .`, exposing a `storywheel`
command. Keep dependencies few: Textual, plus whatever is truly needed at run
time. NLTK and other build-time tools belong in an optional dev extra, not
the runtime install. No network access at run time.

Tests use pytest with a seeded random generator so results are reproducible.
Test the picking math directly (weights, floor, exclusions, overrides not
leaking between stories), the reference substitution behavior, and the
markdown export.

Prefer plain, readable code over clever abstractions. The owner will open the
JSON lists and templates by hand to add their own material, so data files
must stay simple, commented where JSON allows (a `"_note"` field is fine), and
documented in the README.
