# Changelog

One entry per batch of work, newest first. The version is in `storywheel/__init__.py` (`storywheel --version`).

## 0.10.2 — Export records and `exports` commands
- Every export is recorded in `.storywheel-exports.json` beside it: file, format, date, the manuscript's word count and a content hash.
- `storywheel exports status [--json]` and `storywheel exports make STORY [--format F] [--json]` (see README).
- A `stable` branch for releases (rule in CLAUDE.md).

## 0.10.1 — Rhymes fixed

- The download works: `cmudict.dict` (the old `cmudict-0.7b` path was a 404), with the repository's LICENSE saved beside it and shown by `storywheel dictionary status`.
  An existing `cmudict-0.7b` in the sources folder is still read.
- The parser reads both layouts (lowercase with `(2)` variants and trailing `# comment` annotations; the old uppercase `;;;` style) and skips lines that are not pronunciations.
- A failed rhymes download is no longer silent: `dictionary install` ends with "Rhymes were NOT installed" and the reason, `dictionary status` says it,
  and the Rhymes box shows the same instead of an empty list.
- Rhymes list only words the main dictionary (WordNet or Moby, with their forms) knows; the "Names and rare words too" box shows the rest. Ordered by
  commonness when wordfreq is installed, else A to Z, and the box says which.

## 0.10.0 — Batch 10

### Tests no longer meet your real LanguageTool
- The two `test_grammar_server.py` failures were not about Java: a real LanguageTool server on the usual port (18081) answered "already running" and
  "running". Every test now gets a free port of its own (`STORYWHEEL_GRAMMAR_PORT`, used unless you chose a port in Settings); no test depends on Java.

### Part A: never merge files you didn't make
- Only `manuscript.md` and `NN-name.md` (what storywheel makes) are manuscript files. Anything else in a manuscript folder (a sync tool's
  "01-opening (xps copy 2026-10-04).md", `notes.md`...) is never merged, counted, exported, searched or opened by the Writer.
- The one-file migration runs once per story (`.one-file-manuscript`); files that turn up later are left alone. A short story that has `manuscript.md`
  is that one file; an old-style `01-name.md` beside it is an extra file.
- The Builder's Scenes tab shows "Extra file in the manuscript folder: ... looks like a copy from another tool" with Open (read-only view), Delete
  (asks; moves it to `.trash`) and Ignore (`.ignored-manuscript-files.json`); the status line says it once when the story opens.

### Part B: Lookup in boxes, and rhymes
- Lookup is five boxes — Meanings, Similar, Opposites, Rhymes, Related — side by side at 150 columns or more, tabs below that, each scrolling on its own.
  Enter or a click on a word in any box looks it up; copy, learn, "use in this universe's stories" and Use in Writer work from any box.
- Rhymes from the CMU Pronouncing Dictionary (cmudict-0.7b), installed with `storywheel dictionary install` (a failure there leaves the dictionary alone;
  run it again to retry) into `rhymes.sqlite`: perfect rhymes first, then near rhymes (at most 300, the commonest), grouped by syllables, with a syllable filter.
  License noted in SOURCES.md (not checked against the downloaded file: no network in development; the file's own header is saved with the index).

## 0.9.0 — Batch 9
Part A: Story words counts names correctly
- An entity's whole name is counted as a phrase, in any case, with or without its leading article and with a possessive ("a wolf in a waistcoat",
  "the silver birch grove's edge"). Single words are counted only for personal names (a character with a proper name: its first or last name), never for
  descriptions, so "wolf in a waistcoat" no longer shows 33 uses for every "in", and "silver birch grove" is found though it is lowercase.

Part B: Words mode
- Tab order: Lookup, **Suggestions**, Vocabulary, Story words, Genre words. The Overused tab is gone: its frequent words and close repeats are the
  **Often used** view of Story words (the second box), with where each is and Enter to open the Writer there.
