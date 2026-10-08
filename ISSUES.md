# storywheel: issues found in the audit

Every problem found while auditing version 0.20.0 (branch `audit-manual`, 2026-10-08), ranked by how much it gets in a writer's way:
first what can change or lose writing, then what gets in the way while writing, then what misleads, then cosmetic and command-line
problems. Nothing was fixed in the audit session. Polish 1 (branch `polish-1`) then fixed issues 1 to 15; each is marked `[FIXED in <commit>]` in its title. The remaining backlog, ranked the same way, is at the end.

Each issue says where it is (file and function), how to reproduce it, what was seen, and a suggested fix. "Verified" says how it was
reproduced: **pilot** (Textual pilot in the real app, 200×50), **headless** (`nvim --headless` with the Writer's config), **terminal**
(Neovim 0.12.5 on a real pty with xterm mouse codes, read back with pyte), **CLI**, or **code** (read only). The three issues the owner
reported are #2, #5 + #7 and #6.

Reproductions used a scratch library (`STORYWHEEL_HOME`, `STORYWHEEL_LIBRARY`, `STORYWHEEL_MANUSCRIPTS`, `STORYWHEEL_DICTIONARY` all
pointing into a temporary folder).

---

## A. Can change or lose your writing

### 1. [FIXED in 6be13f9] The scene sidebar leaves the Writer in the wrong mode: its keys fail after F9, and afterwards typing runs Vim commands

- **Where:** `storywheel/nvim/lua/sw/sidebar.lua` `M.open`, `M.jump`, `M.close`; F9 is mapped in `sw/init.lua` `M.map_global` and
  `sw/notepad.lua` `M.map_buffer` (`key_sidebar`).
- **Reproduce:** open a story with two scenes in the Writer (notepad mode, the default). Press **F9**. The sidebar opens, the message line
  says `E21: Cannot make changes, 'modifiable' is off`, and Up/Down don't move; Enter gives "Press ENTER or type command to continue".
  Press **Esc** (now the sidebar keys work), **Down**, **Enter** to jump to scene 2, then type `dd`.
- **Seen:** the whole paragraph "The guild hall was dark. Priya went in anyway." was deleted and saved to the file. After **Esc, q**
  (close the sidebar) and `dd`, the first scene's `* * * Opening` line was deleted. Typing `Q` gave `E354: Invalid register name`.
  When the session had remembered the sidebar as open, F9 closed it and the typed letters went into the marker line instead
  ("* * qdd* The Hall"). Ctrl+Z brings the text back.
- **Why:** F9 runs from Insert mode; `M.open` makes the sidebar current without leaving Insert mode (the F12 menu's `open` calls
  `stopinsert`; the sidebar doesn't). After a jump or close, the writing window is current in Normal mode, and notepad mode's
  `ModeChanged *:n` autocmd never fires because the mode doesn't change.
- **Fix:** in `M.open`, `vim.cmd("stopinsert")` (as `sw.menu.open` does). In `M.jump` and `M.close`, after making the writing window
  current, call `require("sw.notepad").insert(true)` when notepad mode is on (as `sw.overview.close` does). Add a test that starts in
  Insert mode and sends the real keys: `<F9><Down><CR>dd` must type "dd" in scene 2, and `<F9>q` + text must type it. Today
  `tests/test_writer.py` calls `sidebar.toggle()` from Normal mode, so it never sees this.
- **Meanwhile:** after F9 press Esc; after using the sidebar press F12 then Esc. (Verified: text typed after that goes into the text.)
- **Verified:** terminal (several runs), headless.

### 2. [FIXED in 52ef67f] Right-click menu: a second right-click, or letting go of the right button over an item, runs that item (reported)

- **Where:** `storywheel/nvim/lua/sw/notepad.lua` `M.setup` (`mousemodel = "popup_setpos"`), `M.popup_menu`, `M.popup_watch`;
  `sw/grammar.lua` `M.map_buffer` (its `<RightMouse>` mapping feeds `<RightMouse>` back to Neovim for the ordinary menu).
- **Reproduce:** in the Writer, press the right button on the text and release it over "Undo" (the menu opens right under the pointer).
  Or open the menu and press the right button on an item.
- **Seen (Neovim 0.12.5, xterm mouse codes):** press on the text, release over Undo: Undo ran. A right press on an item while the menu
  was open closed the menu without running it here; the owner sees it run the item in kitty. A left click runs it, as it should.
  Right-clicking inside the F12 Writer menu (or the help) opens this same Undo/Cut/Paste menu on top of it.
- **Why:** this is Neovim's built-in pop-up menu. Its loop (`pum_show_popupmenu`) treats the right button like the left (a right
  release or right press over an item selects it). No option changes that, and mappings don't run while it is open.
- **Fix:** stop using the native PopUp. Set `mousemodel=extend` and map `<RightMouse>` in the Writer's buffers (manuscript and floats) to
  open a small floating menu of our own at the mouse (the F12 menu, `sw.menu.open`, is already such a float with click handling). In
  that float, `<RightMouse>`/`<RightRelease>` close it and do nothing else; only `<LeftMouse>`/`<LeftRelease>` or Enter run an item.
  The grammar menu (`sw.grammar.menu`) is already a float and can share the code. A float can be tested headlessly with
  `nvim_input_mouse`, which the native menu can't (it never opens without a UI).
- **Meanwhile:** close the menu with Esc or a left click outside it; choose items with a left click.
- **Verified:** terminal (release over an item runs it; menu inside the F12 float); owner's report for the second right-click.

### 3. [FIXED in 6940b28] Builder: f, Space, R, + / -, n and d act on the entity card while you are in the Outline

- **Where:** `storywheel/builder.py` `BuilderScreen.action_roll_field`, `action_roll_blank`, `action_reroll_all`, `action_rate`,
  `action_new_entity`, `action_delete_entity` (only `action_write_field` checks `self.focused is self.top`).
- **Reproduce:** open a story, click in its Outline (or Tab there), press `f`.
- **Seen:** the selected **character** was rolled a new name and renamed ("Renamed 'Sara Lionmane' to 'Nina Quinn'"), with no preview
  because nothing mentioned it. `R` asked to reroll the entity, `+` liked an entity field, `n` made a blank entity, `d` asked to delete
  the entity, all while looking at the outline. The help says the Outline is click-to-select, right-click or `e` to edit.
- **Fix:** when the Outline (or the Scenes list or the story notes) has the focus, these keys should either act on the outline (`f` on a
  beat rolls that beat with `outline.roll_beat`, which `A` already uses; `+`/`-` do nothing) or say "On the outline, e or right-click
  edits a row". Test: focus the outline, press each key, assert the entity file is unchanged.
- **Verified:** pilot.

### 4. [FIXED in 2ea7716] F3 from the Wheel opens an unrelated story

- **Where:** `storywheel/tui.py` `MainScreen._leave` (sends only the first ticked universe), `storywheel/hub.py` `Hub.open_writer`,
  `storywheel/modes.py` `_resolve_story` (falls back to the last Builder story, then the universe's first story).
- **Reproduce:** in the Builder open story "Legacy Labels" in Thornwood. F1. Open the draft "A Curfew for Xavi", which was promoted into
  its own universe "A Curfew for Xavi" and has Thornwood ticked. Press F3.
- **Seen:** the Writer opened `thornwood/legacy-labels`. The Writer shows no title, so you can write into the wrong story without
  noticing.
- **Fix:** from the Wheel, F3 should open the draft's own story when it is promoted (`story["promoted"]`), and otherwise say "This
  draft has no manuscript yet: send it to the Builder (B) first" instead of guessing. Separately, show the story's title somewhere in
  the Writer (the status line or the window title; `titlestring` is "storywheel: writing" today).
- **Verified:** pilot (with `writer.run` replaced to record which story it was given).

---

## B. Gets in the way while writing

### 5. [FIXED in e6880cd] Every Writer float gets the paragraph indent: a stray gutter on the left and ragged wrapping (reported)

- **Where:** `storywheel/nvim/lua/sw/init.lua` `M.start`, the `sw_decorate` autocmd (`TextChanged`/`TextChangedI` →
  `prose.decorate(ev.buf)` for **any** buffer); `sw/prose.lua` `M.decorate` doesn't check what buffer it is given.
- **Reproduce:** F3 (help), Ctrl+O (outline) or F12 (menu) in a prose story, at 120 columns.
- **Seen:** every non-blank line of the help buffer had a 4-space inline virtual-text extmark in the `sw_prose` namespace (42 marks in
  the help, 39 in the outline). The text is pushed 4 columns right, so lines that were wrapped to the window's width overflow: single
  words ("one", "key", "for", "text") drop to the start of the next row; the outline's long beats wrap back to column 0; the F12 item
  "Add the word under the cursor to this universe's dictionary" breaks as "dictionar". The section underlines (`-----`, `───`) are
  indented too.
- **Fix:** in the autocmd callback, return unless `vim.bo[ev.buf].filetype == "storywheel"` (the manuscript), and put the same guard at
  the top of `prose.decorate`. The help, outline, menu, peek, lookup, replace and restore floats then draw at column 0. Add a test:
  open each float and assert no `sw_prose` extmarks in its buffer.
- **Verified:** terminal (screens), headless (extmark counts).

### 6. [FIXED in 822b22c] The outline overlay repeats Story Spine openers: "Once upon a time. Once upon a time, …" (reported)

- **Where:** `storywheel/nvim/lua/sw/overview.lua` `M.lines` / `plain`: it strips `**` from each beat paragraph of `story.md`.
- **Reproduce:** a story whose `## Story Spine` section stores labels, as stories promoted by older versions do:
  `**Once upon a time.** Once upon a time, Ann lived in Redwater.` Press Ctrl+O.
- **Seen:** `1. Once upon a time. Once upon a time, Ann lived in Redwater.`, `2. Every day. Every day, Ann swept the porch.` The Builder's
  Outline shows the same story correctly (`outline.beat_label` drops a label the sentence already starts with), and
  `tests/test_outline.py::test_old_style_outlines_with_doubled_labels_are_cleaned_for_showing` covers the Python side only.
  New promotions don't store labels for the Story Spine, so the owner's older stories are the ones affected.
- **Fix:** don't parse the outline twice. Have `storywheel story show --json` include `outline.rows(story)` (already plain text, labels
  handled), and build the overlay from those rows. Or port the rule: drop a leading `**Label.**` when the body starts with the label.
  Add the legacy fixture to `tests/test_overview_writer.py`.
- **Verified:** headless.

### 7. [FIXED in 5c7cf6e] The help float and the outline overlay are laid out poorly beyond the gutter (reported)

- **Where:** `storywheel/nvim/lua/sw/init.lua` `M.help`, `help_bar`; `sw/overview.lua` `M.open`, `M.lines`.
- **Seen (120×36):** the help's tab bar is wider than the window, so the first tab is cut: `<se   2 Writing basics   3 Keys   4
  Export  Tab / Shift+Tab / 1-4 · / search · F3, Esc, q close`; the open tab's own name is the part lost. Headings are underlined with
  `-----`. In the outline, numbered beats and the premise wrap back to the left edge instead of under their text; the protagonist's
  fields are a plain `Age: 52` list; the rumor starts lowercase. The outline's height counts lines, not wrapped rows, so its last
  lines are below the bottom edge until you scroll.
- **Fix:** after #5: put the key hints in the window's `footer` (Neovim 0.10+) instead of the winbar, and shorten tab titles if the bar
  is still too wide; set `breakindent` with `breakindentopt=shift:3` (or `list:-1` with a `formatlistpat`) so numbered beats and
  wrapped lines hang under their text; size the outline with `nvim_win_text_height` so wrapped lines count. Render the help's headings
  with a highlight instead of `-----`.
- **Verified:** terminal.

### 8. [FIXED in 59a2101] Deleting a Wheel draft is permanent, and the quit box deletes with one key

- **Where:** `storywheel/store.py` `delete` (unlinks the JSON and markdown); `storywheel/tui.py` `MainScreen._story_deleted`,
  `_quit_chosen` (QuitScreen `d`).
- **Reproduce:** Past stories > Del > y; or Q > `d`.
- **Seen:** the files are removed. The confirm says "This can't be undone"; the quit box has no confirm at all. Meanwhile drafts with
  nothing kept are moved to `~/.storywheel/.trash`, everything deleted in the Builder goes to the library's `.trash`, and
  `data/help/backups.md` says "Nothing is destroyed".
- **Fix:** move deleted drafts to `<home>/.trash/` like the empty ones (and say where), and ask before the quit box's `d` deletes.
- **Verified:** pilot, code.

### 9. [FIXED in e498192] The Writer's status line counts the float you are in as "this scene"

- **Where:** `storywheel/nvim/lua/sw/stats.lua` `M.scene` (`buf = buf or vim.api.nvim_get_current_buf()`).
- **Reproduce:** open the help (F3), the outline (Ctrl+O) or find and replace (Ctrl+R).
- **Seen:** "words: in this scene 356" with the help open, 268 with the outline, 0 with find and replace.
- **Fix:** always count the writing window's buffer (`layout.main`), whatever window is current.
- **Verified:** terminal.

### 10. [FIXED in 08a12ae] Alt with an unmapped letter types the letter

- **Where:** `storywheel/nvim/lua/sw/notepad.lua` `M.map_buffer` (disables unmapped Ctrl letters and F keys, not Alt letters).
- **Reproduce:** in a prose story press Alt+F (the flip test key, which only exists in screenplays).
- **Seen:** an "f" was typed at the cursor ("fPriya watched the gate.").
- **Fix:** map every unmapped `<A-a>`…`<A-z>` in Insert and Select mode to nothing, as the Ctrl letters are; for Alt+F in prose, say
  "The flip test is for screenplays."
- **Verified:** terminal.

### 11. [FIXED in d699348] On a scene-break line the raw marker shows, and typing breaks the scene break

- **Where:** `storywheel/nvim/lua/sw/prose.lua` `M.prepare_window` (`concealcursor = "nvc"`, no `i`) and `M.decorate`.
- **Reproduce:** put the cursor on a `* * * The Hall` line (the Writer can reopen there) and type.
- **Seen:** the line shows `* * * The Hall` at the left and the centered `*  *  *  The Hall` at the same time; typed letters go into the
  marker ("* * qdd* The Hall"), which turns it into a paragraph.
- **Fix:** keep the cursor off marker lines in notepad mode (move to the next line on `CursorMovedI`, as the scene-break key already
  leaves you after the break), or conceal in Insert mode too and treat the line as read-only (edits go through the sidebar's rename).
- **Verified:** terminal.

### 12. [FIXED in e7ba35c] Peek (F8) shows fields A to Z and cuts the last ones off

- **Where:** `storywheel/nvim/lua/sw/world.lua` `M.card_lines` (`table.sort(order)`), `M.peek` (`height = math.min(#lines, 24)`,
  `focusable = false`).
- **Seen:** Age, Flaw, Job, Need, Rival, Role, Secret, Trait; Want was missing, because the long Secret wrapped and the height counts
  lines, not screen rows. The card can't be focused to scroll.
- **Fix:** order fields as the schema does (send the field order in `entity list --json`), size the window with
  `nvim_win_text_height`, and let F8 a second time focus it for scrolling.
- **Verified:** terminal.

### 13. [FIXED in 7c8cb9d] Wheel "Use protagonist" / "Use setting" send to a universe, not to this story

- **Where:** `storywheel/tui.py` `MainScreen.story_act` → `_sent_piece`; `StoryList.BINDINGS` (`+Protagonist`, `+Setting`); the buttons
  `st-protagonist`, `st-setting`; `data/help/wheel.md`.
- **Seen:** the button and `p` ask "Send the protagonist of 'Blood and March in Dunmarrow' to which universe?" and save it there. The help
  says "Use its protagonist in the current story" and "p and s send its protagonist or setting to the current story".
- **Fix:** decide which is wanted. If it is the universe: label the buttons "Protagonist → universe…" and fix the help. If it is the
  draft: offer it as a candidate on this draft's protagonist step (the code that "uses" a universe entry, `use_universe_entry`, does
  that already).
