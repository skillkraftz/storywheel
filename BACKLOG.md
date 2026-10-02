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
  including the F1–F5 mode keys, with the same conflict checks.
- **Obsidian `[[wikilinks]]` resolving to entities.** *Missing.* CLAUDE.md says
  wikilinks in notes "should resolve to entities where possible"; nothing reads
  them. Resolve `[[Name]]` in entity notes and outlines (Builder: show as links
  and in "Links"/"Appears in"; Writer: peek and completion).

## 4. Dictionary, thesaurus and Words: follow-ups

Built in batches 1 and 2a (see Done). Still open:

- **Roget's Thesaurus (1911) for "opposite ideas".** *Missing, evaluated.* The Roget file that ships with the Moby
  project (`roget13a.txt`, Project Gutenberg #3202) has 1,000 numbered categories but the pairing of opposite
  categories is not in the data: its own header says the side-by-side layout "has been abandoned" and words are listed in
  entry order. Adjacent categories are often opposites (31 Greatness / 32 Smallness) but not always (7 State / 8
  Circumstance), so an automatic pairing would sometimes show unrelated ideas as opposites. Not used. If wanted: pair
  categories by hand once (about 400 pairs), or by title prefixes (in-/un-/non-) and review the list.
- **Indirect opposites per meaning.** *Idea.* They are computed from all of a word's similar words, so a word with
  several meanings can show an opposite that belongs to another meaning ("fast" → "mobile", via "immobile"). Compute
  them per meaning, and show them under that meaning.
- **Shift+Home/End twice, and Ctrl+Shift+arrows.** *Idea.* The rest of the notepad selection keys.
- **Look up from a Builder field's right-click menu** ("look up" the word under the mouse). *Missing.*
- **Bundling the index.** *Idea.* It is 42 MB now (relations added), so it is downloaded on request
  (`storywheel dictionary install`, about 10 seconds) rather than shipped. Revisit if a smaller index (common words
  only) is wanted in the package.
- **Words: richer overused-word checks.** *Idea.* Repeated sentence openings, adverbs in -ly, "filter" words (felt, saw,
  noticed); a per-scene view; a threshold setting.
- **Words: word bank in the Writer.** *Idea.* Complete from the bank while typing, like character names.
- **Words: look up a word from the Wheel's cards** (a key on the selected field's text). *Idea.*
- **Inflection** covers regular English plus about 150 irregular verbs and 80 irregular nouns; multi-word phrases inflect
  the first word of a verb phrase and the last of a noun phrase. Rare irregulars and adjective/adverb edge cases may
  come out plain ("more joyful" for a long adjective is deliberate). *Note.*

## 4b. Found in batch 1 and 2a

- **Find and replace** works on the current file only (a novel has one file per chapter) and is literal text only.
  *Idea:* replace in all chapters; regular expressions.
- **Ctrl+R** is the default for replace now. *Verify* in the owner's terminal that Ctrl+R arrives as itself (VTE
  sends 0x12 for it, which is distinct from Tab, Enter and Backspace, so it should).
- **`storywheel lookup` start-up time** is fine (under 0.1 s) because the CLI imports lazily; keep it that way when
  adding commands. *Note.*
- **The dictionary index must be rebuilt** after upgrading to batch 2a (schema 2): `storywheel dictionary install`.
  Lookups say so plainly if the index is older. *Note.*

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
  (`b1-dictionary-tui`, replaced by the Words mode in batch 2a), the Writer card on F7/F6 with replace-in-place
  (`b1-dictionary-writer`).

### Batch 2a: the Writer's keys and the language tools

- **Neovim's insert-mode Ctrl keys** (Ctrl+U deleting a line, W, T, D, O, R, K, E, N, P, J, L, ], ^, _, @, \) do nothing in
  notepad mode — `b2a-ctrl-keys`.
- **Unmapped function keys** do nothing (F5 used to type "<F5>"; F5 is now Words) — `b2a-fkeys`.
- **Ctrl+H / Ctrl+Backspace** delete the previous word (Ctrl+Delete the next); **replace** moved to Ctrl+R —
  `b2a-replace-key`.
- **Shift+Home / Shift+End** select to the start/end of the visible line — `b2a-shift-home`.
- **Undo and Redo** in the right-click menu and the Writer menu, every right-click entry labelled with its key —
  `b2a-undo-menu`.
- **Writer card:** every similar word, grouped by meaning, then the full broad list, scrollable, with a filter
  (`b2a-card-all`); opposites plus indirect opposites, labelled; Roget evaluated and not used (`b2a-card-opposites`);
  the same keys for F6 and F7 — Enter looks a word up, b/n back and forward, r replaces, i inserts, c copies, keys in
  the footer (`b2a-card-keys`); replacements in the same form as the original, running → sprinting (`b2a-card-form`,
  with the engine in `b2a-inflect`).
- **Words mode (F5)** — a fifth mode, from every mode including the Writer: `b2a-words-mode`; Lookup with meanings,
  every similar and opposite word, wider/narrower words, parts, related forms, history (`b2a-words-lookup`); Use in
  Writer (`b2a-words-use`); vocabulary builder (`b2a-words-vocab`); word bank per story or universe saved as an atom
  list (`b2a-words-bank`); overused words (`b2a-words-overused`, data layer `b2a-overused-data`, `b2a-wordbank`).
- **Shift+Home/End** and the **"Inflect the replacement"**, **"Part of speech in the card"** and **"Lookup history"**
  follow-ups from batch 1 are done (above).
