# storywheel backlog

A short roadmap. CLAUDE.md describes the design, REPORT.md the state of the last batch, CHANGELOG.md what each version added. When an item is
finished, move it into **Done** with the tag that finished it. Status words: **Bug**, **Stub**, **Partial**, **Missing**, **Verify**, **Idea**.

Last updated after polish 2 (ISSUES 1-36 fixed; ISSUES.md lists what is left).


## Now

Nothing is broken that I know of; ISSUES.md is the list of what was found and fixed. What is worth doing first, from real use:

- **Check the kitty Writer window on your machine.** *Verify.* kitty is not installed on the development machine, so the launch command
  (`font_size`, `modify_font cell_height N%`, `window_padding_width`, `background_opacity`, `--start-as=maximized`) is tested only against fakes.
  Needs kitty 0.30+. Try Settings > Writer, then `storywheel kitty --probe` to see whether in-place restyling via remote control is on offer.
- **Check Ctrl+R (find and replace) and Ctrl+O (story outline) in your terminal.** *Verify.*
- **Install rhymes for real** (`storywheel dictionary install`) and compare the CMU license header with SOURCES.md. *Verify.* Only a hand-made file in cmudict's format was tested.
- **Run `install.sh` for real** on a clean machine. *Verify.* Tested only as a dry run on a pretend machine; the Neovim download and `apt`
  steps are unchecked here.
- **Try LanguageTool for real** (Settings > Grammar). *Verify.* Tested against a fake server only; report noisy rules.


## Next

- **Novel profile.** *Partial.* Shunn's novel title page (contact block, word count, title, byline), each chapter on a new page a third of the
  way down with its heading, chapters as the sidebar's top level with scenes inside, adding/renaming/reordering chapters.
- **From batch 18 (held back to keep to the checklist).** *Idea.*
  - The novel's own help tab (today a novel gets Writing prose) and a novel guide once the novel profile is deeper.
  - Fade In's lowercase "(cont'd)" style as a choice beside (CONT'D).
  - The story form for the universe too (genre leanings, exclusions and boosts are still typed in a box with `s`).
  - Per-format default targets in Settings (today: 5,000 words, 80,000 words, 110 pages, 12 pages, in `formats.py`).
  - A help tab for the Wheel's current step (the step hint is on the card today).
- **Versions from real use.** *Verify.* Try a short story and its screenplay side by side. Held back: a key in the Writer to jump to another
  version; mapping beats between structures by hand in the Builder (today you copy text between the sections); "Also start as" in the plain prompt's
  promotion (only the full-screen preview and `promote --also` have it); a "sync this outline into the other version" action (versions are copies on purpose).
