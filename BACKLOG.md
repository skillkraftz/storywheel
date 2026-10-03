# storywheel backlog

The pile of things still to build or finish, after batch 6 (1462 tests, tag b6-final). Work through it in batches; when an item is done, move it
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
- **Words: complete from the universe's own added words in the Writer.** *Idea.* The words put on a universe's lists (Words > Universe words) could
  complete while typing, like character names.
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

## 4c. Found in batch 2b

- **Curly quotes while writing** (optional in the brief): the Writer could *show* ' and \" as curly marks without changing the file (a
  concealed overlay per mark). *Idea.* Not done: the export already makes them curly.
- **Spellcheck on by default** applies to stories that have no remembered choice: a story whose Writer remembered "off" (the Writer
  keeps toggles between visits) stays off until you turn it on once. *Note.*
- **Autocorrect** is a short list (about 45 slips) and never changes capitals at the start of a sentence. *Idea:* capitalize sentence
  starts; a list you can edit in Settings.
- **wordfreq is a dependency** (about 57 MB installed). `pipx inject storywheel wordfreq` adds it to an existing install; a fresh
  `pipx install .` brings it. Words > Vocabulary says so if it is missing. *Note.*
- **Vocabulary subjects.** *Idea.* The subject list uses WordNet's categories (Animals, Moving...) plus the most used subject areas; a plainer set
  would be friendlier.
- **Transparent background**: selected rows, cursor and scrollbars still use solid colors (deliberately: they must stay visible).
  Textual's ANSI theme uses your terminal's own colors for text and accents unless you set Text color / Accent color. *Note.*

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

## 7. Review: what a writer would find confusing (batch 2b; **addressed in batch 3**, see Done)

I walked the Wheel, Builder, Settings, Words and the Writer as a writer would. Each row: the control, what it really does, and what is
unclear about it. Batch 3 applied these; the tables are kept as the record of what was unclear; "Fix" is my suggestion.

### The Wheel
| Control | What it does | What is unclear / fix |
|---|---|---|
| **Use: no** button (universe panel) | Cycles how the generator uses ticked universes for whole-step candidates: no / mix in (about a third of rolls) / only from them | The label says nothing about *what* it uses. Fix: "Whole characters and places from them: no / sometimes / only" |
| **Builder (F2)** button (universe panel) | Leaves for the Builder | Looks like it belongs to the universe list; the F2 key already does this. Fix: drop the button or label it "Open this universe in the Builder" |
| **Mix** button | Opens the mix editor: which kinds of material (tags, lists) this story leans toward or avoids | "Mix" means nothing to a new user. Fix: "Flavors" or "Tune the flavor" |
| **▲ ▼** beside each line | Like / dislike that line; disliked wording and word pairs are used less in later rolls | Never explained on screen. Fix: tooltip and a first-use hint |
| **Skip** / **Back** | Skip leaves the step empty and moves on; Back returns to the previous step | Clear, but Skip's effect on later steps (stand-ins) isn't |
| **Send to Builder** (card) vs **Send** (Past stories) vs **+Prot / +Place** | Send to Builder promotes the current story into a universe; Send does the same for a past story; +Prot / +Place copy a past story's protagonist / setting into the current one | Three near-identical words with different meanings. Fix: "Promote to a universe", "Use its protagonist", "Use its setting" |
| **Hist** and the history panel | Lists every roll of this step (what changed) or the selected field's earlier values (h toggles) | The panel title explains h but the footer calls it "Hist" |
| `3/8`, `done` in Past stories | Steps kept out of 8, or finished | "3/8" means *kept*, not the current step; add a hint |
| Quit (q) | Asks Keep or Delete, then leaves the whole program | In every other mode q means "back". Fix: show "q Quit program" vs "q Back" consistently |

