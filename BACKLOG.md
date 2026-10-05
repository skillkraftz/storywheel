# storywheel backlog

A short roadmap. CLAUDE.md describes the design, REPORT.md the state of the last batch, CHANGELOG.md what each version added. When an item is
finished, move it into **Done** with the tag that finished it. Status words: **Bug**, **Stub**, **Partial**, **Missing**, **Verify**, **Idea**.

Last updated after batch 13.


## Now

Nothing is broken that I know of (no open bugs). What is worth doing first, from real use:

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
- **Screenplay profile.** *Stub.* Today it writes an unformatted `.fountain`. Needs Fountain editing (scene headings, character names,
  transitions; Tab/Enter moves between elements) and export to formatted pages (Courier 12, element margins, page numbers) as .docx and PDF.
- **Rewrite the legacy frames.** *Partial.* Mystery, horror, sci-fi and romance share 35-65% of their frames; give each its own (the three newest share none). `LEGACY_CEILING` in `tests/test_genre_content.py` holds them where they are.
- **Content for the last three genres** (heist, coming-of-age, adventure): atom lists, templates, name sets, with
  features on every atom and `tests/test_genre_content.py` (add the genre to `GENRES`). Heist is thriller's and noir's neighbor.
- **Configurable keys outside the Writer.** *Missing.* Settings > Keys covers the Writer only; extend it to the Wheel, Builder, Settings and the
  F1–F5 mode keys, with the same conflict checks.
- **Obsidian `[[wikilinks]]` resolving to entities.** *Missing.* Resolve `[[Name]]` in entity notes and outlines (Builder links and "Appears in";
  Writer peek and completion).
- **Words typed outside the Writer aren't counted** (Obsidian, say). *Partial.* Count the difference when the program notices a file changed.
- **Changing the library folder** only points at the new place. *Partial.* Offer to move the universes.
- **A draft can only be promoted once.** *Partial.* Decide: re-promoting updates the universe (with a preview), or stays one-way.


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

- Writing sprints: a timer with a word target in the status line.
- Show curly quotes while writing without changing the file (a concealed overlay).
- Richer repeated-word checks: sentence openings, -ly adverbs, "filter" words (felt, saw, noticed), a per-scene view.
- Roget's 1911 categories as "opposite ideas": the pairing is not in the data (evaluated in batch 2a, not used); would need ~400 pairs by hand.
- A plainer set of Vocabulary subjects than WordNet's categories.
- Join with nothing selected: join the run of lines around the cursor.
- Switch windows in place with kitty remote control instead of a second window (see `storywheel kitty --probe`); not depended on.


## Done

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
