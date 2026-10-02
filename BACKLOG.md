# storywheel backlog

The pile of things still to build or finish, after the fifth pass (925 tests,
tag pass5-export). Work through it in batches; when an item is done, move it
to the Done list at the bottom with the tag that finished it. Add new items as
they come up. CLAUDE.md describes the design; this file tracks the work.

Status words match REPORT.md: **Bug**, **Stub**, **Partial**, **Missing**,
**Verify** (probably works, needs checking), **Idea** (not decided).


## 1. Bugs

- **Title bar still expands when clicked.** *Bug.* `QuietHeader._on_click`
  overrides the method, but Textual calls the click handler of every class in
  the MRO, so `Header._on_click` still runs and toggles `-tall`. Fix: take the
  event and call `event.prevent_default()`. Verified: with that change the
  header stays 1 line after a click; with the current code it goes 1 → 3.
  Add a pilot test that clicks the title in every mode and checks the height.
- **Home and End** go to the start and end of the whole paragraph, not the
  visible wrapped line. *Partial.* In a notepad-style editor they should act on
  the screen line (and Home twice could go to the paragraph start).


## 2. Stubs and partials

- **Screenplay profile.** *Stub.* Today it writes an unformatted `.fountain`.
  Needed: Fountain editing (scene headings, character names and transitions
  recognized; Tab or Enter moves between elements the way screenwriting apps
  do), and export to properly formatted screenplay pages (Courier 12, standard
  element margins, page numbers) as .docx and PDF.
- **Novel profile.** *Partial.* Needed: Shunn's novel title page (contact
  block, word count, title, byline), each chapter starting on a new page about
  a third of the way down with its heading, chapters as the sidebar's top
  level with scenes inside them, and adding, renaming and reordering chapters.
- **Builder ratings** are recorded but don't change rolls. *Partial.* Entity
  field rolls need the same provenance (frame and atoms) the Wheel has, so +/-
  can down-weight them.
- **Builder field history** isn't saved between runs. *Partial.* Save it with
  the entity (or beside it) so the scroll wheel still works tomorrow.
- **Neovide** is untested on a real install. *Verify.* Install it, try the
  font, size and line-spacing settings, and fix what shows up.
- **A draft can only be promoted once.** *Partial.* Decide whether
  re-promoting should update the universe (with a preview) or stay one-way.
- **Words typed outside the Writer aren't counted** (for example in
  Obsidian). *Partial.* Count the difference in manuscript words when the
  program notices the file changed.
- **Changing the library folder** only points at the new place. *Partial.*
  Offer to move the existing universes there.
- **Renaming through the history wheel** opens the rename preview every
  time. *Partial.* Only offer the rename when the wheel stops on a name.
- **Join with nothing selected** says so and does nothing. *Idea.* Joining
  the run of lines around the cursor could be friendlier.
- **Schema files edited in place** are only noticed on restart. *Partial,
  low priority.*
- **Scenes tab → Writer** at the chosen scene. *Verify.* Earlier marked
  Partial ("the Writer doesn't jump to it yet"); the one-file manuscript pass
  may have finished it.


## 3. Missing basics for a writing app

- **Find and replace in the Writer.** *Missing.* Ctrl+F finds; there's no
  replace. Ctrl+H (or a configurable key) with replace-one, replace-all, match
  case and whole word, and a count of replacements.
- **Restore from backups.** *Missing.* Rolling backups and conversion backups
  exist, but there's no way to browse and restore one. A list of backups per
  story with date, word count and a preview, and "restore" that itself backs
  up the current version first.
- **Configurable keys outside the Writer.** *Missing.* Settings > Keys
  covers the Writer only. Extend it to the Wheel, Builder and Settings keys,
  including the F1–F4 mode keys, with the same conflict checks.
- **Briefed features to confirm.** *Verify.* Audit CLAUDE.md against the
  code and list anything described there that doesn't exist yet (for example
  Obsidian `[[wikilinks]]` resolving to entities, universe-specific atom lists,
  starting a Wheel draft from inside a universe).


## 4. Dictionary and thesaurus (new)

Look up any word without leaving the program: definitions, similar words and
opposite words, fully offline.

**Data.** Open English WordNet (CC BY 4.0, the maintained successor to
Princeton WordNet) gives definitions by part of speech, example sentences,
synonyms, antonyms, and "kind of" relations. Moby Thesaurus II (public domain)
adds much broader synonym lists. Build a compact SQLite index once, so
lookups take milliseconds; either bundle it if the size is reasonable, or
fetch it with a one-time `storywheel dictionary install` command (the only
network use, and only when asked). Record sources and licenses in SOURCES.md.

**Lookups** understand inflected forms ("running" finds "run", "geese" finds
"goose"), and say plainly when a word isn't found, with close spellings.

**In the Writer.** A key (configurable, for example F7) on the word under the
cursor, or on a selection, opens a floating card: definitions grouped by part
of speech, synonyms, antonyms. Picking a synonym replaces the word, keeping
its capitalization. A second key opens the same card for a typed word. Also in
the right-click menu.

**In the TUI.** A Lookup dialog reachable from every mode with one key: type a
word, see the same card. In the Builder, a field's right-click menu could
offer "look up" for the word under the mouse.

**CLI.** `storywheel define WORD --json` and `storywheel thesaurus WORD
--json`, which the Writer uses.

**Tests.** Lookups for common, inflected and missing words; the Writer card
opens and replaces with capitalization kept; the TUI dialog; no network use
at run time.


## 5. Content and generator

- **The other twelve genres.** Write and annotate atom lists, templates and
  name sets for mystery, romance, horror, sci-fi, comedy, heist, ghost story,
  coming-of-age, noir, thriller, fantasy and adventure, the way western and
  fairy tale were done (features on every atom, the fidelity and repetition
  reports). Raise "modern" where sci-fi, comedy and heist need it.
- **The world model.** See CLAUDE.md's roadmap: simulate a small cast with
  values, goals and relationships and pick events whose preconditions hold, so
  "because of that" is literally true. Universes are its natural input.


## 6. Ideas (not decided)

- **Writing sprints:** a timer with a word target, shown in the status line.
- **Overused words:** highlight words repeated close together, and a report of
  the most frequent words in a story.
- **A terminal that sends Ctrl+I distinctly** (kitty, WezTerm, foot, ghostty)
  would make Ctrl+I italic work outside Neovide. Not code; a setup note.


## Suggested batches

1. Bugs (section 1), the verify items, find and replace, and the dictionary
   and thesaurus.
2. Novel and screenplay profiles.
3. The rest of section 2, backups restore, and configurable keys everywhere.
4. Content: the twelve genres, a few at a time.
5. The world model.


## Done

(Move items here with the tag that finished them.)
