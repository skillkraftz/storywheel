# Changelog

One entry per batch of work, newest first. The version is in `storywheel/__init__.py` (`storywheel --version`).

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
