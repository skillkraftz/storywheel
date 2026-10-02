# storywheel — project brief

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

**Content status**: western and fairy tale are fully written and annotated
with features. The other twelve genres run on general atoms until their lists
are written. Expanding genre content is ongoing work outside this sweep.


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
- **Screenplay**: Fountain (`.fountain`) files with Fountain-aware editing.
  Export through a Fountain converter if one is installed. It's fine for this
  to be a clearly marked stub in the first sweep.


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
- Entity field history in the Builder lives for the session only.
- Ratings on Builder fields are recorded but do not (yet) down-weight anything.
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