- New **Suggestions** tab with three lists and Genre words' row actions: *For this story* (high genre-fit words not yet in the manuscript, by part of
  speech), *For your characters and places* (words the dictionary relates to characters' jobs and things, places and groups: synonyms, broader and
  narrower words, parts, related forms) and *Fresh alternatives* (the most overused words, each with genre-fitting replacements). Worked out in the
  background (`suggest.py`).
- Vocabulary: a word that appears in any manuscript (any form: ran for run) is marked **Known** automatically, leaves the lists and keeps a note of where
  it was used (`wordsused.py`); a new view *✓ Known* lists those words with the place.

Part C: structures and the Writer
- **Repeatable beats.** A structure marks beats that can occur several times, with a minimum and a maximum (`"repeat": {"min": 1, "max": 4}`): the Story
  Spine's second "Because of that", the Three-Act's rising action, Kishōtenketsu's development. In the Wheel, `A` / `X` (or the +Beat / -Beat buttons) add
  or remove one on the story body (a new beat is rolled to follow the others and can reuse the threads in play; threads that nobody mentions retire;
  the step's history starts again); in the Builder's outline, `A` / `X` do the same in `story.md`, the count kept in its front matter. Occurrence keys are
  `because_2__2`...; stories without extra beats are unchanged.
- **Ctrl+O** in the Writer (a setting, `key_overview`, in Settings > Keys and the Writer menu): a floating read-only overlay with the title, premise,
  structure beats, twist, protagonist, setting and rumor; scrollable; Escape closes it.
- The status line shows the goal as `today 312 / 1,000 words · 31%` (without a goal: `today 312 words`).

Part D: Builder layout
- The right column is gone. The left column is Universes (small), **Stories** (titles only; **+Story** makes a blank story with no Wheel draft) and a large
  **Story** panel with tabs Outline / Scenes / Notes for the selected story (a click on a scene opens the Writer there; Notes are the story's own, in
  `notes.md`). The middle stays the entity area, and an entity's own notes moved under its card (`E`). On a narrow window the Story panel takes the whole
  width in turns with the cards (keys 6 7 8 or backslash; focus follows, so no key ever lands in a hidden box).
- "+Wheel draft" and `W` are gone from the Builder. In the Wheel, **Belongs to** (universe panel) chooses the universe a draft lives in; promoting it
  (Send to Builder, B, or Q on leaving) skips the "new or existing universe" question, shows the preview and puts the story in that universe's Stories.
  A draft started for a universe belongs to it.

### Part E: kitty replaces Neovide

- Inside kitty, the Writer opens in **its own kitty window** with the writing settings (font, size, line height via `modify_font cell_height`,
  padding, opacity) and the window closes when Neovim does. storywheel keeps normal spacing. Outside kitty the Writer runs in the same terminal,
  and a one-line note at start says kitty gives a better Writer and how to install it (`sudo apt install kitty`).
- Neovide is removed everywhere (settings, setup, install.sh, tools, arm64 special cases). New settings: `writer_kitty`, `writer_line_height`,
  `writer_padding`, `writer_opacity` (with `writer_font`, `writer_font_size`). Old `neovide`, `neovide_opacity`, `line_spacing` are converted once
  (`migrate.migrate_settings`) in the global, local and story settings files.
- `storywheel kitty` no longer applies tall lines (the `--line-height` option is gone); `--probe` reports what the installed kitty's remote
  control offers (not depended on).

### Part F: roadmap

- BACKLOG.md is a short roadmap (Now, Next, Later, Ideas) with finished work collapsed into one list with its tags; stale items removed.

## 0.8.1 — Genre words reworked: long lists of words, ranked by genre
- **Genre words** is now what it was meant to be: long lists of words by part of speech, from the dictionary, not the generator's slot lists. A
  main box picks Nouns, Verbs, Adjectives or Adverbs (every lemma, each with a one-line meaning); *Genres…* picks Any genre or one or more genres,
  which only RANK the words (a small ●●● ●●○ ●○○ mark shows the fit; nothing is hidden); a commonness filter uses Vocabulary's bands
  (everyday / uncommon / rare / very rare); sort by genre fit, commonness or A to Z; a search box filters as you type. Enter opens the Lookup
  entry, `c` copies, `u` uses the word in the Writer, `l` marks it ★ Learning (it shows in Vocabulary's Learning view), `w` puts it on a generator list.
- The lists are virtual (`virtuallist.py`): only the rows on screen and a page either side are read and drawn, so 100,000 nouns open in about
  a tenth of a second on this machine and scroll smoothly; the order is held as plain integers and rows are read 64 at a time.
- **Genre fit** (`genrefit.py`) is worked out once and kept in the dictionary index (tables `lexicon`, `fit`, `meta.fit_stamp`): seeds are the
  words in each genre's own lists and frames; the glow spreads through WordNet synonyms, similar-to, also-see, broader/narrower, parts/wholes, one
  step of derivation, and (a small share) Moby neighbors, with decaying weight; WordNet subject domains mapped to genres in `genres.json`
  (`_domains`) add their meanings. It is built by `storywheel dictionary install`, by `storywheel update`, and in the background the first time
  the tab opens after the genre lists change (the stamp is a hash of the seed words and domains). It works from the index you already have: no download.
- A short *From the Wheel* group is kept at the bottom of the main box: first and last names (with *More like these*), jobs, places, things.
  The sentence-template categories (premises and twists, rumors, wants, needs, flaws, secrets, messages, manners, motives) and the others are gone.
- Without the dictionary installed the tab says so and offers only *From the Wheel*.
- `tools/genre_fit_report.py` prints the best-fitting words of each genre (REPORT.md has the top 30 adjectives and verbs).
- The full suite now passes in one run (1887 tests before this change).

## 0.8.0 — Batch 8: neighbors, Words tabs, three more genres
Part A: fixes from the batch 7 samples
- The wildcard floor no longer spreads over every other genre. `genres.json` has `_neighbors` for each genre; the floor's share goes to untagged lists
  and lists of neighboring genres, and genres that are not neighbors get a tenth of it between them. Where a slot has no neighbor lists, the floor
  shrinks to that tenth (the rest stays with the story's own and the general lists). Fantasy no longer gets an insurance adjuster, comedy no longer
  gets dragon's blood. A genre with no `_neighbors` entry keeps the old even floor. The fidelity thresholds loosened in batch 7 are restored,
  except the per-slot threshold for the western/fairy tale blend (2 points), which has no neighbor lists of its own.
- An era that names a season sets it ("the week before Christmas" is winter; `data/seasons.json` lists the words). Rerolling the season follows the
  era; rerolling the era passes over eras that name another season.
- Moods lean toward the genre: each mood is tagged with the genres it suits ("absurd" is comedy's, "eerie" is horror's, ghost story's, mystery's and
  fantasy's), so "comedy · eerie" is rare. Moods skip the recent-picks memory, which flattened them.
- Sentence breaks: particle verbs take a pronoun in the middle ("traded it away"); lint now flags a manner phrase after a preposition ("a favor from
  in the king's name") and a prize placed at a landmark ("Wants a fortress at the village cinema"); manners that only fit some verbs ("in the old
  tongue", "with drawn steel", "in silent dread") carry the restricted features `speech`, `carrying`, `feeling` and are drawn only where a frame asks
  for them (`{MANNER:speech}`); lint also reports a restricted atom no frame asks for.

Part C: horror, sci-fi, romance (each its own commit and tag, with neighbors set in genres.json)
- Horror: dread, isolation, wrongness, things that moved when no one was looking; remote towns, cellars and wells; profile weight 4.
- Sci-fi: ships, stations, colonies, AI, corporations; names from everywhere; profile weight 4 and modern 0.3 for near-future settings.
- Romance: relationships, obstacles, longing and misunderstandings; portable towns, bookshops, letters and keepsakes so it blends with every other
  genre; profile weight 4.
- The repetition report no longer flags a rare entry picked a handful of times (it must also be 4 standard deviations above chance).

Part B: Words mode tabs
- The *My words* tab is gone: Vocabulary has a *New words / ★ Learning* box (the ★ words, flashcards, remove) and an entry for a word of your own.
- New *Genre words* tab: browse the generator's lists by genre (default: the story's genres; tick more to borrow) and category, with a search box;
  each row shows its genre tags. Look up, copy, use in the Writer, add to the universe (name -> character, place -> place, thing -> thing, else the
  universe's generator list), and *More like these* invents new names with the genre's Markov name maker.
- New *Story words* tab replaces *Universe words*: names and odd words read from the manuscript with counts and places, look-alikes and near-misses
  flagged ("Glasswater" / "Glass Water", "Stacy" / "Stacie"); add to the spelling list, make a character/place/thing, rename everywhere with the
  existing preview. The old generator-word review is a section at the bottom of the tab.
- Every tab starts with one plain sentence saying what it is for (also in the help screen).

## 0.7.0 — Batch 7: update by commit, and three genres written
- `storywheel update` now remembers the commit it installed from (`~/.storywheel/installed-source.json`, written by the update and by install.sh) and
  reinstalls whenever the source folder's commit differs, not only when the version number does. A fix committed without a version bump reaches the
  typewriter. Uncommitted changes in the source count as different code. An install with no record reinstalls once to make one. Messages:
  `Installed: 0.7.0 (commit abc1234). Source ~/projects/storywheel: 0.7.0 (commit def5678). Same version number, but the source is at commit def5678. Reinstalling.`
  `update --record` just records.
- Genre content for **comedy**, **fantasy** and **mystery**, written the way western and fairy tale were: their own names (with Markov training sets),
  jobs, places and town-name parts, landmarks, things, people, troubles, rivals, title words, traits, verbs, abstractions, and frames for every
  premise, twist and beat of all three structures; every atom carries features. Comedy is situations and people (misunderstandings, schemes, pride,
  escalating mishaps), not jokes. Mystery has clues, suspects, alibis and reveals, and later beats reuse the clue, suspect and crime through threads.
- Fantasy is epic and high fantasy (orders, ruins, old wars, magic that costs something) and no longer shares lists with fairy tale. Fairy-tale lists
  were untagged as fantasy; fairy tale's profile leans on the "medieval" tag instead.
- Profiles: comedy 4 (modern 0.2), fantasy 4 (general 0.15, modern 0), mystery 4 (modern 0.2). Fidelity (own material): comedy 85%, fantasy 90%, mystery 85%;
  comedy/fairy tale 85%, fantasy/mystery 88%, mystery/western 85%. Repetition report: no line five times or more, nothing over 3x its fair share.

## 0.6.1 — `storywheel update` fixed
- It compared a private clone with the remote and said "Already up to date" while a newer version waited. It now compares the INSTALLED version with the
  version in the folder the install came from (found in pip's `direct_url.json`; an editable install runs from it), fetching and fast-forwarding that
  folder's git remote first if it has one (the typewriter pulls from xps), reinstalling when the versions differ, then running migrations and rebuilds.
  The `~/.storywheel/source` clone is gone; the update remote setting is optional (used only if the source folder is missing). Messages say what was
  compared: `Installed: 0.5.0. Source ~/projects/storywheel: 0.6.0. Reinstalling.`

## 0.6.0 — Batch 6: smoother switching, tidier layouts, downloads
- One Textual app now holds the Wheel, Builder, Settings and Words as kept screens (`hub.py`): F1, F2, F4 and F5 switch instantly, nothing is rebuilt, and
  each mode keeps its place (selection, scroll, open tab, the word you typed). The Writer starts from the same app and the screen is cleared on the way in
  and out; your shell prompt is never shown between modes. Heavy parts (the Words screen with the dictionary and wordfreq, Settings, grammar) load the
  first time they are opened. `STORYWHEEL_CLASSIC=1` still runs the old one-app-per-mode loop. `tools/measure_switch.py` measures it.
- Layouts: the Wheel's left column is three boxes (Steps; Universes to draw from; Past stories with its buttons underneath); the Builder's left column is
  two boxes (Universes; Stories in <name>), the entity card has labels and values in columns with wrapped values hanging under the value, a card title of
  just "Thing: name", a one-line legend, no blank row under the tab bar; Settings and Words use one-line boxes; the footer drops the least important
  keys instead of cutting one in half; narrow terminals (under 150 columns) get thinner side columns, and the Builder's right column takes turns with the cards.
- Downloads send a normal User-Agent (`storywheel/VERSION`): `storywheel grammar install` no longer fails with HTTP 403 at languagetool.org. If a server
  still refuses, curl or wget is tried when installed. The dictionary download uses the same code. `--from FILE.zip` is unchanged.

## 0.5.0 — Batch 5: backlog cleanup, typewriter fixes, optional grammar checking
- BACKLOG.md reconciled with what is done.
- Neovide is not offered on arm64 (no ready-made build): Settings and setup say so; the terminal is used.
- `storywheel kitty`: opens storywheel in its own kitty window with a chosen font and taller lines. Ctrl+I italic is confirmed to work under
  kitty's keyboard protocol (and is on automatically there). README: "Writing in kitty".
- Optional grammar checking with a local LanguageTool (off by default): `storywheel grammar install [--from FILE.zip] | status | start | stop`;
  the Writer starts the server when you turn it on and stops it when you turn it off or leave. Changed paragraphs are checked after a pause;
  problems are underlined in their own colour; right-click for the message, fixes, Ignore, Turn off this rule; F10 next, Shift+F10 the list;
  Settings > Grammar.

## 0.4.1 — Sync code removed
- `storywheel sync`, the sync question in setup, the Sync tab in Settings and the Builder's sync-conflict notice and screen are gone: syncing between
  machines is a separate tool outside storywheel. Links into a sync folder that `sync link` made in `~/.storywheel` are turned back into real files
  the first time storywheel starts (or `storywheel migrate`), and it says so; the sync folder's copies are left alone.
- Kept: the `settings.toml` / `settings.local.toml` split, and `storywheel update` (the remote is passed to git unchanged: `xps:projects/storywheel` works;
  Settings > Updates).

## 0.4.0 — Batch 4: fixes from use, installing, updating
- Names: an entity records whether its name is proper ("Red Draw") or a description ("a locked box", "the sheriff"); promotion and rolls keep
  descriptions lowercase with their article; `storywheel names fix` (and `F` in the Builder) repairs older entities with a preview.
- Writer: name completion starts on any word of 3+ letters of any proper name, in any case; a finished name typed in the wrong case is corrected.
- Spellcheck: knows every word in the offline dictionary and its forms; a lenient list accepts known words plus common endings/prefixes;
  the secondary spelling marks can be softened or hidden.
- Dictionary: the downloaded sources are kept; an older index is rebuilt from them, offline.
- `storywheel --version`, this changelog, `install.sh`, `storywheel setup`, `storywheel update`.
- Machine-only settings in `settings.local.toml` (folders, Neovide, fonts, the update remote).

## 0.3.4 — Batch 3: clarity and safety
`q` is back and `Q` quits; restore from backups; one wording for missing tools; Builder field history and ratings; Words: universe
words, start over, add by hand; renames and on-screen explanations; Writer menu groups.

## 0.3.3 — Batch 2b
Vocabulary and My words, transparent backgrounds, appearance settings, straight quotes, autocorrect, per-universe spelling lists.

## 0.3.2 — Batch 2a
Words mode (F5), dictionary and thesaurus, the Writer's keys.

## 0.3.1 — Batch 1
Title bar, Home/End, find and replace, dictionary core.

## 0.3.0 — Fifth pass
The Writer and export ready for real use.
