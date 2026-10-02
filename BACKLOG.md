# storywheel backlog

The pile of things still to build or finish, after the fifth pass (925 tests,
tag pass5-export). Work through it in batches; when an item is done, move it
to the Done list at the bottom with the tag that finished it. Add new items as
they come up. CLAUDE.md describes the design; this file tracks the work.

Status words match REPORT.md: **Bug**, **Stub**, **Partial**, **Missing**,
**Verify** (probably works, needs checking), **Idea** (not decided).


## 1. Bugs

(none open)


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
- **Neovide** look is unchecked. *Verify.* Checked in batch 1: Neovide 0.16.2 is
  installed here and starts with our config, stays running, and prints no
  errors. What is not checked is how it looks (font, size, line spacing); a
  screenshot from this session could not see the window (Wayland). Try the
  three settings and report.
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


## 3. Missing basics for a writing app

- **Restore from backups.** *Missing.* Rolling backups and conversion backups
  exist, but there's no way to browse and restore one. A list of backups per
  story with date, word count and a preview, and "restore" that itself backs
  up the current version first.
- **Configurable keys outside the Writer.** *Missing.* Settings > Keys
  covers the Writer only. Extend it to the Wheel, Builder and Settings keys,
  including the F1–F4 mode keys, with the same conflict checks.
- **Obsidian `[[wikilinks]]` resolving to entities.** *Missing.* CLAUDE.md says
  wikilinks in notes "should resolve to entities where possible"; nothing reads
  them. Resolve `[[Name]]` in entity notes and outlines (Builder: show as links
  and in "Links"/"Appears in"; Writer: peek and completion).

## 4. Dictionary and thesaurus: follow-ups

Built in batch 1 (see Done). Still open:

- **Inflect the replacement.** *Idea.* Looking up "running" and picking
  "sprint" gives "sprint", not "sprinting". Match the looked-up form (plural,
  past tense, -ing) when replacing.
- **Look up from a Builder field's right-click menu** ("look up" the word under
  the mouse). *Missing.*
- **Part of speech in the Writer card.** *Idea.* Group the similar words by
  the meaning (sense) they belong to instead of one flat list; the flat list
  is long for common words.
- **Bundling the index.** *Idea.* It is 28 MB, so it is downloaded on request
  (`storywheel dictionary install`, 6 seconds) rather than shipped. Revisit if
  a smaller index (common words only) is wanted in the package.
- **Lookup history / recent words** in the dialog and card. *Idea.*


## 4b. Found in batch 1

- **Shift+Home / Shift+End** in notepad mode still select to the start/end of
  the whole line, not the visible wrapped line. *Partial.*
- **Find and replace** works on the current file only (a novel has one file per
  chapter) and is literal text only. *Idea:* replace in all chapters; regular
  expressions.
- **Ctrl+H** reaches Neovim as Backspace in terminals that send ^H for
  Backspace (most send DEL, so it works; if yours doesn't, set another key in
  Settings > Keys, for example Alt+H). *Verify* in the owner's terminal.
- **`storywheel lookup` start-up time** is fine (under 0.1 s) because the CLI
  imports lazily; keep it that way when adding commands. *Note.*

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

1. ~~Bugs (section 1), the verify items, find and replace, and the dictionary
   and thesaurus.~~ Done (tags b1-*).
2. Novel and screenplay profiles.
3. The rest of section 2, backups restore, and configurable keys everywhere.
4. Content: the twelve genres, a few at a time.
5. The world model.


## Done

- **Title bar clicks** (`prevent_default()`; pilot test in every mode; the old code goes 1 → 3) — `b1-header`.
- **Home and End** act on the visible wrapped line; Home again goes to the paragraph start — `b1-homeend`.
- **Verify, section 2:** Scenes tab → Writer at the chosen scene (works; covered by tests) — `b1-verify`.
  Neovide: starts and runs, look unchecked (see section 2).
- **Verify, section 3:** the CLAUDE.md audit. Universe-own atom lists and starting a Wheel draft from inside a
  universe both work and now have tests; wikilinks are missing (listed in section 3) — `b1-verify`.
- **Find and replace in the Writer** (Ctrl+H or the Settings > Keys choice; match case, whole word, replace one,
  replace all in one undo step, live match count) — `b1-replace`.
- **Dictionary and thesaurus** — data and lookups (`b1-dictionary-core`), the Lookup dialog on F5 in every mode
  (`b1-dictionary-tui`), the Writer card on F7/F6 with replace-in-place (`b1-dictionary-writer`).
