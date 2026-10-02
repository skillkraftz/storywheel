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
| Conflicts | Works | a hidden `.storywheel-story` file in each folder holds `universe/story`. A folder owned by another story, or an existing folder with files and no marker, gets the universe name added ("Title (Universe)", then a number). A path equal to, inside or containing the library is refused or skipped, so nothing is written into the library. Same-day re-exports become "... -2", "... -3" (for odt/pdf too, including the .docx they are made from). Characters file systems refuse are dropped from titles |
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

