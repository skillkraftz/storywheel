# Foundation sweep: report

Everything in the roadmap's foundation sweep is built and usable end to end. Status words: **Works** (built, tested,
used end to end), **Partial** (works, with a stated gap), **Stub** (marked as such, not the real thing), **Not started**.
The full suite is **615 tests, all passing** (it was 413 at the start of the sweep). Tags: `stage-3-ui`,
`foundation-storage`, `foundation-promotion`, `foundation-builder`, `foundation-universes-wheel`, `foundation-writer`,
`foundation-switching`, `foundation-export`.

What no test can see (how the Writer looks, Ctrl+I in your terminal, the .docx in a word processor, a real clipboard
copy, the hand-over between the Builder and Neovim) is in the manual test script in section 3. Please start there.

## 1. Checklist

### Storage and universes (`foundation-storage`)
| Item | Status | What's missing |
|---|---|---|
| Library folder (STORYWHEEL_LIBRARY, default ~/Writing/storywheel) | Works | |
| Universes as folders; entities as markdown with YAML frontmatter | Works | the frontmatter is read/written by a small built-in reader (valid YAML, no dependency); one level of nesting only |
| Entity schemas as data: character, place, thing, group, note | Works | add or replace types with a JSON file in `~/.storywheel/entities/`; group names have no natural list, so they roll as "The {noun} Company" |
| Links between entities by stable id | Works | a new blank entity has a placeholder id (`character-1`) that becomes a real slug once named (links follow); after that the id never changes |
| Migration of universe.json into "Loose Ends", with backup | Works | runs at start-up of the combined app and from `storywheel universes`/`universe`; the old file is renamed `universe.json.migrated-DATE` |
| Global settings in settings.toml | Works | author, address, email, phone, font, goals; per-story settings fall back to them |

### Promotion, Wheel to Builder (`foundation-promotion`)
| Item | Status | What's missing |
|---|---|---|
| Leaving the Wheel with a kept story shows the message: new / existing / not now | Works | also in the plain prompt; a story with nothing kept just asks Keep or Delete |
| Promotion creates entities and the outline per the table, with a preview, and offers merges | Works | the preview lets you switch each same-name duplicate between merging and creating another; merging only fills blanks |
| Past stories show which drafts were promoted and can promote later | Works | a draft can only be promoted once |

### Universe Builder (`foundation-builder`)
| Item | Status | What's missing |
|---|---|---|
| Left: universes (create, rename, delete with confirm) and their stories | Works | |
| Middle: overview or story outline boxes, tabs Characters / Places / Things / Groups / Notes with cards | Works | the tabs are a tab bar over one list + card (keys 1-5), not five separate panes |
| Right: notes, links and appearances for the selected entity | Works | appearances = recorded at promotion, or a whole-word name match in outlines/manuscripts |
| New entities blank; click/f rolls, right-click/e writes, space rolls blanks, history + scroll wheel | Works | field history lasts for the session, it is not saved to disk |
| Rolls use the universe's mix, the entity's other fields, and existing entities | Works | rival, owner, parent place and leader can be real entities |
| Write-only fields marked; custom per-entity fields | Works | |
| Rename with a preview of every match across notes, outlines and manuscripts | Works | matches are toggled one by one ("all or one at a time"), case-sensitive, whole-word, possessives handled; Neovim buffers are fresh on the next Writer start rather than reloaded live |
| Universe settings: genre leanings, exclusions/boosts, own lists folder | Works | no in-app editor for the lists, you drop JSON files into `<universe>/lists/` |
| Ratings on entity fields | Partial | recorded, but they don't yet change Builder rolls (no frame/atom provenance for entity fields) |

### Universes in the Wheel (`foundation-universes-wheel`)
| Item | Status | What's missing |
|---|---|---|
| Universe panel is a checklist of universes to draw from, saved per draft | Works | a draft started from the Builder (`W`) has its universe ticked |
| Entities become atoms in matching slots, boosted | Works | rivals read oddly: "the Sheriff Lund" (the templates say "the {rival}") |
| no / mix / only whole-step candidates from selected universes | Works | protagonist from characters, setting from places; blanks are completed with an ordinary roll |

