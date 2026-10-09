# storywheel: feature inventory

Every mode, screen and control, what it is for, which test covers it, and its status. Written during the audit of version 0.20.0
(branch `audit-manual`, 2026-10-08). Nothing in the program was changed for this. Polish 1 (issues 1 to 15) and polish 2 (16 to 36) then fixed
the problems it lists; rows say "was ISSUES #n" where a problem has been fixed since the audit, and the Past stories buttons are now "Use protagonist" and "Use setting".

## How this was checked

| Mark | How |
|---|---|
| **P** | Driven in this session with Textual's pilot inside the real `Hub` app at 200×50 (and 120×40 for the narrow layout), in a scratch library |
| **N** | Driven with `nvim --headless` and the Writer's own config (the same harness as `tests/test_notepad.py`) |
| **T** | Run in a real terminal: Neovim 0.12.5 on a pty, read back with `pyte`, keys and SGR mouse codes sent as bytes (xterm-256color) |
| **C** | The command run in the scratch library |
| **R** | Read in the code and its tests only (needs kitty, LanguageTool, LibreOffice output read by eye, or the real dictionary) |

Status words: **works**; **broken** (does the wrong thing, or does nothing where it should act); **confusing** (works, but the screen,
the label or the help says something else, or it surprises); **duplicated** (the same job is done in two places that can disagree);
**unused** (reachable but leftover, or never reached). Problems are numbered as in ISSUES.md (for example `ISSUES #1`).

Versions here: Python 3.13, Textual 8.2.8, Neovim 0.12.5, LibreOffice present, kitty and LanguageTool absent, dictionary: the test fixture
(`tests/dictfixture.py`), not the real 40 MB index.

---

## Everywhere (all modes)