### The Universe Builder
| Control | What it does | What is unclear / fix |
|---|---|---|
| Left column **+New / Rename / Del** (universes) and the entity column's **+New / Roll blanks / Del** | New / rename / delete a *universe*; new / fill every blank field of / delete an *entity* | Same labels in two places with different targets. Fix: put the target in the label ("+Universe", "+Entity") |
| **Outline / Write / Export / +Draft** (stories) | Open the story's outline in the right column; open the Writer; make a .docx/.md/...; start a new Wheel draft inside this universe | "Outline" duplicates the right column's Outline tab; "+Draft" doesn't say it is a *Wheel* draft. Fix: "+Wheel draft" |
| Right column tabs **Outline / Scenes / Notes** and entity tabs **Groups / Notes** | Story outline / the story's scenes / the selected entity's own notes; entity types Groups and Notes | Two different things are called "Notes". Fix: rename the right-hand one "Entity notes" |
| **Roll blanks** | Fills every empty field of the selected entity with generated values | Not clear it never overwrites what you wrote |
| **▲ ▼ and ✎** on a field | Rate the generated value; ✎ = the generator can't fill this field (write it yourself) | ✎ is explained only in help |
| Top **Writing** box | Today's words against the goal, streak, story and universe totals | Not interactive; looks like a status bar. Fine, but the title could say "Your writing" |
| Title text "(o: universe overview)" | Pressing o shows the universe's overview in this panel | Easy to miss; the key isn't in the footer |

### Settings
| Control | What it does | What is unclear / fix |
|---|---|---|
| Tab **Universes** | One setting: how much more likely a universe's own people and places are in rolls | Label is a sentence-long question; fix: "Preference for your own names (1.5)" with a short hint |
| **Quick export file type** | The file type the Writer's one-key export uses | "Quick export" isn't a thing elsewhere. Fix: "Default export type" |
| **Terminal: blank lines between paragraphs** | A visual gap (not typed) between paragraph lines in a terminal Writer | Odd wording. Fix: "Space between paragraphs (terminal)" |
| **Default format** | short-story / novel / screenplay for new stories | Novel and screenplay are partial / a stub: say so in the hint |
| **Keys** tab | Writer shortcuts; changes apply the next time the Writer starts | Fine; the fixed keys listed below the fields are easy to miss |
| **Library folder** | Where universes live; "Changing it does not move anything" | Users expect a move. Fix: offer to move (BACKLOG section 2) |

### Words
| Control | What it does | What is unclear / fix |
|---|---|---|
| Lookup **Use in Writer** | Goes back to the Writer and replaces the word you were on | Disabled unless you came from the Writer (F5 there); the reason is only in the status line. Fix: grey text under the button |
| Lookup **Add to My words** vs **Add to universe word list** | Keeps the word to learn / puts it on the universe's list for a slot so the Wheel and Builder use it | Both are "word lists" to a reader. Fix: "Learn this word" and "Use in this universe's stories" |
| Vocabulary markers **★ ✓** | ★ = Learning (in My words), ✓ = Known (never offered again) | No legend. Fix: a one-line legend under the list |
| Vocabulary **difficulty** (any / uncommon / rare / very rare) | How uncommon the words are by how often people use them | Names are relative; a hint with examples ("lantern", "serendipity", "gallivant") would help |
| **New batch** | A fresh 20 words never shown before | "Forget what I've seen" (to start over) isn't offered yet |
| Overused **Analyze** | Reads the story and lists frequent words and close repeats | Needs a story chosen; the empty list says nothing until Analyze is pressed |

