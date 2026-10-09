# storywheel decisions log

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

- Polish 1 (ISSUES.md 1-15): the Writer's right-click menu is our own float (`sw/context.lua`; `mousemodel=extend`), not Neovim's pop-up, which runs an
  item when the right button is let go over it. The cursor never rests on a scene-marker line in notepad mode (`prose.guard_marker`; arriving moves it
  on; renaming a scene is the sidebar's `r`). F3 in the Wheel opens only the draft's own promoted story, never the last one. A deleted Wheel draft goes to
  `<home>/.trash`. Past stories' protagonist/setting buttons stay "send to a universe" and say so (offering them as a candidate on the current draft is
  undecided). `tests/nvdrive.py` (keys and mouse into a headless Writer, step by step) and `tests/ptydrive.py` (a real terminal read through pyte) are the
  drivers for tests that must press keys and click; a headless Neovim cannot fire CursorMoved while keys are queued, so cursor-movement behavior is tested on a pty.

- Polish 2 (ISSUES.md 16-36): the test pty (`tests/ptydrive.py`) is sized before Neovim starts and drops DCS strings before pyte sees them (pyte prints them
  as text); `STORYWHEEL_NVIM` picks the Neovim the tests use. Story settings (`S`) store only what the story sets (`settings.story_own`, `clear_story`; the
  first choice of each row is "your default"). Settings keeps the default format as `format` + `script_kind` (shown as one of four choices; `script_kind`
  is inherited by stories). Past stories' "Use protagonist / Use setting" use the piece in the current draft (`_src` "past") or send it to a universe, and
  stay read-only for a promoted draft. The Builder's thin column (under 150 columns) shows a summary (`#story-summary`), not the Story panel's tabs. F12
  menu keys are 1-9, then letters (not j, k, q), then capitals (`sw.menu.hotkeys`). `post-update` is dispatched before argparse so `--help` does not list
  it; `export` is an alias of `draft-export`; `universe` is retired. The generator-content guide lives in `docs/generator.md` (checked in batch 18, not
  re-checked); the README points at `docs/manual.md`.

- Shapes (branch batch-21-shapes, 0.23.0). *Branches:* `main` did not yet hold the versions work (0.22.0, on `claude/gallant-knuth-qu093q`), so
  batch-21-shapes starts from that branch. *Flash fiction* is a short story to the Writer and the export (`format = "short-story"`), told apart by
  `script_kind = "flash"` (the setting a screenplay already uses for its kind; it is inherited like the format, so a default of flash works).
  `Format.short` is the list label. *The format is asked first* only when a person starts the draft (`ask_format` on the screen, set by
  `cli.run`, `modes.run_wheel` and the hub); tests and reopened drafts are never asked, and the plain prompt doesn't ask. `STORYWHEEL_ASK_FORMAT=0` turns the
  question off (the shared `home` test fixture sets it, because dozens of tests drive the Wheel by keys; tests of the question set it back to 1). A draft is "new" while it has no
  `format`, nothing kept and step 0. *Structures:* new ones reuse the `act_*` frames (as the screen structures do), so the old test that prose
  structures share no slots now covers only the original three; beat keys are prefixed (`stc_`, `hj_`, `sp_`, `fr_`, `sm_`, `ci_`, `im_`) because thread labels
  are keyed by beat; only the Story Spine and Kishotenketsu were added to flash among the old ones. *Focus:* the investigation found that nearly
  every body frame says `{first}` and about a third read the protagonist's own fields (`name last age job trait want need flaw secret rival`).
  With no protagonist, `{first}` and `{name}` become "everyone in {place}" (a place) or "someone" (no one), those frames, `{first}'s`, atoms that
  say `{first}`, and titles that name the character are set aside (`steps.Ctx.template_accept`, `slot_accept`), and the Protagonist step is skipped
  at the move from the step before it (`Session._advance`). Rejected: "they" (object and possessive forms), the place or the motif as the subject
  (personification, and abstract motifs such as "call"). A protagonist already kept stays in the draft but is ignored (and not promoted) while the
  focus is not a person. Two leads and an ensemble add a `partner` or a `company` (three people) to the Protagonist step; promotion makes them
  characters (role protagonist and ally). *Ending:* a template's optional `"ending"` (string or list); the genre files carry none, so with an
  ending picked a beat draws six times in ten (`ENDING_SHARE`) only from frames tagged for it, else from everything that is untagged or tagged for
  it. "Any" is the default and filters nothing, so older drafts and seeded samples are unchanged.

- Versions (branch batch-20-versions, 0.22.0): a version is a separate story folder in the same universe. Siblings share a `family` id in
  story.md (the first story's slug, written into the source story when its first version is made) and a `version` number (the first story is 1; each
  new one the next). Content is COPIED, never synced. Stories with no `family` have no siblings and behave exactly as before; a family is only an id,
  so renaming or deleting one version never touches another (a delete goes to .trash; the family survives the first story's deletion).
  `Story` now compares and hashes by its path. The copy choices are `outline` (non-beat sections), `notes`, `seed`, `genres`, `structure` (the beat
  sections and `structure`/`repeats` in the meta) and `manuscript`; all but the manuscript are on by default. When the copied structure doesn't fit the
  new format, its sections are copied as they are AND the new format's default structure is added with blank beats and becomes the active `structure`,
  so nothing is lost and the writer maps beats by hand. The slug is the title's slug, with the format key added when taken (then numbered). Manuscript
  copies are always a "rough start", said in the status line, in a note at the top of a new script.fountain and in the CLI notes: prose to prose copies
  the files; prose to script writes every paragraph as Fountain action with a forced heading (`.NEW SCENE`, or the break's title in capitals) for each
  scene break (`versions.prose_to_fountain`, which the prose `.fountain` export now uses too, so paragraphs are separated by blank lines); script to
  prose makes each heading a named scene marker, action a paragraph and a speech `"Words," Name said.` (transitions, parentheticals, sections and
  synopses dropped). In the Builder's list a family is a disabled title row with one row per format (short labels "Short story", "Novel",
  "Feature film", "Short film"; "N words" or "~N pages"); `v` opens the form (title, format, target, copy checklist), `]`/`[` move between versions.
  Wheel promotion's preview lists the other formats as ticks (`plan.also`); entities are created once and each tick calls `versions.new_version` on
  the new story. The Writer's status line and window title read "Title (format)"; a long title is shortened before the format is. (The "Batch 20"
  entries above are the earlier numbering; this is a later piece of work on the branch of that name.)
