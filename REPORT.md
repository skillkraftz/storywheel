# Foundation sweep: report

Everything in the roadmap's foundation sweep is built and usable end to end. Status words: **Works** (built, tested,
used end to end), **Partial** (works, with a stated gap), **Stub** (marked as such, not the real thing), **Not started**.
The full suite is **752 tests, all passing** (413 at the start of the first sweep, 615 at its end). Tags: `stage-3-ui`,
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

---

# Second pass: fixes and additions from first real use

_Status words as above. Updated after each area; each area has a tag `pass2-...`._

## P1. Checklist

### Promotion is easy to find (`pass2-send-to-builder`)
| Item | Status | What's missing |
|---|---|---|
| A visible "Send to Builder" button and key (`B`) in the Wheel once a story has kept steps; same on Past stories | Works | the button is under the card from the start (greyed out until something is kept); once sent it reads "Open in Builder" and `B` opens the story there; Past stories has a "Send" button (and `P`) |
| F2 from a draft with kept steps offers to send it first | Works | choices: send it first, just go, or Escape to stay; a draft with nothing kept or already sent goes straight through |

### Builder fixes (`pass2-builder-fixes`)
| Item | Status | What's missing |
|---|---|---|
| The entity list must not move when an item is clicked; list and card in stable, separate areas | Partial | I could **not** reproduce a jump on a plain click in an automated run, so I fixed what I could reproduce and what could plausibly cause it: rolling a field used to rebuild the list and reset its scroll to the top (now the list is left alone unless a name changes, and then it keeps its scroll); the list, card and columns now have fixed sizes and never scroll themselves; list scrollbars reserve their space; the top box takes at most 30% of the height so the list keeps room on a short screen. **Needs your eyes** (manual script step 3) |
| Top box: left-click selects and allows scrolling; only right-click or `e` edits | Works | the wheel scrolls the top box (it no longer steps through history there); Enter does nothing |
| Universe entities know they're proper names ("the {rival}" renders "Sheriff Lund") | Works | done as a rule in the text filler (an article directly before a universe character's or place's name is dropped), so it also fixes "a/the" before places; names that already start with an article are left alone |

### Builder layout (`pass2-builder-layout`)
| Item | Status | What's missing |
|---|---|---|
| Right column becomes tabbed: Outline, Scenes, Notes (keys 6, 7, 8) | Works | Outline = the story's outline (the universe overview when no story is open), same click/e rules as before; Notes = the entity's notes (saved as you type), links both ways and appearances; the chosen tab is remembered |
| Scenes tab lists the manuscript's scenes and opens the Writer at one | Partial | Enter / "Write here" pass the scene to the Writer (`STORYWHEEL_SCENE`), and the list shows first lines and word counts; **the Writer itself does not yet jump to it** (that arrives with the one-file manuscript, below) |
| Top box becomes a stats box | Works | today vs the goal with a bar, current and best streak, this week, totals for the story and the universe; read from each story's `stats.json`, so it counts what the Writer recorded |

### Settings, F4 (`pass2-settings`)
| Item | Status | What's missing |
|---|---|---|
| A Settings mode on F4, in every help screen | Works | F4 in the Wheel, Builder, Writer; `storywheel settings`; `q` returns to where you pressed it; F1-F3 go on from there; remembered in `state.json` |
| Author details, goals, Writer preferences, export defaults, universe boost, library location | Works | tabs You, Goals, Writer, Export, Universes, Library; each change is saved to `~/.storywheel/settings.toml` as you make it; story settings still override (and now only store what the story itself sets, so your defaults keep applying); the universe boost is a default, a universe can pin its own (blank in `s` = follow the default); the library path can also be set here (the `STORYWHEEL_LIBRARY` variable still wins, and nothing is moved) |
| A Stats tab: words per day history, streaks, per-story totals | Works | counts what the Writer recorded in `stats.json` |

The Writer settings on that tab (notepad mode, Neovide, font, line spacing, paragraph spacing) are stored now; the Writer starts using them in the notepad / Neovide areas below.