### The Writer
| Control | What it does | What is unclear / fix |
|---|---|---|
| **F12 / Alt+M** menu | A list of Writer actions | Long (20+ items) and unsorted: group it with separators (Edit, Look up, Story, Leave) |
| **Switch to Vim keys (this session)** | Turns notepad mode off until you leave | Sounds permanent / dangerous; the permanent switch is in Settings. Fix: "Use Vim keys for now" |
| **This story's settings.toml** | Opens the raw settings file in the editor | Not for a writer. Fix: link to Settings (F4) instead |
| **Peek at the name under the cursor** (F8) | Shows a character/place card | Nothing says which names it knows; names from the universe only |
| **Ctrl+Q** vs **F2** | Both go back to the Builder | Fine, but the status line doesn't show either |
| Status line `scene / manuscript / today` | Words in this scene, in the story, and written today against the goal | The three numbers aren't labelled in the narrow layout |
| The pad windows | Blank columns either side that centre the text | Invisible; clicking in them does nothing |

### Found in batch 4
- **Names recorded as proper or description** only for new entities; older ones are fixed with `names fix` (the preview covers only names that match a
  generator atom, or a thing with one capitalised word); other odd names stay as they are.
- **Renaming a "fixed" name** does not rewrite old mentions in notes and manuscripts ("Locked box" stays where it was typed).
- **The lenient spelling list** accepts any known word + ending, so a few non-words slip through ("unhouse"); turn it off in Settings > Spelling.
- **Name case correction** needs the spellchecker on and skips names that are also ordinary words ("Hope", "Will").
- **`storywheel update` of a plain install** needs a git remote that serves the repository (not a tarball); there is no signature check.
- **`install.sh`** is tested only as a dry run on a pretend machine; the real downloads (Neovim, Neovide) are unchecked here.

### Found in batch 3
- **Peek and the world.** The Writer's F8 peek still doesn't say which names it knows; a short "no entity called X in <universe>" line would help.
- **Builder `Notes` entity tab** (type) and **Entity notes** (right-hand tab) are now distinct in name, but key `5` and key `8` are easy to mix up.
- **Field-history files** (`<universe>/.field-history/`) are never pruned except when an entity is deleted; they are small.
- **Ratings** on a hand-written value record the line but cannot teach the generator (no frame or atoms): by design, noted in the status line only for rolled values.
- **Missing-tool commands** assume Debian/Ubuntu (`sudo apt install ...`); edit `storywheel/tools.py` for another system.
- **Keys outside the Writer** are still fixed (section 3).

## Suggested batches

Done: bugs, verify items, find and replace, dictionary and thesaurus (b1); Words mode (b2a); Vocabulary, appearance, spellcheck (b2b); clarity,
backups restore, half-done items (b3); names, spelling lists, install/update (b4); typewriter notes and grammar (b5).

1. Novel and screenplay profiles (section 2).
2. The rest of section 2, and configurable keys everywhere (section 3).
3. Content: the twelve genres, a few at a time.
4. The world model.


## Done

### `storywheel update` fixed (`b6-update-fix`)

