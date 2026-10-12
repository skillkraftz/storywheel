# The Writer
The Writer is Neovim, set up as a full-screen, distraction-free writing room that knows about your story: a centered column, scenes, spelling, names from your universe, word counts and export. By default it is in notepad mode, so it behaves like an ordinary editor: you are always typing and Escape does nothing. Everything is saved as you go, and backups are kept in the story's .backups folder.
## Keys
### writer | Shortcuts you can change (Settings > Keys)
key_italic: Italic: wraps the selection or toggles at the cursor (Ctrl+I too, only if your terminal can send it)
key_bold: Bold: wraps the selection or toggles at the cursor (Ctrl+B always works)
key_scene_break: Insert a scene break (a line holding only ***, shown centered)
key_menu: Open the Writer menu: export, sidebar, toggles, settings, help
key_sidebar: Show or hide the scenes sidebar (Enter jumps, a adds, r renames, J and K move)
key_peek: Peek at the character or place under the cursor (again: scroll a long card)
key_overview: Show the story outline (title, premise, beats, twist, protagonist, setting, rumor)
key_builder: Save and go back to the Builder
key_replace: Find and replace in this file
key_quit: Quit storywheel (asks first)
key_lookup: Dictionary and thesaurus card for the word under the cursor (Enter on a similar word replaces it)
key_lookup_word: Look up a word you type
key_grammar_next: Jump to the next grammar problem
key_grammar_list: List the grammar problems
key_new_scene: Add a new scene (opens the sidebar's scene prompt)
key_invisibles: Show or hide invisible characters (dots for spaces, a mark at paragraph ends)
key_typewriter: Typewriter mode: keep the line you are on in the middle of the screen
key_spell: Spellcheck on or off
key_stats: Word counts: this scene, the story, today
key_copy_manuscript: Copy the whole manuscript as plain text
key_export: Export the manuscript (a script: as a PDF)
key_writer_settings: Edit this story's settings
key_keycheck: Check which keys your terminal sends (is Ctrl+I told apart from Tab?)
key_center: Center the line, or the selected lines, or put them back at the left (stored as >text<)
key_center2: The same as the center key above, on a second key
key_sprint: Start a writing sprint (asks how long, and for an optional word target), or stop the one running
key_versions: Versions of this story: a list of its versions (title, format, status); Enter opens the chosen one in the Writer
key_flip_test: A screenplay's flip test: long action blocks and speeches, camera directions, CUT TO: overuse, the length against the target (a list that jumps to each)
### fixed | Fixed keys
<C-c>: Copy
<C-x>: Cut
<C-v>: Paste (leading spaces and empty lines are dropped)
<C-z>: Undo
<C-y>: Redo
<C-s>: Save now
<C-a>: Select all
<C-f>: Find
<C-g>: Find next
<A-g>: Find previous
<A-j>: Join the selected lines (or the lines around the cursor) into one paragraph
<C-i>: Tab (many terminals cannot tell it from Ctrl+I; Alt+I always works)
<C-m>: Enter
<C-j>: Enter
<C-[>: Escape
<F1>: Go to the Wheel
<F2>: Go to the Builder
<F3>: Open this help (a tab bar: Tab, Shift+Tab, numbers or a click switch tabs)
<F4>: Go to Settings
<F5>: Go to Words, carrying the word under the cursor
<A-m>: The Writer menu (always works)
<C-b>: Bold (always works)
<C-h>: Delete the previous word
<C-BS>: Delete the previous word
<C-Del>: Delete the next word
## Mouse
- Click places the cursor; drag selects; double-click selects a word. The wheel scrolls.
- Right-click opens the everyday menu (Undo, Redo, Cut, Copy, Paste, Look up, fixes on a marked word, Add to dictionary) and More… for the full Writer menu. Only a left click or Enter runs an item; a second right-click, Esc or q closes it and runs nothing.
## With Vim keys on
In Settings > Writer you can turn notepad mode off to get Vim. Every action has a key that works while typing (the Keys tab, the first column); in Vim's Normal mode press Space first for the same actions (shown in [ ] on the Keys tab). Keys and the Space keys are listed only there: see the Keys tab (press 3, or Tab until it opens).
## Versions
If this story has other versions (the same story as a short story and as a screenplay, made in the Builder with V), F12 > Versions of this story, or the versions key (Alt+O; change it in Settings > Keys), lists them with their format and status. Enter saves everything here and opens the chosen one in the Writer. With no other versions it only says so. Space o does the same in Vim mode.

## Writing sprints
F12 menu > Start a writing sprint, or the sprint key (Alt+D; change it in Settings > Keys), asks how long (the default is Settings > Goals > Writing sprint length, 25 minutes) and for a word target if you want one. The status line shows the time left and the words written since it began, with a tick when the target is reached; pasted text does not count. Nothing sounds or pops up. When the time is up one quiet line says how many words, in how long, and the words a minute; the sprint is added to the story's stats.json (a "sprints" list). Press the key again to stop early; leaving the Writer ends a running sprint the same way. SWSprint 25 500 starts one from the command line of Vim mode, and SWSprint stop stops it.
## Completion
While you type a word of three letters or more, the Writer offers matching names from your universe (characters and places, with the name's own capitals) and, after them, the words you added to the universe's dictionary (Add to dictionary in the right-click menu, marked [added]). The same keys pick and accept them; a capital you typed first is kept.
## Grammar (optional)
Off by default. Install once with storywheel grammar install, then turn it on in the Writer menu or Settings > Grammar. A local LanguageTool checks each paragraph you changed, a moment after you stop typing. Problems have an orange wavy underline; right-click one for the message, fixes, Ignore this one and Turn off this rule.
## Leaving
F2 or the Builder key saves everything and goes back to the Builder; F1 the Wheel; F4 Settings. With Vim keys on, :q works too; in notepad mode (the default) you cannot type a : command, so use F2.
## This help
It has tabs: the guide to this story's format (Screenplay, or Writing prose for a short story or a novel), Writing basics, Keys and Export. It opens on the format's guide. Tab and Shift+Tab, the number keys or a click on a tab switch. Scroll with the arrow keys or PgUp/PgDn, search the tab with / (n for the next match), close with F3 again, Esc or q. The other mode keys (F1, F2, F4, F5) close it and switch as usual.