### Writer: one manuscript file (`pass2-manuscript`)
| Item | Status | What's missing |
|---|---|---|
| One manuscript file per story with scene markers inside it (novels: one file per chapter) | Works | a scene starts at a marker line `* * *` or `* * * Title` (the same line the scene-break key inserts; exported as a centered `#`; a marker at the very top only names the first scene). Short story = `manuscript/manuscript.md`; a novel keeps one file per chapter. Marker lines are not counted as words (Python and Lua agree) |
| Sidebar lists and jumps to scenes by their markers (add, rename, reorder) | Works | rename edits the marker's title; J/K swaps neighbouring scenes in the same file (an unmarked first scene gets a marker when it moves; moving across chapter files is refused with a message); the cursor stays on your text; `]]` / `[[` step between scenes |
| Migrate existing scene files in order, with a backup | Works | runs when the Writer starts and at app start (`storywheel migrate` does it by hand): scene files are merged in order into `manuscript.md` (each one's name becomes its marker title) and the originals are moved to `<story>/.backups/migrated-DATE/`; a novel and single-file stories are left alone; nothing is merged twice |
| Opening the Writer at a chosen scene (from the Scenes tab and the sidebar) | Works | the Builder's Scenes tab passes the scene (`STORYWHEEL_SCENE`); the Writer opens at the first line of its text |

### Writer: notepad mode (`pass2-notepad`)
| Item | Status | What's missing |
|---|---|---|
| Notepad mode, on by default: stays in typing mode (Escape does nothing) | Works | Neovim has no "insert mode only" option, so Normal mode is simply never rested in (it drops straight back to typing); Escape closes a popup or clears a find highlight |
| Mouse selection like a normal app; typing replaces the selection; Shift+arrows select | Works | uses Neovim's Select mode with an exclusive selection; **dragging with the mouse is configured but can only be tried by hand** (manual script 10) |
| Ctrl+C / X / V system clipboard | Works | with `xclip`/`wl-copy` etc.; with none, copy and paste work inside the Writer only and you are told; the real clipboard path is manual (script 11) |
| Ctrl+Z / Y, Ctrl+S, Ctrl+A, Ctrl+F (find; Ctrl+G next, Alt+G previous) | Works | undo goes a word at a time (an undo break at each space) |
| A right-click menu | Works | Cut, Copy, Paste, Select All, Italic, Bold, Scene Break, Find, Writer Menu |
| A key that opens a menu of Writer actions | Works | **F12 or Alt+M**: sidebar, new scene, find, peek, invisibles, typewriter, spellcheck, counts, export, copy manuscript, settings.toml, Settings, Builder, Wheel, help, switch to Vim keys; Ctrl+Q goes back to the Builder. (Peek moved from F10 to F8, since GNOME Terminal keeps F10 for its own menu.) |
| A setting turns Vim behavior back on | Works | "Notepad mode" in Settings (F4), per story or global |
| Home/End | Partial | they go to the start/end of the paragraph, not of the wrapped screen line |

### Writer: Neovide and the status line (`pass2-neovide`)
| Item | Status | What's missing |
|---|---|---|
| Optional Neovide front-end (same config, real fonts from settings, extra line spacing) | Partial | `Use Neovide` (global or per story), font, size and line spacing are settings; Neovide is started with `--no-fork` and the same environment; Ctrl+I works there. **I could not run Neovide here (it isn't installed), so how it looks is untested**, though the launch command and the options it gets are tested |
| Detect whether Neovide is installed and say so if not | Works | falls back to the terminal with a plain message in the Builder (and before launching from the Wheel/CLI); Settings > Writer shows whether Neovide and Neovim are found |
| In the terminal, extra space between paragraphs as the closest equivalent | Works | `paragraph_spacing` (0-3 blank lines shown between paragraphs; display only, nothing is typed) |
| Check the statusline renders correctly | Works | read off a real terminal emulator (tmux) in both modes: `scene 11 · manuscript 11 · today 0/1,000` on the row above the command line, nothing else on it and no file path anywhere. The garbling seen earlier was the Python screen emulator I used for the capture (`pyte`), not Neovim; I also made the Writer start with a blank status line, short messages and a short window title, so a path can never show there

## P2. Tests added in the second pass
| Area | File | Tests |
|---|---|---|
| Send to Builder | `test_send_to_builder.py` | 9 |
| Builder fixes | `test_builder_fixes.py` | 13 |
| Builder layout and writing stats | `test_builder_layout.py` | 18 |
| Settings mode and stats tab | `test_settings_mode.py` | 20 |
| F4 from the Writer | `test_writer.py` | +1 |
| One manuscript file, markers, migration, scene tools (and the Writer tests rewritten for markers) | `test_manuscript.py` | 23 |
| Notepad mode | `test_notepad.py` | 34 |
| Neovide, GUI settings, paragraph spacing | `test_neovide.py` | 14 |
| Status line on a real terminal (tmux) | `test_statusline.py` | 2 |

## P3. Manual test script additions
1. In the Wheel, keep one step: the **Send to Builder** button under the card should light up. Click it (or press `B`).
2. Press **F2** in a draft with kept steps: you should be offered "send it first".

3. In the Builder with a long list of entities: scroll the list, click an item near the top and the bottom edge, roll fields on the card
   (click a field, press space): the list should stay put and the card should change beside it. Tell me if it still shifts, and
   what size your terminal is.
4. In a story's outline box (top): left-click a row (it highlights, nothing opens), scroll the wheel (it scrolls), right-click or press `e` (an edit box opens).
5. Put a universe character in the rival slot (`Use: only` is not needed; boost the universe): the text says "Sheriff Lund", not "the Sheriff Lund".

6. In the Builder: look at the box at the top (today's words, streak, totals) and the three tabs on the right (keys 6, 7, 8). Open the
   Scenes tab, press Enter on a scene.

7. Press **F4** in each mode: Settings opens. Change your name, toggle a switch, set the daily goal; open `~/.storywheel/settings.toml`
   and see it written. Look at the Stats tab. Press `q`: you return to the mode you came from.

8. Migration: open a story that still has several scene files (from before this pass): run `storywheel migrate`, then look in the story
   folder: one `manuscript.md` with `* * * Title` lines, and the old files in `.backups/migrated-.../`.
9. In the Writer press `Space n`: scenes are listed by their markers. Press `a` to add one, `r` to rename, `J`/`K` to move, Enter to jump.
   In the Builder's Scenes tab press Enter on a scene: the Writer should open on its first line.

10. **Notepad feel** (the main thing for your eyes): open the Writer. You should be typing at once; press Escape (nothing happens).
    Drag the mouse over some words, type: they are replaced. Shift+arrows select. Ctrl+C, Ctrl+V into another program and back.
    Ctrl+Z / Ctrl+Y, Ctrl+S, Ctrl+A, Ctrl+F (type a word, Enter; Ctrl+G for the next one). Right-click: a menu. F12: the Writer menu.
11. Real clipboard: copy a sentence in the Writer, paste it in a browser; copy in a browser, Ctrl+V in the Writer. (If you have no
    `xclip` or `wl-copy`, a notice says copy/paste stay inside the Writer.)
12. **Neovide look** (if you install it): in Settings (F4) > Writer switch on "Use Neovide", set a font and a line spacing (try 15),
    then open the Writer: a window with that font and a double-spaced look. If Neovide is not installed you get a message and the terminal.
    In the terminal, set "Terminal: blank lines between paragraphs" to 1 and look at the gap.
13. **List stability** (Builder): the long entity list should not move when you click items or roll fields.

## P4. Known issues / open questions (second pass)
- Mouse dragging and the real clipboard are untested by machine (no screen/clipboard in the tests); see steps 10 and 11.
- In notepad mode the Vim `Space` shortcuts are not available; their jobs are on F8, F9, F12 / Alt+M, Alt+I/B/S and the right-click menu.
- A scene marker is a visible line in the file (`* * * Title`); on screen it is drawn centered, with the title dim beside it. Deleting that line merges the scene into the one before.
- Changing the library folder in Settings only points at it; moving or copying your existing universes there is up to you.
- The stats box counts words as the Writer recorded them in `stats.json`; words typed outside the Writer are not counted.
- The "list moves when clicked" report could not be reproduced headlessly (see above); please re-test by hand.
- Past stories' button is labelled just "Send" (a longer label did not fit the column).

---

# Third pass: fixes from real use (screenshots reviewed)

_Same status words. Tags `pass3-...`._

## T1. Checklist

### Builder layout (`pass3-layout`)
| Item | Status | What's missing |
|---|---|---|
| Lists jump when clicked (the focused list lost its border) | Works | cause confirmed: `OptionList:focus { border: none }` removed the default border only when focused. Every list and text box in the Builder now has the same (no) border focused or not, and focus shows by colour. A test focuses every list, tree, text box and table in the Builder (all three right-hand tabs), the Wheel and Settings and fails if anything anywhere moves or resizes; it fails on the old CSS |
| Links and Appears in under the entity card | Works | they sit at the bottom of the card (they describe the selected entity); the Notes tab is now only for notes |
| Rebalance widths | Works | left column 46, entity list column 40, right column 52: every button (Roll blanks, Del, Outline, +Draft...) shows whole at 220, 180 and 160 columns; left-column titles wrap rather than truncate; each universe in the list shows "N entities" |
| Outline tab as readable text | Works | one row per beat (numbered, or with its own label if the structure shows labels), setting lines as rows, no `**`, no list dashes, no "Once upon a time. Once upon a time,"; right-click or `e` edits just that beat or setting line and writes it back to story.md. Promotion no longer adds a label when the sentence already opens with it (older outlines are cleaned for showing) |

### Data correctness (`pass3-data`)
| Item | Status | What's missing |
|---|---|---|
| "the sorcers apprentice" vs "a sorcerer's apprentice" | Partial | The exact path that produced your screenshot could not be reproduced: promotion, the outline and the frontmatter round-trip keep the text exactly (a test now proves it from Wheel through promotion, outline, Builder and the .docx/.md/.txt exports). Fuzzing the Wheel's own rewriting found three real mangling paths, all fixed: `singular()` turned gallows→"gallowse", prairie→"prairy", cactus→"cactuse"; thread replacement could cut into a longer word ("sorcerer" inside "sorcerer's"); a pronoun pass could eat part of a possessive. A swap of a protagonist's name now also follows the surname ("O'Brien's cottage"). If "sorcers" shows up again, note which Wheel step you were on |
| Hand-written title recomputes the motif | Works | in the Wheel (edit field, write own, $EDITOR) and in the Builder's title edit; a note says "The motif now follows your title"; if you changed the motif yourself in the same edit, yours stands |
| Season is a real Place field; "Located in" | Works | Season sits after Era on the Place card and can be rolled; promotion stores it as a field; older places with a custom `season` are read as the field. The link is labelled "Located in" |
| Universe counts agree | Works | one shared count (`universe_atoms.counts_text` / `named`): checklist reads "4 characters · 2 places · 3 things"; the panel has Characters / Places / Things groups with the same numbers. Only characters and towns can be "used" as a whole step; things and landmarks say why |

### Wheel drafts (`pass3-drafts`)
| Item | Status | What's missing |
|---|---|---|
| No draft file until something is kept; tidy old ones | Works | a draft is written on its first keep. At the next Wheel start (or `storywheel list`) drafts with nothing kept are moved to `<home>/.trash/` and the status line says how many |
| Past stories show kept progress | Works | "5/8" is steps kept, "done" is a finished story. Titles show 22 characters, not 15 |
| Finished draft reopens where it ended | Works | on its last step, with a line saying so (CLI: same). It no longer jumps to step 1 |
| Promoted draft in the Wheel | Works (read-only) | see Decisions: opened read-only, `C` makes an editable copy as a new draft; roll/keep/edit/write/skip/history-pick say why they do nothing. Plain `resume` offers the copy |

### Own review pass (`pass3-review`): found and fixed
Clicked through the Wheel, Builder (every tab) and Settings (every tab) at 200x50 and checked each for the same kinds of trouble.
| Found | Fixed |
|---|---|
| Builder entity card: "Relationships ✎(blank)" ran together (label column too narrow for the marker) | label column now counts the marker |
| "5 words in 1 scene(s)" raw plural in the Builder's stats and Outline | proper plurals |
| Settings > Stats tables clipped names ("Thornwoo", "Null") | explicit column widths |
| Wheel Past stories cut titles at 15 characters | 22 |
| Wheel/Builder buttons could clip at narrower widths | tests check 160, 180 and 220 columns |
| Counts across modes | Wheel checklist, Wheel panel, Builder universe list and tab counts now agree (shared function) |
| Data changing between modes | promoted drafts can no longer be edited in the Wheel; the Builder is the one place the story changes |
| Raw markup | none left in the Outline; the Wheel's "story so far" and the Builder's Outline read the same |

## T2. Tests added in the third pass
| Area | File | Tests |
|---|---|---|
| Focus never moves anything; layout holds together; review-pass checks | `test_layout_stability.py` | 14 |
| Outline as readable rows, one-row edits | `test_outline.py` | 8 |
| Possessives through the whole pipeline, singular/plural round trip, motif follows title, Season | `test_data_correctness.py` | 26 |
| Drafts: no empty files, tidy to .trash, progress, finished reopen, promoted read-only + copy | `test_drafts.py` | 11 |

Full suite before the final commit: **811 passed** (all tests, including the real-terminal ones).

## T3. Manual test script (things tests can't see)
1. Click every list in the Builder, the Wheel and Settings: nothing should shift a row or change size, only the highlight colour changes.
2. Builder: select a character; Links and Appears in sit under the card; widths feel right at your usual window size.
3. Open the Outline tab and read it like the Wheel's story so far. Right-click (or `e`) a beat and a setting line and edit them.
4. Hand-write a title in the Wheel and keep it; the motif should follow. Do it again in the Builder.
5. Wheel: start it and quit without keeping anything; no draft appears in Past stories. Keep one step, quit, relaunch: it is there with "1/8".
6. Open a finished draft: it lands on Twist (last step) with the "finished" line. Open a promoted draft: edits say "Read-only"; press C and edit the copy.
7. Tick a universe in the Wheel: the counts line and the three groups below agree.

---

# Fourth pass: errors and performance from real use

_Same status words. Tags `pass4-menus`, `pass4-export`, `pass4-perf`._

## F1. Checklist

### Writer menus (`pass4-menus`)
| Item | Status | What's missing |
|---|---|---|
| Right-click "E329: No menu 'Go to definition'" | Works | reproduced headlessly (`doautocmd MenuPopup` raised it). Cause as you described: Neovim 0.11's `nvim.popupmenu` handler. `popup_menu()` now deletes every MenuPopup autocmd (by id, so the group name doesn't matter) and the group by name, in `pcall`s; test asserts none are left |
| Other menu items show errors | Works | new tests open the right-click menu (MenuPopup fires, then each item runs via `emenu`, with and without a selection; Find is answered) and the Writer menu (every item by number, by Down+Enter, and by mouse click), and fail on anything in `v:errmsg` or `:messages`. They found: **Help** opened in Insert mode, so `q`/Esc did nothing and typing gave E21 (fixed: Normal mode, closes with q/Esc/Enter and returns to typing; the menu only restarts typing when you are back in the writing window); the **E31** left in `v:errmsg` by `aunmenu` (cleared). No other menu item errored |

### Export location (`pass4-export`)
| Item | Status | What's missing |
|---|---|---|
| Manuscripts folder, one folder per story | Works | setting `manuscripts_dir` (Settings F4 > Export, or `STORYWHEEL_MANUSCRIPTS`), default `~/Writing`. `<folder>/<Title>/<Title> <YYYY-MM-DD>.docx` (also odt, pdf, md, txt, fountain). The library's layout is unchanged; `exports/` inside stories is no longer used |
| Messages | Works | paths shown with `~`; warnings say "Settings (F4) > You". Writer: "Exported ~/Writing/..." |
| Move existing exports | Works | `migrate.migrate_exports()` runs where the other migrations run (startup, `storywheel migrate`) and prints "Moved N exports out of your library to ~/Writing (one folder per story)." Files keep their own date |

### Performance (`pass4-perf`)
| Item | Status | What's missing |
|---|---|---|
| Keep the universe in memory, reload by modification time | Works | `vault.memo/stamp`: every entity file, story outline, manuscript text, word count and scene list is read once and remembered until the file's time or size changes (the Writer and Obsidian are noticed; our own writes forget a file at once). `entities()`/`entity()` hand out copies; internal lookups (`resolve`, `links_to`) use the shared objects. Schema files are read once per change of their folder |
| Cache word counts and Appears in per story | Works | by story file stamps; the regex search runs only for a story whose files changed |
| A field roll redraws only the card | Works | `refresh_all(light=True)`: card and links only; no stats box, outline, notes or Appears in. A name change still rebuilds the lists |
| Performance test | Works | generated universe of 160 entities and four ~20k-word stories (`tests/bigworld.py`). Measured here: selecting an entity 10 ms (was 70), rolling a field 6-13 ms (was 140); the tests allow 50 ms. They also check a roll reads at most one entity file and does not recompute the stats box, and that outside changes are noticed |
| Wheel and Settings | Works | checked with the same universe ticked: Wheel roll/keep/redraw 5-11 ms; Settings Stats tab 45 ms once, then cached. No reload-everything pattern left |

## F2. Tests added in the fourth pass
| Area | File | Tests |
|---|---|---|
| Every right-click and Writer menu item, run like a user | `test_menus.py` | 23 |
| Export location, conflicts, migration, setting | `test_export_location.py` | 12 |
| Performance and cache correctness | `test_performance.py` | 9 |

## F3. Manual test script
1. Right-click in the Writer on text and on a selection; try every entry; open the Writer menu (F12) and try Help (q closes it) and the sidebar. Nothing should print an error.
2. Export from the Writer menu and from the Builder (`x`); look in `~/Writing/<Story Title>/`. Export again the same day: " -2" appears.
3. Make a second story with the same title in another universe and export it: its folder has the universe name.
4. Start the program once: if you had exports inside the library you get the "Moved N exports" line.
5. In your real library: click around entities and roll fields; it should feel instant. If anything still lags, note which action.

## F4. Known issues
- Schema files edited in place (not added or removed) are noticed on the next start.
- A file rewritten twice within the file system's timestamp tick with the same size by another program could be missed until it changes again; our own writes never are.

Full suite before the final commit: **855 passed**.

---

# Fifth pass: the Writer and export, ready for real use

_Same status words. Tags `pass5-paragraphs`, `pass5-menus`, `pass5-keys`, `pass5-export`._

## G1. Checklist

### Paragraphs (`pass5-paragraphs`)
| Item | Status | What's missing |
|---|---|---|
| One line = one paragraph everywhere | Works | Writer (indent, Enter, scene break), word counts (they were already line based), scenes, and export (`export.paragraphs()` no longer joins lines). A pasted 50-paragraph story with no blank lines exports as 50 paragraphs (test) |
| Every paragraph line gets the indent; blank lines optional; `paragraph_spacing` still adds a gap | Works | display: every non-blank, non-break line is indented (it used to need a blank line before it). Export: every paragraph has the half-inch first-line indent, including the first after a scene break. The terminal gap now sits between paragraph lines (after each paragraph line that is followed by another), not on blank lines. Old blank lines are ignored in export and counts |
| Paste strips leading tabs/spaces; Tab at a paragraph start does nothing | Works | Ctrl+V and the terminal's paste (bracketed, in one piece or chunks) drop leading tabs/spaces/non-breaking spaces and empty lines; spaces inside a line are kept. Tab at the start of a paragraph does nothing and says "Indents are automatic" once per session; Tab elsewhere in a line still inserts (as spaces) and still walks the name completion |
| Join selected lines into one paragraph | Works | Alt+J, `:SWJoin`, "Join lines into one paragraph" in the Writer menu and "Join Lines" in the right-click menu. It needs a selection (with one line per paragraph there is no "the paragraph" to guess, and joining a whole run of lines by accident would be bad); with nothing selected it says so. Blank lines and scene breaks inside the selection are dropped |
| Convert existing manuscripts, with a backup, and report | Works | `Story.migrate_paragraphs()`, once per story (a `.one-line-paragraphs` file records it; new stories get it at once). Only files that use blank lines between paragraphs are touched: lines of a paragraph that were wrapped are joined, blank lines are dropped, originals go to `.backups/paragraphs-DATE/`, and the startup migration (or the Writer's start) says e.g. "joined 2 hard-wrapped paragraphs and removed 4 blank lines in manuscript.md". A file with no blank lines is taken to be in the new form already |
| Optional export setting: one space after periods | Works | Settings > Export "One space after periods" (`export_one_space`); applies to .docx, .md and .txt. "3.5  apples" (no sentence end) is left alone |

### E21 and real key paths (`pass5-menus`)
| Item | Status | What's missing |
|---|---|---|
| Insert mode inside the read-only menu | Works | cause as you found: `run_menu_item('menu')` ended with `insert(true)` while the menu window was current. `notepad.can_type()` (the writing window is current and modifiable) now guards every way into Insert mode (`insert`, `start_typing`), so it can't happen from any menu, help or sidebar |
| Tests with real key sequences | Works | `test_menu_keys.py`: every Writer-menu item by F12+Down+Enter, by F12+number, and by right-click > Writer Menu > Down > Enter; each must work after exactly those keys (menu closed, effect done, back in the writing window, or the right mode left for) with no error message. They fail on the old code (checked). Extra: right-click > Writer Menu > Export makes the file on the first Enter; keep typing straight after |

### Title bar (`pass5-menus`)
| Item | Status | What's missing |
|---|---|---|
| Header never goes tall | Works | `header.QuietHeader` ignores clicks and never takes the `-tall` class; used in the Wheel, Builder and Settings (test clicks it twice in each) |

### Manuscript export (`pass5-export`)
| Item | Status | What's missing |
|---|---|---|
| Title in bold (default on); header full title (default) or Shunn's keyword | Works | Settings > Export: "Title in bold", "Page header shows" (full / keyword; a story's `title_keyword` still works for keyword) |
| Anonymous export | Works | setting "Always export anonymously", plus a choice per export: Builder export list ("Word (.docx), anonymous"), Writer menu ("Export anonymous manuscript"), CLI `--anonymous`. No name, contact block, byline or surname; header "Title / page"; the word count stays top right; the document author property is blank. Markdown/text exports drop the byline |
| Missing author details | Works | no name in Settings > You: the anonymous layout is exported and the message says so ("exported anonymously, with no name or contact block"). No "Your Name"/"Author" placeholder anywhere. A missing address still only warns |

### Scene breaks and keys (`pass5-keys`)
| Item | Status | What's missing |
|---|---|---|
| Configurable scene break, default `***` | Works | Settings > Writer: `***`, `* * *` or `#`. A line holding only one of them (also `* * * Title`, `*** Title`) is a break everywhere (Python and Lua); `***bold italic***` inside text is not. Alt+S inserts the chosen form; typing `***` (or `* * *`, `#`) alone on a line and pressing Enter makes it the chosen form and starts a new line |
| Keys section in Settings | Works | Settings > Keys: italic, bold, scene break, menu, sidebar, peek, back to the Builder. You may type "Alt+I", "ctrl+b", "<A-i>", "F9"; it is stored in Neovim's form. Refused: a bare letter, unknown names, keys the Writer needs (Ctrl+C/X/V/Z/Y/S/A/F/G, Alt+G, Alt+J, Alt+M, Ctrl+B, F1-F4...) and a key another shortcut already has, each with a message. Applies the next time the Writer starts. Extra keys that always work (Alt+M, Ctrl+B) are kept |

## G2. Review of the Writer the way you use it
`test_writer_review.py` does it in one go: pastes 30 paragraphs (one per line, alternating tab and 4-space indents, with blank lines in between) through the terminal-paste path, types a new paragraph, a scene break with Alt+S, a paragraph, then `***`+Enter and a paragraph, saves with Ctrl+S, exports, and reads the .docx with python-docx. Confirmed: 33 paragraphs (30 + 3 typed), nothing indented in the file, exactly two scene breaks (`#` centred in the export), every paragraph indented 0.5", title bold, byline, header "Writer / The Last Clause / page".

## G3. Tests added in the fifth pass
| Area | File | Tests |
|---|---|---|
| Paragraphs in the Writer, paste, Tab, join, breaks, conversion | `test_paragraphs.py` | 23 |
| Export of paragraphs and the new options | `test_paragraph_export.py` | 13 |
| Menus by real keys | `test_menu_keys.py` | 5 |
| Shortcuts and Settings > Keys | `test_keys.py` | 23 |
| Title bar | `test_header.py` | 3 |
| Whole use of the Writer then export | `test_writer_review.py` | 1 |
(Several older Writer tests changed to the one-line rule: Enter, indent, scene break, paste, menu numbers.)

## G4. Manual test script
1. Paste a few pages from another program (one paragraph per line, with tabs). Every paragraph should show an indent; nothing should be indented in the file (look with Show invisibles).
2. Press Tab at the start of a paragraph: nothing, and the note once. Select several hard-wrapped lines and press Alt+J.
3. Type `***`, Enter: it becomes a centred break. Try Alt+S. Change the break form in Settings > Writer and try again.
4. Settings > Keys: change Italic to something else, restart the Writer, try it; try a conflicting key and read the message.
5. Right-click > Writer Menu > Down > Enter on any item: it should work with that one Enter.
6. Export (and the anonymous export) and open the .docx in your word processor: indents, `#` breaks, bold title, header text.
7. Click the title bar in each mode: it should stay one line.

## G5. Known issues / decisions to check
- Join needs a selection (see above); say if you would rather it join the whole run of lines around the cursor.
- A manuscript that has NO blank lines at all is assumed to be in the new form already, so an old single hard-wrapped paragraph without blank lines isn't joined by the conversion (use Alt+J).
- Key changes apply at the next Writer start.
- Stories made by the Python side (Builder "new scene") still put a blank line before and after a marker; it is ignored everywhere.


Full suite before the final commit: **925 passed**.

---

# Batch 1 (BACKLOG.md): title bar, Home/End, verify items, find and replace, dictionary and thesaurus

_Tags `b1-header`, `b1-homeend`, `b1-verify`, `b1-replace`, `b1-dictionary-core`, `b1-dictionary-tui`, `b1-dictionary-writer`._

## H1. Checklist
| Item | Status | What's missing |
|---|---|---|
| Title bar expands on click | Works | `QuietHeader._on_click(event)` calls `event.prevent_default()`, which stops the base Header handler (Textual runs every class's handler in the MRO). Pilot test clicks the title three times in the Wheel, Builder and Settings and checks the height stays 1; with the old override the same test fails (1 → 3) |
| Home/End on the visible wrapped line | Works | Home goes to the start of the screen line, and again to the paragraph start; End to the end of the screen line (after the last character on the last one). Shift+Home/End still select by whole line (BACKLOG 4b) |
| Verify items, section 2 | Works / Partial | Scenes tab → Writer at the scene: works (existing tests). Neovide: it is installed here (0.16.2), starts with our config, stays running, prints no errors. How it looks could not be checked (a screenshot of the Wayland session came back black), so that stays a Verify for you |
| Verify items, section 3 (CLAUDE.md audit) | Done | Checked against the code; two features now have tests: a universe's own `lists/` are merged and used when rolling in it, and "+Draft" from a universe starts a Wheel draft with it ticked. **Missing:** Obsidian `[[wikilinks]]` resolving to entities (no code reads them): in BACKLOG section 3. Everything else in the brief exists |
| Find and replace (Ctrl+H, configurable) | Works | a form over the writing window: Find and Replace lines, Enter = next, Alt+R replace this one, Alt+A replace all (one undo step), Alt+C match case, Alt+W whole word; the title shows "N matches" live, highlights them, says "replaced N"/"not found"/"nothing to replace". Literal text only; current file only (BACKLOG 4b). Prefills from a selection. In the F12 menu; `:SWReplace`; key in Settings > Keys (`key_replace`) |
| Dictionary: data and lookups | Works | Open English WordNet 2025 (CC BY 4.0) + Moby Thesaurus II (public domain) in one 28 MB SQLite file (178,351 words, 107,519 meanings, 30,260 thesaurus entries), built in ~5 s. Lookups take 1-25 ms. Inflected forms by WordNet's own irregular forms plus the regular endings (running, geese, wolves, ran, leaves → leaf and leave, happier...); a missing word returns close spellings (misspellings with the same letters first). Opposites include those reached through "similar" adjectives (cheerful → unhappy). Both licenses checked 2026-10-02 against the files themselves and recorded in SOURCES.md |
| Dictionary: install | Works | **Not bundled** (28 MB would be heavy in the repo and the package); `storywheel dictionary install` downloads both files (36 MB, the only network use, only when asked) and builds the index in about 6 seconds (run end to end here into a temporary home). `dictionary status`, and `dictionary build --oewn FILE --moby FILE` for files you already have. **You need to run `storywheel dictionary install` once** before F5/F7 work; until then they say so |
| TUI Lookup dialog | Works | F5 in the Wheel, Builder and Settings (also in each help and footer); type a word, Enter; shows the same card; credit line for the licenses. In the Builder's right-click menu: not done (BACKLOG 4) |
| Writer card | Works | F7 on the word under the cursor or a selection, F6 for a typed word, "Look Up" in the right-click menu, two entries in the F12 menu; keys configurable in Settings > Keys. The card shows meanings by part of speech with an example, similar words (WordNet's first) and opposite words; arrows/j/k move, Tab jumps to the next section, Enter on a word replaces the looked-up word keeping capitalization (Dog → Hound, DOG → HOUND); for a typed word Enter inserts at the cursor; Esc closes and you are typing again. Not found → close spellings you can pick |
| CLI | Works | `storywheel define|thesaurus|lookup WORD [--json] [--limit N]`, `dictionary install|status|build`; without the index the JSON has `"error"` and `"installed": false` and the exit code is 1. The Writer uses `lookup` (one process instead of two) |

## H2. Tests added in batch 1
| Area | File | Tests |
|---|---|---|
| Title bar in every mode | `test_header.py` | 4 |
| Home/End | `test_notepad.py` | 4 |
| Audit (own lists, draft from a universe) | `test_audit.py` | 2 |
| Find and replace | `test_replace.py` | 11 |
| Dictionary core, CLI, no network, speed | `test_dictionary.py` | 31 |
| Lookup dialog | `test_lookup_screen.py` | 6 |
| Writer card | `test_lookup_writer.py` | 16 |
(The tests use a tiny hand-made index, `tests/dictfixture.py`, so they never download anything.)

## H3. Manual test script
1. Run `storywheel dictionary install` once. Then `storywheel define serendipity`.
2. F5 in each mode: look up "geese", "running", a misspelling. Esc closes.
3. In the Writer, put the cursor in a word, press F7, pick a similar word with Enter; try a capitalized word and an ALL CAPS word. Try F6.
4. Ctrl+H in the Writer: find a word, replace one, replace all, Ctrl+Z once to undo the lot.
5. Home/End in a long wrapped paragraph.
6. Click the title bar in every mode.
7. Settings > Writer: turn on Use Neovide and try the font settings; tell me how it looks.


Full suite at the end of batch 1: **998 passed**.

---

# Batch 2a (BACKLOG.md): the Writer's keys and the language tools

_Tags `b2a-ctrl-keys`, `b2a-fkeys`, `b2a-replace-key`, `b2a-shift-home`, `b2a-undo-menu`, `b2a-inflect`, `b2a-card-all`, `b2a-card-opposites`, `b2a-card-keys`, `b2a-card-form`, `b2a-wordbank`, `b2a-overused-data`, `b2a-words-mode`, `b2a-words-lookup`, `b2a-words-use`, `b2a-words-vocab`, `b2a-words-bank`, `b2a-words-overused`. Several items were done in one commit and carry all their tags._

**You need to run `storywheel dictionary install` again** (the index has relations now, schema 2); until then lookups and Words say so.

## J1. Writer keys
| Item | Status | What's missing |
|---|---|---|
| Neovim's insert/select-mode Ctrl keys | Works | in notepad mode every Ctrl letter that is not deliberately mapped (and Ctrl+@ ] ^ _ \ Space) does nothing in Insert and Select mode: U, W, T, D, O, R(was register paste), K, E, L, J, N, P (these two still walk a completion list when one is open) and the rest. Ctrl+M (Enter), Ctrl+I (Tab) and Ctrl+[ (Escape) are left alone. Tests press each key and check the text, cursor and mode did not change; Ctrl+U no longer deletes the line |
| Undo/Redo in the menus, labelled | Works | right-click menu: Undo, Redo first, and every entry shows its key beside it (Ctrl+X, Alt+I, F12...; the configurable ones show the configured key); the F12 menu has "Undo (Ctrl+Z)" and "Redo (Ctrl+Y)". Tests run both through the menu |
| Ctrl+H / Ctrl+Backspace | Works | both delete the previous word (with a selection: delete the selection); Ctrl+Delete deletes the next word. **Replace moved to Ctrl+R** (a distinct code in VTE: 0x12, not Tab, Enter or Backspace). I can't press keys in your VTE from here: please check (BACKLOG 4b). Both are reserved in Settings > Keys, and replace can be given another key there |
| Unmapped function keys | Works | F1-F12 with Shift/Ctrl/Alt do nothing in Insert and Select mode (F5 used to type "<F5>"); F1-F5 are the modes, and F6-F9, F12 are the configured keys |
| Shift+Home / Shift+End | Works | select to the start / end of the visible (wrapped) line, the other end stays where it was; again extends; typing replaces, Ctrl+C copies |

## J2. Writer cards (F7 and F6)
| Item | Status | What's missing |
|---|---|---|
| All similar words, grouped, scrollable, filter | Works | no limit and no "N more" anywhere (CLI `--limit` is gone). Each meaning lists its own similar words; then "More similar words (N)", the full Moby list, alphabetical; the card scrolls; `/` filters every list, Esc clears the filter. Words are wrapped like text and the one under the cursor is highlighted (arrows, Tab for the next group, mouse click) |
| Opposites: indirect, and Roget | Partial | indirect opposites (the opposites of each similar word, shown as "sad (glad)") are in the card, labelled. **Roget 1911 was evaluated and not used**: the file's own notes say the opposite-side-by-side layout was abandoned, so the pairing of opposing categories is not in the data and adjacency is not reliable (31 Greatness / 32 Smallness, but 7 State / 8 Circumstance). Recorded in BACKLOG.md and SOURCES.md; nothing from it is in the program. Indirect opposites are computed for the word as a whole, so a word with several meanings can show one from another meaning (BACKLOG) |
| Same behaviour for F6 and F7 | Works | Enter looks the word under the cursor up; `b` back / `n` forward (a position like [2/3] in the title); `r` replaces the word that was under the cursor when the card was opened (F6 uses the word under the cursor too); `i` inserts at the cursor; `c` copies; `w` asks for another word; keys are in the footer (`r` only when there is a word to replace) |
| Replacement matches the original's form | Works | `inflect.py`: running → sprinting, ran → sprinted, dogs → domestic dogs, geese → swans, happier → gladder, happiest → most joyful, wrote/written; capitals kept (Running → Sprinting, DOGS → DOMESTIC DOGS). WordNet's own irregular-form lists turned out incomplete and untagged ("write" lists "written" but not "wrote"), so irregulars come from tables in the code (about 150 verbs, 80 nouns, the irregular adjectives); the lookup tells which base word and form the original is; `storywheel inflect ORIGINAL BASE WORD` does the work |

## J3. Words mode (F5)
| Item | Status | What's missing |
|---|---|---|
| F5 from every mode, including the Writer | Works | the Wheel, Builder, Settings and Words itself have F1-F5; in the Writer F5 saves, hands over the word under the cursor (or the selection) and where it is, and leaves (like F2); help screens, footers, the Writer's help and menu, and the Settings > Keys notes all list F5. The old F5 Lookup dialog is gone (Words replaces it) |
| Lookup | Works | meanings, examples, every similar word per meaning, the broad list, every opposite and the indirect ones, wider ("a kind of") and narrower ("types of it") words, parts and "part of", related forms (derivation etc.); Enter or a click on a word looks it up; back/forward (keys and buttons) with a history; a filter box; `a` adds the word to the word bank, `c` copies it |
| Use in Writer | Works | `u` / button: returns to the Writer at the same spot with the original word replaced by the picked one in the same form and with the original's capitals; the Writer applies it before the first screen, saves the file, and puts the cursor after the new word; if the text changed meanwhile nothing is replaced and it says so. Without a word from the Writer the button is disabled and a message says to press F5 in the Writer |
| Vocabulary builder | Works | from a word or topic: kinds of it, types of it (two levels), parts of it, terms from its WordNet subject domain, and the Moby thesaurus's related words; Enter/space chooses a word, `g` a whole group, `a` adds the chosen to the word bank (with the topic as a note), `l` looks one up. CLI: `storywheel vocabulary WORD [--json]` |
| Word bank per story or universe; save as atom list | Works | `wordbank.json` in the story or universe folder (choose in the tab); add by hand (comma separated), remove with `d`; "Save as atom list" with a slot (every slot of the built-in lists) writes `<universe>/lists/<slot>/wordbank-<name>.json` tagged with the universe's genres, so the Wheel and Builder roll with it (tested: the words are drawn). Atoms are five words at most: longer entries are skipped and the message says how many |
| Overused words | Works | for a story you pick (default: the current one): the most frequent non-everyday words, counted by stem (walk + walked + walks), with the forms; and words repeated within about 50 words; choosing one lists every place with its scene, line and a snippet; Enter on a place opens the Writer at that line |

## J4. Tests added in batch 2a
| Area | File | Tests |
|---|---|---|
| Ctrl keys, function keys, Shift+Home/End, Ctrl+H, menu keys | `test_notepad.py` | 36 more |
| Word forms | `test_inflect.py` | 71 |
| Dictionary index v2, vocabulary, indirect opposites, inflect CLI | `test_dictionary.py` | 37 (was 31) |
| Writer card | `test_lookup_writer.py` | 24 |
| Words mode | `test_words.py` | 28 |
| Writer hand-over | `test_words_writer.py` | 8 |
| Word bank and overused words | `test_wordbank_overused.py` | 8 |

## J5. Manual test script
1. `storywheel dictionary install` (rebuilds the index). Then try `storywheel lookup running`.
2. In the Writer: press Ctrl+U, Ctrl+W, Ctrl+T, Ctrl+D, F5 (it goes to Words now), F10: nothing should be typed or deleted. Ctrl+Backspace deletes a word. **Ctrl+R opens replace** (tell me if it doesn't in your terminal).
3. Right-click: Undo and Redo with their keys listed.
4. Shift+End / Shift+Home in a long wrapped paragraph, then type.
5. F7 on "running": r should give "sprinting"-style replacements; try a plural, a past tense, a capitalized word, an ALL CAPS word. Enter on a word, then b and n. `/` to filter.
6. F5 in the Writer on a word: Lookup opens on it; pick another word; `u` returns and replaces it.
7. Words > Vocabulary: "kitchen" or "saddle"; choose words; Word bank: save as an atom list; roll in the Builder or Wheel in that universe.
8. Words > Overused on your longest story; Enter on a place opens the Writer there.


Full suite at the end of batch 2a: **1162 passed**.

## Fix after batch 2a: Words crashed on a word that is in two lists
`DuplicateID` while looking up "whisper": a word such as "whispering" is a similar word of two meanings, so two rows had the same
id and Textual refused the list. Every row in the Lookup and Vocabulary lists now has a unique id (a number after the word). I looked up
26 words (whisper, run, light, set, take, bank, left, spring... plus misspellings) and eight vocabulary topics on the real index in
the Words screen without an error, and added tests for a word in several lists and a word in two vocabulary groups. Tag `b2a-fix-duplicate-id`.
That slipped through because the test dictionary was too small to repeat a word across lists; the new tests build exactly that case.

---

# Batch 2b: corrections to Words, appearance and spellcheck

_Tags `b2b-vocab-remove`, `b2b-vocab-learn`, `b2b-wordfreq`, `b2b-mywords`, `b2b-transparent-tui`, `b2b-transparent-writer`, `b2b-appearance-settings`, `b2b-straight-quotes`, `b2b-autocorrect`, `b2b-spell-universe`, `b2b-spell-buffer`, `b2b-spell-default`, `b2b-review`._

**Two things to do:** run `storywheel dictionary install` once more (the index now also holds each meaning's subject kind, schema 3) and add the
frequency package: `pipx inject storywheel wordfreq` (a fresh `pipx install .` brings it). Words says so plainly if either is missing.

## K1. Checklist
| Item | Status | What's missing |
|---|---|---|
| Remove the topic explorer and the word bank | Works | the tab, the CLI `vocabulary`, `dictionary.vocabulary()` and the bank screens are gone. Old word banks (per story and per universe) are moved into My words the first time Words opens (their files are renamed `wordbank.json.migrated`, nothing deleted) and it says how many |
| "Add to this universe's word list" | Works | `w` (or the button) on any word in Lookup and My words opens a small picker for the slot (job, thing, place... with plain hints) and adds the word to `<universe>/lists/<slot>/words-added.json`, tagged with the universe's genres; the Wheel and Builder draw it (tested). Without a universe it says to open one in the Builder |
| Vocabulary tab for learning words | Works | rows are word, part of speech, one-line meaning (WordNet's gloss: the first clause, no parenthetical); Enter / click opens the full Lookup entry; markers ★ Learning, ✓ Known |
| wordfreq, offline; license recorded | Works | `learn.py` reads the Zipf frequency of WordNet's single words (a random sample is checked until twenty fit, ~10 ms). **Licenses (SOURCES.md):** wordfreq's code is Apache-2.0; its data files are CC BY-SA 4.0 (plus the terms of its public sources, listed in its README); storywheel doesn't copy the data, it is a dependency read at run time |
| Filters | Works | difficulty: uncommon (Zipf 3.0-3.8), rare (2.3-3.0), very rare (1.5-2.3), any (1.5-3.8): "house" is 5.7, "lantern" 3.6, "serendipity" 2.7, "sesquipedalian" 1.2; part of speech; subject = WordNet's kinds of meaning in plain words (Animals, Moving, Feelings...) plus the 30 most used subject areas (law, medicine, music...) |
| New batch, Known / Learning, My words, flashcards | Works | "New batch" never shows a word again (seen, known or already being learned are excluded; if the filter runs out it says so); `l` Learning adds to My words with its meaning, `k` Known removes it from the list for good; My words shows meanings (taken from the dictionary for migrated words); flashcards: the word, Space shows the meaning, `k` I know it, `n` next. State is in `~/.storywheel/vocabulary.json` |
| Transparent background (TUI) | Works | the apps use Textual's ANSI theme (`ansi-dark`: every background is `ansi_default`), the title bars are bold accent text instead of blue bars. Checked cell by cell in a terminal (pyte): 99+% of the screen's cells have the terminal's default background in the Wheel, Builder, Settings, Words **and the Writer**; only selected rows, the cursor and scrollbars keep a color |
| Writer: `guibg=NONE` everywhere | Works | Normal, NormalNC/NormalFloat, FloatBorder/Title/Footer, SignColumn, EndOfBuffer, WinSeparator, StatusLine(NC), MsgArea, Pmenu (the chosen entry is shown by reversing, not by a color), the pad windows, sidebar, cards (they link to these), re-applied on ColorScheme |
| Settings > Appearance | Works | Transparent background (default on), Text color, Accent color (names or hex; blank = your terminal's / the usual), Neovide opacity (its own setting, used when transparent is on; 1 otherwise). Changes apply live to Settings itself and to the other modes when they open; the Writer takes them on its next start. The accent is used for titles, borders, scene breaks, search and the chosen item in the Writer |
| Curly apostrophes | Works | typed curly marks become straight as you type (InsertCharPre); pasting straightens them; existing manuscripts are converted once per story with a backup (`.backups/quotes-DATE/`, a message says how many marks); **the export makes them curly** by context ("don't", `"hello"`, `'90s`, `'em`, italics and brackets handled), in the .docx, .md and .txt, the title and the header; setting `export_curly_quotes` (default on). Verified with `spellbadword`: couldn't, I've, we'll, don't, it's pass; couldn’t is flagged. Showing curly marks in the Writer without changing the file is not done (BACKLOG 4c) |
| Autocorrect | Works | i → I, im / i'm → I'm, ive / i've → I've, i'll, i'd, dont/doesnt/didnt/isnt/wasnt/arent/werent/cant/couldnt/wouldnt/shouldnt/hasnt/havent/hadnt/wont, thats, theyre, youre, a few more and common typos (teh, adn...); on the space or punctuation that ends the word, keeping a capital first letter; only whole words; setting `autocorrect` (default on). A fix is skipped if more was typed already (keys queued up), so it can never mangle text |
| Spell list per universe; Add to Dictionary | Works | at Writer start `<universe>/spell/names.utf-8.add` is written from entity names (all types), and the story outline's proper nouns, with possessives ("Glasswater's": Vim doesn't guess them); right-click > Add to Dictionary (also in the F12 menu) saves to `<universe>/spell/en.utf-8.add`, which is never overwritten and is seen by every story in the universe and by no other universe (tested) |
| `set_spell` language on the writing buffer | Works | it set `spelllang` on whatever buffer was current (a card, the sidebar); now spell is set on the writing window and the language and word lists on every manuscript buffer (also when it is opened later) |
| Spellcheck on by default | Works | the default is on. A story whose Writer remembered "off" keeps that until toggled once (BACKLOG 4c) |
| Broader review | Done | BACKLOG.md section 7: every mode's controls with a one-line description of what each does and what is unclear. Nothing there was changed in this batch |

## K2. Tests added in batch 2b
| Area | File | Tests |
|---|---|---|
| Words worth learning, Known/Learning, migration, universe word list | `test_learn.py` | 17 |
| Words screens (Vocabulary, My words, flashcards, slot picker) | `test_words.py` | 11 new, old bank tests removed |
| Quotes | `test_quotes.py`, `test_spelling.py` | 15 + 26 |
| Transparency in a real terminal, themes, Writer highlights | `test_appearance.py` | 16 |

## K3. Manual test script
1. `storywheel dictionary install`, then `pipx inject storywheel wordfreq` (if the second isn't already there).
2. F5 > Vocabulary > New batch: try uncommon / rare / very rare, a part of speech, a subject. Press `l` and `k` on a few; look at My words; try flashcards.
3. In Lookup press `w` on a word, pick a slot, then roll in the Builder/Wheel in that universe.
4. Settings > Appearance: with kitty's `background_opacity 0.85` every mode and the Writer should show the translucency; try a text and an accent color.
5. In the Writer: type `couldn't` and `it’s` (curly); no red underlines; autocorrect `i dont` + space; right-click a name or odd word > Add to Dictionary. Export and look for curly quotes in the .docx.
6. Neovide: Settings > Appearance > Neovide opacity.


Full suite at the end of batch 2b: **1240 passed**.


# Batch 3: clarity and safety

_Tags `b3-autocorrect-words`, `b3-autocorrect-ie`, `b3-q-back`, `b3-footer-modes`, `b3-rename-wheel`, `b3-rename-builder`, `b3-rename-words`, `b3-rename-settings`, `b3-legends`, `b3-writer-menu`, `b3-statusline`, `b3-tools-messages`, `b3-restore-cli`, `b3-restore-writer`, `b3-restore-builder`, `b3-field-history`, `b3-builder-ratings`, `b3-universe-words`, `b3-vocab-startover`, `b3-vocab-add-by-hand`._

## L1. Checklist
| Item | Status | What's missing |
|---|---|---|
| Autocorrect: `wont`, `cant` removed | Works | both are real words and stay as typed |
| Autocorrect: `i.e.` | Works | a lone `i` followed by `.` is left alone (`i.e.`, `e.g.` unchanged); `i. wait`, `i, i; i!` still become `I`; tested |
| `q` = back, `Q` = Quit storywheel (with a confirmation) | Works | every mode, footers and help screens; back returns along a trail of modes (or closes the panel/dialog); the plain-prompt fallback keeps its own `q` |
| Footers label F1-F5 as modes | Works | "Modes: Wheel F1 ..." in each footer; the current mode is greyed out |
| Wheel renames | Works | "Whole characters/places from these: no / sometimes / only", Flavor (button, key `m`, screen), Promote, Use protagonist, Use setting, "Open in the Builder" |
| Builder renames | Works | +Universe; +Character / +Place / +Thing / +Group / +Note follows the tab; +Wheel draft; right-column tab "Entity notes" |
| Settings renames | Works | "Preference for your own names", "Default export type", "Space between paragraphs (terminal)", Default format hint says novel is partial and screenplay a stub |
| Words renames | Works | "Learn this word", "Use in this universe's stories" (buttons, keys, help) |
| On-screen explanations | Works | ▲▼ / ✎ / Roll blanks legend under the Builder card; ▲▼ line in the Wheel; ★ ✓ and difficulty examples in Vocabulary; grey note on why Use in Writer is disabled; `o` shown in the Builder footer as "Universe overview" |
| Writer menu | Works | grouped (Edit, Look up, Story, Leave, More) with titles; "Use Vim keys for now"; Settings (F4) instead of settings.toml; Quit storywheel (Alt+Q) |
| Status line labels | Works | "words: in this scene N · in the story N · written today N of GOAL" |
| One wording for missing tools | Works | `tools.missing()` for dictionary, wordfreq, Neovim, LibreOffice, Neovide, clipboard, python-docx; the Lua clipboard messages repeat the text. Commands assume Debian/Ubuntu + pipx |
| Restore from backups | Works | CLI `storywheel backups list/show/restore`; Writer menu (list + preview, Enter restores after asking); Builder "Backups…" screen (button or `b` on a story). Lists rolling, conversion and migration backups with date, kind, file, words and a preview; a restore first copies the current version to `.backups/restore-...` |
| Builder field history saved | Works | `<universe>/.field-history/<id>.json`; follows the placeholder id rename; removed with the entity |
| Builder ratings change rolls | Works | frame and atoms are kept with a rolled value (also across runs); slot fields apply `atom_bias`; step fields already used the engine's ratings. Hand-written values can be rated but teach nothing |
| Review/remove words added to a universe's lists | Works | Words > Universe words (select, `d` or button) |
| Vocabulary: start over, add by hand | Works | Start over forgets words seen (Known/Learning stay); My words takes typed words (comma separated), meaning from the dictionary; a Known word typed again is learning again |
| Quit key in other places (Alt+Q) | Works | Writer only; the Builder/Wheel use `Q` |

## L2. Tests added in batch 3
| Area | File | Tests |
|---|---|---|
| Autocorrect (wont, cant, i.e.) | `test_spelling.py` | cases updated/added |
| Navigation: q, Q, trail, footers | `test_navigation.py` | 19 |
| Backups (list, preview, restore, CLI) | `test_backups.py` | 8 |
| Restore in the Writer | `test_restore_writer.py` | 8 |
| Missing-tool wording | `test_tools.py` | 10 (4 functions, parametrized) |
| Words: labels, notes, start over, add by hand, universe words | `test_words.py` | 10 new |
| Field history | `test_field_history.py` | 7 |
| Builder ratings | `test_builder_ratings.py` | 4 |
| Existing tests updated | layout stability, mouse, settings, status line, Writer, Builder, Wheel | labels, keys |

## L3. Manual test script
1. Press `q` in Settings, Words and the Builder: you go back to the mode you came from. Press `Q`: "Quit storywheel?" asks first. In the Writer press Alt+Q.
2. Look at each footer: F1-F5 are labelled as modes.
3. Builder: select a story, press `b` (or "Backups…"); pick a backup, read the preview, press `r` and confirm; the manuscript is the old one and the previous version is under `.backups/restore-...`. Do the same from the Writer menu (F12 > Restore from a backup…).
4. Builder: make a character, roll a few fields, scroll the wheel back; quit and reopen; the wheel still goes back. Press ▼ on a generated line several times over a session and watch it come up less.
5. Words: Vocabulary > Start over; My words > type "lantern, gallivant" and Add; Universe words > remove an entry.
6. Rename tour: Wheel (universe panel, buttons under the card, Past stories), Builder tabs, Settings > Universes/Export/Writer.
7. Rename `dictionary` away or run without wordfreq/LibreOffice and read the message: what, why, the command.
8. The Writer: F12 menu groups; the status line labels.

## L4. Known issues / questions
- The commands in `tools.py` assume Debian/Ubuntu.
- Ratings on a hand-written Builder value cannot teach the generator.
- Field-history files are only pruned when an entity is deleted.
- Keys outside the Writer are still not configurable (BACKLOG 3).


Full suite at the end of batch 3: **1311 passed** (1310 in the full run, plus the one menu test fixed after it started and re-run: tests/test_notepad.py 73 passed).


# Batch 4: fixes from use, installing, updating (syncing was built, then removed: see N below)

_Tags `b4-names-case`, `b4-name-completion`, `b4-spell-dictionary`, `b4-spell-lenient`, `b4-spell-marks`, `b4-dictionary-sources`, `b4-version`, `b4-install-script`, `b4-setup`, `b4-update`, `b4-sync-layout`, `b4-sync-conflicts`, `b4-final`. Version 0.4.0._

The full suite before starting (one run, not two partial ones): **1311 passed**.

## M1. Checklist
| Item | Status | What's missing |
|---|---|---|
| Names: proper vs description | Works | entities record `proper: yes/no`; promotion, the Builder's rolls and hand-written names set it; "a locked box" / "the sheriff" stay as descriptions, "Red Draw" is Title Case; the engine only drops "the" before proper names |
| Fix existing entities with a preview | Works | `storywheel names fix UNIVERSE [--apply]`, Builder `F` (a confirm lists every change); finds names that match a generator atom, or a thing with only its first word capitalised. Other odd names stay; mentions in notes/manuscripts aren't rewritten |
| Writer name completion | Works | starts at 3 letters of any word of a proper name (first, last, any), any case, inserts the name's own capitals; the whole name is offered for its first word. Headless-tested; the popup's look is for manual checking |
| Wrong-case names corrected | Works | "gise " → "Gise" like autocorrect (needs the spellchecker on; skips ordinary words such as "hope"); off with autocorrect |
| Spell list from the dictionary | Works | `swdict` (WordNet + Moby words, plural/-s/-ed/-ing/-er/-est), compiled by headless Neovim into `~/.storywheel/spelllang/`, rebuilt when the index changes (also at `dictionary install` and Writer start). Real index: about 330,000 words, compiled in a fraction of a second |
| Lenient setting | Works | `swlenient`: known word + -ing -ed -er -ers -ly -ness -less -ful, un-/re-; a second Neovim spell file added to `spelllang` (Settings > Spelling, default on). A few non-words slip through ("unhouse") |
| Secondary spelling marks | Works | `spell_marks`: subtle (default, dotted grey), all, misspellings only; the Writer's help (F-keys `?`) and Settings say which colour is which |
| Dictionary sources kept; offline rebuild | Works | `~/.storywheel/dictionary-sources/`; an older index is rebuilt from them with a one-line note; download only if missing |
| `--version`, CHANGELOG.md | Works | 0.4.0, one place (`storywheel/__init__.py`); bump it every batch |
| install.sh | Partial | tested as a dry run on pretend machines (bare, old Neovim, new distro Neovim, arm64, URL source); the real downloads (Neovim release, Neovide) weren't run here; the Neovim tarball names are those of recent releases |
| storywheel setup | Works | author details, folders, terminal/Neovide, transparency, dictionary, update remote; remembers answers (`setup_done` in settings.local.toml); `--again`, `--defaults` |
| storywheel update | Works | git fetch + fast-forward only; reinstall with pipx only when the version changed; `post-update` migrations and rebuilds in a new process; shows commits and CHANGELOG entries; `--check`. Tested against local git repositories with a fake pipx |

## M2. Tests added in batch 4
| Area | File | Tests |
|---|---|---|
| Names (flag, promotion, rolls, repair, engine) | `test_names.py` | 8 |
| Name completion and case correction | `test_writer.py` | 3 new |
| Spelling from the dictionary, lenient, marks | `test_spelldict.py` | 8 |
| Kept sources, offline rebuild | `test_dictionary.py` | 3 new |
| Setup and update, version | `test_setup_update.py` | 18 |
| install.sh | `test_install_script.py` | 8 |

## M3. Manual test script
1. `./install.sh --dry-run` on this machine and, if you have one, on a fresh Debian/Ubuntu/Pi: read the plan. Then run it for real there.
2. `storywheel --version`, `storywheel setup` (answer a few), run it again (it asks nothing), `storywheel setup --again`.
3. `storywheel names fix THE-UNIVERSE`: does the list look right? `--apply`, or press `F` in the Builder.
4. In the Writer type `sta` (a lowercase start of a character's name): is it offered? Type a character's name in lowercase and a space: does it get its capital? Type "hope " (no change).
5. Type "gunsmithing", "unlatching": no red line. Try Settings > Spelling > Spelling marks with a lowercase sentence start and a word like "colour".
6. `storywheel dictionary install` on a second machine; move `~/.storywheel/dictionary-sources/` away and run Words after a version bump to see the message.
8. `storywheel update --check` and `storywheel update` against your git remote.

## M4. Known issues / questions
- See BACKLOG.md "Found in batch 4".


Full suite at the end of batch 4 (one run): **1378 passed**.


# N. Sync code removed (0.4.1, tag `b4-remove-sync`)

Syncing between machines is a separate tool outside storywheel, so everything about it was taken out.

## N1. Checklist
| Item | Status | What's missing |
|---|---|---|
| Remove `storywheel sync`, `.stignore`, the Syncthing steps and checks, the setup question, Settings > Sync items, the Builder's conflict notice and `Y` screen | Works | `sync.py`, its tests and the "syncthing" tool message are gone; the setup has 6 questions; Settings has an "Updates" tab with the update remote only; a test fails if the words appear in the code again |
| One-time migration of links into a sync folder | Works | `migrate.migrate_sync_links()` (run at Builder start, by `storywheel migrate`, and after `update`) copies each linked item back into `~/.storywheel`, says so, leaves the sync folder as it was, notes links whose target is gone, and drops the old `sync_folder` setting |
| Keep `settings.local.toml` split and `storywheel update` | Works | the remote is passed to git unchanged (after `--`); a test checks `xps:projects/storywheel` reaches `git fetch` exactly |
| Full suite | Works | see below |

## N2. Tests
`test_sync.py` (15) removed. Added `test_settings_split_migration.py` (6: the settings split, link migration, `migrate` command, nothing left, old setting) and one remote-passed-unchanged test in `test_setup_update.py`; the two sync setup tests were removed.

## N3. Manual test script
1. If you ever ran `storywheel sync link`: `ls -l ~/.storywheel` before and after `storywheel migrate`; the links are real files, the other folder is unchanged.
2. `storywheel sync` now reports an unknown command. Settings (F4) has no Sync tab; Updates holds the git remote.
3. Set the remote to `xps:projects/storywheel` and run `storywheel update --check`.

Full suite after the removal: **1367 passed**.


# Batch 5: backlog cleanup, typewriter fixes, optional grammar checking

_Tags `b5-backlog`, `b5-neovide-arm64`, `b5-kitty`, `b5-grammar-server`, `b5-grammar-check`, `b5-grammar-ui`, `b5-grammar-settings`, `b5-grammar-tests`, `b5-final`. Version 0.5.0._

## P1. Checklist
| Item | Status | What's missing |
|---|---|---|
| Reconcile BACKLOG.md | Works | finished items removed (Vocabulary start over, universe word list review, manual index rebuilds, overused words, restore from backups, the review "Everywhere" list); open ones kept; "Suggested batches" rewritten |
| Neovide on arm64 | Works | Settings shows "not available on arm64" and refuses the switch, setup says so and doesn't ask, the Writer's launch note says so; a self-built Neovide on arm64 is still used |
| kitty launcher | Works | `storywheel kitty [--font --size --line-height --print]`; not run here (kitty isn't installed); options are from kitty's docs |
| Ctrl+I under kitty | Works | checked with the real `CSI 105;5u` bytes sent to a real Neovim: italics toggle, Tab does not; automatic when `KITTY_WINDOW_ID`/kitty TERM is set; a plain terminal keeps it off. Not checked in kitty itself |
| Grammar: local server started/stopped by storywheel | Works | start when turned on, stop when turned off or the Writer closes (tested); nothing runs otherwise (tested). Real LanguageTool/Java not run here |
| `grammar install` / `--from` / `status` | Works | download (fails with the `--from` hint when offline), unzip with checks; status shows Java, version, memory needs and every problem with its fix command; missing Java uses the usual message |
| Check changed paragraphs after a pause; markup stripped, offsets right | Works | per-line, cached by hash (also between sessions); `*` removed; UTF-16 offsets mapped back (emoji, quotes, italics tested); distinct orange underline |
| Right-click: message, fixes, ignore, turn off rule; next key; list | Works | tested in Lua and with a real right-click through a terminal emulator; F10 / Shift+F10 |
| Settings > Grammar | Works | on/off, 13 category switches (picky ones off), turned-off rules, pause, memory limit; ignored items per story (CLI to list/forget) |
| Help note (free rules, no n-gram data) | Works | Writer help, Settings > Grammar, README, `grammar status` |
| Tests with a fake LanguageTool | Works | start/stop, offsets, applying a fix, ignoring, turning a rule off, missing/slow/broken server |

## P2. Tests added in batch 5
| Area | File | Tests |
|---|---|---|
| arm64 / Neovide | `test_arm64.py` | 4 |
| kitty keys and launcher | `test_kitty_keys.py`, `test_kitty_launcher.py` | 2 + 3 |
| Grammar server, install, status, settings | `test_grammar_server.py` | 17 |
| Grammar in the Writer | `test_grammar_writer.py` | 19 |

## P3. Manual test script
1. On the typewriter: `sudo apt install default-jre-headless`, then `storywheel grammar install` (or `--from` a copied zip) and `storywheel grammar status`.
2. Open a story, F12 > Grammar check: turn on. Wait for "grammar: ..." in the status line (up to a minute the first time).
3. Type "He ate alot of pie." and pause: an orange wavy underline under the problem. Right-click it: the message and fixes; apply one. Try Ignore and Turn off this rule.
4. F10 and Shift+F10. Turn it off in the menu: `ps` shows no java process. Leave the Writer with it on: no java process either.
5. Settings > Grammar: switch Style on and see whether fiction trips it constantly.
6. `storywheel kitty --print`, then `storywheel kitty` in kitty; try `--line-height 160`. Italic with Ctrl+I in kitty.
7. On the Pi: Settings > Writer shows Neovide as not available; `storywheel setup --again` doesn't offer it.

## P4. Known issues
See BACKLOG.md "Found in batch 5".

Full suite at the end of batch 5 (one run): **1414 passed**.


# Batch 6: smoother switching, tidier layouts, downloads

_Tags `b6-downloads`, `b6-hub-wip`, `b6-hub`, `b6-layouts`, `b6-narrow`, `b6-layout-tests`, `b6-final`. Version 0.6.0._

## Q1. Checklist
| Item | Status | What's missing |
|---|---|---|
| Downloads: a normal User-Agent everywhere | Works | `download.fetch` sends `storywheel/0.6.0`; the grammar and dictionary downloads use it; tested against local servers that refuse Python's default agent. The real languagetool.org was not contacted from here |
| Fallback to curl or wget when refused | Works | tried on 401/403/406/429/451 and TLS errors, curl first; the message names both tools or says neither is installed; `--from` kept |
| One Textual app, kept screens | Works | Wheel, Builder, Settings, Words are modes of `Hub`; each built once, in place when you return (selection, tab, scroll, typed word, Wheel step) |
| The Writer from the single app, no shell shown | Works | `quiet_suspend`; a real-terminal test counts the alternate-screen escape codes (two leaves in a Writer round trip: Neovim's and the final one). Not seen on a real screen here |
| Lazy loading | Works | a subprocess test shows the Words screen, dictionary, wordfreq, grammar and Settings are not imported when the program starts in the Builder; the Wheel's engine is built when the Wheel is first opened |
| Switch times before and after | Works | see Q2; `--plain` untouched |
| Wheel left column: three boxes | Works | Steps; Universes to draw from (with the "whole characters/places" control on two rows); Past stories (list, then its buttons) |
| Builder left column: Universes and Stories boxes | Works | rows are cut with an ellipsis, never wrapped; the Stories box is titled "Stories in <name>" cut to 30 characters; buttons underneath, as asked (Delete spelled out) |
| Entity card: wider, columns, hanging indent | Works | card ~72 wide at 190 columns (was ~70, but the list column no longer grows with the terminal); labels, values and ▲▼ in columns; a long value wraps under itself. The Wheel's card does the same |
| Card title just "Thing: name" | Works | the hints are in the footer (Roll, Write...) and the help |
| ▲▼ / ✎ / Roll blanks explanation | Works | one line under the card (`▲ ▼ rate · ✎ write it yourself · space fills blanks · ? help`); the full sentence is in the Builder's help |
| No empty row under the tab bar | Works | the tab bar is 2 rows high, and the boxes start right under it (tested) |
| Footer fits | Works | `FitFooter` drops the least important keys (from the end of each screen's list) and keeps F1-F5, q, Q and ?; tested at 190, 150, 120 and 100 columns in every mode. Words opens with the cursor in a box, so Textual hides q/Q there (as before) |
| Check every mode at ~190x50 and smaller | Works | `tools/screens.py`; fixes: Settings and Words boxes and buttons are one line; the Wheel's universe control no longer overflows its box; narrow layouts at 120x34 for the Builder and Wheel |

## Q2. Switch times (milliseconds, this machine: i7-12700H, 190x50, 80 entities; in-process, so they leave out Python start-up)
These include about 24 ms that the test harness itself spends waiting for idle.

| Switch | Before (each mode its own app) | After: first visit | After: coming back |
|---|---|---|---|
| to the Builder | 285-340 | 126-157 | 103-116 |
| to Settings | 360-495 | 460-600 | 84-105 |
| to Words | 205-230 | 310-380 | 52-53 |
| to the Wheel | 220-290 | 370-425 | 57-141 |

Before, a switch also showed your shell between the two apps and rebuilt everything. Coming back is now about 30-90 ms net of the harness. First visits
cost more than before for Settings, Words and the Wheel (they are built once, and the Words screen is imported then). Most of a repeat switch was
Textual re-applying every style rule; that is now skipped unless the look changed (`KeptScreen`). **On a Raspberry Pi** (estimated, not measured: roughly
3-5 times slower per core) coming back should take 0.15-0.4 s and a first visit up to 2 s for Settings; `python tools/measure_switch.py hub` on the Pi
gives the real numbers.

## Q3. Tests added in batch 6
| Area | File | Tests |
|---|---|---|
| The hub (switching, kept place, trail, quit, Writer, lazy loading, speed, real terminal) | `test_hub.py` | 21 |
| Layouts, narrow terminals, footer | `test_layout_batch6.py` | 18 |
| Downloads | `test_download.py` | 9 |
| Existing tests updated | switching, navigation, mouse (arrow clicks find the arrows on screen), layout stability, dictionary | - |

## Q4. Manual test script
1. `storywheel`, then F4, F5, F1, F2 repeatedly: instant, nothing flashes, each mode where you left it. Type a word in Words, leave, return.
2. F3 from the Builder, write a line, F2 back: the screen should clear to the Writer and back without your shell appearing.
3. Look at the Wheel and Builder at your full-screen size, then in a small kitty window (about 120x34): the Builder's right column should come with 6 7 8.
4. `storywheel grammar install` (the 403 should be gone).
5. `python tools/measure_switch.py hub` on the typewriter, and tell me the numbers.

## Q5. Known issues
See BACKLOG.md "Found in batch 6" (no git remote configured, so nothing was pushed; the Pi times are estimates; Switch widgets are still tall).

Full suite at the end of batch 6 (one run): **1462 passed**.


# `storywheel update` fixed (0.6.1, tag `b6-update-fix`)

## R1. Checklist
| Item | Status | What's missing |
|---|---|---|
| Always compare against the installed version | Works | `Installed: X. Source <folder>: Y.` is printed; the old private clone compared with its own remote is gone (it is never created; a test checks) |
| Find the source folder from the install (PEP 610) | Works | `installed_source()` reads `direct_url.json` (editable flag too); falls back to the checkout the code runs from; the `update_remote` setting is now optional, used only for a temporary clone when the folder is gone |
| Fetch and fast-forward the folder's remote; none = just compare | Works | tested with a real "xps" repo and a clone ("typewriter"); dirty and diverged checkouts stop with a message; a remote typed in Settings still reaches git unchanged |
| Reinstall when the versions differ, then migrations and rebuilds | Works | pipx (or pip); tested with a fake runner. New commits with the same version rebuild but do not reinstall; an older source changes nothing; an editable install needs no reinstall |
| Messages say what was compared | Works | exactly the form asked for, plus "Same version", "Already up to date.", and what is fetched |
| Tests | Works | 14 update tests replace the old ones in `test_setup_update.py` (older, same, source ahead after a fetch, folder missing with and without a remote, editable, dirty, diverged, direct_url parsing, fallback) |

## R2. Manual test
On the typewriter: `storywheel update --check`, then `storywheel update`, then `storywheel --version`.

Full suite after the fix: **1469 passed**.


# Batch 7: update by commit, and three genres (0.7.0)

## B1. Checklist
| Item | Status | What's missing |
|---|---|---|
| Update records the commit installed from | Works | `installed-source.json`; written after reinstalling, by `update --record` and by install.sh |
| Reinstall whenever the source commit differs | Works | also for uncommitted changes (fingerprint "+hash"); no record means one reinstall; messages name both commits; `--check` changes nothing |
| Comedy | Works | 28 atom lists + 27 template slots (245 frames); situations and people, not jokes; 85% own material |
| Fantasy | Works | own epic/high content incl. magic-with-cost (`loss`), orders, ruins, old wars; fairy tale untagged; 90% own material |
| Mystery | Works | clues, suspects, alibis, reveals; village names; later beats reuse the clue, suspect and crime via threads; 85% own material |
| Profiles in genres.json, incl. "modern" share | Works | comedy 4/0.2, fantasy 4/0 (general 0.15), mystery 4/0.2 |
| Fidelity, repetition report, lint | Works | see B2 |
| Blends comedy/fairy tale, fantasy/mystery, mystery/western | Works | 85%, 88%, 85% own material, both genres at least 20% of picks, nothing repeated |
| Names with Markov training sets | Works | 85-90 first names and 55-65 surnames per genre, `markov: 0.5` |

## B2. Numbers (200 stories, seed 101)
| Genre | Own material | Lines repeated 5+ times | Entries over 3x fair share | Lint |
|---|---|---|---|---|
| comedy | 85% | 0 | 0 | clean |
| fantasy | 90% | 0 | 0 | clean |
| mystery | 85% | 0 | 0 | clean |
| comedy / fairy tale | 85% | - | - | - |
| fantasy / mystery | 88% | - | - | - |
| mystery / western | 85% | - | - | - |

## B3. Tests added
- `tests/test_genre_content.py` (parameterised by genre and blend): profile, name list sizes, atoms and frames per slot, annotation ratios, per-slot and overall
  fidelity, voice in verbs, repetition, blends; plus fantasy vs fairy tale share no list, fantasy has no modern names, and mystery clues recur in later beats.
- `tests/test_setup_update.py`: 5 new update tests (same-version fix, unrecorded install, dirty source, check-only, `--record`).
- Thresholds relaxed by a few points (and noted) in test_fidelity and test_kinds_floors because every new genre adds lists the wildcard floor can draw from.

## B4. Manual test script
1. `storywheel update --check`, commit a change on xps, `storywheel update` on the typewriter: it should say "Same version number, but the source is at commit …".
2. `storywheel sample comedy -n 3`, `sample fantasy -n 3`, `sample mystery -n 3`: read them for lines that sound wrong.
3. In the Wheel, choose Fantasy, then Fairy tale, and see that they read differently; try Mystery with Western.
4. Pick Mystery and look at the Threads line: the clue should come back in the climax and the twist.

## B5. Known issues
See BACKLOG.md "Found in batch 7".

## B6. Seeded samples (`storywheel sample GENRE -n 5 --seed 7`)

### Comedy
```
1. THE GREAT LOWER TITTERING COMMITTEE DISASTER   (motif: committee)
   comedy · absurd · Story Spine

  * Ferdinald Chiswick, 40, a fussy vicar. Wants a wedding ring and a place in
    the parade before anyone wakes up. Needs to laugh at bossiness instead of
    hiding fear behind it. Flaw: turns every small problem into a plague of
    garden gnomes and blames vanity. Secret: entered a contest for a spot on
    television under a false name without a plan. Rival: the lady of the
    manor.
  * Lower Tittering · the week before Christmas · summer. Landmark: the public
    library. Rumor: the lady of the manor accidentally sold a pair of trick
    scissors in a panic.

    A fussy vicar named Ferdinald accidentally enters the contest for a free
    dinner and, worse, starts winning.

    Once upon a time, in Lower Tittering, a fussy vicar named Ferdinald kept a
    secret: Ferdinald entered a contest for a spot on television under a false
    name without a plan.
    Every day, Ferdinald walked past the public library politely and hoped for
    a blue rosette.
    One day, a postcard from nowhere meant for the lady of the manor landed in
    Ferdinald's hands.
    Because of that, Ferdinald promised the mayor's chain to their ex before
    the cake is cut.
    Because of that, a scheming cousin lied to Ferdinald in a disguise, and a
    borrowed ladder went missing.
    Until finally, Ferdinald gave up the committee to sell the borrowed
    ladder, and Lower Tittering was saved.
    Ever since then, Ferdinald keeps safe a flask of holy oil buried at the
    public library, just in case.

    Twist: Ferdinald had held the borrowed ladder behind the tea urn all
    along, and the lady of the manor knew.
    Threads: message: a postcard from nowhere (One day) · someone: a scheming
    cousin (Because of that) · thing: a borrowed ladder (Because of that)

2. THE UNSUITABLE CAKE   (motif: cake)
   comedy · melancholy · Three-Act Outline

  * Darry Pettle, 81, a busybody tourist board officer. Wants a front-row seat
    and peace for Pennywhistle. Needs to admit the truth about the cake to
    their mother. Flaw: boasts about the reward and hides pride behind
    obsession. Secret: writes letters to their business partner about the fire
    as a fan. Rival: the head of the garden society.
  * Pennywhistle · the talent show night · autumn. Landmark: the picnic area.
    Rumor: a determined newlywed is looking for a stack of parking tickets
    near Pennywhistle.

    Darry, a busybody tourist board officer in Pennywhistle, must find a
    telegram by the first chime or lose the village cup.

    Act I: Setup — Everyone in Pennywhistle knew Darry as a busybody tourist
    board officer, and Darry wanted a front-row seat and peace for
    Pennywhistle.
    Act I: Inciting incident — Darry won a house in Pennywhistle, and a
    disguised old king came to collect.
    Act I: First turn — Darry promised the Best in Show ribbon to their sister
    before the guests leave, and could not turn back.
    Act II: Rising action — Darry was caught between friendship and the
    chairmanship at the worst moment.
    Act II: Midpoint — The disguised old king turned out to know Darry's
    spouse, and Darry defended the head of the garden society very loudly.
    Act II: Crisis — Darry shielded the disguised old king at the last minute,
    and the whole plan collapsed.
    Act III: Climax — The whole of Pennywhistle gathered at the picnic area,
    and Darry flattered the head of the garden society during the fete.
    Act III: Resolution — Pennywhistle laughed about it for years: Darry
    waters the picnic area and keeps an eye on their brother.

    Twist: The head of the garden society and Darry were alike: both secretly
    wanted a good review.
    Threads: someone: a disguised old king (Act I: Inciting incident)

3. LINDA'S FUSSY GOAT   (motif: goat)
   comedy · bittersweet · Story Spine

  * Linda Underwood, 48, a polite hat maker. Wants a vial of dragon's blood
    for their son before the fete opens. Needs to let their neighbor win a
    spot on television for once. Flaw: always says too much about the secret
    meeting and calls it a clear conscience. Secret: lied under oath about the
    third key in a borrowed hat. Rival: the estate manager.
  * Dribbleton · the great marrow summer · spring. Landmark: the cheese shop.
    Rumor: everyone knows the estate manager answered an anonymous letter.

    A polite hat maker in Dribbleton tells one small lie about a gambler's
    ring, and it grows until even the estate manager believes it.

    Once upon a time, Linda, a polite hat maker of Dribbleton, kept a mayoral
    sash under the hat stand and feared boredom.
    Every day, Linda complained to their twin about fibbing and circled the
    cheese shop.
    One day, the goat arrived in Dribbleton and mistook Linda for someone
    important.
    Because of that, Linda filed a chain letter and told no one.
    Because of that, the chain letter was read aloud at the cheese shop, to
    the horror of Linda's one true ally.
    Until finally, the estate manager slipped on the mayoral sash in disguise,
    and the secret was out.
    Ever since then, Linda paints the cheese shop every spring, and avoids
    their father.

    Twist: The mayoral sash had never been lost: Linda's best customer had it
    inside the piano all along.
    Threads: thing: a mayoral sash (Once upon a time) · someone: the goat (One
    day) · message: a chain letter (Because of that)

4. FRESH FORTS FOR SIDNEY   (motif: fort)
   comedy · whimsical · Kishōtenketsu

  * Sidney Nightwatch, 27, an anxious estate agent. Wants an apology from
    their cousin and the last tart. Needs to trust their old teacher with the
    truth about the money. Flaw: swears oaths in anger and keeps exaggeration
    over the quiet life. Secret: once dropped a golden egg at the barber's
    shop during a plague of crows. Rival: the neighbor.
  * Hobbs's Nettleby · this very week · winter. Landmark: the barber's shop.
    Rumor: the barber's shop was built to hide a rented tuxedo.

    To impress Sidney's business partner, Sidney, an anxious estate agent in
    Hobbs's Nettleby, claims to know a gossiping neighbor.

    Ki (introduction) — In Hobbs's Nettleby, Sidney dusted the barber's shop
    in full view, as Sidney did every winter.
    Shō (development) — Sidney kept meaning to return a chocolate fountain,
    and the winter slipped by.
    Ten (twist) — Then Sidney saw the chocolate fountain anew; it had never
    been about an apology from their cousin and the last tart.
    Ketsu (reconciliation) — In the end, Sidney understood the inheritance,
    and dignity mattered more than a free dinner.

    Twist: None of it was real: a failed comedian and Sidney's ex had staged
    it for the mayor's chain.
    Threads: thing: a chocolate fountain (Shō (development))

5. THE LUCKY PORTRAIT   (motif: portrait)
   comedy · eerie · Story Spine

  * Hortimer Fotherham, 60, a blustering choir master. Wants a very old
    fruitcake back, and a place in the parade too. Needs to value honest work
    more than a front-row seat. Flaw: cannot resist a spare key, whatever it
    costs a clear conscience. Secret: told a fortune teller a lie about the
    hidden letter long ago. Rival: the local magician.
  * Great Pudding · present day · autumn. Landmark: the launderette. Rumor: a
    spindle lies buried near the launderette.

    Everyone in Great Pudding believes Hortimer, a blustering choir master,
    owns a jar of pickled onions, and Hortimer cannot afford to say otherwise.

    Once upon a time, Hortimer, a blustering choir master in Great Pudding,
    guarded a brass band tuba and a secret.
    Every day, Hortimer dusted a fridge full of trifle in front of everyone
    and complained about the family curse.
    One day, a forged reference arrived from a very old countess, asking
    Hortimer to come to the launderette.
    Because of that, Hortimer hid a stuffed pike in a dead man's coat, hoping
    nobody would ask.
    Because of that, the very old countess tucked away the brass band tuba on
    a dare, which made matters worse.
    Until finally, the very old countess stood up at the launderette and
    confessed to everything.
    Ever since then, Hortimer gossips about their mother and never fibs about
    the empty grave.

    Twist: The brass band tuba was worth a week at the spa, and the very old
    countess traded away it for a song.
    Threads: thing: a brass band tuba (Once upon a time) · message: a forged
    reference (One day) · someone: a very old countess (One day)
```

### Fantasy
```
1. LAST OATHS OF SHATTERED WATCH   (motif: oath)
   fantasy · absurd · Story Spine

  * Lioba Hart, 46, a cunning insurance adjuster. Wants a royal pardon at the
    crypt of kings. Needs to stop hiding wonder and trust their best customer.
    Flaw: trusts a whispered promise over the realm. Secret: was there when a
    siege began, and said nothing to their cousin. Rival: the inquisitor.
  * Shattered Watch · the order's third age · autumn. Landmark: the crypt of
    kings. Rumor: a storm of ash was summoned by the inquisitor.

    Every guest at the crypt of kings has a motive for an undead uprising, and
    Lioba, a cunning insurance adjuster, must name one before the gates fall.

    Once upon a time, Shattered Watch stood at the wastes' edge, and Lioba, a
    cunning insurance adjuster, kept a barrel of black powder beneath the
    throne.
    Every day, Lioba prayed at the crypt of kings for courage and cursed
    doubt.
    One day, someone broke into the crypt of kings and took a chest of
    tribute.
    Because of that, Lioba bargained with a hunted witch for a lordship and
    gave up their oath.
    Because of that, the hunted witch betrayed Lioba in the king's name, and
    their daughter fell.
    Until finally, the inquisitor fell at the crypt of kings, and Lioba chose
    duty over vengeance.
    Ever since then, Lioba sharpens the barrel of black powder and watches
    over the hunted witch.

    Twist: The Order had sworn to guard the barrel of black powder, not to use
    it: Lioba used it at an army's head anyway.
    Threads: thing: a barrel of black powder (Once upon a time) · someone: a
    hunted witch (Because of that)

2. THE SWORN DRAGON OF CINDERMERE   (motif: dragon)
   fantasy · cozy · Three-Act Outline

  * Gunnar Hartwell, 39, a guarded exiled prince. Wants a rune-stone and a
    blade of legend before the vicar notices. Needs to stop running from
    regret and reconcile with their landlady. Flaw: cannot forgive the dragon
    and calls it the old ways. Secret: carries a mirror of the dead inside a
    hollow statue. Rival: the usurper.
  * Cindermere · the war's fourth winter · spring. Landmark: the old
    wardstone. Rumor: a lost legionnaire is hiding from the usurper at the old
    wardstone.

    After a goblin raid fell on Cindermere, the usurper blamed the Order, and
    Gunnar, a guarded exiled prince, takes up a knight's gauntlet to answer.

    Act I: Setup — In Cindermere, Gunnar was a guarded exiled prince who
    wanted a rune-stone and a blade of legend before the vicar notices and was
    kept from it by bloodlust.
    Act I: Inciting incident — A mercenary captain came to Cindermere at great
    cost bearing a coronation cloak, and asked for Gunnar.
    Act I: First turn — Gunnar swore an oath to a prince in disguise and rode
    for the old wardstone by torchlight.
    Act II: Rising action — At the old wardstone, Gunnar met a captured spy,
    who offered help in the old tongue.
    Act II: Midpoint — The truth about Gunnar's real name came out: the prince
    in disguise guarded the coronation cloak all along.
    Act II: Crisis — The prince in disguise took the coronation cloak, and
    Gunnar had nothing left to bargain with.
    Act III: Climax — The prince in disguise forsook the usurper and fought
    beside Gunnar.
    Act III: Resolution — The songs of Cindermere named Gunnar, and Gunnar
    paid their memory of home in silent dread.

    Twist: Gunnar was the lost heir, and the prince in disguise knew it all
    along.
    Threads: thing: a coronation cloak (Act I: Inciting incident) · someone: a
    prince in disguise (Act I: First turn)

3. TAMSIN AND THE CURSED CURSE   (motif: curse)
   fantasy · gritty · Story Spine

  * Tamsin Whitecliff, 70, a grim tax-reeve. Wants a ball of golden thread and
    a knight's spurs. Needs to let go of despair and keep faith with a sworn
    word. Flaw: always says too much about the deal with the rival house's
    heir and calls it loyalty. Secret: once stashed a set of blueprints for a
    hooded seer. Rival: the high priest.
  * Ashenfall · the age of ruin · winter. Landmark: the ash plains. Rumor: a
    war-chest of gold lies in a sealed crypt, lost with the last king.

    After a blood moon fell on Ashenfall, Tamsin, a grim tax-reeve, sets out
    to carry a talking mirror and pays for it with their sword arm.

    Once upon a time, Tamsin, a grim tax-reeve of Ashenfall, served the Order
    and wanted a ball of golden thread and a knight's spurs.
    Every day, Tamsin patrolled the ash plains before dawn and carried into
    battle a blade of cold iron.
    One day, Tamsin woke to find a bottle of forgotten memories humming under
    a loose flagstone.
    Because of that, Tamsin rode to the ash plains to ask a rival house's
    envoy about the debt.
    Because of that, Tamsin's son dueled them through the storm, and the
    muster was lost.
    Until finally, Tamsin bound the rival house's envoy at the ash plains and
    chose mercy over cowardice.
    Ever since then, the songs of Ashenfall name Tamsin, and Tamsin mourns at
    the ash plains under the black moon.

    Twist: Tamsin had held the blade of cold iron in a dead man's saddlebag
    all along, and the high priest knew.
    Threads: thing: a blade of cold iron (Every day) · someone: a rival
    house's envoy (Because of that)

4. THE BLOODIED MARCH   (motif: march)
   fantasy · tense · Story Spine

  * Lysander Penhall, 36, a dutiful dragon scout. Wants a warhorse for their
    one true ally. Needs to say sorry to their godmother about the lost
    heirloom. Flaw: would sooner unseal a prophecy in verse than admit
    homesickness. Secret: once sacrificed a staff of bone at the lake during a
    county-wide gossip. Rival: the archmage.
  * Highwatch · the age of broken crowns · autumn. Landmark: the lake. Rumor:
    the archmage burned a war-council summons before the war.

    To win the throne, Lysander, a dutiful dragon scout, must slay a reporter
    at the lake before the cake is cut.

    Once upon a time, when the realm was young, Lysander, a dutiful dragon
    scout, served Highwatch and feared tenderness.
    Every day, Lysander sharpened a cursed amulet and had tea with their
    foster sibling.
    One day, an old enemy, a charred knight, rode into Highwatch on the eve of
    battle with a dragon's tooth.
    Because of that, Lysander left behind a throne-room tapestry in a hidden
    vault and rode for the lake at the last minute.
    Because of that, the cursed amulet demanded their voice, and Lysander paid
    it.
    Until finally, Lysander gave up their shadow to hide the cursed amulet,
    and Highwatch was saved.
    Ever since then, Lysander corresponds with the charred knight and keeps
    the old oath.

    Twist: The cursed amulet was a decoy: the archmage had stowed the real one
    in a reliquary.
    Threads: thing: a cursed amulet (Every day) · someone: a charred knight
    (One day)

5. DERYN'S UNBOWED SIEGE   (motif: siege)
   fantasy · melancholy · Three-Act Outline

  * Deryn Highthorn, 21, a loyal oathkeeper. Wants a high council seat and
    peace for Dunmarrow. Needs to put honor before ambition. Flaw: mistakes
    dread for the realm. Secret: owes a disgraced knight a favor from in the
    king's name. Rival: the king's chancellor.
  * Dunmarrow · the old kings' dying · spring. Landmark: the standing stones.
    Rumor: the king's chancellor sold Dunmarrow to a grave-robber.

    A loyal oathkeeper named Deryn inherits a ward-chain of iron and a debt of
    their name to a rogue priestess.

    Act I: Setup — The king's chancellor ran Dunmarrow, and Deryn, a loyal
    oathkeeper, watched with drawn steel.
    Act I: Inciting incident — The ward over the standing stones failed, and a
    silent gardener crawled out in the old tongue.
    Act I: First turn — Deryn staked out the standing stones in a panic and
    stashed a hag-stone in a hollow tree trunk.
    Act II: Rising action — The silent gardener hunted Deryn's sister out of
    prophecy.
    Act II: Midpoint — Deryn won a hard victory over the king's chancellor,
    then lost their oath.
    Act II: Crisis — The hag-stone was destroyed, and Deryn had nothing left
    but loyalty.
    Act III: Climax — Deryn walked out to meet the king's chancellor at great
    cost, with the hag-stone and nothing else.
    Act III: Resolution — Deryn kept the hag-stone in a false-bottomed chest
    as a reminder of vengefulness.

    Twist: The king's chancellor had been Deryn's oldest friend, bound by
    courage.
    Threads: someone: a silent gardener (Act I: Inciting incident) · thing: a
    hag-stone (Act I: First turn)
```

### Mystery
```
1. LOCKED MOTIVES OF NORTH COMBE   (motif: motive)
   mystery · absurd · Story Spine

  * Eustace Ington, 43, a dry pathologist. Wants a fortress at the village
    cinema. Needs to stop hiding homesickness and confide in their cousin.
    Flaw: keeps notes on everyone and trusts envy over forgiveness. Secret:
    keeps a dead man's ledger in the cellar wall and tells no one of the will.
    Rival: the village gossip.
  * North Combe · the house party weekend · autumn. Landmark: the village
    cinema. Rumor: a hired nurse is hiding from the village gossip at the
    village cinema.

    After a hit-and-run in North Combe, the village gossip accuses a lady with
    a veil, and Eustace, a dry pathologist, thinks otherwise.

    Once upon a time, North Combe had never seen an arson at the mill, and
    Eustace, a dry pathologist, liked it so.
    Every day, Eustace wrote down every oddity in North Combe in the fog and
    told no one.
    One day, Eustace was asked to return a railway timetable by midnight, and
    wondered why.
    Because of that, Eustace burned a late telegram and unmasked a preacher
    with a secret.
    Because of that, the arson at the mill grew worse when Eustace dusted for
    prints a muddy bootprint.
    Until finally, Eustace unmasked the village gossip at the village cinema
    with the railway timetable and the family name.
    Ever since then, Eustace avoids their oldest friend and never speaks of
    the third key.

    Twist: The village gossip had planted the railway timetable behind a
    bookcase to frame the preacher with a secret.
    Threads: disaster: an arson at the mill (Once upon a time) · thing: a
    railway timetable (One day) · message: a late telegram (Because of that) ·
    someone: a preacher with a secret (Because of that)

2. THE INQUEST AT BLACKMERE   (motif: inquest)
   mystery · hopeful · Three-Act Outline

  * Reginah Eversley, 20, a wary parish clerk. Wants a will missing a codicil
    and a promotion. Needs to forgive the lost heirloom and keep loyalty.
    Flaw: reaches for a bribe to avoid shame. Secret: once tucked away a
    monogrammed handkerchief for a retired spy under a false name. Rival: the
    insurance investigator.
  * Blackmere · the night of the dinner · winter. Landmark: the tea shop.
    Rumor: a pawn ticket lies under a loose floorboard where no one looks.

    Reginah, a wary parish clerk, receives an anonymous letter from a
    gossiping housekeeper and has until midnight to solve a bin strike.

    Act I: Setup — The insurance investigator ran Blackmere, and Reginah, a
    wary parish clerk, watched at an army's head.
    Act I: Inciting incident — Reginah was called to the tea shop, where a
    blood moon had left a wedding veil behind.
    Act I: First turn — Reginah walked past the tea shop before breakfast and
    stashed a locked jewel case in a sealed crypt.
    Act II: Rising action — Each time Reginah neared a blade of legend, deceit
    pulled the other way.
    Act II: Midpoint — At the war council, Reginah named the traitor, and the
    insurance investigator laughed.
    Act II: Crisis — Reginah learned the true cost of the wedding veil and
    wept at the last minute.
    Act III: Climax — Reginah laid a trap at the tea shop by candlelight,
    baited with a smudged fingerprint card.
    Act III: Resolution — Blackmere changed: Reginah locks up the tea shop and
    trusts a little less their son.

    Twist: The wedding veil was a decoy; a pair of spectacles lay in a teapot.
    Threads: disaster: a blood moon (Act I: Inciting incident) · thing: a
    wedding veil (Act I: Inciting incident)

3. FRESH FORTS FOR VICTOR   (motif: fort)
   mystery · gritty · Kishōtenketsu

  * Victor Elliersley, 26, a methodical police sergeant. Wants a candlestick
    from the gatehouse. Needs to laugh at secrecy instead of hiding longing
    behind it. Flaw: mistakes greed for justice. Secret: was there when a
    locked-room death began, and said nothing to their godmother. Rival: the
    magistrate.
  * Oddington · wartime · spring. Landmark: the gatehouse. Rumor: the
    magistrate paid a con artist to keep quiet behind closed doors.

    Victor, a methodical police sergeant, is the last person to see a
    detective from the Yard, and the first suspect in a series of thefts.

    Ki (introduction) — Every spring, Victor, a methodical police sergeant of
    Oddington, walked past the gatehouse without asking.
    Shō (development) — A quiet trouble came: a bomb threat touched Oddington,
    and Victor called on the magistrate in whispers.
    Ten (twist) — Then Victor saw that the magistrate had wanted a candlestick
    from the gatehouse too, and had hidden panic behind temper.
    Ketsu (reconciliation) — Victor laid down pride at the gatehouse, and the
    case was closed.

    Twist: A fatal fall was staged with great dignity to hide the night of the
    storm.
    Threads: disaster: a bomb threat (Shō (development))

4. THE CASE OF THE WHISPERING WITNESS   (motif: witness)
   mystery · eerie · Three-Act Outline

  * Ottilippa Haversham, 56, a vain undertaker. Wants the reward before the
    police arrive. Needs to give up recklessness and choose the truth. Flaw:
    hides hope behind vanity. Secret: owes the witness a favor from on a dare.
    Rival: the suspicious solicitor.
  * Kingsbridge St Mary · the jazz age · summer. Landmark: the river bridge.
    Rumor: the river bridge is where a retired doctor burned a spare key.

    In Kingsbridge St Mary, Ottilippa, a vain undertaker, is asked to hide a
    stopped watch, and learns that the suspicious solicitor lied about the
    money.

    Act I: Setup — Ottilippa, a vain undertaker of Kingsbridge St Mary,
    noticed their real name and wanted the reward before the police arrive.
    Act I: Inciting incident — Ottilippa found a cufflink buried at the river
    bridge, and knew it did not belong.
    Act I: First turn — With Ottilippa's grandmother watching, Ottilippa
    returned to the river bridge and began.
    Act II: Rising action — A break-in at the vicarage hit Kingsbridge St Mary
    again, and Ottilippa blamed a grieving widow.
    Act II: Midpoint — The cufflink turned up in a locked desk drawer, and the
    grieving widow denied everything.
    Act II: Crisis — Ottilippa learned that their foster sibling had lied
    about the cufflink in plain sight.
    Act III: Climax — Ottilippa laid a trap at the river bridge without a
    witness, baited with the cufflink.
    Act III: Resolution — Ottilippa learned to give up recklessness and choose
    the truth, and Kingsbridge St Mary forgot the false alibi.

    Twist: The alibi the grieving widow offered was false, and the cufflink
    was the proof.
    Threads: thing: a cufflink (Act I: Inciting incident) · someone: a
    grieving widow (Act II: Rising action)

5. DEATH AND THE WATCH AT WYCHWOOD   (motif: watch)
   mystery · tense · Story Spine

  * Gwen Ington, 42, a meticulous head gardener. Wants a pardon before the
    inquest. Needs to admit the truth about the empty grave to their father.
    Flaw: trusts a closed case over mercy. Secret: has been paid by a retired
    colonel over tea to keep quiet. Rival: the jealous neighbor.
  * Wychwood · a foggy November · autumn. Landmark: the quarry. Rumor: a
    missing witness once walked past the quarry after dark.

    When a walking stick turns up in a hatbox, Gwen, a meticulous head
    gardener of Wychwood, uncovers a kidnapping no one remembers.

    Once upon a time, the old war had ended in Wychwood, and Gwen, a
    meticulous head gardener, wanted a pardon before the inquest.
    Every day, Gwen locked up a staff of bone in the fog and noticed
    everything at the quarry.
    One day, a prophecy in verse arrived from a crooked solicitor, asking Gwen
    to come to the quarry.
    Because of that, Gwen pocketed a broken pocket watch on the quiet and
    wrote down the stranger's visit.
    Because of that, the jealous neighbor trailed Gwen under a false name for
    asking about the staff of bone.
    Until finally, Gwen named the crooked solicitor at the quarry too late,
    with the staff of bone as proof.
    Ever since then, Gwen visits the crooked solicitor and studies the staff
    of bone in a flowerpot.

    Twist: Everyone had a motive, but only the crooked solicitor had the staff
    of bone.
    Threads: thing: a staff of bone (Every day) · message: a prophecy in verse
    (One day) · someone: a crooked solicitor (One day)
```


Full suite at the end of batch 7 (one run): **1663 passed**.


# Batch 8 (0.8.0)

## Part A: fixes from the batch 7 samples

| Item | Status | What's missing |
|---|---|---|
| Neighbors in genres.json; floor goes to general and neighbors, a tenth to the rest | Works | all 14 genres name neighbors; a test checks that; off-genre picks in fantasy/comedy/western fell to about 1% of the slot picks |
| Restore the batch 7 fidelity thresholds | Partial | all restored except the western/fairy tale per-slot threshold (-0.02): neither has neighbor lists |
| Era and season agree | Works | `data/seasons.json`; reroll of either field follows |
| Moods lean toward the genre | Works | comedy: under 8% eerie/dreadful/bleak/uneasy; mystery over 15% |
| "traded away it" | Works | `fix_particles` for the particle verbs in the library |
| "a favor from in the king's name" | Works | lint rule and template fixed |
| "crawled out in the old tongue", "paid ... in silent dread" | Works | restricted manner features |
| "Wants a fortress at the village cinema" | Works | lint rule; the want/rumor templates use a thing |
| Scan of a few hundred samples for more | Works | 5 genres x 120 stories (7,895 distinct lines) scanned for particle pronouns, repeated words, chained prepositions; nothing else found that a rule could catch |

Tests added: `tests/test_sentence_polish.py` (9), 3 in `test_kinds_floors.py` (neighbors).


Full suite after part A: **1675 passed**.

## Part B: Words mode tabs

| Item | Status | What's missing |
|---|---|---|
| Remove "My words"; Vocabulary gets a ★ Learning filter and the typed-word entry | Works | the first box switches New words / ★ Learning; flashcards, Known, remove work in the Learning view |
| Genre words tab: genre picker, category picker, search, tags on each row | Works | 21 categories (names, jobs, places, landmarks, things, people, troubles, title words, traits, flaws, wants, needs, secrets, rumors, messages, eras/moods, manners, motives, verbs, premises/twists) |
| Genre words actions: look up, copy, use in Writer, add to universe, generator list | Works | frames (whole phrases) can be browsed but not looked up or used |
| "More like these" for names | Works | first and last names only; uses the generator's Markov name maker trained on the chosen genres |
| Story words replaces Universe words | Works | names, unknown words, look-alikes/near-misses with counts and places; needs the dictionary to find unknown words |
| Story words actions: spelling list, make an entity, rename everywhere (with preview) | Works | |
| Old generator-word review at the bottom of Story words | Works | |
| One plain sentence of help per tab | Works | on each tab and in the help screen |

Tests added: `tests/test_genre_words.py` (14), 10 in `tests/test_words.py` (the old tab tests were moved to the ★ view).

### Manual test for part B
1. F5, then Vocabulary: switch the first box to *★ Learning*; type a word and press Enter.
2. Genre words: pick *Jobs*, press Genres… and tick a second genre; search "smith"; press `e` on a job (goes to the generator list) and on a first name (becomes a character in the Builder).
3. Genre words, *First names*: press `m` for new names; add one with `e`.
4. Story words on a real story: look at the ≈ rows; try `r` on a look-alike (the preview), `s` on a made-up word, `e` on another.

Full suite after part B: **1699 passed**.
