# Changelog

One entry per batch of work, newest first. The version is in `storywheel/__init__.py` (`storywheel --version`).

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
