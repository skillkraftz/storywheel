# storywheel — project brief
## Cloud sessions
- Work on a new branch named for the task and push only that branch. Never
 push to main and never move "stable": stable is only moved on xps after a
 full local run.
- Things the cloud can't check (real kitty, typewriter's Pi, real
 LanguageTool, the real dictionary) go in the session's report for Andy to
 check by hand.

## What this is

storywheel is a personal writing program for one writer (Andy). The goal is a
single terminal program that covers the whole path from "I have nothing" to "a
manuscript ready to submit": generate an idea, grow it into a world, write the
story, and export it in the format editors expect.

Today that path takes three programs and constant switching: storywheel for
ideas, Obsidian for world and character notes, and FocusWriter for drafting.
FocusWriter also can't export a properly formatted, double-spaced manuscript.
storywheel replaces all three with three modes that share one set of data:

1. **The Wheel** (exists): roll a story idea piece by piece, keep what clicks.
2. **The Universe Builder** (new): grow kept ideas into worlds full of
   characters, places, things and notes, with the generator on hand to fill
   any field.
3. **The Writer** (new): a full-screen, distraction-free Neovim setup for
   drafting, aware of the world, with manuscript export.

One hotkey moves between Builder and Writer, and the program always remembers
where you were.

### Who and where

This is a personal tool, not a product. It runs full-screen in a modern
terminal emulator on a Linux desktop, with a mouse. Don't spend effort on small
terminals, SSH sessions, Windows, or other people's setups. Setup on a new
machine should still be painless for the owner: Python with pipx, Neovim 0.10
or newer, and pandoc. Anything else should be optional and say so when missing.

### How to use this document

This describes the intent and a working design. It's a guide, not a contract.
When the code reveals a better way, take it, and record the change in the
Decisions log at the end. When something here is ambiguous, pick the simplest
thing that serves the writer and write down what you chose. The owner tests
by using the program, so a feature that works end to end beats a feature that
is complete on paper.


## The flow

```
Wheel ──(keep a story, leave)──▶ "Bringing this story into the Universe Builder"
                                         │
                                         ▼
                 Universe Builder ◀──hotkey──▶ Writer (Neovim)
                   │  characters, places,        manuscript,
                   │  things, groups, notes,     scene sidebar, stats
                   │  stories in this universe
                   ▼
                 Export: Shunn manuscript .docx, .odt, .md, .txt (PDF optional)
```

Universes also feed back into the Wheel: when rolling a new story, the writer
selects which universes the generator may draw from, so new ideas can reuse
existing characters, places and things.


## Current state (tag stage-3-dependencies, plus the UI pass)

The Wheel is a working Textual app with a plain-prompt fallback. In brief:

- **Steps**: genre & mood, structure, title (with motif), protagonist,
  setting, premise, the story body (beats from the chosen structure), twist.
  Forward-only: later steps read what earlier steps kept.
- **Per step**: roll, keep, reroll one field, edit a field, write your own,
  $EDITOR, history with per-field history, back, skip, rate lines +/-.
- **Mouse**: left-click a field rerolls it, right-click edits it, the scroll
  wheel steps through that field's earlier values, ▲▼ rate a line, and buttons
  under the card do Roll, Keep, Back, Skip and Mix.
- **Layout**: three columns. Left: steps (with ✓ kept, yellow ● built on a
  stand-in or something changed, red ✗ refers to something no longer kept),
  the universe panel, and past stories. Middle: the card and history. Right:
  the story so far as plain text, with issues listed at the top.