- **Verified:** pilot.

### 14. [FIXED in 31efb84] Words: `k` does nothing outside Vocabulary, and `a` learns the wrong word outside Lookup

- **Where:** `storywheel/words_app.py` `WordsScreen.mark` (handles "known" only in Vocabulary), `action_add` → `current_word` (reads
  only the Lookup boxes).
- **Seen:** in Lookup, `k` on a word left the status unchanged. In Genre words, with "dog" highlighted, `a` (shown in the footer as "a
  Learn this word") said "“glad” is ★ Learning": the word highlighted in the hidden Lookup tab. `l` learned "dog" correctly.
- **Fix:** make `a` and `k` use the same "word you are on" lookup as `l` (`gw_learn` etc.) on every tab, or bind them per tab; drop `a`
  from the footer where it doesn't apply.
- **Verified:** pilot.

### 15. [FIXED in 65e7b7b] Builder: Write, Export and Copy quietly use the first story when none is open

- **Where:** `storywheel/builder.py` `BuilderHooks.open_writer`, `export`, `copy_manuscript` (`story = screen.universe.stories()[0]`).
- **Seen:** with the universe overview showing, `C` copied "Blood and March in Dunmarrow" and `x` offered to export it.
- **Fix:** ask which story (a short list), or say "Open a story first (left column)".
- **Verified:** pilot.

---

## C. Misleading text and help

### 16. In-app help pages that say the wrong thing

Seventeen places, listed in `docs/manual.md`, Appendix B (the ones about #1, #2, #3, #8, #13 and #14 were corrected with those fixes). The worst: Past stories `p`/`s` (#13), the universe panel's `e`/`d`/`n` (#17),
"Nothing is destroyed" (#8), heist/adventure/coming-of-age "not written yet" in `genres-and-flavor.md`, `:q` in notepad mode, Words
`k` and `a`. **Where:** `storywheel/data/help/*.md`. **Fix:** correct the free text; consider a test that every key named in free text
(`` `x` ``, "press X") exists in that mode's bindings, which would have caught most of these.

### 17. Wheel help: the universe panel promises e, d and n

- **Where:** `data/help/wheel.md` "The universe panel"; `tui.UniverseEntryScreen` has only Use and Close; `UniverseTree` binds `t` and
  `u`.
- **Seen:** "then Enter or u to use it in this story (as a new candidate), e to edit it, d to delete it (with a confirm), n to add a new
  one". None of e, d, n exist there (they were in the old single-universe panel).
- **Fix:** remove them from the help, or add them (edit/delete in the Wheel would duplicate the Builder; the Builder is the place).

### 18. `U` in the Wheel is described as removing; it only points to the Builder

- **Where:** `tui.MainScreen.action_universe_remove`; its help description `universe_remove` in `data/help/wheel.md`.
- **Fix:** describe it as "Where to remove a value from a universe (the Builder)", or drop the binding and the "u/U" footer label.

### 19. Builder messages that name the wrong key

- **Where:** `builder.py` `BuilderScreen.edit_top` ("The structure was set in the Wheel."), `action_start_script` ("Set its format to
  screenplay (S, story settings) or give it a screen structure.").
- **Seen:** right-click on the Structure row says the first; `P` on a prose story says the second. The structure and the format are
  changed on the story form, `m`.
- **Fix:** "Change it with m (format, structure, genres, target)."

### 20. Story settings (S) and Your details (G) duplicate Settings, with weaker controls

- **Where:** `builder.py` `SETTINGS_FIELDS`, `action_story_settings`, `GLOBAL_FIELDS`, `action_global_settings`.
- **Seen:** `S` is a column of text boxes: font typed freely (Settings offers a choice), yes/no settings typed as `true`/`false` and shown
  as Python's `True`/`False`, the title cut off ("…format, structure and target: m" is lost). It doesn't say which values are the story's
  own and which follow your defaults (only overrides are stored, so leaving a box alone is right, but the box shows the inherited value
  as if it were set). `G` repeats Settings > You without the surname.
- **Fix:** `G` opens Settings on the You tab. `S` gets switches and choices like Settings, marks inherited values ("your default"), and
  a way to clear an override.

### 21. The TUI help screen's layout

- **Where:** `storywheel/helpscreen.py` `HelpScreen` (the hint line), `storywheel/helpdoc.py` (key tables).
- **Seen (200×50):** the hint line is cut at "↑ ↓ PgUp PgDn scroll ·", losing how to close it; a key description that wraps continues
  at the left edge instead of under the description; `+/-` and `-` are two rows (the `+` binding's `key_display` already says "+/-"),
  likewise `u/U` and `U`.
- **Fix:** wrap or shorten the hint line; hang wrapped descriptions; skip a binding whose key already appears in another row's
  `key_display`.

### 22. README.md is out of date in many places

- **Seen:** the Wheel key table ("q quit (asks)", "Mix", "v universe panel"; Q is quit now, the mix is Flavor); "Quitting: q asks Keep
  or delete"; the universe panel "grouped by kind (Protagonist, Setting…)" with "n or [+ New]" and "t or [Use: …]"; the library layout
  shows `manuscript/01-opening.md … one file per scene` and an `exports/` folder per story (now one `manuscript.md`, and exports go to
  ~/Writing); "Edit it in the Builder with G"; the Writer table ("Enter: blank line between", "Alt+S: * * * in the file",
  "Space n", "Space ?": Vim-mode keys presented as the normal ones); "storywheel universe rm KEY N".
- **Fix:** point the README at `docs/manual.md` for use and keep only install, update and development notes there.

---

## D. Small and cosmetic

### 23. Builder: a new card has no highlighted row

`builder.py` `_build_card` keeps `highlighted = None`; `field_key` treats None as row 0. After `n`, `f`/`e` act on the Name with nothing
highlighted, and the first Down only highlights the Name. **Fix:** highlight row 0 when the card is built for a new entity. (pilot)

### 24. Wheel card: a near miss on ▲ ▼ rerolls the field

`tui.CardList.on_click`: ▲ is 3 cells and ▼ 3 cells at the far right of the row; any other click on the row rerolls the field (x = 97
rerolled; 98–103 rate, at 200 columns). The old value is still in the history, but it surprises. **Fix:** widen the target, or make
clicks between the value's end and ▲ do nothing. (pilot)

### 25. Wheel Past stories: titles cut at 22 characters; copies look identical

`tui.MainScreen.refresh_stories` formats `title[:22]` though the box is 46 wide; a copy made with `C` has the same title as its
original, so two rows read "Blood and March in Dun 10-08 done". **Fix:** use the box's width; mark copies ("(copy)"). (pilot)

### 26. The F12 menu numbers only items 1–9

`sw/menu.lua` `M.open`: about 35 items, numbers only on the first nine (all in "Edit"). **Fix:** letters for the rest, or numbers per
group. (terminal)

### 27. Find and replace: the key hint on the bottom border is cut on the left

`sw/replace.lua`: the border shows `╰< replace · Alt+A all · Alt+C case · Alt+W word · Esc close ╯`. **Fix:** shorten it, or widen the
float to fit. (terminal)

### 28. F7 without the dictionary: the message wraps mid-word and waits for Enter

`sw/lookup.lua`: "…To fix it, run:  storywheel dict / ionary install … Press ENTER or type command to continue". **Fix:** a one-line
message ("No dictionary yet: run storywheel dictionary install"), echoed without history so there is no hit-enter prompt. (terminal)

### 29. Narrow Builder: the Story panel's outline is 16 columns wide

`builder.py` CSS `-narrow #left { width: 34 }`: at 120 columns the outline's values wrap to 4–16 characters ("thri", "wond"). The
full-width view needs 6/7/8 or backslash. **Fix:** at narrow widths, show the outline only in the full-width view and a one-line
summary in the column. (pilot)

### 30. Settings opens with nothing focused, and old messages stay

`settings_app.SettingsScreen.on_mount` focuses nothing: the first Tab focuses nothing visible, Left/Right do nothing until the tab bar
has the focus. The status line keeps the last message across tabs (a color error stayed while on Stats). **Fix:** focus the tab bar on
open; clear the status line on tab change. (pilot)

### 31. Settings > Export > Default format offers "screenplay", not the two screenplay kinds

`settings_app.SECTIONS` ("short-story", "novel", "screenplay") while the story form has four formats (`formats.py`: short-story, novel,
feature-film, short-film); "screenplay" here means a feature film (`formats.global_default`). **Fix:** offer the four formats by label.
(code, pilot)

---

## E. Command line and development

### 32. `storywheel builder`, `settings` and `writer` start full-screen without a terminal

`cli_world.cmd_builder`, `cmd_settings`, `cmd_writer` call `modes.run` regardless; with stdin and stdout not a terminal they print escape
codes and wait (`wheel` falls back to the plain prompt). `writer` with no story opens the Builder. **Fix:** refuse with a message when
not a terminal. (CLI)

### 33. Three commands called export, and a leftover `universe` command

`export N --out DIR` (copy a draft's markdown), `exports status|make` and `manuscript export` are different things with near-identical
names. `universe [rm KEY N]` only says the single universe is gone and lists universes (`universes` does that). **Fix:** rename `export`
to `draft-export` (keep the old name as an alias for a while); retire `universe`. (CLI)

### 34. Small CLI wording

"(1 words)", "(2 entities, 1 stories)" in `story list` and `universes`; `post-update` is listed in `--help` as "==SUPPRESS==" (a hidden
subparser still shows). **Fix:** plural helper (`text.plural_n` exists); drop `help=` for `post-update` and remove it from the choices
listing. (CLI)

### 35. `storywheel promote N` crashes at end of input

`cli_world.cmd_promote` calls `input("  Promote? [y/N] ")` without catching `EOFError`; with no input it ends in a traceback. **Fix:**
treat EOF as "no". (CLI)

### 36. Comments, docstrings and notes that drifted

`sw/replace.lua` header says Ctrl+H (it is Ctrl+R); `tests/test_replace.py` docstring says Ctrl+H; `builder.py`'s module docstring
describes a right column that no longer exists; BACKLOG.md says "Nothing is broken that I know of" and still lists the `Space n`
help item that was fixed. **Fix:** update them with the next code change in those files.

---

## The backlog, ranked the same way

From BACKLOG.md, what is still worth doing, most useful to a writer first. "Now" items there are checks for the owner to do by hand
(kitty window, Ctrl+R and Ctrl+O in the real terminal, rhymes install, `install.sh` on a clean machine, LanguageTool); they stay as they
are.

1. **Novel profile** (Partial): Shunn novel title page, chapters on a new page a third down with headings, chapters as the sidebar's
   top level with scenes inside, adding, renaming and reordering chapters. Needed before a novel can be written and sent.
2. **Find and replace across all chapters, and with patterns** (today: the current file, literal text). Matters as soon as a novel has
   several files.
3. **Renaming through the history wheel** should offer the rename only when the wheel stops on a name: today every notch over a Name
   field renames the entity (with the preview each time the old name is mentioned somewhere).
4. **Words typed outside the Writer are not counted** (Partial): count the difference when a manuscript changed on disk.
5. **A draft can only be promoted once** (Partial): decide between re-promoting with a preview and staying one-way (and say so in the
   Wheel).
6. **Configurable keys outside the Writer** (Missing): Wheel, Builder, Settings, the F1–F5 keys, with the same conflict checks.
7. **Changing the library folder** only points at the new place (Partial): offer to move the universes.
8. **Place names that double a word** ("Hollow Hollow"): skip a feature that repeats the adjective. Seen in rolls; a writer notices.
9. **The oddity titles are unreachable** since frames stopped using the floor: give them a small share or remove them.
10. **Look up a word from a Builder field's or a Wheel card's right-click.**
11. **Obsidian `[[wikilinks]]` resolving to entities** (Missing) in notes and outlines, Builder links, "Appears in", peek and completion.
12. **Complete from a universe's added words** in the Writer, like names.
13. **Autocorrect:** capitalize sentence starts; an editable list in Settings.
14. **Screenplays from real use:** scene numbers on the page, moving scenes from the sidebar, Story words and Overused that understand
    Fountain, dual dialogue across pages, a tighter page estimate, more title-page fields, `.docx` scripts, Fade In's "(cont'd)".
15. **From batch 18:** the novel's own help tab, the story form for the universe (genres, exclusions and boosts are still typed with
    `s`), per-format default targets in Settings, a help tab for the Wheel's current step.
16. **Western and fairy tale frames of their own**; a teen protagonist's close people by genre.
17. **Indirect opposites per meaning** in the dictionary (today "fast" can show "mobile").
18. **Compact Settings switches** (Textual's Switch is three lines tall).
19. **Remove the old per-mode apps** (`BuilderApp`, `WordsApp`, `SettingsApp`, `StorywheelApp`) once no test needs them.
20. **Prune `.field-history/`** files; **bundle a smaller dictionary index**.
21. **The world model** (roadmap 4): large; design it when the time comes.

Already done, can leave BACKLOG: **"Peek says 'no entity called X'"**: peek already says "No character, place or thing from this
universe under the cursor." And the "Space n" help note (batch 19, item 6): `writing-prose.md` now says "The sidebar key (see the Keys
tab)".

From "Ideas", the one most likely to help day to day is **writing sprints** (a timer with a word target in the status line).