### Writer, Neovim (`foundation-writer`)
| Item | Status | What's missing |
|---|---|---|
| Self-contained config via NVIM_APPNAME, shipped in the package | Works | no plugins; needs Neovim 0.10+ and says so if absent |
| Full screen, centered column, minimal statusline, soft wrap, mouse | Works | the look is checked by hand (section 3); two blank pad windows make the margins |
| Ctrl+I / Ctrl+B italic and bold with concealed markup | Partial | Alt+I, Alt+B and Ctrl+B work everywhere. **Ctrl+I only works where the terminal can tell it from Tab**, and the terminal on this machine (VTE: GNOME Terminal family) cannot, so Ctrl+I is not mapped there (Tab stays Tab); `Space k` asks your terminal and remembers |
| Virtual first-line paragraph indent; Enter starts a new paragraph | Works | |
| Scene break key (`* * *` stored, centered on screen) | Works | Alt+S |
| Show-invisibles, typewriter, spellcheck toggles | Works | remembered between visits |
| Scene sidebar with first lines: jump, add, rename, reorder | Works | no delete from the sidebar (deliberately) |
| World peek card; name completion | Works | |
| Stats: scene / manuscript / today vs goal in the statusline; stats.json | Works | |
| Autosave plus rolling backups | Works | |
| Story settings from settings.toml, editable from the Builder | Works | |

### Switching and state (`foundation-switching`)
| Item | Status | What's missing |
|---|---|---|
| Builder hotkey suspends the app and opens the Writer; a Neovim hotkey saves and returns; Builder refreshes | Works | exercised in a real pseudo-terminal; how the hand-over *looks* is manual |
| Neovim restores open scenes and cursor per story | Works | its own per-story JSON, not Vim sessions |
| state.json; plain `storywheel` reopens exactly where I left off | Works | in a terminal only; with `--plain` or a pipe it is still the plain prompt |
| Consistent mode keys (F1 Wheel / F2 Builder / F3 Writer) in every help screen | Works | |

### Export (`foundation-export`)
| Item | Status | What's missing |
|---|---|---|
| Shunn short-story .docx, verified by reading it back | Works | built with python-docx (no pandoc here); read back for spacing, font, margins, first-page block, header, `#`, END, italics; also opened in LibreOffice and rendered to PDF, and the first page and page-2 header looked right |
| .md and .txt compile; .odt; PDF via soffice | Works | .odt and .pdf come from the .docx through LibreOffice and say so plainly if it isn't installed |
| Export from the Builder and from the Writer; copy manuscript as plain text | Works | |
| Novel profile | Partial | each scene file becomes a chapter on a new page; Shunn's novel title page is not reproduced |
| Screenplay profile | Stub | writes an unformatted `.fountain` file and says so |

## 2. Tests added (413 before the sweep, 615 now: +202)

| Area | File | Tests |
|---|---|---|
| Storage: frontmatter, settings, schemas, universes, entities, links, migration, JSON commands | `test_storage.py` | 25 |
| Promotion logic and command | `test_promote.py` | 12 |
| Promotion in the app and Past stories | `test_promote_ui.py` | 10 |
| Filling fields with the generator; renames | `test_fill_rename.py` | 17 |
| The Builder driven by keys, clicks and the wheel | `test_builder.py` | 28 |
| Universes in the Wheel (atoms, boost rate, genre blend, whole-step candidates, panel) | `test_universes_wheel.py` | 32 |
| The Writer: headless Neovim plus one real terminal | `test_writer.py` | 55 |
| Switching and state, including real-terminal hand-overs | `test_switching.py` | 21 |
| Export: the .docx read back, other formats, commands, from the Builder and the Writer | `test_export.py` | 28 |
| Dependencies, stale candidates, no-repeat rerolls (from the start of the sweep) | `test_inputs.py` | 23 |
| (the old global-universe panel tests were replaced by the above) | | -14 |

Besides these: the headless Neovim tests need Neovim; the terminal tests need `pyte` (a dev dependency); the LibreOffice
tests skip themselves if `soffice` is missing.

## 3. Manual test script

Set up: `pipx install --editable .` (or `pip install -e .`), then `storywheel`. Use a full-screen window.

**A. First run and the Wheel**
1. Run `storywheel`. The Wheel opens. Keep a few steps (`k`), then press `q`.
2. The "bringing this story into the Universe Builder" message appears. Choose *new universe*, accept the name, read the
   preview, press `p`. You should land in the Builder on the new story.

**B. The Builder**
3. Press `2` (Places), `1` (Characters). Click an entity; left-click a field (it rolls), right-click another (a box to
   write in), scroll the wheel over a field (earlier values). Press `n` for a new blank entity, then `space` (it fills in).