- **Dependencies**: candidates record their inputs (`_inputs`). A candidate
  built on something that changed shows a banner with Update, Reroll and
  Ignore. Stand-ins (values invented because an earlier step isn't kept yet)
  are labeled. Keeping an earlier step updates later kept steps.
- **Exit**: asks "Keep this story or delete it?", then prints the story as
  plain text, its markdown path and the resume command.
- **Other**: `c` copies the story as plain text, a per-story mix editor,
  ratings with a `report` command, `--json` on list, show, export and sample.
- **Universe (old model)**: one global pool in `~/.storywheel/universe.json`,
  keyed by step, with a no/mix/only pull mode. This gets replaced by real
  universes (see below).

Code lives in `storywheel/`: `engine.py`, `frames.py`, `library.py`, `mix.py`,
`steps.py`, `structures.py`, `threads.py`, `refs.py`, `session.py` (logic
shared by both interfaces), `tui.py`, `cli.py`, `store.py`, `ratings.py`,
`report.py`, `clipboard.py`. Content is JSON in `storywheel/data/`.


## The generator (exists; keep its behavior)

These are the rules the generator already follows. New code that rolls
anything, including Builder fields, should go through the same engine.

**Lists, tags and the mix.** Content lives in JSON lists, one slot per list
(`job`, `thing`, `someone`, `landmark`...), each with tags. Genre profiles in
`genres.json` give tags default weights. A story's mix blends the profiles of
its genres, plus per-story overrides (exclude a tag or list, boost a tag) that
never change the profiles. A list's weight is the largest weight among its
tags. A wildcard floor (12%, and about 4% for anchor slots that repeat
through a story: rival, job, place, names, landmark) lets off-genre material
in occasionally. Exclusions are absolute, except that if every list for a
slot is excluded, the exclusion is ignored for that slot and the user is told.

**Atoms, frames and features.** Lists hold atoms: short pieces, five words or
fewer, no clauses. Templates are frames with at least two slots; the spine
openers are the only frozen text. `{UPPERCASE}` slots draw fresh each time,
`{lowercase}` slots refer to what the story has kept. Atoms carry features
(portable, buryable, magic, human, creature, authority, diggable...) and
frames and verbs declare requirements (`{THING:buryable}`, "enchanted" needs a
magic subject). The solver fills nouns first, then verbs that fit. Strict
character fields: wants are obtainable, needs are inner lessons, routines are
everyday, secrets are hideable.

**Threads, motif and seeds.** A body beat that introduces a thing, person,
message or disaster records it as a thread, and later beats prefer templates
that reuse it. The title produces a motif with a kind (object, person,
creature, place, idea). Names and places invented in passing become seeds that
first rolls of later steps reuse.

**No repeats.** No atom repeats within a story. A persisted memory avoids
recent atoms across sessions (seeded samples ignore it, so they stay
repeatable).

**Structures** are data in `data/structures/`: Story Spine, Three-Act
Outline and Kishōtenketsu ship today. User structures go in
`~/.storywheel/structures/`.

**Ratings** gently down-weight frames and atom pairs that keep getting -.

**Content status**: western, fairy tale, comedy, fantasy, mystery, horror,
sci-fi, romance, ghost story, noir, thriller, heist, adventure and coming-of-age are fully written and annotated with features. Expanding
genre content is ongoing work outside this sweep.


## Core concepts

- **Library**: the folder where everything the writer keeps lives (universes,
  their entities, their stories and manuscripts). Plain files.
- **Universe**: a named world. It has its own notes, genre leanings, and
  collections of entities. Stories belong to a universe.
- **Entity**: one thing in a universe: a character, place, thing, group, or
  note. Each type has a set of fields, most of which the generator can fill.
- **Wheel draft**: a story being rolled in the Wheel. Drafts live in app
  storage until promoted.
- **Story (promoted)**: a kept idea that has been brought into a universe. It
  has an outline (everything the Wheel produced), settings, and a manuscript.
- **Manuscript**: the story's actual prose, as scene files.
- **Format profile**: short story, novel, or screenplay. It decides editor
  behavior and export layout.


## Storage

Everything the writer keeps should be plain, readable files, so it can be
opened in Obsidian, backed up, or put in git. Entities are markdown with YAML
frontmatter: fields in the frontmatter, free-form notes in the body. That
also makes the library a valid Obsidian vault folder.

A suggested layout (adjust if something works better):

```
<library>/                         default ~/Writing/storywheel, setting: STORYWHEEL_LIBRARY
  universes/
    the-thornwood/
      universe.md                  name, genres, mix overrides, notes
      characters/stacie-anderson.md
      places/red-draw.md
      things/the-hunting-horn.md
      groups/the-land-office.md
      notes/the-dry-years.md
      stories/
        the-last-clause/
          story.md                 outline: title, premise, structure, beats, twist
          seed.json                the Wheel draft it came from
          settings.toml            format, goals, editor preferences
          manuscript/
            01-opening.md
            02-the-letter.md
          stats.json               words per day and per session
          exports/

~/.storywheel/                     app storage (STORYWHEEL_HOME)
  stories/                         Wheel drafts (as today)
  state.json                       where the writer left off
  settings.toml                    global: author name, address, email, defaults
  ratings.json, recent.json, lists/, structures/, genres.json  (as today)
  nvim/                            the Writer's Neovim state (sessions, shada)
```

Links between entities use stable ids (the file's slug) in frontmatter, so
renaming a character doesn't break links. Obsidian-style `[[wikilinks]]` in
notes are welcome and should resolve to entities where possible.

**Never lose writing.** The Builder saves on every change. The Writer autosaves
(on leaving insert mode, on focus loss, and on a short idle timer) and keeps
rolling backups of manuscript files (for example, a daily snapshot in a hidden
backups folder inside the story). Deleting anything asks first.

**Migration.** The old `universe.json` becomes a universe called "Loose Ends":
protagonist entries become characters, setting entries become places, and
anything else becomes notes. Keep the old file as a backup. Existing Wheel
drafts keep working as they are.


## Mode 1: the Wheel (changes)

The Wheel stays as it is, with three changes.

**Universes replace the global pool.** The universe panel lists universes
with a checkbox each: "the generator may draw from this one." Selection is
per draft, saved with it, and defaults to none (or to the universe the draft
was started from, if the writer started it from inside the Builder). The
existing no/mix/only mode still governs whole-step candidates: in mix or only
mode, a protagonist candidate can be a character from a selected universe.
The panel can still open an entry and "use in this story."

**Promotion on leaving.** When the writer leaves the Wheel with a kept story,
a message says plainly that the story is about to be brought into the
Universe Builder, with three choices: bring it into a new universe (named
after the story by default, editable), bring it into an existing universe, or
not now (it stays a draft; it can be promoted later from Past stories). A
story with nothing kept just asks Keep or Delete, as today.

**Past stories** show which drafts have been promoted and to which universe.

### What promotion creates

| From the Wheel | Becomes in the universe |
|---|---|
| Protagonist | Character, role "protagonist", with every protagonist field |
| Rival (e.g. "the sheriff") | Character stub, role "rival", the rival text as its name or description |
| Setting: place, era, season, rumor | Place (the town), with those fields |
| Landmark | Place, inside the town |
| Motif | Thing if it's an object; a character if it's a person or creature |
| Threads: someone / thing / message / disaster | Character stub / Thing / Thing (a document) / Note (an event) |
| Title, genre, mood, structure, premise, every beat, twist | The story's `story.md` outline |
| Genre and mood | The universe's default genre leanings, if the universe is new |

When promoting into an existing universe, offer to merge obvious duplicates
(same name) instead of creating a second copy, and show what will be created
before it's created.


## Mode 2: the Universe Builder (new)

The Builder is where a kept idea grows into a world. It should feel like a
desk covered in index cards that the generator can help fill in.

### Layout

A suggested layout; refine it as it gets used:

- **Left column**: the list of universes (open one, create, rename, delete
  with confirm), and inside the open universe its stories (open a story's
  outline, start writing it, start a new Wheel draft inside this universe).
- **Middle**: the open universe. Fixed boxes at the top for the universe's
  overview (name, genre leanings, notes) or, when a story is open, its
  outline (title, premise, structure, beats, twist, settings). Below them, a
  tabbed area with one tab per entity type: Characters, Places, Things,
  Groups, Notes. Each tab lists its entities and shows the selected one as a
  card of fields.
- **Right column**: a detail panel for the selected entity: its free-form
  notes (editable), its links to other entities, and the stories it appears
  in.

### Entity fields

Each entity type has a schema, defined as data (for example
`data/entities/character.json`), so fields can be added without code. A field
says its label, whether it's short or multi-line, and how the generator fills
it (a slot, a frame, a link to another entity type, or "write only"). Suggested
starting schemas, reusing what the Wheel already generates:

- **Character**: name, role (protagonist, rival, ally, supporting...), age,
  job, trait, want, need, flaw, secret, rival (a link to another character, or
  text), plus notes and relationships.
- **Place**: name, kind (town, landmark, building, wild place), parent place
  (link), era, feature, rumor, plus notes.
- **Thing**: name, description, features (portable, magic...), owner (link),
  history, plus notes.
- **Group**: name, kind, goal, leader (link), members (links), plus notes.
- **Note**: title and body (lore, events, timelines, anything).

The writer can add their own fields to a single entity (free key and value);
those are write-only.

### Rolling and writing fields

The Builder uses the same conventions as the Wheel:

- A new entity starts with every field blank.
- **Left-click** a field (or `f` on the highlighted field) rolls it with the
  generator. **Right-click** (or `e`) writes it by hand. A key (`space`) rolls
  every blank field at once; a separate key re-rolls the whole entity after a
  confirm.
- Rolling uses context: the universe's genre leanings and mix, the entity's
  other fields (a character's need should fit their flaw), and the universe's
  existing entities (a character's rival can be an existing character; a
  thing's owner an existing character; a place's parent an existing place).
- Each field keeps its own history; the scroll wheel steps through it, as in
  the Wheel. Ratings work here too.
- Fields with no generator support are write-only, and show that they are.

### Links and renames

Links (rival, owner, parent, leader, members, relationships) point at entities
by id. Renaming an entity updates its name everywhere it's shown, and offers to
find and replace the old name across this universe's entity notes, outlines
and manuscripts: a preview lists every match (whole word, including
possessives like "Stacie's") with its context, and the writer confirms all or
one at a time. Neovim buffers are reloaded afterward.

### Universe settings

A universe has genre leanings (which become the mix for anything rolled in it,
using the existing mix rules), optional tag exclusions and boosts, and
optionally its own atom lists (a `lists/` folder inside the universe, merged
like `~/.storywheel/lists/`), so a world's own vocabulary feeds its rolls.


## Universes as generator input

When a universe is selected in the Wheel, or when rolling inside the Builder:

- Its entities become atoms in the matching slots: characters in `someone`,
  `close`, `rival` (and their first and last names in the name slots), places
  in `place` and `landmark`, things in `thing`. Their features come from their
  fields, or sensible defaults for their type.
- Universe atoms get a boost, so the world's own people and places show up
  often but don't crowd everything else out. The boost is a setting.
- Its genre leanings blend into the mix.
- Whole-step candidates (no/mix/only) can be universe characters and places.

The no-repeat-within-a-story rule still applies, and a universe character
used as the protagonist isn't also drawn as a passing stranger.


## Mode 3: the Writer (new)

The Writer is Neovim, set up as a full-screen, distraction-free writing room,
with a small Lua plugin that knows about storywheel. Neovim does the hard parts
of editing (undo, search, selection, large files), so storywheel shouldn't
build its own text editor.

### Running it

The Writer runs Neovim with its own configuration via `NVIM_APPNAME`, so it
never touches any personal Neovim setup. The configuration ships inside the
package (for example `storywheel/nvim/`) and is installed or linked on first
run. Prefer small, hand-written Lua over third-party plugins; if a plugin is
worth using, pin it and bundle it so the Writer works offline and doesn't
change under the writer's feet.

The Writer gets the story's details from the CLI with `--json` (for example
`storywheel story show <id> --json`, `storywheel entity list <universe>
--json`), so the Lua side stays thin and the engine stays in Python.

### Switching

From the Builder, a hotkey opens the selected story in the Writer: the
Textual app suspends itself and runs Neovim full-screen. A hotkey in Neovim
saves everything and quits back to the Builder, which resumes exactly where it
was and refreshes word counts and anything that changed. Neovim restores the
open scenes and cursor positions per story (sessions or shada stored under
`~/.storywheel/nvim/`). If switching ever feels slow, running both inside a
terminal multiplexer is the fallback, but start with suspend-and-return.

### The writing room

- **Full screen, centered column** of configurable width, with nothing else
  on screen by default: no line numbers, no sign column, minimal status line.
- **Prose editing**: soft wrap at word boundaries, movement by displayed
  lines, sensible spellcheck (toggle), mouse on.
- **Formatting keys**: Ctrl+I italic, Ctrl+B bold, in insert and visual mode
  (wraps the selection or toggles at the cursor). Markup characters are
  concealed and the text is shown in actual italic or bold. Note: most
  terminals send the same code for Ctrl+I and Tab. Neovim can tell them apart
  only when the terminal supports an extended keyboard protocol (the kitty
  protocol or similar). Detect what the owner's terminal does, make Ctrl+I work
  if possible, and provide a fallback (for example Alt+I) either way.
- **Paragraphs**: in the file, paragraphs are separated by a blank line and
  start flush. On screen, the first line of each paragraph shows an indent
  (virtual text, not typed spaces), and pressing Enter at the end of a
  paragraph starts a new one properly. Export applies real formatting.
- **Scene breaks**: one key inserts a scene break line, stored as `* * *` in
  the file and shown centered on screen. Export renders it per format (Shunn
  uses a centered `#`).
- **Show invisibles** (toggle): dots for spaces, a mark for trailing or double
  spaces, ¶ at paragraph ends, and tabs shown.
- **Typewriter mode** (toggle): keeps the current line in the middle of the
  screen.
- **Scene sidebar** (toggle): a panel listing every scene with its first line,
  in order. Enter jumps there. Scenes can be added, renamed and reordered from
  it. Scenes are files in `manuscript/`; inside a file, `* * *` breaks also
  show as sub-entries.
- **World peek**: a key shows the entity under the cursor (a character or
  place name) in a floating card, read-only, with its key fields and notes.
  Completion of character and place names from the universe while typing.
- **Stats**: the status line shows words in this scene, words in the
  manuscript, and words today against the daily goal. `stats.json` keeps
  words written per day and per session.
- **Settings**: the story's settings (format profile, column width, goal,
  indent display, typewriter default, invisibles default) live in
  `settings.toml`, are editable from the Builder's story view, and a Writer
  command opens them too. Changes apply on the next return to the Writer, or
  immediately if easy.

### Format profiles

- **Short story** (default): scene files, Shunn short-story export.
- **Novel**: chapters as files (with headings), scenes inside them; Shunn
  novel export.
- **Screenplay**: one Fountain file with Fountain-aware editing and export to
  script pages. See Screenplays below.


## Screenplays

A screenplay story is written in Fountain (plain text) and exported as standard script pages. Built in batch 17; a first usable version.

- **The story.** Its `settings.toml` says `format = "screenplay"`, `script_kind` (feature-film or short-film) and `target_pages`. Its manuscript is one file,
  `manuscript/script.fountain`, and none of the prose rules touch it: blank lines are kept (they mean something in Fountain), paste keeps the
  layout, there is no virtual paragraph indent, no `***` rewriting, and no one-line-paragraph or one-file migration. Spelling, autocorrect and
  quote straightening still work. Grammar checking reads only action, dialogue, parentheticals and lyrics.
- **Making one.** Choose the format Screenplay (feature film) or Screenplay (short film) in the Wheel's structure step or on the Builder's
  story form (batch 18, `formats.py`). Their structures are Feature Film (three acts in eight sequences, 110 pages) and Short Film (12 pages),
  in `data/structures/` with `"screen": true` and `"formats"`. They reuse the three-act frames and are offered only for their format. P in the Builder writes the
  script from the outline: a title page, each beat as a Fountain section (`# Act One`, `## Sequence A`) with its text as a synopsis (`= ...`),
  which never print. A script that already has scenes is never overwritten, and a forced replace backs it up first.
- **Reading Fountain.** `fountain.py` is the one reader. It parses the title page and every element (headings, action, cues with extensions
  and `^` dual, parentheticals, dialogue, transitions, centered, `===`, sections, synopses, lyrics; notes and boneyard are skipped while
  line numbers stay true). The page estimate, flip test, scene list, word count, export and grammar skip list all use it. The Writer's
  `sw/script.lua` ports its line classifier, and a test checks that both read the fixture the same way.
- **The Writer.** Tab cycles the line's element (action, character, parenthetical, dialogue, transition), fixing the blank lines around it.
  Enter after a cue or parenthetical starts dialogue; Enter after dialogue starts action. Headings, and cues of known names, are
  capitalized. Character names and locations complete from the script and the universe. Display-only inline indents approximate the page.
  The sidebar shows scenes by heading under their sections. The status line shows "p. N of ~T". Alt+F (`key_flip_test`) runs the flip test
  into a list that jumps to each spot.
- **The flip test** (`screenplay.flip_test`) flags action blocks over 4 printed lines, speeches over 10, and camera directions (we see,
  CAMERA, ANGLE ON, PAN, ZOOM...). It also flags CUT TO: used more than once per five scenes, and a length more than 15% off the target.
- **Export** (`screenplay_pdf.py`, our own renderer, chosen in batch 17 Part A over screenplain, afterwriting and Wrap). It uses reportlab
  and the bundled Courier Prime (OFL), on US Letter with 12-pt type, 10 characters an inch, and 55 lines of 12 pt. Margins are 1.5" left,
  ending at 7.5", with the body 1" from the top. Cues sit at 3.7", parentheticals at 3.1" (25 wide), dialogue at 2.5" (35 wide), and action
  is 60 wide. Transitions end at 7.5", and page numbers ("2.") run from page 2 at 0.5" down. Two blank lines go before a heading, and a
  heading is kept with what follows. A speech splits after a dialogue line, preferring a sentence end, with (MORE) and "NAME (EXT) (CONT'D)".
  Action splits only with 2+ lines on each side. Dual dialogue is set in columns. The title page comes from Settings > You: title at row 21
  centered, "Written by", the name, contact bottom left, and the date bottom right. Anonymous leaves out the name, credit and contact. Also
  `.fdx` (`screenplay_fdx.py`, Final Draft XML) and `.fountain` (the title page rebuilt from settings). A script asked for docx/odt/md/txt
  gets a PDF and says so. Exports go to the manuscripts folder and the export record like any other.
- **(CONT'D)**: across a page break always; after action in the same scene when `script_contd` is on (default, as Final Draft and Fade
  In do): in the PDF and dimmed on screen, never written into the file, never doubled (`fountain.auto_contd`, `sw.script.contd_rows`).
- **Not done** (BACKLOG.md): scene numbers on the page, revision colours and marks, a screenplay word bank, Fountain in Words' Story words,
  Fountain-aware `storywheel lookup` of cues, and moving scenes from the sidebar.


## Export

Export compiles the manuscript (all scene files in order) and applies the
format profile. It runs from the Builder (a key on a story) and from the
Writer (a command), and writes to the story's `exports/` folder.

- **Shunn manuscript format, .docx** is the one that matters most. Based on
  William Shunn's "Proper Manuscript Format" guide: 12-point Times New Roman or
  Courier (a setting), double-spaced, 1-inch margins, first-line paragraph
  indents of half an inch, no extra space between paragraphs. First page:
  author's legal name, address, email and phone at top left; word count at top
  right (rounded as the guide recommends); the title centered about halfway
  down the page, with the byline under it. Following pages: a header at top
  right with surname, a short title keyword, and the page number. Scene breaks
  as a centered `#`. "END" centered after the last line. Italics stay italics.
  Check the details against Shunn's guide when building it, since it has a
  short-story and a novel variant. Author details come from global settings.
- **.odt** with the same layout, if it comes cheaply from the same path.
- **Plain .md** (the compiled manuscript) and **.txt** (no markup at all).
- **PDF** is optional: converting the .docx with LibreOffice in headless mode
  if `soffice` is installed. Avoid LaTeX.
- **Clipboard**: copy the compiled manuscript as plain text, as the Wheel's
  `c` already does for drafts.

pandoc with a reference document and a Lua filter is the expected route, but
if Shunn's first page and headers are easier to get exactly right by building
the .docx directly (for example with python-docx), do that. Correctness is
judged by reading the result back and checking it against the spec.


## Remembering where the writer left off

`~/.storywheel/state.json` records the current mode, the open universe and
story, the selected tab and entity, the Wheel draft and step, and anything
else that makes reopening feel seamless. Running `storywheel` with no
arguments returns to that exact place. The Wheel can still be reached
directly with `storywheel wheel` (or `new` and `resume`, as today).

Mode keys should be consistent everywhere: one key to the Wheel, one to the
Builder, one to the Writer (for example F1, F2 and F3), plus the in-Neovim key
to return. Pick keys that don't collide with existing ones, and list them in
every help screen.


## Interface conventions (all modes)

- Left-click a field rolls it, right-click writes it, the scroll wheel steps
  through its history. `f`, `e`, `space`, `k`, `?` mean the same thing
  everywhere they apply.
- Every destructive action asks first.
- Problems are shown, never hidden: stand-ins, stale values, missing tools
  (no pandoc, no soffice, no clipboard tool) each get a plain message.
- Help screens list every key and mouse action for that screen.


## Testing and reporting

Tests use pytest and a seeded random generator. Keep the existing suite green.
For the new modes:

- **Storage and promotion**: round-trip entities through markdown with
  frontmatter; promotion creates the right entities and outline; merges don't
  duplicate; migration from `universe.json` works and keeps a backup.
- **Builder**: Textual pilot tests at a desktop size (for example 200×50):
  create an entity, roll a field by click and by key, write a field by
  right-click, step through field history, link two entities, rename with the
  preview, and confirm the files on disk match.
- **Universes as input**: a selected universe's characters and places appear
  in rolls at roughly the boosted rate; unselected universes never appear.
- **Writer**: test the Lua plugin headlessly (`nvim --headless` with the
  Writer's config): the scene break key inserts the right line, the italic
  mapping wraps a selection, word counts are correct, the scene list matches
  the files, settings are read. Visual things (centering, concealing, the
  virtual indent) can't be fully tested; list them for manual checking.
- **Export**: generate the .docx and read it back with python-docx: line
  spacing, font and size, margins, first-page block, header text, `#` scene
  breaks, "END", and italics preserved.
- **Switching and state**: state is saved and restored; the suspend-and-return
  path is exercised as far as tests allow, and listed for manual checking.

Every sweep ends with a written report (`REPORT.md`, updated as work goes, so
it's current even if a session ends early):

1. A checklist of every feature asked for, each marked **Works**, **Partial**,
   **Stub**, or **Not started**, with one line on what's missing.
2. A synopsis of the tests added, grouped by area, with counts.
3. A manual test script: the exact steps the owner should try, especially for
   anything tests can't see (how the Writer looks, Ctrl+I in their terminal,
   the .docx opened in a word processor, a real clipboard copy).
4. Known issues, questionable decisions, and open questions.

Commit after each area with a clear message and a tag, so the history shows
what each piece added.


## Roadmap

0. **Done**: the Wheel (engine, content for two genres, structures, TUI,
   ratings, dependencies, UI pass).
1. **Foundation sweep (next)**: storage and library, universes, promotion,
   the Builder, universes as generator input, the Writer, switching and state,
   Shunn export, rename, stats. Breadth first: everything usable end to end
   for a first demo, rough edges allowed and reported.
2. **Polish from real use**: the owner writes with it and reports issues.
3. **Content**: write and annotate atom lists for the remaining twelve genres.
4. **A world model** (future): instead of filling beats from templates,
   simulate a small cast with values, goals and relationships, plus objects
   with owners, and pick events whose preconditions the current state allows,
   so "because of that" is literally true. This is the Dwarf Fortress idea
   (simulate first, describe after), with storylet-style events. Universes
   built in the Builder are the natural input for it. Design it when the time
   comes; don't build it in the foundation sweep.
5. **Range**: novel and screenplay formats in depth, more stats, more
   structures.


## Principles

- Plain files the writer can read and edit by hand. Data, not code, wherever
  content or schemas are involved.
- The generator assembles ideas from parts; it doesn't deal pre-written ideas.
  Nothing specific should repeat.
- Never lose the writer's work.
- Readable code over clever code. No network access at run time. Few
  dependencies; anything optional degrades with a message.
- Show problems plainly; don't fix things silently behind the writer's back.


## Development rules (firm)

- Any shell command that runs storywheel while developing (the CLI, a script that imports it, a sample, a screenshot, a report tool) sets
  `STORYWHEEL_HOME` and `STORYWHEEL_LIBRARY` (and `STORYWHEEL_MANUSCRIPTS`, and `STORYWHEEL_DICTIONARY` when a dictionary is needed, pointing at a
  copy) to a temporary folder first. Never touch the owner's real `~/.storywheel` or `~/Writing`, and never use the network outside tests.
- Docs and code with backticks go through quoted heredocs (`<<'EOF'`), never unquoted ones: the shell would run the backticked text.
- **The data files are the source of truth** (`storywheel/data/**/*.json`). Edit them directly. Never write content through a generator script
  and never rerun an old one: earlier batches used scratch scripts that later hand edits made out of date, and rerunning one silently undoes those
  edits (it happened in batch 15 with a job's age band). The scratch scripts were deleted in batch 16; none are kept in the repository.


- **Testing policy (firm; batch 14).**
  - Tests carry two markers, assigned in one place (`tests/conftest.py`: `SERIAL_FILES`, `SLOW_FILES`, `SLOW_TESTS`, and any test that opens a real terminal on a pty).
    `serial` = cannot run in parallel (real terminal, the hub, shared ports). `slow` = real terminals, performance, and the 200-story fidelity / repetition checks.
    A new test of either kind is added to those lists.
  - While working, run only the tests related to what changed, and leave the slow ones out: `pytest -m "not slow" tests/test_<area>.py`. Never the whole suite mid-batch.
  - End of a batch: ONE full run, `tools/fulltest.sh` (parallel pass with `-n auto -m "not serial"`, then the serial pass `-m serial`). If anything fails, fix it, rerun
    only the failed tests (`--lf`) and their files, and then move `stable`. Run the whole suite again only if the fix changed engine code or data used by many genres.
  - No background polling loops while tests run (no `until`/`sleep` watchers). Start the run, and stop when the checklist is done. Further ideas go to BACKLOG.md,
    not into fixes beyond the checklist.
  - The report states the full run's time (batch 13 serial: 20 min 27 s; batch 14 with xdist: about 5 min 26 s).
- The `stable` branch is what typewriter installs. At the end of every batch, and only after the end-of-batch full run has passed (see the testing policy), move it to that
  commit (`git branch -f stable HEAD`). Never move it any other time (not after a partial test run, not mid-batch). Never push.


## Decisions log

Decisions made so far that aren't obvious from the code. Add to this as you go.

- A list's weight is the largest weight among its tags, not the sum.
- Wildcard floor 12%; about 4% for anchor slots. Set in `genres.json`.
- Excluding every list for a slot ignores the exclusion for that slot and
  says so.
- general 0.3 and modern 0.1 in all genre profiles; sci-fi, comedy and heist
  will need modern raised when their content is written.
- Atoms at most five words, no clauses; frames need at least two slots.
- Seeded samples ignore ratings and the cross-session no-repeat memory.
- The stale-candidate banner offers Update, Reroll and Ignore. Ignore only
  dismisses the banner.
- Earlier kept steps are never rewritten by later ones; they're flagged
  instead.
- The markdown export has no page-break divs. Page layout belongs to the
  manuscript export.
- Textual is required; the plain prompt (`--plain`) remains as a fallback.
- Entity frontmatter is read and written by a small built-in reader (text in double quotes, lists as JSON,
  one level of nested "custom"), not a YAML library. It is valid YAML, so Obsidian reads it.
- A new blank entity gets a placeholder id (`character-1`). The first time it has a name it is renamed to a
  slug of the name and links to it are rewritten. After that the id never changes, even if the name does.
- Link fields hold an entity id; if the value isn't an id of an existing entity it is shown as plain text.
- Deleting a universe, entity or story moves it to `<library>/.trash/`. (The UI still asks first.)
- The old `universe.json` is renamed to `universe.json.migrated-DATE` after migration (that is the backup).
- Group names have no natural list, so they roll from `title_noun` as "The {noun} Company".
- Settings are TOML, read with `tomllib` when Python has it and a small reader otherwise.

- Builder entity tabs are a `Tabs` bar over one shared list and card (keys 1-5), not five separate panes.
- Renames: matching is case-sensitive and whole-word (possessives included); the entity's `id:` and `name:` lines are
  never rewritten as text. "One at a time" is done by toggling matches in the preview list.
- Entity field history in the Builder is kept beside the entity (batch 3: `<universe>/.field-history/`).
- Ratings on Builder fields carry the same provenance as the Wheel's and change later rolls (batch 3).
- The Wheel's universe panel no longer asks a question on start. A draft's universes are ticked in the panel and saved
  with the draft (`universes`), default none; no/mix/only (`universe_mode`) still governs whole-step candidates.
- Universe atoms are tagged `universe:<slug>` and boosted through the story's mix (never saved into it). The
  universe's `atom_boost` defaults to 1.5, which gives its lists roughly the share of a strong genre list.
- A universe character used as the protagonist is added to the "used" atoms for `someone`, `close` and `rival`.
- `u` in the Wheel saves into the single ticked universe, or asks which; `U` only explains that deleting happens in
  the Builder.
- The Writer's Neovim config has no plugins. It lives in `storywheel/nvim/` and is symlinked into
  `~/.storywheel/nvim/config/storywheel-writer` (copied if links fail). Neovim's data and state folders are under
  `~/.storywheel/nvim/` too.
- Ctrl+I is mapped to italic only when the terminal is one known to report it apart from Tab, or after `Space k`
  (`:SWKeyCheck`) proved it works; Alt+I always works. VTE terminals (GNOME Terminal) do not.
- The centered column is made of two blank "pad" windows either side of the text window (the left one doubles as
  the scene sidebar), not of a padded text window.
- A word is a run of non-space characters containing a letter or digit, so `* * *` counts as no words. Python
  (`vault.count_words`) and Lua (`sw.util.count_words`) use the same rule.
- The Writer keeps its own per-story session (open scenes, cursors, toggles) as JSON under Neovim's state folder, not
  Vim's `:mksession`.
- Backups are copies named `HHMM-<scene>.md` in `<story>/.backups/<date>/`, made when a scene changed and at least
  15 minutes after the previous copy; 30 days of folders are kept.
- Each mode is its own Textual app (or Neovim); `storywheel/modes.py` loops between them using what each says it wants
  next (F1/F2/F3, promotion). Only Builder -> Writer uses Textual's suspend, as the brief asks; the Wheel hands over by
  closing and being reopened.
- Leaving Neovim with `:q` (not F2) returns to the Builder; F1 in Neovim goes to the Wheel.
- Plain `storywheel` only resumes the saved mode in an interactive terminal; with `--plain` or a pipe it is still the
  plain prompt for a new draft.
- Export builds the .docx directly with python-docx (no pandoc on the machine); .odt and .pdf are LibreOffice
  conversions of it. Word count on page 1 is rounded to the nearest hundred (nearest ten under 100). The header keyword
  is the story's `title_keyword` setting, else the first real word of the title.
- A novel is the same pages with each scene file as a chapter on a new page (partial); a screenplay exports an
  unformatted `.fountain` file with a visible "stub" warning.
- `python-docx` is a required dependency; `pyte` is a dev dependency (terminal-screen tests).
- "Send to Builder" is a button (and `B`) in the Wheel from the first kept step, "Open in Builder" once sent; F2 from an unsent
  draft with kept steps asks whether to send it first. Sending asks only "new or existing universe", then shows the usual preview.
- Builder lists: rolling a field does not rebuild the entity list (only a name change does, and it keeps its scroll); columns
  never scroll themselves. In the top box only right-click or `e` edits, and the wheel scrolls.
- Proper names: instead of flagging atoms, the text filler drops "the/a/an" directly before the name of any character or place
  in the ticked universes (`Engine.proper`), so templates that say "the {rival}" read "Sheriff Lund".
- Builder layout: the box at the top is a writing-stats box (today vs goal, streaks, totals), read from the stories' `stats.json`
  (`writing_stats.py`). The right column is tabs: Outline, Scenes, Notes (keys 6-8). Notes holds the entity notes, links and appearances.
- A fourth mode, Settings, on F4 (`settings_app.py`), reachable from every mode and listed in every help screen. It edits
  `~/.storywheel/settings.toml`, saving each change as it is made. `q` returns to the mode F4 was pressed in.
- Story `settings.toml` files store only what that story sets itself; everything else follows the global defaults
  (writer preferences, goals, font, column width...). A universe's `atom_boost` is stored only if the universe pins its own;
  otherwise it follows the global `atom_boost`.
- The library folder can be set in Settings (`library = "..."` in settings.toml); `STORYWHEEL_LIBRARY` still overrides it.
  Changing it never moves files.
- Manuscript = one file per story (`manuscript/manuscript.md`) with scene markers; a novel has one file per chapter. A marker is a line
  `* * *` or `* * * Title` (the scene-break key inserts the plain one). A marker at the very start names the first scene and is not a
  break. Markers are exported as a centered `#` (not counted as words). Old stories with one file per scene are merged, in order, into
  `manuscript.md` when the Writer starts or on `storywheel migrate`, with the originals kept in `.backups/migrated-DATE/`.
- Notepad mode (setting `notepad_mode`, default on) makes the Writer behave like an ordinary editor: Neovim has no insert-only
  option, so the writing window simply never rests in Normal mode. Selection uses Select mode with `selection=exclusive`
  (inclusive only while "select all" is active). Ctrl+C/X/V use the `+` register; with no clipboard tool an in-process provider
  is installed and the writer is told. Escape is a no-op in Insert mode. F12 / Alt+M opens the Writer menu; peek moved to F8.
- Neovide is optional (`neovide` setting): started as `neovide --no-fork` with the same environment plus `STORYWHEEL_GUI=neovide`;
  if missing, the terminal is used and a message says so. The font, size and `line_spacing` (pixels) come from settings.
  In the terminal, `paragraph_spacing` adds display-only blank lines between paragraphs.
- Focus never changes geometry: every list, tree and text box in every mode has the same border focused or not (none, for the
  Builder's and the Wheel's lists) and shows focus by colour. `tests/test_layout_stability.py` enforces it for every mode.
- The Builder's Outline tab is built by `outline.py` from story.md: one row per beat or setting line, markdown stripped for
  showing, edited one row at a time. Promotion writes a beat's label (`**Label.** text`) only for structures that show their labels.
- The Wheel panel's groups (Characters, Places, Things) count named entities, the same numbers the checklist shows; only
  characters and towns can be a whole step, the rest are boosted atoms and say so when you try to "use" them.
- Promoted Wheel drafts are read-only in the Wheel (chosen over syncing edits back to the outline). Once promoted, the
  Builder holds the real story; a second place to edit it would drift, and syncing would need an entity-by-entity diff and
  merge for every reroll. Instead the Wheel says so, nothing mutates (roll, keep, edit, write, skip, history picks), and `C`
  (or the offer in plain `resume`) makes an editable copy as a new, unpromoted draft (`store.copy_as_new`). The original stays.
- A Wheel draft gets a file only when something is kept. Drafts with nothing kept are moved (never deleted) to
  `<home>/.trash/` the next time the Wheel starts or `list` runs, and the count is said. Past stories show steps kept ("5/8"),
  "done" for finished ones. A finished draft reopens on its last step, never silently on step 1.
- Hand-writing a title recomputes the motif from it (Wheel and Builder), saying so, unless the motif was edited in the same
  edit. Season is a real Place field; a place's parent link reads "Located in".
- Text rewriting never changes part of a word: thread/stand-in replacement matches whole words (possessives included),
  `singular()` knows -ie, -us, -is and irregular nouns and leaves possessives alone, and a renamed protagonist's surname
  follows too.
- Exports go to the manuscripts folder (`manuscripts_dir`, default `~/Writing`), `<Title>/<Title> <date>.<ext>`, one folder per story,
  never inside the library. A hidden `.storywheel-story` marker holds the owning `universe/story`; a folder owned by another story, or
  a hand-made folder with files, makes us use "Title (Universe)". Same-day re-exports add " -2". Old `exports/` folders are moved
  out by `migrate.migrate_exports()` at startup. Warnings point to Settings (F4) > You.
- The Writer's right-click menu deletes Neovim's own MenuPopup autocmds (Neovim 0.11's `nvim.popupmenu` raises E329 once the
  default items are gone). Floating windows an item opens (Help, sidebar) keep Normal mode; the menu restarts typing only if the
  writing window is current. `tests/test_menus.py` runs every item of both menus and fails on any error message.
- Reading is remembered by file time and size (`vault.memo`): entities, outlines, manuscripts, word counts, scenes, "Appears in", and
  schemas (by folder time). Our own writes forget a file at once; the Writer's and Obsidian's changes are noticed by time. Callers get
  copies of entities, so changing one never changes what is remembered. A field roll redraws only the card and its links.
  `tests/test_performance.py` guards 50 ms for a roll and a selection in a 160-entity, four-story universe.
- One line is one paragraph (Writer, counts, scenes, export). Blank lines are allowed and mean nothing. Every paragraph line is
  indented (virtual in the Writer, a first-line indent in the .docx), `paragraph_spacing` puts a visual gap between paragraph lines,
  Enter starts the next line, paste strips leading whitespace and empty lines, Tab at a paragraph start does nothing, Alt+J joins a
  selection. Old manuscripts with blank-line paragraphs are converted once per story (`.one-line-paragraphs`), with a backup.
- Scene breaks: a line holding only `***`, `* * *` or `#` (or `* * * Title` / `*** Title` to name the scene). The one inserted is the
  `scene_marker` setting (default `***`); typing a break and Enter rewrites it to that form. `***text***` inside a line is bold italic.
- Never `startinsert` unless `notepad.can_type()` (writing window current and modifiable). Menus are tested with real key sequences.
- `QuietHeader` replaces Textual's Header (no tall mode).
- Export: title bold (default), header full title or keyword, anonymous (setting or per export; no name/contact/byline/surname, header
  "Title / page"); no author name means anonymous with a message, never a placeholder; `export_one_space` collapses double spaces after
  sentences.
- Shortcuts (Settings > Keys) are stored in Neovim notation, validated by `keys.py` (modifier or F key; not a reserved or already used
  key) and read by the Writer at start-up.
- The title bar handler calls `event.prevent_default()`: Textual runs the handler of every class in the MRO, so an override alone
  does not stop `Header._on_click`.
- Home/End in notepad mode act on the visible (wrapped) line; Home again goes to the paragraph start.
- Find and replace (Ctrl+H, `key_replace`) is a two-line floating form that matches literal text (case and whole-word options) in
  the current file; replace-all is one undo step.
- Dictionary and thesaurus: Open English WordNet 2025 (CC BY 4.0, meanings, examples, synonyms, opposites, "kind of") and Moby
  Thesaurus II (public domain, wider similar words) in one SQLite index (`dictionary.sqlite` in app storage), built by
  `dictionary_build.py` with the standard library only. The index is NOT shipped (28 MB): `storywheel dictionary install` downloads the
  sources on request (the only network use) and builds it. `dictionary.py` does the lookups (inflected forms by OEWN's own forms
  plus regular endings; close spellings for misses). One CLI entry, `lookup`, serves the Writer; `define` and `thesaurus` show parts of it.
  Screens: F5 dialog in the Wheel, Builder and Settings; F7/F6 card in the Writer. Sources and licenses are in SOURCES.md.
- Notepad mode disables, for Insert and Select mode, every Ctrl letter that is not deliberately mapped (and Ctrl+@ ] ^ _ \ Space)
  and every unmapped function key (they used to type their own name). Ctrl+H and Ctrl+Backspace delete the previous word. Find and
  replace is Ctrl+R by default (Ctrl+H arrives as Ctrl+Backspace in VTE terminals). Shift+Home/End select the visible line.
- The right-click menu entries are labelled with their keys (`<Tab>Ctrl+Z` in the menu name), including Undo and Redo.
- Words is a fifth mode (F5, `words_app.py`): Lookup, Vocabulary, Word bank, Overused. It replaces the F5 Lookup dialog. From the Writer
  it receives `{word, replace: {file,row,start,end,text}}` through `<return file>.data` (written by `sw.leave("words", data)`); "Use in
  Writer" returns `replace.new` (the picked word, inflected and capitalized like the original) in the next Writer payload, which sets
  `STORYWHEEL_REPLACE`; the Writer applies it before its first screen.
- The dictionary index is schema 2 (relations, related forms); an older index says to run `dictionary install` again. A word's
  similar words are never cut off. Indirect opposites are labelled as such. Roget's 1911 thesaurus was evaluated for "opposite ideas" and
  not used: the opposing-category pairing is not in the data.
- Word forms (`inflect.py`): irregular verbs/nouns/adjectives come from tables in the code because WordNet's own irregular lists are
  incomplete and untagged; the rest follows spelling rules. A lookup reports its base word and form so a replacement can be put in the same form.
- Word banks are `wordbank.json` in a story or universe folder; "Save as atom list" writes `<universe>/lists/<slot>/wordbank-<name>.json`
  tagged with the universe's genres (atoms are at most five words). Overused words are stem-counted, leave out everyday words, and report
  scene, line and a snippet for each place.
- Words mode now has four tabs: Lookup, Vocabulary (words worth learning, picked by `wordfreq` frequency from WordNet's single words:
  difficulty bands in Zipf terms, part of speech, subject), My words (Known / Learning, flashcards, state in `vocabulary.json`) and
  Overused. The topic explorer and the per-story/universe word banks were removed (banks migrate into My words). "Add to this universe's
  word list" puts a word on `<universe>/lists/<slot>/words-added.json`. `wordfreq` is a dependency (Apache-2.0 code, CC BY-SA 4.0 data,
  not copied); the index is schema 3 (each meaning's WordNet lexicographer file = its subject kind).
- Appearance: the Textual apps use the ANSI theme (every background is the terminal's default) unless Settings > Appearance turns
  transparency off; titles are bold accent text, not colored bars. The Writer sets `bg = NONE` on every background group and takes the
  text and accent colors; Neovide has its own `neovide_opacity`. Checked by rendering each mode in a terminal and counting default-background cells.
- Manuscripts keep STRAIGHT quotes and apostrophes (the spellchecker can't read ’ inside a word). Typing and pasting straighten curly marks;
  existing files are converted once per story (backup); the export makes quotes curly by context (`quotes.smarten`, setting on by default).
- Spellcheck is on by default; autocorrect (a short list, whole words, on the delimiter that ends the word, skipped if keys are queued) is a
  setting; each universe has a generated names list (`spell/names.utf-8.add`, with possessives) and a user list (`spell/en.utf-8.add`,
  written by Add to Dictionary); both are compiled with `mkspell!` at Writer start. `spelllang`/`spellfile` are set on every manuscript buffer.

- Batch 3 (clarity and safety): `q` means "back" in every mode (the previous mode from a trail kept in `modes.TRAIL`, or closing the panel/dialog);
  `Q` is "Quit storywheel" and always asks; in the Writer it is Alt+Q (`key_quit`). F1-F5 are labelled as modes in every footer
  (`navigation.py` builds the bindings for all modes).
- Backups can be listed and restored per story (`backups.py`, CLI `backups`, Writer menu, Builder "Backups…"). A restore first copies the current
  file to `.backups/restore-<date>-<time>/`, so it can itself be undone; backup ids are paths relative to `.backups`.
- The Writer menu is grouped with titles (Edit, Look up, Story, Leave, More); the status line reads "words: in this scene N · in the story N ·
  written today N of GOAL".
- Missing tools are all worded by `tools.missing()`: "<X> isn't installed. <What needs it>. To fix it, run:  <command>". The commands assume
  Debian/Ubuntu and pipx; they live in one table in `tools.py`. (Lua messages repeat the clipboard text.)
- Builder field history lives in `<universe>/.field-history/<entity id>.json` (values per field, plus the frame and atoms that produced each rolled
  value); it follows a placeholder id when the entity is first named, and goes when the entity is deleted. Ratings given in the Builder carry that
  provenance and slot-filled fields apply `atom_bias`, so they change rolls the way the Wheel's do (step fields already did via the engine).
- Words: "Universe words" lists and removes the words added to a universe's lists (`wordbank.added_words/remove_added`); Vocabulary has Start over
  (forget words seen; Known and Learning stay) and My words takes words typed by hand (meaning from the dictionary).
- Wheel renames: "Use: no/mix/only" is "Whole characters/places from these: no / sometimes / only" (stored values unchanged), Mix is Flavor,
  Past stories Send/+Prot/+Place are Promote/Use protagonist/Use setting.

- Batch 4: an entity records `proper: yes|no` in its frontmatter (absent = not recorded). Proper names are Title Case without an article; descriptions are
  lowercase and keep their article ("a locked box", "the sheriff"). `promote.is_proper` decides from text ("Red Draw", "The Hunting Horn" proper; "The sheriff"
  not); rolled names carry what the generator knows (`Filler.last_proper`: step name fields and group names proper, thing atoms as written); a hand-written
  name is judged by how it was typed. Only proper names stop the engine adding "the" (`Engine.proper`). `names.py` repairs older entities by matching the
  generator's atoms, with a preview (CLI `names fix`, Builder `F`).
- Writer name completion uses the words of proper names (3+ letters, any case; whole name when it is the first word). A finished lowercase word that is a
  known name word is capitalised only if the spellchecker is on and calls the lowercase word bad.
- Spelling lists from the dictionary (`spelldict.py`): `swdict` (all WordNet and Moby words plus plural/-s/-ed/-ing/-er/-est forms) and `swlenient` (known
  word + -ing -ed -er -ers -ly -ness -less -ful, un-/re-), compiled by a headless Neovim into `<home>/spelllang/spell/*.utf-8.spl` (a runtimepath folder, so
  `spelllang=en_us,swdict,swlenient`); stamped with the index's time and size and rebuilt when it changes. SpellCap/Rare/Local are dotted in grey by default
  (`spell_marks`: all, subtle, misspellings only; the last also clears `spellcapcheck`).
- Dictionary sources stay in `<home>/dictionary-sources/`; an index older than the schema is rebuilt from them offline when first opened (a note is queued
  in `dictionary.NOTES`), and only an absent source asks for a download.
- Version lives in `storywheel/__init__.py` (`pyproject` reads it); CHANGELOG.md has one entry per batch. `install.sh` supports Debian-family on x86_64/arm64.
- Machine-only settings (library, manuscripts_dir, update_remote, Neovide, fonts, line/paragraph spacing, setup_done) live in `settings.local.toml`;
  `settings.toml` is the part that can be copied between machines.
- storywheel does NOT sync and must not know about syncing (removed in 0.4.1; a separate tool outside the project does it). `migrate.migrate_sync_links()`
  turns any symlinks `sync link` left in `~/.storywheel` back into real files and drops the old `sync_folder` setting, once, saying so; the folder they
  pointed into is never touched.
- `storywheel update` passes the remote to git exactly as written (after `--`; `xps:projects/storywheel` works), fast-forwards only (an unclean tree or diverged history stops it), reinstalls with pipx only when the version changed (an in-place checkout
  needs none), and runs `post-update` in a new process so the new code does the migrations and rebuilds.

- Batch 5: Neovide is not offered on arm64 (`tools.is_arm64`, `STORYWHEEL_ARCH` overrides for tests); an installed (self-built) one is still used.
  `storywheel kitty` builds a kitty command (font and size from Settings > Writer, `modify_font cell_height N%`); Ctrl+I needs no new code: the Writer
  already turns it on under kitty, and `tests/test_kitty_keys.py` sends kitty's `CSI 105;5u` to a real Neovim to prove it is distinct from Tab.
- Grammar (optional, off by default): `grammar.py` installs LanguageTool into `<home>/languagetool/` (download or `--from zip`, zip-slip checked), starts
  `java -Xmx<N>m -cp languagetool-server.jar org.languagetool.server.HTTPServer --port P` detached (pid file, log), stops it by pid when grammar is turned
  off or the Writer closes (`VimLeavePre`). `sw/grammar.lua` sends each changed line alone (curl POST /v2/check) after a pause, with `*` markup stripped and a
  UTF-16 offset map back to byte columns; results are cached per story by line hash (`.grammar-cache.json`, invalidated when the language, disabled
  categories or rules change). Categories are switches (`grammar_cat_*`; TYPOS, TYPOGRAPHY and the picky ones off by default); turned-off rules are the
  `grammar_off_rules` setting; ignored items are per story (`grammar-ignore.json`, rule + flagged text). Memory limit and port are machine settings.
  Keys: F10 next problem, Shift+F10 list (Settings > Keys). Tests use `tests/fake_lt.py`; `STORYWHEEL_LT_CMD` replaces the server command.

- Batch 6: the Wheel, Builder, Settings and Words are screens of one Textual app (`hub.py`, `Hub`), registered with `add_mode` and built lazily by a factory
  the first time `switch_mode` reaches them, then kept. The screens still talk to a small host object (`self.b`): for the hub it is a `Handle` (Settings,
  Words) or `BuilderHandle(BuilderHooks)`; the standalone `BuilderApp`/`SettingsApp`/`WordsApp`/`StorywheelApp` stay (tests, `STORYWHEEL_CLASSIC=1`). The
  Wheel talks to `self.app.go(where, payload, message)`; promotion carries its report to the Builder's status line. Coming back to a kept screen calls its
  `enter(payload)` (Builder refreshes everything; Settings re-reads the saved values into its boxes; Words restarts only for a Writer handover or another
  universe; the Wheel switches draft only when asked for a new/named one). Trail and `back` logic are `modes._arrive`/`modes.TRAIL`, shared with the old loop.
- `hub.quiet_suspend` replaces `App.suspend` for the Writer: the driver's "leave the alternate screen" is swapped for "clear the screen", and after Neovim
  exits (it leaves the alternate screen itself) we write enter-and-clear before Textual paints, so the shell never shows. A real-terminal test counts the
  escape codes.
- `KeptScreen` skips Textual's restyle-everything on `ScreenResume` unless `app.style_version` (bumped by `appearance.apply`) changed: most of a switch's cost.
- Every download goes through `download.fetch` (User-Agent `storywheel/VERSION`; on 401/403/406/429/451 or a TLS problem it tries curl, then wget; the
  half-written file is removed). The first request is still Python's, so a server that answers it is never bothered by an external tool.
- Layout: cards are rich `Table.grid` rows (label | value | ▲▼ column), so a long value wraps under the value; list rows are a name column cut with an
  ellipsis plus a dim count; the footer is `FitFooter` (drops optional keys from the end; F1-F5, q, Q, ? always stay). Under 150 columns a screen gets
  the `-narrow` class (thinner side columns; the Builder shows its right column in place of the cards on demand). Settings and Words use Textual's
  compact Input/Select/Button; a disabled button's border is removed by an inline style because the theme re-adds it.

- `storywheel update` (0.6.1): the comparison is always installed version (the running code) against the version in the install's source folder. The
  folder comes from pip's `direct_url.json` (PEP 610; an editable install is the folder itself), else the git checkout the code runs from. If that folder has
  a git remote it is fetched (the Settings remote, if set, otherwise the first remote, passed to git exactly as written) and fast-forwarded when clean; with no
  remote it is only read. A different (newer) version reinstalls with pipx, or pip outside pipx; the same version with new commits only runs `post-update`.
  There is no private clone: `update_remote` is used only when the source folder is gone, for a temporary clone that is deleted afterwards.
- `storywheel update` records the installed source's fingerprint (git HEAD, plus "+" and a hash of `git diff HEAD` when dirty) in
  `~/.storywheel/installed-source.json` (written after each reinstall, by `update --record`, and by install.sh) and reinstalls whenever the source's
  fingerprint differs from it, even with the same version. No record means one reinstall to make one.
- Genre content lives in per-genre files tagged by the genre (`lists/<slot>/<genre>.json`, `templates/<slot>/<genre>.json`); a genre's profile weight is 4
  where its own material should be about 85% of picks. Comedy: modern 0.2. Fantasy: modern 0 and general 0.15 (it has so much of its own, and general
  atoms are mostly everyday). Mystery: modern 0.2. `tests/test_genre_content.py` holds every written genre to the same checks (sizes, annotations,
  fidelity, voice, repetition, blends); adding a genre means adding it to `GENRES`.
- Fantasy is epic and high fantasy and shares no list with fairy tale: fairy-tale lists are tagged `["fairy tale", "medieval"]` and the fairy tale
  profile gives "medieval" 1.5. "Magic with a cost" is a `loss` list (slot `{LOSS}`) used in fantasy frames.
- Mystery keeps its clues in the thread system: its escalation, climax and twist frames use `{the_thing}`, `{the_someone}`, `{the_message}` and
  `{the_disaster}`, and a test checks that threads recur in later beats.

- Batch 8 (A): `genres.json` has `_neighbors` (genre -> tags of the genres next door). `Mix.list_probabilities` splits the wildcard floor into "near"
  lists (untagged, or tagged with a neighbor or the story's own genre) and "far" ones; far lists share FAR_SHARE (10%) of it, and where a slot has no near
  lists the floor shrinks to that tenth. A genre without a `_neighbors` entry keeps the even floor (tests with made-up genres rely on that).
- An era's own words fix the season (`data/seasons.json`; `steps.season_of`). The setting step rolls the era first and the season follows it; a
  single reroll of the era passes over eras naming another season.
- Moods are entries tagged with genres, drawn by `steps.mood_field` with a mix based on the genre just rolled (`roll_mood` for samples). The `mood` slot is
  `MEMORYLESS`: the recent-picks memory would flatten its weights.
- Restricted features (`frames.RESTRICTED`: speech, carrying, feeling): an atom carrying one is drawn only by a slot that names it. Lint
  (`report.grammar_problems`) rejects a manner phrase after a preposition, a prize at a landmark, and a restricted atom no frame asks for.
  `text.fix_particles` moves a pronoun inside a particle verb the library knows ("traded away it" -> "traded it away").
- The genre scripts used to write batch 7's JSON are not kept; the JSON files are the source, edit them directly.

- Batch 8 (B): Words has five tabs: Lookup, Vocabulary, Genre words, Story words, Overused. The ★ Learning words are a view of Vocabulary (`vview`), not
  a tab. `genrewords.py` lists the library's entries by genre tag (an entry's own tags, else its list's) and category (a category is a set of atom slots
  plus frame slots such as flaw/want/need) and invents names with `markov.NameMaker`; `add_to_universe` makes a character/place/thing or writes
  `words-added.json`. `storywords.py` reads the manuscript(s), counts entity names, finds words `dictionary.base_words` does not know, and flags
  look-alikes (a space/hyphen/apostrophe squeezes to the same letters, or a near-miss: same first letter, one slip, or two in words of 5+ letters with
  similarity 0.7) of an entity name or a more frequent unknown word; words already on `<universe>/spell/*.add` are left out; rename uses
  `rename.find_matches` with a stand-in object for a word that is not an entity.

- Batch 8 (C): horror, sci-fi and romance are written like the batch 7 genres (profile weight 4; sci-fi modern 0.3 for near-future settings; horror's
  neighbors are ghost story, mythological and rural, so until ghost story exists its floor shrinks to a tenth rather than leaking mystery lists in).
  Romance's lists are deliberately portable (towns, bookshops, letters, keepsakes) because it is the commonest pairing; `test_romance_blends_with_every_other_written_genre`
  checks it against every written genre. The repetition report only flags an entry that is also 5 standard deviations above chance (4 in batches 8 to 13; it flagged a rare mood by luck about once a run), so a rare entry
  (a mood) picked 5 times against 1 expected is not reported.

- Batch 8 rework (Genre words): the tab lists WORDS, not generator slots. `wordlists.py` reads the dictionary's lemmas by part of speech from a `lexicon`
  table (one row per word and part of speech; a satellite adjective is an adjective; its first meaning; Zipf x 100 from wordfreq) and holds only the
  ordered row ids; `View.page` reads 64 rows with their meanings at a time into `virtuallist.VirtualList`, a ScrollView that renders only the visible lines.
  Genres rank (`fit` table, best score over the chosen genres), never filter. Bands are Vocabulary's, in Zipf x 100: everyday >= 380, uncommon 300-380,
  rare 230-300, very rare below 230. Proper nouns are not told apart (the index keeps lowercase lemmas).
- `genrefit.py` builds `lexicon`, `fit` and `meta.fit_stamp` INTO the existing index from the index itself (no sources or network needed, so it works on an
  index built by an older version), and `ensure()` does it when the stamp (a hash of seed words, part-of-speech hints, `_domains`, the code version and
  the index) differs. A seed's weight falls with the number of genres using the word (1, .6, .3, then 0), with how many meanings the word has, and a
  frame's fixed words count a third of an atom; a seed from an adjective/verb/noun list lights that part of speech fully and the others half. A word's
  fit by a meaning that is far down its own list of meanings is reduced. Subject domains are WordNet lemmas of topics (`genres.json` `_domains`).
  `cli_world.cmd_dictionary` and `update.post_update` call `ensure`; the Genre words tab runs it in a background thread the first time it is shown.
- The sentence-template categories were removed from Genre words ("they aren't words"); `genrewords.py` keeps only first and last names, jobs, places
  (places and landmarks) and things as the "From the Wheel" group.
- Pitfall met twice: markdown backticks in an UNQUOTED shell heredoc make the shell run them. Always `<<'EOF'`.


- Batch 9: Story words counts each entity's name as a whole phrase (case-insensitive, article optional, possessives); single words are counted only
  for the first/last name of a proper character name. A word found in any manuscript is marked Known automatically (`wordsused.py`) with where it is used.
  Overused is folded into Story words ("Often used"); Suggestions (`suggest.py`) is a tab.
- Structure beats can repeat (`repeat: {min,max}`); occurrences are keys `base__N`, the count is stored in the draft (`repeats`) and promotion writes it
  into the outline. The Writer's story overview is Ctrl+O (`key_overview`); the status line goal reads "N / M words · P%".
- Builder: no right column. Left: Universes, Stories (titles only), then a large Story panel (Outline / Scenes / Notes, `notes.md`). A Wheel draft belongs
  to a universe (`home`) and promotes into it without asking; the Builder no longer starts Wheel drafts.
- kitty replaces Neovide: inside kitty (and `writer_kitty` on) the Writer opens in its own kitty window using `writer_font`, `writer_font_size`,
  `writer_line_height` (modify_font cell_height %), `writer_padding`, `writer_opacity`; outside kitty it runs in the same terminal and a start note
  says how to install kitty. `storywheel kitty` opens storywheel itself with kitty's normal spacing; `--probe` reports remote-control abilities. Old
  Neovide settings are converted once by `migrate.migrate_settings()`. Switching in place by remote control is NOT used (see REPORT.md).

- Batch 10: only `manuscript.md` and `NN-name.md` are manuscript files (`vault.KNOWN_FILE`, mirrored in `sw/story.lua`); a short story with
  `manuscript.md` is that one file. Anything else in the folder is an "extra file": never merged, counted, exported or opened by the Writer; the Builder
  offers Open (read-only), Delete (to `.trash`) and Ignore (`.ignored-manuscript-files.json`). The one-file migration runs once per story
  (`.one-file-manuscript`). Never merge or read files storywheel did not make.
- Tests never use a real LanguageTool server: `grammar.config()` takes its port from `STORYWHEEL_GRAMMAR_PORT` when the setting is the default;
  `tests/conftest.py` sets a free port for every test.
- Lookup is five boxes (`words_app.PANES`, `lookup_panes`): Meanings, Similar, Opposites, Rhymes, Related; side by side from 150 columns, a tab bar
  below. Rhymes (`rhymes.py`) come from the CMU Pronouncing Dictionary into `rhymes.sqlite` beside the dictionary index, built offline from the kept
  `dictionary-sources/cmudict-0.7b` and downloaded by `dictionary install` (a failed download does not undo the dictionary). A perfect rhyme shares the
  sound from the last stressed vowel and differs before it; a near rhyme shares the vowel with an ending of the same consonant classes, or the ending
  after a vowel of the same family. Words are grouped by syllables, commonest first (wordfreq); near rhymes are capped at 300.

- Rhymes (0.10.1): the source is `cmudict.dict` (cmusphinx/cmudict master) plus its LICENSE (`cmudict.LICENSE`); `cmudict-0.7b` is still accepted. `rhymes.parse`
  strips ` # comment`, reads both layouts and skips non-pronunciations. A failed rhymes install is recorded in `rhymes-error.txt` and said plainly by
  `dictionary install`, `dictionary status` and the Rhymes box (never an empty list). By default only words `dictionary.knows` (an entry in WordNet/Moby or
  a form of one) are listed; the box has a "Names and rare words too" switch. Order: wordfreq commonness, else A to Z, and the box says which.

- Exports record what they were made from: `.storywheel-exports.json` in the story's export folder (hidden, like `.storywheel-story`) lists every export with
  file, format, ISO date, the manuscript's word count, a SHA-256 of the compiled manuscript text and whether it was anonymous. "Changed since the last
  export" is decided by that hash, not the word count. `storywheel exports status [--json]` lists every story in the library (state: never exported / up to
  date / changed); `storywheel exports make UNIVERSE/STORY [--format F] [--json]` exports non-interactively in the story's own export format (else yours,
  else docx) with the story's export settings and prints the path. Looking at status never creates an export folder (`export_folder(create=False)`).

- Help (batch 11): one source, `storywheel/data/help/*.md` (`helpdoc.py`). A page has an introduction, `## Keys` groups (`### ClassName | title` then
  `action: one-line description`), and free sections. Key tables are generated from the real bindings (the mode screen's and its list widgets' Textual
  `BINDINGS`; the Writer's `keys.WRITER_KEYS` and `keys.RESERVED`), F1-F5 shown as one row; `helpdoc.missing_descriptions()` must be empty (a test).
  Adding a binding or a Writer shortcut means adding its description. `tui.HELP`, `builder.HELP` etc. are lazy module attributes (the page text) for
  tests. The key of the mode you are in and `?` open the shared `helpscreen.HelpScreen`; the Writer's F3 and menu Help open a float filled by
  `storywheel help writer --width N`. Footers (`navigation.footer`) show the five modes, ? Help, q Back and at most three keys.
- Mode switching (batch 11): `Hub.show` records the wanted mode and `_drain` switches the screen first, then refreshes the mode (`_enter`); requests are
  serialized, so a burst of F-keys ends on the last one.
- Menus (batch 11): the Writer's right-click menu (`notepad.popup_menu`, rebuilt on every `MenuPopup` by the `sw_popup` autocmd group) holds only Undo, Redo,
  Cut, Copy, Paste, Fix Spelling… (when `spell.bad_word()`), Look Up, Add to Dictionary and More… (the full menu, `sw.menu`, whose height follows the window). Do
  not add a broad `OptionList { height: ... }` rule to a screen's CSS without checking dropdowns: `Select`'s list is an OptionList (`tests/test_dropdowns.py`).

- Batch 17 (screenplays): our own PDF renderer (reportlab + bundled Courier Prime), chosen after measuring screenplain, afterwriting and Wrap
  (REPORT.md, batch 17 Part A); `fountain.py` is the one reader of a script. A screenplay's manuscript is `manuscript/script.fountain`
  (`vault.SCRIPT_FILE`) and is exempt from every prose rule. Screen structures (`"screen": true`) are never rolled at random. The two
  LibreOffice export tests run in the serial pass (`conftest.SERIAL_TESTS`): two soffice processes at once share a profile and one fails.
- Batch 18: a story's format is picked, never typed. `formats.py` has the four formats (short-story, novel, feature-film, short-film); settings.toml
  keeps `format` as short-story/novel/screenplay (what the Writer and export read) plus `script_kind`, and the target as `target_words` or
  `target_pages`. A structure's JSON `"formats"` lists the formats it fits (default: the prose two; a screen structure feature-film). A Wheel
  draft keeps its format key as `format`; the structure step's `format` field shows it and is picked (click, f or e), never rolled, and a
  structure typed at the plain prompt that doesn't fit is refused with the list. The Builder's story form (`storyform.py`; + Story and `m`)
  has a title box, Format / Structure / Genres rows that open pickers, and a digits-only target box. Changing prose <-> screenplay keeps
  both kinds of files; `Story.extra_files` never lists the other format's own files. A new story with a structure gets its beats, empty,
  in the outline (`outline.blank_beats`).
- Help in tabs (batch 18): `helpdoc.tabs(page, fmt)`. The Writer: [Screenplay | Writing prose, Writing basics, Keys, Export]; a mode:
  [guide, Keys, Topics]. The TUI's `HelpScreen` has a `Tabs` bar (Tab/Shift+Tab priority bindings, digits, clicks) and searches every tab;
  the Writer's float shows them in a clickable winbar (`%N@v:lua.SwHelpTab@`). `storywheel help PAGE --tabs [--format F] [--json]`.
- Batch 12 genres: ghost story (melancholy, grief, memory, a house that remembers; horror's neighbor), noir (money, cynicism, a city that always wins; mystery's and
  thriller's neighbor) and thriller (pressure, a clock, pursuit; neighbor of mystery, noir and heist) are written like the batch 7/8 genres (profile weight 4, lists for every
  slot, frames for every beat, names with Markov training sets). Shared floor lists tagged `rural` and `mythological` (eight slots each) are the real neighbors of western,
  fairy tale, horror and fantasy; `tests/test_fidelity.py` has its exact threshold again. Lessons: an inner prize or verb whose text also exists in another list WITHOUT the
  `inner` feature makes `tests/test_coherence.py` fail (it compares by text), so give such atoms their own wording; a new neighbor list lowers a genre's own share a little
  (sci-fi has a 2-point allowance per slot in `test_genre_content.py`).

- Batch 13: ghost story, noir and thriller have frames of their own (a test caps frame sharing between genres; the older four are held at their current levels).
  `genres.json` `_own_slots` restricts a genre's concrete slots to its own lists plus general, untagged and `universe:*` lists (not neighbors'); `_tech` gives a
  genre's default technology and the `modern` / `period` features keep atoms from the wrong era. `report.sentence_problems` lints sentence shapes found by reading samples.
- Genre fit (`genrefit.VERSION` 2): `data/genre_core.json` (hand-picked adjectives `a` and verbs `v`, 40+ per written genre) is the strongest seed (`CORE_SHARE` 1.0);
  `DOMAIN_SHARE` is 0.3; `is_browsable` drops numbers, number words, Roman numerals, unknown short fragments and words under three letters from the lexicon and the fit.

- Batch 14: heist, adventure and coming-of-age are written like the batch 13 genres (own frames for every beat, `_own_slots`, `_tech`, a core vocabulary of 40+ words).
  Heist and coming-of-age default to modern technology and have a few period eras; adventure is period only. `Ctx.draw` and `pick_atom` do not filter the `era` slot by
  technology: the era is what sets the technology, so a genre can reach an era of the other kind; protagonist frames of such genres ask for `{THING:!modern}` because the
  protagonist is rolled before the setting. A frame is a near copy of another genre's when `difflib` finds it 93% alike; the three newest genres may not share more than 10%
  identical or 8% near-copy frames with any other genre, and their frames were written in distinct voices (heist: the plan and the crew; adventure: the road and the chart;
  coming-of-age: the summer and the first time) to make that possible.

- Batch 15: every genre with frames has frames of its own (at most 10% identical with any other genre, 8% near copies at 93% alike; `tests/test_genre_content.py`
  `SHARED_LIMIT`, `NEAR_LIMIT`). The rewritten genres' frames were written with `/tmp`-only generator scripts; the JSON files are the source.
- Ages: genres.json `_ages` ({genre: [youngest, oldest]}, `_default` 20-80; coming-of-age 13-19; a blend uses the overlap, else the first). Jobs carry `child`, `teen`,
  `adult`, `elder`; a job with none is `adult`, and an adult's job is open to an elder (`steps.job_bands`). The protagonist's age is invented in the job's bands when the
  job is known, and the job is drawn for the age's band when the age is known (`Ctx.invent_age`, `Ctx.job_accept`), so either order agrees.
- The same atom text in two lists has the union of their features (`Engine.features_of`): "tutor" is a teen's job in coming-of-age's list. Era lists may not disagree
  about technology for the same text (a test).
- An empty (or blank) field in a kept step or the current item is missing, not a value (`steps.filled`): frames get a stand-in.
- Eras: never against a modern/period atom already in the story; with a genre default technology, other genres' eras of the other kind are ruled out, the genre's
  own eras never (`Ctx.era_accept`, `Ctx.own_eras`). Western, fairy tale and fantasy are `period` in `_tech`. Faker's jobs carry `modern` (`engine.GENERATED_FEATURES`).
- Repetition: `report.FAIL_SD` 5 fails, `report.WATCH_SD` 4 lists a "watch" item. `tools/genre_check.py` is the all-genre check; run it at the end of a content batch.

- Batch 16: frames (every template slot: titles, premises, twists, beats) come only from the story's own genres. `Mix.list_probabilities` keeps only the lists
  of the story's genres plus general and untagged ones for any template slot and gives the floor nothing there; `Mix.frame_entry_ok` drops a general frame
  whose entry tags name only other genres (`Engine.choose_entry`). Neighbors and the floor still apply to atoms. The `wildcard` oddity titles therefore no
  longer appear unless a story's genres include `wildcard`.
- People know the protagonist's age: `close` and `someone` entries may carry `child`/`teen`/`adult`/`elder`; an entry with none fits anyone, `adult` includes
  `elder` (`steps.person_fits`, `Ctx.slot_accept`). Every `close` entry is marked; a `someone` is marked only when it implies a grown-up's relationship to the
  protagonist (an old flame, a jilted fiancé, a former partner).
- The repetition report's expected count is the larger of the weighted share and an even share among the list's entries that were picked at all: the
  recent-picks memory rotates a list's usable entries, so weights alone underestimated untagged frames and narrowed verb sets and flagged them falsely.

- Batch 19 (exception to the stable rule, at the owner's request because usage was nearly out): after each item passes its related tests it is committed,
  tagged `b19-N` and `stable` is moved to it, without a full run in between. Item 1: `N` / the New draft button in the Wheel asks for a universe and starts a fresh draft.