- **Screenplays from real use.** *Verify.* Batch 17 built a first usable version (Fountain in the Writer, the flip test, PDF/.fdx/.fountain
  export). Write a few pages and report what needs polish. Ideas held back from batch 17 to keep to its checklist:
  - Scene numbers on the page (Fountain `#12#` is parsed but not printed) for shooting scripts; revision colours, revision marks (`*` in the margin), locked pages.
  - Move scenes from the sidebar (today: cut and paste); a scene's synopsis shown in the sidebar.
  - Story words and Overused that understand Fountain (skip cues and headings); character speech counts per scene.
  - Smarter prose-to-script conversion (versions copy prose as Fountain action with forced headings; recognising dialogue is not attempted).
  - Dual dialogue that breaks across pages (today the pair moves to the next page whole).
  - A tighter page estimate in the Writer (it uses the PDF's wrap widths but adds a flat 4% for the keep-together rules instead of applying them).
  - Title page fields beyond Title/Credit/Author/Source/Draft date/Contact (Notes, Copyright, WGA registration).
  - `.docx` screenplay export for people who insist on Word.
- **Configurable keys outside the Writer.** *Missing.* Settings > Keys covers the Writer only; extend it to the Wheel, Builder, Settings and the
  F1–F5 mode keys, with the same conflict checks.
- **Obsidian `[[wikilinks]]` resolving to entities.** *Missing.* Resolve `[[Name]]` in entity notes and outlines (Builder links and "Appears in";
  Writer peek and completion).
- **Words typed outside the Writer aren't counted** (Obsidian, say). *Partial.* Count the difference when the program notices a file changed.
- **Changing the library folder** only points at the new place. *Partial.* Offer to move the universes.
- **A draft can only be promoted once.** *Partial.* Decide: re-promoting updates the universe (with a preview), or stays one-way.


## Weak spots found by the batch 15 check (`tools/genre_check.py`; batch 16 fixed the rest)

- **Place names can double a word** ("Hollow Hollow" from `place_adj` + `place_feature` in horror). Skip a feature that repeats the adjective.
- **Western and fairy tale have no frames of their own** (they use the general frames); the frame-sharing check does not cover them.
- **The oddity titles are unreachable.** The `wildcard` title frames came only through the floor, which no longer applies to frames. Give them a
  small share of their own (an occasional strange title) or remove them.
- **A teen protagonist's close people are one general list.** Marked by age now, but not by genre: a coming-of-age story and a western share it.


## Later

- **The world model** (CLAUDE.md roadmap 4): simulate a small cast with values, goals and relationships plus objects with owners, and pick events
  whose preconditions hold, so "because of that" is literally true. Universes are its input. A dedicated love-interest slot belongs here.
- **Find and replace** across all chapters, and with regular expressions (today: the current file, literal text).
- **Autocorrect:** capitalize sentence starts; a list you can edit in Settings.
- **Indirect opposites per meaning** in the dictionary (today computed from all of a word's similar words, so "fast" can show "mobile").
- **Look up a word** from a Builder field's right-click menu and from the Wheel's cards.
- **Complete from a universe's added words** in the Writer, like character names.
- **Peek says "no entity called X in <universe>"** when it finds nothing.
- **Renaming through the history wheel** should offer the rename only when the wheel stops on a name.
- **Remove the old per-mode apps** (`BuilderApp`, `WordsApp`, `SettingsApp`, `StorywheelApp`) once no test needs them.
- **Compact Settings switches**: Textual's Switch is three lines tall; a plain "[x] on" widget would save about 40 lines on the Writer tab.
- **Prune `.field-history/`** files (only removed with their entity today; they are small).
- **Bundle a smaller dictionary index** (common words only, instead of the 42 MB one that is downloaded on request).


## Ideas (not decided)

- **Shapes (batch 21) left over.** *Partial.* (1) *Two leads and an ensemble* only add a partner or a company to the Protagonist step; every beat still
  tells the lead's story in the singular. A real version needs frames with a plural or dual subject (agreement for habit verbs, "they"), beats that
  alternate between the leads, and a Builder view of the cast. (2) *A place* and *no one* use "everyone in {place}" and "someone" as the subject of
  frames written for a person, and set aside the frames that read the protagonist's job, traits, want or need (about a third of the body frames,
  and all but 7 of the setup, 7 of the "once" and 8 of the premise frames until batch 21 added person-free ones). A mood piece would read better with
  frames written for it (images, weather, objects as the subject), and a place story with frames where the place acts (the town "remembers", the
  river "rises"). (3) *Endings:* only the general climax and resolution frames carry an ending (about 30 of 180 climax frames); the genre files
  carry none, so `steps.ENDING_SHARE` makes six in ten draws come from the tagged ones. Tagging the genre files, by hand, would make the endings
  read in the genre's own voice. (4) The structure step's format picker does not start on the current format (the new ones do). (5) The plain
  prompt does not ask the format first. (6) Flash fiction has no structure of its own beyond Single Moment, and no shorter Story Spine.

- Writing sprints: a timer with a word target in the status line.
- Show curly quotes while writing without changing the file (a concealed overlay).
- Richer repeated-word checks: sentence openings, -ly adverbs, "filter" words (felt, saw, noticed), a per-scene view.
- Roget's 1911 categories as "opposite ideas": the pairing is not in the data (evaluated in batch 2a, not used); would need ~400 pairs by hand.
- A plainer set of Vocabulary subjects than WordNet's categories.
- Join with nothing selected: join the run of lines around the cursor.
- Switch windows in place with kitty remote control instead of a second window (see `storywheel kitty --probe`); not depended on.


## Done

- **Shapes (0.23.0):** Flash fiction; the format asked first and changeable (F); Save the Cat, Hero's Journey, Seven-Point, Freytag, Single Moment,
  Circular Story and In Medias Res; story focus (one, two leads, ensemble, a place, no one); ending (any, triumph, bittersweet, tragic, open).
- **Versions (0.22.0):** the same story in several formats as sibling stories in one universe (New version, grouped list, `]`/`[`, Wheel promotion's
  "Also start as", `story version`, rough manuscript conversions, the Writer showing title and format).

Tags are in git (`git tag`); CHANGELOG.md says what each batch contained.

- **Foundation sweep and the first passes:** storage, universes, promotion, Builder, Writer, switching, Shunn export, manuscripts, notepad mode,
  menus, paragraphs, settings — `foundation-*`, `pass2-*` to `pass5-*`.
- **Batch 1:** title bar clicks, Home/End, find and replace, dictionary and thesaurus core, Lookup card in the Writer — `b1-*`.
- **Batch 2a:** Ctrl keys and function keys do nothing odd in notepad mode, undo in menus, Words mode (Lookup, Vocabulary, Overused), inflection,
  Writer card keys — `b2a-*`.
- **Batch 2b:** transparent background and Appearance settings, straight quotes with curly export, autocorrect, per-universe spelling lists,
  Vocabulary with wordfreq, review of every mode — `b2b-*`.
- **Batch 3:** `q` back / `Q` quit, clear labels and legends, grouped Writer menu, one wording for missing tools, backups restore (CLI, Writer,
  Builder), field history and ratings in the Builder, vocabulary start-over — `b3-*`.
- **Batch 4:** proper names vs descriptions, name completion, spelling from the dictionary, version and changelog, `install.sh`, `storywheel setup`,
  `storywheel update`, sync built and removed again — `b4-*`.
- **Batch 5:** optional LanguageTool grammar checking, `storywheel kitty`, Ctrl+I under kitty's protocol — `b5-*`.
- **Batch 6:** one Textual app for the four screen modes, kept screens, quiet Writer suspend, layouts and narrow layouts, download fallbacks,
  `storywheel update` fixed — `b6-*`.
- **Batch 7:** update by commit, comedy, fantasy and mystery content — `b7-*`.
- **Batch 8:** neighbors, seasons, moods and sentence breaks; horror, sci-fi, romance; Words tabs reworked; Genre words as long ranked lists —
  `b8-a`, `b8-b`, `b8-horror`, `b8-scifi`, `b8-romance`, `b8-genre-words`.
- **Batch 16:** frames only from the story's genres; people fit the protagonist's age; western and fairy tale repetition; generator scripts retired (`b16-*`).
- **Batch 15:** own frames for mystery, horror, sci-fi and romance; ages and jobs; no blank fills; eras and technology in every genre; watch list; the all-genre check (`b15-*`).
- **Batch 13–14:** the three genres resolved (`b13-*`); testing policy and heist, adventure, coming-of-age (`b14-*`).
- **Batch 11–12:** help and footers (`b11-*`), the help toggle (`b12-a`), ghost story, noir, thriller and the shared rural and mythological floor lists (`b12-*`).
- **Batch 10:** extra files in a manuscript folder are never merged (`b10-a`); Lookup in five boxes with rhymes from CMU (`b10-b`).
- **Batch 9:** Story words counts whole names as phrases (`b9-a`); Words tabs reordered, Suggestions, Overused folded into Story words, used words
  auto-Known (`b9-b`); repeatable beats and Ctrl+O story outline, goal in the status line (`b9-c`); Builder with a large Story panel, +Story,
  a draft's home universe (`b9-d`); the Writer in its own kitty window, Neovide removed (`b9-e`); this roadmap (`b9-f`).


## Notes worth keeping

- Genre fit is a guess: it ranks, never hides. Dials: `DECAY`, `MOBY_SHARE`, `DOMAIN_SHARE`, `KEEP` in `genrefit.py`, and each genre's `_domains`
  in `genres.json`. Genres without lists of their own rank only by subject domains.
- Missing-tool commands assume Debian/Ubuntu; they live in one table in `storywheel/tools.py`.
- `storywheel update` of a plain install needs a git remote that serves the repository; there is no signature check.
- Switch times on a Raspberry Pi are an estimate; `tools/measure_switch.py hub` on the Pi gives real figures.
- No git remote is configured in this checkout on purpose; nothing is pushed.

## Help pages that may name keys that no longer exist (batch 19, item 6: a quick search, not an audit)

- Searched the help pages for removed things (Neovide, "Wheel draft" started from the Builder, the right column, sync, Ctrl+H find): nothing found.
- `writing-prose.md` now says "The sidebar key (see the Keys tab)", not "Space n" (fixed in batch 19).
- Not checked: every key named in free text (as opposed to the key tables, which are made from the real bindings and tested).