| Control | Key / mouse | What it is for | Test | Status | Checked |
|---|---|---|---|---|---|
| Mode keys | F1 Wheel, F2 Builder, F3 Writer, F4 Settings, F5 Words | Move between the five modes; everything is saved first. F3 in the Wheel opens the draft's own story (or says it was never sent); the Writer's status line and window title name the story (was ISSUES #4) | test_hub.py, test_navigation.py, test_switching.py | works | P |
| Key of the mode you are in | e.g. F2 in the Builder | Opens that mode's help (and closes it again) | test_help_toggle.py | works | P |
| Help | `?` | The mode's help in tabs (guide, Keys, Topics) with a search box | test_help.py, test_help_tabs.py | works (hint line, wrapped descriptions and duplicate key rows fixed: was ISSUES #21) | P |
| Back | `q` | Back to the mode you came from, or close the dialog | test_navigation.py | works | P |
| Quit | `Q` (Alt+Q in the Writer) | Quit storywheel, after asking | test_navigation.py | works | P |
| Footer | click a key | Every footer: the five modes, ? Help, q Back and up to three keys | test_layout_batch6.py | works (a focused list adds its own keys, so the "three keys" rule is broken in Past stories) | P |
| Title bar | click | Shows mode and what is open; never grows when clicked | test_header.py | works | P |
| Status line (bottom) | — | One-line messages; at start, the kitty note when not in kitty | — | works | P |
| Remember where you were | plain `storywheel` | Reopens the last mode, universe, story, tab, entity, draft, step | test_switching.py | works | R |
| Transparent background | Settings > Appearance | Terminal background shows through every mode | test_appearance.py | works | R |
| Narrow layout | under 150 columns | Thinner side columns; Builder's Story panel takes turns with the cards | test_layout_batch6.py | works; under 150 columns the left column shows a story summary and the outline shows at full width on request (was ISSUES #29) | P |

---

## Mode 1: the Wheel (F1)

### Main screen: left column

| Box / control | Key / mouse | What it is for | Test | Status | Checked |
|---|---|---|---|---|---|
| **Steps** box | Up/Down, Enter or click | The eight steps with ✓ kept, – skipped, ▶ current, · to do, yellow ●, red ✗; jump to one | test_tui.py, test_ui_pass.py, test_mouse.py | works | P |
| **Universes to draw from** checklist | `v` focuses it; Space, Enter or click ticks | Which universes the generator may draw people, places and things from (per draft) | test_universes_wheel.py | works | P |
| "Whole characters/places from these" button | click, or `t` in the panel | no / sometimes / only: whether a whole protagonist or setting can be a universe entity | test_universes_wheel.py | works | P |
| "Belongs to" button | click | The universe this draft will be promoted into | test_promote_ui.py | works | P |
| "Open in the Builder" button | click | Same as F2 (offers to send the draft first) | test_send_to_builder.py | works | P |
| Universe tree (Characters / Places / Things) | Enter opens a group; Enter or click on an entry previews it; `u` uses it | Preview a universe entity and use it as a new candidate | test_universes_wheel.py | works (the help no longer promises e/d/n: was ISSUES #17) | P |
| Entry preview dialog | Enter or `u` use, Esc close | "Use in this story" (nothing kept until k) | test_universes_wheel.py | works | P |
| **Past stories** list | Enter or click opens a draft | Every Wheel draft with date, "5/8" or "done", ⇢universe when promoted | test_promote_ui.py, test_drafts.py | works (titles use the box's width; a copy says "(copy)": was ISSUES #25) | P |
| Past stories: New | button, or `N` anywhere | New draft; asks which universe it belongs to | test_drafts.py, test_universes_wheel.py | works | P |
| Past stories: Del | button or `d` in the list | Delete a draft (asks; moves it to `<home>/.trash`, and says where) | test_ui_pass.py, test_polish1.py | works (was ISSUES #8) | P |
| Past stories: Promote | button or `P` in the list | Bring a past draft into a universe | test_promote_ui.py | works | P |
| Promotion preview: Also start as | Enter or click on a format row | Tick other formats; each makes a sibling version in the same family; entities are made once | test_versions_wheel.py | works | P |
| Past stories: Use protagonist / Use setting | buttons, `p` / `s` in the list | Ask: use that draft's protagonist / setting in the draft you are on (a new candidate, tagged "from a past story"; `k` keeps it), or send it into a universe you choose | test_polish2.py, test_polish1.py, test_universes_wheel.py (`test_send_a_past_storys_protagonist_to_a_chosen_universe`) | works (was ISSUES #13) | P |

### Main screen: the card (middle)

| Control | Key / mouse | What it is for | Test | Status | Checked |
|---|---|---|---|---|---|
| Format question | appears on a new draft; Enter picks, Esc takes your default | What you are writing: Flash fiction, Short story, Novel, Screenplay (feature film or short film) | test_wheel_format.py | works (the plain prompt does not ask) | P |
| Card frame | `F` changes the format | The frame always names the step and the draft's format; a kept structure that no longer fits is swapped, the body dropped, and the screen says so | test_wheel_format.py | works | P |
| Focus line (Genre step) | click, `f` or `e`; Enter picks | One protagonist, two leads, an ensemble, a place, no one; a place or no one skips the Protagonist step | test_focus.py | works (two leads and an ensemble only add a partner or company: BACKLOG.md) | P |
| Ending line (Genre step) | click, `f` or `e`; Enter picks | Any, triumph, bittersweet, tragic, open: steers climax and resolution frames | test_endings.py | works (only general frames carry an ending: BACKLOG.md) | P |
| Hint line | — | One line about the step | test_tui.py | works | P |
| Stale banner + Update / Reroll / Ignore | `a` update, `i` ignore, buttons | A candidate built on a stand-in or on something that changed since | test_inputs.py, test_ui_pass.py | works | P |
| "#N of M" line | — | Which roll of this step you are looking at | test_tui.py | works | P |
| Card rows | Up/Down | The candidate's fields | test_tui.py | works | P |
| Roll the step | Space, Roll button | A new candidate (fields locked by a keep stay) | test_tui.py, test_mouse.py | works | P |
| Keep | `k`, Keep button | Keep the step and move on | test_tui.py | works | P |
| Reroll one field | `f`, Enter, left-click on a row | Reroll only that field | test_mouse.py | works (clicks in the gaps beside ▲▼ do nothing: was ISSUES #24) | P |
| Edit one field | `e`, right-click on a row | Edit that field in a box | test_tui.py, test_mouse.py | works | P |
| Write your own | `w` | One box per field, starting from what is there | test_tui.py | works | P |
| $EDITOR | `E` | Edit the whole step in your editor | test_tui.py | works | R |
| Like / dislike | `+` (or `=`), `-`, click ▲ / ▼ | Rate a line; liked wording comes up more | test_tui.py, test_mouse.py, test_ratings.py | works | P |
| Field history by wheel | scroll over a row | Step through that field's earlier values | test_mouse.py | works | R |
| Format line (structure step) | click, `f` or `e` | Pick short story / novel / feature film / short film | test_storyform.py | works | P |
| Structure line | `f` / click rolls, `e` / right-click picks | A structure that fits the format | test_storyform.py | works | P |
| +Beat / -Beat | buttons, `A` / `X` on the story body | Add or remove a repeatable beat | test_repeatable_beats.py, test_tui.py | works | P |
| Legend line | — | Explains ▲ ▼ | — | works | P |
| Button row | Roll, Keep, Back, Skip, Flavor, +Beat, -Beat, Send to Builder, New draft | Mouse versions of the keys | test_mouse.py, test_send_to_builder.py | works | P |
| Back a step | `b`, Back button | Previous step | test_tui.py | works | P |
| Skip | `x`, Skip button | Skip; later steps invent stand-ins | test_tui.py | works | P |
| Send to Builder / Open in Builder | `B`, button | Promote this draft (or open it in the Builder once promoted) | test_send_to_builder.py | works | P |
| Copy story | `c` | The story so far as plain text to the clipboard | test_ui_pass.py | works | P |
| Copy as new | `C` | Editable copy of a promoted (read-only) draft | test_drafts.py | works | P |
| Save to universe | `u` | Save the showing candidate into the ticked universe (or ask which) | test_universes_wheel.py | works (saves without a preview) | P |
| Remove from universe | `U` | Only says deleting happens in the Builder | test_universes_wheel.py | works (the help says where to remove a value: was ISSUES #18) | P |
| Back to the card | Esc | Focus the card from a list | test_tui.py | works | P |
| Promoted draft is read-only | any edit key | Says so and offers `C` | test_drafts.py | works | P |

### Main screen: history and right column

| Control | Key / mouse | What it is for | Test | Status | Checked |
|---|---|---|---|---|---|
| History list | Tab to it; Enter or click picks a roll | Every roll of the step and what changed | test_tui.py, test_mouse.py | works | P |
| Field history | `h` (again to go back) | One field's earlier values; Enter brings one back | test_tui.py | works | P |
| The story so far | — | Kept content as plain text; problems listed on top | test_ui_pass.py | works | P |

### Wheel dialogs and screens

| Dialog | Keys | What it is for | Test | Status | Checked |
|---|---|---|---|---|---|
| Flavor (mix editor) | `m`; `e`/Space exclude, `+`/`-` boost, `0` unboost, Tab or `l` tags/lists, `r` reset, `q`/Esc close | This story's mix of tags and lists | test_tui.py, test_mix.py | works | P |
| Edit / Write box | Enter next / done, Esc cancel | Edit fields | test_tui.py | works | P |
| Choice list | Enter or click, Esc | Format, structure, universe pickers | test_storyform.py | works | P |
| Send: new or existing | Enter, Esc | First question of promotion (skipped when "Belongs to" is set) | test_send_to_builder.py | works | P |
| Name the new universe | Enter | Defaults to the story's title | test_promote_ui.py | works | P |
| Promote preview | `p` Promote, Enter toggles merge on a yellow duplicate, Esc cancel | Shows every entity and the outline before anything is written | test_promote_ui.py | works | P |
| Quit screen (Q) | `p` into its universe, `n` new, `e` existing, `k`/Enter not now, `d` delete, Esc cancel | Leave with or without promoting | test_promote_ui.py, test_navigation.py | works; `d` asks first, then moves the draft to `.trash` (was ISSUES #8) | P |
| Done screen (last keep) | `Q`/Enter quit, `q`/Esc keep editing | Story finished | test_tui.py, test_navigation.py | works | R |
| Help screen | Tab/Shift+Tab, 1-3, `/` search, Esc/`q`/`?` close | Wheel help | test_help*.py | works (was ISSUES #21) | P |

### The plain prompt (`storywheel --plain`, or no terminal)

| Control | Key | What it is for | Test | Status | Checked |
|---|---|---|---|---|---|
| Prompt loop | Enter/r roll, k, f N, e N, E, w, + / - N, p N, h [N], u / U, b, x, q, ? | The Wheel without the full-screen app | test_tui.py, test_session.py, test_structures.py | works | C |
| Universe question at start | numbers | Which universes to draw from (the TUI no longer asks) | test_universes_wheel.py | works | C |

---

## Mode 2: the Universe Builder (F2)

### Left column

| Box / control | Key / mouse | What it is for | Test | Status | Checked |
|---|---|---|---|---|---|
| **Universes** list | Enter or click opens | Your universes with entity counts | test_builder.py | works | P |
| +Universe | button, `N`, or `n` in the list | New universe (name, optional genres) | test_builder.py | works | P |
| Rename | button, `r` in the list | Rename a universe | test_builder.py | works | P |
| Delete | button, `d` in the list | Delete a universe (asks; to .trash) | test_builder.py | works | P |
| **Stories** list | Enter or click opens the story | The universe's stories (titles only) | test_builder_layout.py | works | P |
| +Story | button, `T` | Story form: title, format, structure, genres, target | test_storyform.py, test_builder_layout.py | works | P |
| Write | button, `w` | Open the story in the Writer | test_switching.py | works; with no story open it asks which story (was ISSUES #15); test_polish1.py | R |
| Export | button, `x` | Export chooser (docx, anonymous docx, odt, pdf, md, txt, fountain; scripts: pdf, anonymous pdf, fdx, fountain) | test_export.py | works; with no story open it asks which story (was ISSUES #15); test_polish1.py | P |
| New version | button, `v` (in the list or anywhere) | Form: title, format, target and a checklist of what to copy; makes a sibling story in the same universe and family | test_versions_builder.py | works | P |
| A family in the Stories list | list | One title row, then a row per format with its words or pages (a story with no versions is one plain row) | test_versions_builder.py | works | P |
| Next / previous version | `]` / `[` | Move between the versions of the open story | test_versions_builder.py | works | P |
| Backups… | button, `b` in the list | List and restore backups (asks; current version kept aside) | test_backups.py | works | P |
| Format, structure… | `m` (in the list or anywhere) | Story form for the open story | test_storyform.py | works | P |
| Delete story | `d` in the Stories list | Delete a story (asks; to .trash) | test_builder.py | works | R |
| **Story** panel: Outline tab | `6`; click selects, wheel scrolls, right-click or `e` edits a row | Title, genre, structure, premise, setting lines, beats, twist, settings, word count | test_outline.py, test_builder_fixes.py, test_polish1.py | works; `f` rolls the beat under the cursor; Space/`R`/`+`/`-`/`n`/`d`/`r`/`c` do nothing here and say so (was ISSUES #3) | P |
| Outline: add / remove beat | `A` / `X` on a beat | Repeatable beats, rolled with the generator | test_outline_beats.py | works | P |
| Outline: Structure row | right-click / `e` | Says "Change the structure with m" | test_polish2.py | works (was ISSUES #19) | P |
| Outline: Settings row | right-click / `e` | Opens Story settings | test_builder.py | works | P |
| Universe overview | `o` | Shows the universe's name, genre leanings, mix changes, notes, contents in the Outline tab | test_builder_layout.py | works | P |
| Scenes tab | `7`; Enter or click opens the Writer at a scene | Scenes with first lines and word counts | test_builder_layout.py | works | P |
| Write here / +Scene | buttons | Writer at the highlighted scene / add a titled scene | test_builder_layout.py | works | P |
| Extra file note + Open / Delete / Ignore | buttons | A file in the manuscript folder storywheel did not make | test_extra_files.py | works | R |
| Notes tab | `8`; type | The story's own notes (`notes.md`), saved as you type | test_builder_layout.py | works | P |
| Story panel on a narrow terminal | `\`, 6 7 8; Esc or 1-5 back | Story panel takes the place of the cards | test_layout_batch6.py | works | P |

### Middle column

| Box / control | Key / mouse | What it is for | Test | Status | Checked |
|---|---|---|---|---|---|
| **Writing** box | — | Today against the goal, streak, week, story and universe totals | test_builder_layout.py | works | P |
| Entity tabs | `1`–`5`, click | Characters, Places, Things, Groups, Notes | test_builder.py | works | P |
| Entity list | Up/Down, click | Entities of that type; Enter goes to the card | test_builder_fixes.py | works | P |
| +Character (+Place…) | button, `n` | New blank entity | test_builder.py | works | P |
| Roll blanks | button, Space | Roll every blank field | test_builder.py | works | P |
| Del | button, `d` | Delete the entity (asks; to .trash; links cleared) | test_builder.py | works | P |
| Card | Up/Down | The entity's fields; ✎ marks write-only | test_builder.py | works (a new card starts on its first row: was ISSUES #23) | P |
| Roll a field | `f`, left-click | Generator fills it, using the universe | test_builder.py, test_fill_rename.py | works | P |
| Write a field | `e`, right-click | Type it, or pick a link / choice from a list | test_builder.py | works | P |
| Field history | scroll over a row | Step through the field's earlier values (kept on disk) | test_field_history.py | works | R |
| Rate | `+` / `-`, click ▲ ▼ | Like / dislike; changes later rolls | test_builder_ratings.py | works | P |
| Reroll whole entity | `R` | All rollable fields again (asks) | test_builder.py | works | P |
| Custom field | `c` | Your own write-only field | test_builder.py | works | P |
| Rename | `r`, or write/roll a new name | Shows every match in notes, outlines, manuscripts first | test_builder.py, test_fill_rename.py | works | P |
| Legend | — | ▲ ▼ rate · ✎ write it yourself · space fills blanks · ? help | — | works | P |
| Entity notes | `E`, click; type | Free notes under the card, saved as you type | test_builder_layout.py | works | P |
| Links | — | Links from and to this entity | test_builder.py | works | P |
| Appears in | — | Stories that mention it | test_builder.py | works | P |

### Builder keys with a dialog

| Key | What it is for | Test | Status | Checked |
|---|---|---|---|---|
| `s` Universe settings | Genre leanings, excluded tags and lists, boosts, the universe's own name boost (typed in boxes) | test_builder.py | works | P |
| `S` Story settings | Font, column width, daily goal, header keyword, indent, typewriter, invisibles, spellcheck, region as choices ("your default (X)" first; on / off; fonts; US / UK), each row saying whether it is the story's own | test_polish2.py | works (was ISSUES #20) | P |
| `G` Your details | Opens Settings on the You tab | test_polish2.py | works (was ISSUES #20) | P |
| `F` Fix names | Names in the wrong capitals, with a preview | test_names.py | works | P |
| `C` Copy manuscript | Plain text to the clipboard | test_ui_pass.py | works; with no story open it asks which story (was ISSUES #15); test_polish1.py | P |
| `P` Start the script | A screenplay's script.fountain from the outline | test_builder_layout.py, test_screenplay.py | works (the message for a prose story says m: was ISSUES #19) | P |
| Rename preview | Enter toggles, `a` all, `n` none, `p` replace, Esc rename only | test_builder.py | works | R |
| Backups dialog | Up/Down, preview, `r` / Enter restore (asks), `q` close | test_backups.py | works | P |
| Story form | Title, Format / Structure / Genres pickers, target; Ctrl+S save, Esc cancel | test_storyform.py | works | P |

---

## Mode 3: the Writer (F3)

Neovim with storywheel's own config. Notepad mode is on by default (always typing; Escape does nothing).

### The screen

| Part | What it is for | Test | Status | Checked |
|---|---|---|---|---|
| Centered column, pad windows either side | Distraction-free text | test_writer.py | works | T |
| Virtual paragraph indent | Every paragraph line shown indented; file has no spaces | test_paragraphs.py | works in the manuscript only; floats are drawn at column 0 (was ISSUES #5); test_polish1.py | T |
| Scene markers shown centered `*  *  *  Title` | `***` / `* * *` / `#` lines, optionally named | test_manuscript.py | works; the cursor never rests on a marker line (was ISSUES #11); test_polish1.py | T |
| Centered lines `>text<` | Shown centered | test_notepad_keys_center.py | works | R |
| Status line | words in this scene · in the story / target · today / goal | test_statusline.py, test_writer.py | works; always counts the writing window, even with a float open (was ISSUES #9); test_polish1.py | T |
| Spelling marks | red wavy, blue, pink, cyan (Settings > Spelling) | test_spelling.py, test_spelldict.py | works | R |
| Name completion | 3 letters of any word of a name | test_writer.py | works | R |
| Autosave and backups | On leaving insert, focus loss, idle; HHMM copies in .backups | test_writer.py | works | R |
| kitty window | Writer in its own kitty window with font/line height | test_kitty_writer.py | works against fakes only | R |

### Keys that never change

| Key | What it does | Test | Status | Checked |
|---|---|---|---|---|
| Ctrl+C / Ctrl+X / Ctrl+V | Copy / cut / paste (paste drops leading spaces and empty lines) | test_notepad.py, test_paragraphs.py | works | N |
| Ctrl+Z / Ctrl+Y | Undo / redo | test_notepad.py | works | N |
| Ctrl+S | Save now | test_notepad.py | works | N |
| Ctrl+A | Select all | test_notepad.py | works | N |
| Ctrl+F, Ctrl+G, Alt+G | Find, next, previous | test_notepad.py | works | N |
| Alt+J | Join selected lines into one paragraph | test_paragraphs.py | works | N |
| Ctrl+B | Bold | test_writer.py | works | N |
| Alt+M | Writer menu | test_notepad.py | works | N |
| Ctrl+H, Ctrl+Backspace / Ctrl+Delete | Delete previous / next word | test_notepad.py | works | N |
| Shift+arrows, Shift+Home/End | Select (Home/End act on the visible line) | test_notepad.py | works | N |
| Enter | New paragraph on the next line | test_writer.py | works | N |
| Tab at a paragraph start | Nothing (says so once) | test_paragraphs.py | works | N |
| F1 / F2 / F4 | Save and go to the Wheel / Builder / Settings | test_writer.py | works | R |
| F3 | This help, in a float | test_help_tabs.py | works; tab bar fits (titles shorten), hints on the border (was ISSUES #7); test_polish1.py | T |
| F5 | Words, carrying the word under the cursor | test_words_writer.py | works | R |
| Unmapped Ctrl letters and F keys | Do nothing (no surprise edits) | test_notepad.py | works | N |
| Unmapped Alt letters | Do nothing (every Alt+letter without a job is silenced; they used to type the letter) | test_polish1.py | works (was ISSUES #10) | T |

### Shortcuts you can change (Settings > Keys), with their defaults

| Key | What it does | Test | Status | Checked |
|---|---|---|---|---|
| Alt+I (Ctrl+I under kitty) | Italic: wraps the selection or toggles at the cursor | test_writer.py, test_kitty_keys.py | works | N |
| Alt+B | Bold | test_writer.py | works | N |
| Alt+S | Scene break (the `scene_marker` setting, `***` by default) | test_writer.py, test_paragraphs.py | works | N |
| F12 | Writer menu | test_menus.py | works (the stray indent is gone: was ISSUES #5) | T |
| F9 | Scenes sidebar | test_writer.py | works from the keyboard: F9 leaves typing, and a jump, add or close puts you back to typing (was ISSUES #1) | T |
| F8 | Peek at the name under the cursor | test_writer.py | works; fields in the card's order, sized by wrapped rows, F8 again to scroll (was ISSUES #12); test_polish1.py | T |
| Ctrl+O | Story outline overlay | test_overview_writer.py | works; layout and doubled openers fixed (was ISSUES #6, #7) | T |
| Ctrl+Q | Save and back to the Builder | test_notepad.py | works (Ctrl+Q is flow control in some terminals) | N |
| Ctrl+R | Find and replace | test_replace.py | works (the hint line fits: was ISSUES #27) | T |
| Alt+Q | Quit storywheel (asks) | test_navigation.py | works | R |
| F7 | Dictionary card for the word under the cursor | test_lookup_writer.py | works | N |
| F6 | Look up a typed word | test_lookup_writer.py | works | N |
| F10 / Shift+F10 | Next grammar problem / list them | test_grammar_writer.py | works against a fake server | R |
| Alt+F | Screenplay flip test | test_screenplay_writer.py | works in a script; in prose says it is for screenplays (was ISSUES #10) | T |
| Alt+N | New scene | test_notepad_keys_center.py | works | R |
| Alt+V / Alt+T / Alt+L | Invisibles / typewriter / spellcheck | test_writer.py, test_notepad_keys_center.py | works | R |
| Alt+W | Word counts | test_notepad_keys_center.py | works | R |
| Alt+Y | Copy manuscript as plain text | test_writer.py | works | R |
| Alt+E | Export (docx; a script: pdf) | test_notepad_keys_center.py | works | R |
| Alt+U | Open this story's settings.toml | test_writer.py | works (edits raw TOML) | R |
| Alt+K | Check what the terminal sends for Ctrl+I | test_writer.py | works | R |
| Alt+C, Ctrl+E | Center the line (stored `>text<`) | test_notepad_keys_center.py | works | R |

### Menus and floats

| Float | Keys / mouse | What it is for | Test | Status | Checked |
|---|---|---|---|---|---|
| Right-click menu | right-click; Undo, Redo, Cut, Copy, Paste, Fix Spelling…, Look Up, Add to Dictionary, More… | Everyday edits; storywheel's own float (`sw/context.lua`): only a left click or Enter runs an item; a second right-click, Esc or `q` closes it; scrolls in a short window | test_menus.py, test_polish1.py (pointer and keys, headless and on a pty) | works (was ISSUES #2) | T |
| Right-click inside a float | right-click | Does nothing (no second menu on the F12 menu or help) | test_polish1.py | works (was ISSUES #2) | T |
| Writer menu (F12 / Alt+M / More…) | 1–9, Up/Down, Enter, click, Esc / `q` | Edit, Look up, Story, Leave, More groups (about 35 items) | test_menus.py, test_menu_keys.py | works (every item shows its own key: 1–9, then letters; was ISSUES #26) | T |
| Help float (F3) | Tab / Shift+Tab / 1–4 / click tab; `/` search; Space / Backspace page; F3, Esc, `q` close | Writer help in tabs | test_help_tabs.py | works; tab bar fits (was ISSUES #7) | T |
| Outline overlay (Ctrl+O) | scroll; Esc, `q`, Ctrl+O close | Title, premise, beats, twist, protagonist, setting, rumor | test_overview_writer.py | works; layout and doubled openers fixed (was ISSUES #6, #7); test_polish1.py | T |
| Scenes sidebar (F9) | Enter / double-click jump, `a` add, `r` rename, `J`/`K` move, `q`/Esc close | Scenes with first lines | test_polish1.py (real F9, Down, Enter, q from Insert mode), test_writer.py | works (was ISSUES #1) | T |
| Peek card (F8) | closes when the cursor moves | An entity's fields and notes | test_writer.py | works; F8 again takes the focus to scroll (was ISSUES #12) | T |
| Dictionary card (F7 / F6) | Enter look up, `b`/Backspace back, `n` forward, `r` replace, `i` insert, `c` copy, `/` filter, `w` word, Tab / arrows / hjkl, Esc / `q` | Meanings and similar words; replace in the same form | test_lookup_writer.py | works (without the dictionary: one short line, no wait for Enter: was ISSUES #28) | N T |
| Find and replace (Ctrl+R) | Enter find next / replace, Tab switch line, Alt+R one, Alt+A all, Alt+C case, Alt+W whole word, Alt+N / Alt+P next / previous, Esc | Literal find and replace in the current file | test_replace.py | works (was ISSUES #27) | T |
| Restore from a backup (menu) | Up/Down, Enter / double-click restore (asks), Esc / `q` | Backups with a preview | test_restore_writer.py | works | R |
| Grammar list (Shift+F10) and grammar right-click menu | Enter / click jump; right-click a problem: message, fixes, ignore, turn off rule | LanguageTool problems | test_grammar_writer.py | works against a fake server | R |
| Key check (Alt+K) | press Ctrl+I | Whether Ctrl+I is told apart from Tab | test_writer.py | works | R |

### Screenplay stories (format Screenplay)

| Control | What it is for | Test | Status | Checked |
|---|---|---|---|---|
| Tab cycles the line's element | action → character → parenthetical → dialogue → transition | test_screenplay_writer.py | works | R |
| Enter after cue / dialogue | Starts dialogue / the next element | test_screenplay_writer.py | works | R |
| Heading and cue capitals, name and location completion | — | test_screenplay_writer.py | works | R |
| Display-only page indents, dimmed (CONT'D) | Approximate the page | test_screenplay_writer.py, test_contd.py | works | R |
| Sidebar by section | Scenes by heading under acts and sequences | test_screenplay_writer.py | works | R |
| "p. N of ~T" in the status line | Page estimate against the target | test_screenplay.py | works | R |

### With Vim keys (notepad mode off, or "Use Vim keys for now")

| Key | What it does | Test | Status | Checked |
|---|---|---|---|---|
| Space n / p / a / i / t / s / w / c / e / S / k / ? | Sidebar, peek, new scene, invisibles, typewriter, spell, counts, copy, export, settings, key check, help | test_keys.py | works | R |
| ]] / [[ | Next / previous scene | test_writer.py | works | R |
| `:SW…` commands | SWBuilder, SWWheel, SWSidebar, SWPeek, SWOutline, SWExport, SWCopy, SWStats, SWHelp, SWSettings, SWKeyCheck, SWSceneBreak, SWJoin, SWLookup, SWReplace, SWInvisibles, SWTypewriter, SWSpell, SWNewScene, SWGrammar… | test_writer.py | works (only reachable with Vim keys) | R |

---

## Mode 4: Settings (F4)

Every box saves as you type (numbers when valid; paths, keys and colours on Enter). Tabs: click, or Tab into the tab bar and use Left/Right.

| Tab | Controls | What it is for | Test | Status | Checked |
|---|---|---|---|---|---|
| You | Legal name, Byline / pen name, Surname for page headers, Address (several lines), Email, Phone | The manuscript's first page | test_settings_mode.py | works | P |
| Goals | Daily word goal | Status line and stats; 0 turns it off | test_settings_mode.py | works | P |
| Appearance | Transparent background (switch), Text color, Accent color | Look of every mode and the Writer | test_appearance.py | works | P |
| Writer | Don't count pasted text, Notepad mode, Open the Writer in its own kitty window, Writer font / font size / line height / padding / window opacity, Space between paragraphs, Scene break in the file, Column width, Show a paragraph indent, Typewriter mode, Show invisibles; kitty and Neovim status line | The writing room | test_settings_mode.py, test_kitty_writer.py | works (kitty items unverified here) | P |
| Spelling | Spellcheck, knows the dictionary's words, accept words built from known words, English spelling (US/UK), Spelling marks, Autocorrect | The spellchecker | test_spelling.py, test_spelldict.py | works | P |
| Grammar | Check grammar, 13 category switches, Turned-off rules, pause (ms), memory limit (MB); Java/LanguageTool status | LanguageTool | test_grammar_server.py | works against a fake server | R |
| Export | Manuscript font, Default format, Default export type, Title in bold, Page header shows, Always anonymous, One space after periods, Curly quotes, Screenplays: automatic (CONT'D), Manuscripts folder | How exports are made | test_paragraph_export.py, test_export_location.py | works ("Default format" offers the four formats by label: was ISSUES #31) | P |
| Keys | One box per Writer shortcut (25), checked for conflicts | Change the Writer's keys | test_keys.py | works | P |
| Universes | Preference for your own names (atom boost) | Default boost for every universe | test_settings_mode.py | works | P |
| Library | Library folder (Enter); app storage and settings file shown | Where universes live (nothing is moved) | test_settings_mode.py | works | P |
| Updates | Git remote to update from | Only used if the install folder is gone | test_setup_update.py | works | R |
| Stats | Summary; Words per day table (`e` edit, `0` reset, with confirms); Per story table (`R` forget, with confirm) | Your writing record | test_settings_mode.py | works | P |
| Help | Search box; results; text | Search every help page | test_help.py | works | P |
| Opening focus | — | The tab bar has the focus when Settings opens; a message is cleared on a tab change | test_polish2.py | works (was ISSUES #30) | P |

---

## Mode 5: Words (F5)

Works offline from the dictionary index. Opened from the Writer it carries the word under the cursor, and "Use in Writer" sends a choice back.

| Tab | Controls | What it is for | Test | Status | Checked |
|---|---|---|---|---|---|
| Lookup | Word box (Enter), Look up, ◀ Back / Forward ▶ (`b` / `n`), filter (`/`); five boxes Meanings, Similar, Opposites, Rhymes (syllables, names and rare words), Related (tabs under 150 columns); Use in Writer (`u`), Learn this word (`a` or `l`), Use in this universe's stories (`w`), Copy (`c`) | Look any word up and pick a better one | test_words.py, test_rhymes.py, test_polish1.py | works; `a`, `l` and `k` act on the word you are on (was ISSUES #14) | P |
| Suggestions | List (For this story / For your characters and places / Fresh alternatives), part of speech, Refresh; Look up, ★ Learn (`l`), Copy, Use in Writer, Add to generator list (`w`) | Words to try | test_suggest.py, test_words.py | works | P |
| Vocabulary | View (New words / ★ Learning / ✓ Known), how rare, part of speech, subject, New batch, Start over, your own word + Add; ★ Learning (`l`), ✓ Known (`k`), Open in Lookup (Enter), Flashcards (`f`), Remove (`d`), Use in this universe's stories (`w`) | Words worth learning | test_learn.py, test_words.py | works | P |
| Flashcards | Space / Enter show meaning, `k` known, `n` / Right next, Esc / `q` stop | Practise ★ words | test_words.py | works | R |
| Story words | Story or whole universe, Names and odd words / Often used, Read again; Add to spelling list (`s`), Make an entity (`e`), Rename everywhere (`r`), Copy; where-list (Enter opens the Writer there); the universe's added words with Remove (`d`) | What your manuscript really uses | test_genre_words.py, test_words.py | works | P |
| Genre words | Part of speech, Genres…, commonness, order, search; Look up, ★ Learn, Copy, Use in Writer, Add to universe (`e`), Add to generator list (`w`), More like these (`m`); From the Wheel lists | Dictionary words ranked by genre fit | test_wordlists.py, test_words.py | works | P |
| Slot picker (`w`) | choose a slot, Add / Cancel | Put a word on the universe's generator list | test_words.py | works | P |

---

## The command line

All run in the scratch library unless marked R.

| Command | What it is for | Test | Status | Checked |
|---|---|---|---|---|
| `story version UNIVERSE/STORY --format KEY [--title T] [--copy outline,notes,seed,genres,structure,manuscript\|none]` | Make another version of a story in another format | test_versions.py | works | C |
| `story show UNIVERSE/STORY --json` | Includes `family`, `siblings` (slugs) and `versions` | test_versions.py | works | C |
| `promote N --also short-film,novel` | Promote a draft and also start it in other formats | test_versions.py | works | C |
| `storywheel` | Reopen where you left off (Wheel if new) | test_switching.py | works | R |
| `storywheel --plain` | The plain prompt Wheel | test_tui.py | works | C |
| `--version` | The version | test_setup_update.py | works | C |
| `new`, `wheel`, `resume [N]` | Wheel on a new / the last / a chosen draft | test_tui.py | works | C |
| `builder`, `settings`, `writer [UNIVERSE STORY]` | Open that mode (writer without a story opens the Builder) | test_switching.py | works (without a terminal they refuse with a message: was ISSUES #32) | C |
| `list [--json]`, `show [N] [--json]` | Wheel drafts | test_ui_pass.py | works | C |
| `draft-export N --out DIR` (alias `export`) | Copy a draft's markdown somewhere | test_ui_pass.py | works (renamed: was ISSUES #33) | C |
| `sample GENRE… -n N [--seed S] [--structure X] [--json]` | Sample stories, nothing saved | test_content.py | works | C |
| `report` | Worst-rated lines and frames | test_ratings.py | works | C |
| `universe [rm KEY N]` | Retired; `migrate` and `universes` do its job | test_polish2.py | removed (was ISSUES #33) | C |
| `universes [new NAME --genres …] [--json]` | List or make universes | test_storage.py | works | C |
| `entity list|show UNIVERSE [ID] [--type T] [--json]` | Entities | test_storage.py | works | C |
| `names fix UNIVERSE [--apply]` | Fix capitals of names | test_names.py | works | C |
| `story list [UNIVERSE]`, `story show UNIVERSE/STORY` | Stories (JSON for the Writer) | test_writer.py | works (was ISSUES #34) | C |
| `promote N --new NAME | --universe SLUG [--dry-run]` | Promote a draft | test_promote.py | works (end of input at the y/N question is a no: was ISSUES #35) | C |
| `manuscript export UNIVERSE/STORY --format F [--out] [--anonymous] [--json]`, `manuscript text …` | Export or print a manuscript | test_export.py | works | C |
| `exports status [--json]`, `exports make UNIVERSE/STORY [--format F] [--json]` | Export records; export in the story's default format | test_exports_cli.py | works | C |
| `backups list|show|restore UNIVERSE/STORY [ID]` | Backups | test_backups.py | works | C |
| `define`, `thesaurus`, `lookup WORD [--json]` | Dictionary | test_dictionary.py | works | C |
| `inflect FORM BASE WORD` | Same form of another word | test_inflect.py | works | C |
| `dictionary install|status|build` | Get and build the index | test_dictionary.py, test_rhymes.py | status works; install not run (network) | C R |
| `grammar install|status|start|stop|rule-off ID|ignored STORY [--clear]` | LanguageTool | test_grammar_server.py | status, rule-off work; install not run | C R |
| `script ensure|start|check|pages|scenes …` | Screenplay helpers | test_screenplay.py | works | R |
| `help [TOPIC] [--tabs] [--format F] [--json] [--width N]`, `help -s WORDS` | Help pages | test_help.py | works | C |
| `migrate` | Old data up to date | test_manuscript.py | works | C |
| `setup [--again|--defaults]` | Questionnaire | test_setup_update.py | works | C |
| `update [--check|--record]`, `post-update` | Update from the install folder | test_setup_update.py | not run (git); `post-update` is no longer listed in `--help` (was ISSUES #34) | R |
| `kitty [--print|--probe|--font|--size]` | storywheel in its own kitty window | test_kitty_launcher.py | `--print` works; rest needs kitty | C R |