4. Press `r` on a named character, type a new name: a list of every mention appears. Toggle one with Enter, press `p`.
5. Press `G` and fill in your real name and address (this goes on the manuscript's first page).

**C. The Writer, and what it looks like** (the part tests can't see)
6. With a story open press **F3** (or `w`). Neovim should fill the screen, the text in a column in the middle, nothing else
   but a quiet line at the bottom: `scene N · manuscript N · today N/500`. Is the column a comfortable width? Is the margin
   either side empty and calm? (Width: story settings, `S`, "column width".)
7. Type a paragraph, press Enter: a blank line should appear and the new paragraph's first line should show an indent
   (on screen only). Press Enter on an empty line: nothing should happen.
8. Press **Alt+S**: a centered `*  *  *` should appear between paragraphs. Check it looks centered.
9. **Ctrl+I in your terminal:** press `Space k`, then Ctrl+I. It will tell you whether your terminal can send it. On a
   GNOME Terminal (VTE) it will say it sends a Tab: use **Alt+I** for italic. Select a word (`viw`), press Alt+I, then Alt+B:
   the `*` marks should disappear and the word should look italic / bold. Move onto that line in insert mode: the marks
   show while you edit.
10. `Space i` (invisibles: dots for spaces, ¶ at line ends), `Space t` (typewriter: the line stays mid-screen), `Space s`
    (spellcheck underlines). Press each again to turn it off.
11. `Space n`: the scene list appears on the left. Try `a` (add), `r` (rename), `J`/`K` (move), Enter (jump), `q`.
12. Type a capital letter and two more of a character's name: a completion list should pop up; Tab picks. `Space p` on a
    name shows a small card.
13. Quit the terminal window mid-sentence (or kill Neovim). Open the story again: the text should be there (autosave),
    and `<story>/.backups/` should hold copies.
14. **F2**: you should be back in the Builder with the word count updated ("Back from the Writer"). Does the screen redraw
    cleanly with no leftover Neovim text?

**D. Switching and remembering**
15. In the Builder press F1, F2, F3 from the Wheel, Builder and Writer; each mode's help (`?` / `Space ?`) lists them.
16. Quit everything, then run plain `storywheel`: it should reopen exactly where you were (mode, universe, story, tab).

**E. Export and the clipboard**
17. In the Builder press `x`, choose Word (.docx). Open the file in your word processor (LibreOffice Writer / Word) and check:
    page 1 has your name and address top left, "about N words" top right, the title about halfway down with "by ..." below
    it; the text is double spaced Times New Roman 12 with half-inch indents; page 2 onward has "Surname / Keyword / 2" at
    the top right; scene breaks are a centered `#`; the last line is a centered END; italic words are italic.
18. Export PDF and .odt (needs LibreOffice) and open them.
19. Press `C` in the Builder (and `Space c` in the Writer), then paste into another program: you should get the plain
    text with `#` for scene breaks. If it says no clipboard, install `xclip` (X11) or `wl-clipboard` (Wayland).

**F. Universes feed the Wheel**
20. Start a new Wheel draft, press `v` and tick your universe. Roll a few protagonists and settings: your characters,
    places and things should turn up now and then. Set `Use: only` and the protagonist should always be one of yours.

## 4. Known issues, questionable decisions, open questions

- **Ctrl+I.** In a VTE terminal it cannot be told from Tab, so italic is Alt+I there. If you switch to kitty, WezTerm,
  foot or ghostty, `Space k` will find that Ctrl+I works. Open question: is Alt+I acceptable as the everyday key?
- **The Writer's statusline** looked slightly garbled in my terminal-emulator test harness (`pyte`); I believe that is the
  harness, not Neovim, but check it on screen (script step 6).
- **Rival names.** A universe character in the `rival` slot reads "the Sheriff Lund": the templates say "the {rival}".
  The fix is a feature on named atoms that the templates can test; not done.
- **Builder ratings** are recorded but don't change rolls (no provenance for entity fields yet).
- **Field history in the Builder** is not saved between runs.
- **Rename** is case-sensitive and whole-word on purpose (so "Stacie" doesn't change "stacie the cat"); it does not
  reload an open Neovim buffer because the Writer is closed while the Builder runs.
- **Renaming through the history wheel** also opens the rename preview each time (safe, but chatty).
- **Novel and screenplay** formats are partial / a stub as planned.
- **Atom boost default (1.5)** is a guess that gives a universe's lists roughly the share of a strong genre list; tune it
  per universe in `s`.
- **Leaving Neovim with `:q`** returns to the Builder (not out of the program); F1 goes to the Wheel.
- **Speed:** `.odt`/`.pdf` export waits for LibreOffice (a few seconds) with the screen showing "Exporting…".
- **Not verified on other machines:** Wayland clipboard (`wl-copy`) and a plain `xterm`.
- **Decisions** I made where CLAUDE.md was ambiguous are in its Decisions log (appended during the sweep).