- Compares installed with the source folder (from pip's direct_url.json), fetches the folder's own remote, reinstalls on a version difference; no private clone.

### Batch 6: smoother switching, tidier layouts, downloads

- **Downloads:** a normal User-Agent on every download, curl/wget fallback when a server refuses (fixes `grammar install` HTTP 403) — `b6-downloads`.
- **One app for the four screen modes**, kept screens, lazy loading, quiet Writer suspend, restyle skipped on return — `b6-hub`, `b6-hub-wip`.
- **Layouts:** Wheel left column in three boxes; Builder boxes, card columns, card title, one-line legend, tab-bar gap, fitting footer — `b6-layouts`;
  narrow-terminal layouts, compact Settings and Words — `b6-narrow`; layout tests — `b6-layout-tests`; full check of every mode at 190x50 and 120x34 — `b6-final`.

### Batch 5: backlog cleanup, typewriter fixes, optional grammar checking

- **BACKLOG.md reconciled** (finished items removed from 4b/4c, section 6, the review "Everywhere" list and "Suggested batches") — `b5-backlog`.
- **Neovide not offered on arm64** (Settings, setup, the Writer's launch note) — `b5-neovide-arm64`.
- **`storywheel kitty` launcher; Ctrl+I under kitty's protocol** verified with the real bytes, on automatically in kitty; README "Writing in kitty" — `b5-kitty`.
- **Optional grammar checking with a local LanguageTool:** install/status/start/stop CLI — `b5-grammar-server`; checking changed paragraphs after a pause with
  offsets kept across markup — `b5-grammar-check`; right-click menu, next/list keys — `b5-grammar-ui`; Settings > Grammar, help text — `b5-grammar-settings`;
  tests with a fake server — `b5-grammar-tests`; README/CHANGELOG — `b5-final`.

### Found in the update fix
- A pip install from an index or wheel records no source folder; then the git checkout the code runs from is used, and with neither the update remote (a temporary clone).
- The reinstall uses pipx when the install lives in a pipx environment (or pipx is on PATH), otherwise pip in the running environment; neither path was run for real here (tests use a fake runner and real local git repositories).
- If the source folder is newer than the installed code *and* has uncommitted changes but no remote, it is installed as it is.

### Found in batch 6
- **No git remote is configured** in this checkout, so "push" could not be done; add one (`git remote add origin URL`) and `git push --follow-tags`.
- **Switch times on a Pi** are an estimate, not a measurement (see REPORT.md). `tools/measure_switch.py hub` on the Pi gives the real figures.
- **Settings switches** (on/off) are still three lines tall: Textual's Switch has no compact form and the transparent theme leaves its small version
  unreadable, so they were left alone. A plain "[x] on" widget would save about 40 lines on the Writer tab.
- **A word typed in Words' Lookup box** is kept when you leave and come back, by design; the Writer's handover replaces it.
- **The Wheel's `Send to Builder` message** shows only its first line in the Builder's status line (the full report was printed after quitting before).
- **The old per-mode apps** (`BuilderApp`, `WordsApp`, `SettingsApp`, `StorywheelApp`) remain for tests and `STORYWHEEL_CLASSIC=1`; they could be removed
  once nothing needs them.

### Found in batch 5
- **Grammar** checks the open manuscript buffer; a novel's other chapters are checked when they are opened. "List of problems" shows the open file only.
- **Ignore this one** is keyed by rule and the flagged text, so it also hides the same wording elsewhere in that story.
- **LanguageTool's first start** is slow on a Raspberry Pi (up to a minute); the status line says "starting…". Java is not installed for you.
- **The real LanguageTool** was not run here (no Java/LanguageTool on this machine): the protocol is tested against a fake server written from its documented
  `/v2/check` answer. Try it on the typewriter and report rule names that are noisy.
- **kitty** is not installed here; the launcher's options (`modify_font cell_height N%`, `--class`, `remember_window_size`) are from kitty's documentation.
  `modify_font` needs kitty 0.30 or newer.
- **Grammar settings in the Settings screen** are one switch per category (13 of them); a compact picker would be neater.

### Sync code removed (`b4-remove-sync`)

- Everything about syncing is gone from storywheel (command, setup question, Settings tab, Builder conflicts screen); old links are turned back into
  real files by a one-time migration. Syncing is a separate tool outside this project.

### Batch 4: fixes from use, installing, updating

- **Names and capitals:** entities record proper or description; promotion/rolls keep descriptions as descriptions; `names fix` and Builder `F` with a
  preview — `b4-names-case`. Writer name completion on any word of 3+ letters, any case, and wrong-case correction — `b4-name-completion`.
- **Spellcheck:** the dictionary's words and forms — `b4-spell-dictionary`; lenient endings/prefixes — `b4-spell-lenient`; softened or hidden secondary
  marks, explained in help — `b4-spell-marks`.
- **Dictionary sources kept; older index rebuilt offline** — `b4-dictionary-sources`.
- **Version and changelog** (`--version`, CHANGELOG.md) — `b4-version`. **install.sh** — `b4-install-script`. **storywheel setup** — `b4-setup`.
  **storywheel update** — `b4-update`.
- **Sync** was built here and then removed again (see above); the settings split stays.

### Batch 3: clarity and safety

- **Autocorrect:** `wont` and `cant` removed (real words); a lone `i` before a full stop is left alone (`i.e.`, `e.g.`), tested — `b3-autocorrect-words`, `b3-autocorrect-ie`.
- **`q` is back, `Q` is Quit storywheel** (with a confirmation) in every mode; a trail of modes so back returns to where you were — `b3-q-back`.
  Footers label F1-F5 as modes everywhere — `b3-footer-modes`.
- **Renames (section 7):** Wheel (`b3-rename-wheel`: "Whole characters/places from these: no / sometimes / only", Flavor, Promote, Use protagonist,
  Use setting, "Open in the Builder"), Builder (`b3-rename-builder`: +Universe, +Character/+Place/+Thing/+Group/+Note per tab, +Wheel draft, Entity notes),
  Words (`b3-rename-words`: Learn this word, Use in this universe's stories), Settings (`b3-rename-settings`).
- **On-screen explanations** (`b3-legends`): ▲▼ and ✎ and Roll blanks in the Builder, ▲▼ in the Wheel, ★ ✓ and difficulty examples in Vocabulary,
  why Use in Writer is greyed out, `o` in the Builder footer.
- **Writer menu** grouped (Edit, Look up, Story, Leave, More), "Use Vim keys for now", Settings (F4) instead of settings.toml — `b3-writer-menu`;
  the status line labels its three numbers — `b3-statusline`; `Alt+Q` quits storywheel from the Writer — `b3-writer-menu`.
- **One wording for missing tools** (`storywheel/tools.py`): "X isn't installed. <what needs it>. To fix it, run:  <command>" — `b3-tools-messages`.
- **Restore from backups:** CLI `storywheel backups list|show|restore` — `b3-restore-cli`; Writer menu — `b3-restore-writer`; Builder
  "Backups…" screen (button and `b` on a story) — `b3-restore-builder`. A restore first copies the current version aside.
- **Builder field history saved** beside the entity — `b3-field-history`. **Builder ratings change rolls** — `b3-builder-ratings`.
- **Universe words screen** (Words > Universe words: see and remove the words added to a universe's lists) — `b3-universe-words`.
- **Vocabulary:** Start over (forget words seen) — `b3-vocab-startover`; add a word to learn by hand in My words — `b3-vocab-add-by-hand`.

### Batch 2b: corrections to Words, appearance and spellcheck

- **Topic explorer and word bank removed**; "Add to this universe's word list" (pick the slot) on any word in Lookup and My words; old word
  banks migrated into My words — `b2b-vocab-remove`.
- **Vocabulary for learning words** (word, part of speech, one-line meaning; click opens the Lookup entry) — `b2b-vocab-learn`; chosen by
  frequency with the wordfreq package (license recorded in SOURCES.md), filters for difficulty, part of speech and subject —
  `b2b-wordfreq`; new batch without repeats, Known / Learning, My words with definitions, flashcards — `b2b-mywords`.
- **Transparent background** in every Textual mode (the terminal's default background; checked cell by cell in a terminal) —
  `b2b-transparent-tui`; the Writer clears every background group and the Neovide window gets its own opacity —
  `b2b-transparent-writer`; **Settings > Appearance** (transparent, text color, accent color, Neovide opacity) — `b2b-appearance-settings`.
- **Spellcheck:** straight quotes in manuscripts (curly ones typed, pasted or already in files are made straight, with a backup; the export makes
  them curly, setting on by default) — `b2b-straight-quotes`; autocorrect — `b2b-autocorrect`; a spelling list per universe built from
  names and the outline's proper nouns, and right-click > Add to Dictionary — `b2b-spell-universe`; the spell language is set on the writing
  buffer — `b2b-spell-buffer`; spellcheck is on by default — `b2b-spell-default`.
- **Review of every mode** (section 7) — `b2b-review`.

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
