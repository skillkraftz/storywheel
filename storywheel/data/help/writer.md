# The Writer
The Writer is Neovim, set up as a full-screen, distraction-free writing room that knows about your story: a centered column, scenes, spelling, names from your universe, word counts and export. By default it is in notepad mode, so it behaves like an ordinary editor: you are always typing and Escape does nothing. Everything is saved as you go, and backups are kept in the story's .backups folder.
## Keys
### writer | Shortcuts you can change (Settings > Keys)
key_italic: Italic: wraps the selection or toggles at the cursor (Ctrl+I too, only if your terminal can send it)
key_bold: Bold: wraps the selection or toggles at the cursor (Ctrl+B always works)
key_scene_break: Insert a scene break (a line holding only ***, shown centered)
key_menu: Open the Writer menu: export, sidebar, toggles, settings, help
key_sidebar: Show or hide the scenes sidebar (Enter jumps, a adds, r renames, J and K move)
key_peek: Peek at the character or place under the cursor
key_overview: Show the story outline (title, premise, beats, twist, protagonist, setting, rumor)
key_builder: Save and go back to the Builder
key_replace: Find and replace in this file
key_quit: Quit storywheel (asks first)
key_lookup: Dictionary and thesaurus card for the word under the cursor (Enter on a similar word replaces it)
key_lookup_word: Look up a word you type
key_grammar_next: Jump to the next grammar problem
key_grammar_list: List the grammar problems
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
<F3>: Open this help
<F4>: Go to Settings
<F5>: Go to Words, carrying the word under the cursor
<A-m>: The Writer menu (always works)
<C-b>: Bold (always works)
<C-h>: Delete the previous word
<C-BS>: Delete the previous word
<C-Del>: Delete the next word
## Mouse
- Click places the cursor; drag selects; double-click selects a word. The wheel scrolls.
- Right-click opens the everyday menu (Undo, Redo, Cut, Copy, Paste, Look up, fixes on a marked word, Add to dictionary) and More… for the full Writer menu.
## Writing
Enter starts a new paragraph on the next line: one line is one paragraph, each shown with an indent. A scene break is *** on a line of its own (typing *** and Enter works too). Tab completes names: type three letters of any word of a character's or place's name, any case. Spelling marks: red wavy means not a word; blue lowercase where a capital belongs; pink a rare word; cyan another region's spelling. Settings > Spelling softens or hides the last three.
## With Vim keys on
In Settings > Writer you can turn notepad mode off to get Vim. In Normal mode, press Space first: n scene sidebar, p peek (also F8), a new scene, i show invisibles, t typewriter mode, s spellcheck, w word counts, c copy the manuscript as plain text, e export, S this story's settings, k check which keys your terminal sends, ]] and [[ next and previous scene, ? this help.
## Grammar (optional)
Off by default. Install once with storywheel grammar install, then turn it on in the Writer menu or Settings > Grammar. A local LanguageTool checks each paragraph you changed, a moment after you stop typing. Problems have an orange wavy underline; right-click one for the message, fixes, Ignore this one and Turn off this rule.
## The scene sidebar
Space n or the sidebar key: Enter jumps, a adds a scene, r renames, J and K move it down and up, q closes.
## Leaving
F2 or the Builder key saves everything and goes back to the Builder; F1 the Wheel; F4 Settings; :q works too.
## This help
Scroll with the arrow keys or PgUp/PgDn, search with / (n for the next match), close with F3 again, Esc or q. The other mode keys (F1, F2, F4, F5) close it and switch as usual.
