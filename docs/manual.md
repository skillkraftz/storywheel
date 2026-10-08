# storywheel: the manual

storywheel takes a story from nothing to a manuscript ready to send: roll an idea, grow it into a world, write it, and export it in the
format editors expect. This manual is for writing with it. It describes version 0.20.0.

**Contents**

- [Before you start](#before-you-start)
- [Chapter 1. The Wheel: finding an idea](#chapter-1-the-wheel-finding-an-idea)
- [Chapter 2. The Universe Builder: growing a world](#chapter-2-the-universe-builder-growing-a-world)
- [Chapter 3. The Writer: writing the story](#chapter-3-the-writer-writing-the-story)
- [Chapter 4. Settings](#chapter-4-settings)
- [Chapter 5. Words: finding the right word](#chapter-5-words-finding-the-right-word)
- [Chapter 6. Sending it out: exports](#chapter-6-sending-it-out-exports)
- [Chapter 7. Keeping your work safe: saving, backups, the trash](#chapter-7-keeping-your-work-safe-saving-backups-the-trash)
- [Appendix A. The command line](#appendix-a-the-command-line)
- [Appendix B. Where the in-app help disagrees with this manual](#appendix-b-where-the-in-app-help-disagrees-with-this-manual)

Places where the program currently misbehaves are marked **Watch out**, with what to do meanwhile. The full list is in ISSUES.md.

---

## Before you start

### What you need

- A Linux desktop terminal, full screen, with a mouse. kitty is the best choice (the Writer then gets a window of its own with your
  font and line height); any modern terminal works.
- Python with pipx and Neovim 0.10 or newer (`install.sh` gets both). Everything else is optional and says so when missing: LibreOffice
  (for .odt and .pdf exports), a clipboard tool such as xclip or wl-copy, Java (for grammar checking). pandoc is not needed: the
  .docx is built directly.

### Installing

From the storywheel folder run `./install.sh`. It checks what is missing, installs it, installs storywheel, and runs
`storywheel setup`, a short questionnaire: your name and address for manuscripts, where your library and exported manuscripts go,
the Writer's kitty window, a transparent background, and fetching the dictionary (the only time storywheel uses the network). Run
`storywheel setup` again any time; it asks only what is new (`--again` asks everything). Every answer can be changed later in Settings.

Get the dictionary once with `storywheel dictionary install` (about 40 MB). Without it, Words, the Writer's lookup card and the
spellchecker's big word list don't work, and they tell you so.

### Starting

Type `storywheel`. The first time it opens the Wheel. After that it reopens exactly where you left off: the same mode, universe, story,
tab and entity, or the same Wheel draft and step.

### The five modes

| Key | Mode | What it is for |
|---|---|---|
| **F1** | The Wheel | Roll a story idea piece by piece |
| **F2** | The Universe Builder | Characters, places, things, groups, notes and stories of a world |
| **F3** | The Writer | Write the story (Neovim, set up as a quiet writing room) |
| **F4** | Settings | You, your goals, how everything looks and works |
| **F5** | Words | Dictionary, thesaurus, rhymes, words to learn, words your story uses |

These keys work in every mode, including inside the Writer. Everything is saved before a mode changes.

### Keys that mean the same everywhere

| Key | Means |
|---|---|
| `?` | Help for the screen you are on (tabs: the guide, Keys, Topics; `/` searches every tab) |
| the key of the mode you are in | Also opens that mode's help; press it again to close |
| `q` | Back to the mode you came from, or close the dialog or panel you are in |
| `Q` | Quit storywheel (it always asks; in the Writer it is Alt+Q) |
| `f` | Roll the highlighted field with the generator |
| `e` | Write the highlighted field yourself |
| Space | Roll (the whole step in the Wheel; every blank field in the Builder) |
| `k` | Keep (in the Wheel) |
| `+` / `-` | Like / dislike a value: liked wording comes up more often in later rolls, disliked less |
| Esc | Back to the card, or close a dialog |

And with the mouse, wherever there is a card of fields: **left-click** a field rolls it, **right-click** writes it, the **scroll wheel**
over a field steps through the values it has had, and **▲ ▼** at the end of a line like or dislike it. Buttons do what their keys do.
The footer at the bottom shows the modes, Help, Back and the few keys that matter most on that screen; click any of them.

To select text with the mouse in the Wheel, Builder, Settings or Words, hold Shift while you drag (the app has the mouse otherwise).

### Where your work lives

- **Your library** (default `~/Writing/storywheel`, Settings > Library) holds your universes: each is a folder of plain markdown files
  (characters, places, things, groups, notes) with its stories inside. It is also a valid Obsidian vault; open it there if you like.
- **Your manuscripts folder** (default `~/Writing`, Settings > Export) is where exports go, one folder per story.
- **storywheel's own folder** (`~/.storywheel`) holds Wheel drafts, your settings, ratings and the dictionary.

If you used an older storywheel with one big "universe", the first start moves it into a universe called **Loose Ends** and keeps the
old file as a backup.

---

## Chapter 1. The Wheel: finding an idea

### What it is for

The Wheel rolls a story idea one piece at a time, in eight steps: **genre and mood, structure, title, protagonist, setting, premise, the
story body (the beats of the structure), and a twist.** You roll a step, keep what clicks, reroll or rewrite any single field, and move
on. Later steps read what you kept earlier: the protagonist's name turns up in the premise, the town in the beats, the thing the title
is about in the twist.

### The screen

- **Left, top: Steps.** ✓ kept, – skipped, ▶ where you are, · still to do. A yellow ● means kept but built on a stand-in or on something
  that changed since; a red ✗ means it mentions something that no longer exists. Click a step (or Enter on it) to go there.
- **Left, middle: Universes to draw from.** Tick universes the generator may borrow people, places and things from. Below the list:
  "Whole characters/places from these" (no / sometimes / only), "Belongs to" (the universe this draft will go into), and "Open in the
  Builder". Under them, the ticked universes' characters, places and things.
- **Left, bottom: Past stories.** Every draft, with its date and progress ("5/8", or "done"); ⇢ marks one already brought into a
  universe. Buttons: New, Del, Promote, Prot. → universe, Setting → universe.
- **Middle: the card.** A hint about the step, the candidate's fields (each with ▲ ▼), and buttons: Roll, Keep, Back, Skip, Flavor,
  +Beat and -Beat (on the story body), Send to Builder, New draft.
- **Middle, below: History.** Every roll of this step and what changed in each.
- **Right: The story so far.** What you have kept, as plain text, with any problems listed at the top.

### Rolling a story, step by step

1. Press **N** (or the New draft button) and choose the universe the draft belongs to, or start from where you are.
2. Press **Space** until a genre and mood appeal to you. Press **k** to keep them.
3. **Structure.** The first line is the format: short story, novel, screenplay (feature film) or screenplay (short film). Click it (or
   `f` / `e`) to pick one from a list. The second line is the structure: `f` or a click rolls one that fits the format, `e` or a
   right-click picks one. Keep with **k**.
4. Carry on the same way through title, protagonist, setting, premise, the story body and the twist.
5. Along the way:
   - **One field is wrong?** Arrow to it and press **f** (or click it) to reroll only that field. Press **e** (or right-click) to
     type it yourself. **w** lets you write the whole step, one box per field.
   - **Liked an earlier version?** Scroll the mouse wheel over the field, or press **h** to see that field's own history and Enter on
     the one you want. **h** again shows every roll; Enter on a roll brings it all back.
   - **Want more of a kind of wording?** **+** likes the line, **-** dislikes it (press again to clear). It changes later rolls gently.
   - **Not ready for a step?** **x** skips it; **b** goes back one. If you roll a step before the ones it needs (the body before the
     protagonist), it invents stand-ins and says so on the card.
6. When you keep the last step, a Done box appears: **Q** or Enter quits storywheel, **q** or Esc keeps editing.

### The story body and repeatable beats

On the story body, some beats can repeat (the Story Spine's "Because of that" up to four times; the Three-Act rising action; the
Kishōtenketsu development). Move to one and press **A** (or +Beat) to add another, rolled to follow the others; **X** (or -Beat) removes
one. Things, people, messages and disasters introduced in one beat come back in later ones ("threads"), and the card lists them.

### Stand-ins and stale candidates

A candidate built on something you have since changed shows a yellow banner, for example "Built for Mark; your protagonist is now
Stacie Anderson", with three buttons: **Update** (`a`) swaps what you kept into a copy, **Reroll** rolls again, **Ignore** (`i`) hides
the banner and leaves the candidate as it is.

### Flavor: what this story leans toward

Press **m** (or the Flavor button). You see every tag with its genre default, your boost and its weight now; Tab (or `l`) switches to
the lists. **e** or Space excludes the highlighted tag or list from this story, **+** / **-** boost it more or less, **0** removes the
boost, **r** resets to the genre defaults, **q** or Esc closes and saves. Flavor changes only this story and only future rolls.

### Drawing on your universes

Tick a universe in the panel (click it, or `v` then Space). From then on its characters, places and things turn up in rolls, more
often than ordinary ones. "Whole characters/places from these" decides whether a whole protagonist or setting may be one of the
universe's: **no**, **sometimes** (about a third of rolls) or **only**. To use a particular one, open its group in the panel, Enter on
it to preview, then Enter or `u` ("Use in this story"): it becomes a new candidate on its step; nothing is kept until you press k.

**u** on the card saves the candidate you are looking at into a universe (the ticked one, or it asks which). **U** only reminds you that
removing something from a universe is done in the Builder.

### Copying, editing outside, rating

- **c** copies the story so far as plain text to the clipboard.
- **E** opens the whole step in your $EDITOR.
- **Esc** returns to the card from any list; Tab moves between the lists (steps, card, history).

### Sending a story to the Builder (promotion)

When the idea is worth growing, bring it into a universe:

1. Press **B** or the Send to Builder button. (F2 from a draft with kept steps offers the same; so does Q when you leave.)
2. If "Belongs to" names a universe it goes straight there. Otherwise choose **a new universe** (named after the story; change the name
   if you like) or **an existing universe**.
3. A preview lists everything that will be made: the protagonist becomes a character, the rival a character, the town and the
   landmark places, the title's motif a thing or a character, each thread a character, thing or note, and the title, premise, beats
   and twist the story's outline. In an existing universe, same-name entities are shown in yellow: Enter switches between merging
   (blank fields filled in, nothing overwritten) and making another. **p** promotes; Esc cancels and nothing is written.
4. You land in the Builder with the new story open.

A promoted draft stays in Past stories (marked ⇢) and becomes read-only in the Wheel, because the Builder now holds the real story.
**C** makes an editable copy as a new draft.

### Past stories

Enter (or a click) opens a draft; the one you leave is saved. **d** (or Del) deletes a draft after asking. **P** (or Promote) brings a
past draft into a universe. **p** and **s** (the "Prot. → universe" and "Setting → universe" buttons) copy that draft's protagonist or setting
**into a universe you choose** (not into the draft you are on).

Deleting a draft (Del, `d`, or `d` in the quit box) always asks first and moves it to `.trash` in your storywheel home (the message says
where), so it can be got back by hand. (Fixed: ISSUES #8.)

### Leaving

- **q** goes back to the mode you came from (the draft is saved).
- **Q** asks what to do with this draft: bring it into its universe (`p`), a new universe (`n`), an existing one (`e`), not now (`k`
  or Enter: keep it as a draft), delete it (`d`), or cancel (Esc). After it closes, storywheel prints the story and the command to
  resume it.

### The plain version

`storywheel --plain` runs the Wheel as a simple prompt (it is also used when there is no terminal). The keys are the same letters:
Enter rolls, `k` keeps, `f 3` rerolls field 3, `e 3` edits it, `p 2` picks roll #2, `h` lists rolls, `h 3` field 3's values, `+` / `-`
rate, `u` / `U` universe, `b` back, `x` skip, `q` save and quit, `?` help.

---

## Chapter 2. The Universe Builder: growing a world

### What it is for

The Builder is where a kept idea becomes a world: the people, places, things, groups and notes of a universe, and the stories set in
it. It is meant to feel like a desk of index cards that the generator helps you fill in.

### The screen

- **Left, top: Universes.** Your universes with their entity counts; +Universe, Rename, Delete.
- **Left, middle: Stories.** The open universe's stories. +Story, Write, Export, Backups….
- **Left, bottom: the Story panel**, with three tabs:
  - **Outline** (key `6`): the open story's title, genre, structure, premise, setting lines, each beat, the twist, its settings and word
    count. With no story open it shows the universe overview (press **o** to get back to it).
  - **Scenes** (`7`): every scene with its first line and word count; Write here, +Scene.
  - **Notes** (`8`): the story's own notes, saved as you type.
- **Middle, top: Writing.** Words today against your goal, your streak, this week, the story's and the universe's totals.
- **Middle: tabs** for Characters, Places, Things, Groups and Notes (keys `1`–`5`), the list of that type with +Character (or +Place…),
  Roll blanks and Del, and the selected entity's **card**. Under the card: its own notes, its links both ways, and the stories it
  appears in.

On a terminal narrower than 150 columns the Story panel takes the place of the cards when you press 6, 7, 8 or backslash; Esc or 1–5
bring the cards back.

### Making a universe

Either send a story from the Wheel (Chapter 1), or press **N** (or +Universe) and give it a name and, if you like, genres. Rename and
Delete are buttons, or `r` and `d` with the Universes list focused. Deleting asks, then moves the universe to the library's `.trash`.

### Filling in a character, place or thing

1. Pick the tab (`1` Characters, `2` Places, `3` Things, `4` Groups, `5` Notes).
2. Press **n** (or the + button). A new entity starts blank.
3. Press **Space** to roll every blank field, or go field by field: arrow to a field, **f** (or click) rolls it, **e** (or right-click)
   writes it. Rolls use the universe's genre leanings, the entity's other fields (a need that fits the flaw), and what already exists
   (a rival, owner, parent place or leader can be one of your entities).
4. Fields marked **✎** can't be rolled; write them yourself. A **link** field (rival, owner, located in, leader, members) opens a list
   of your entities to choose from; "(write plain text instead)" is at the bottom.
5. Scroll the mouse wheel over a field to step back through its earlier values. **+** / **-** like or dislike a value.
6. **R** rolls the whole entity again (asks first; what you wrote in ✎ fields stays). **c** adds a field of your own (write-only).
7. Write free notes in the box under the card (**E** jumps there). They are saved as you type.

> **Watch out:** a new card has no highlighted row, so `f` and `e` act on the Name; the first Down only highlights the Name row.
> (ISSUES #23.)

### Renaming

Press **r**, or write or roll a new name. If the old name appears in this universe's notes, outlines or manuscripts, a preview lists
every place, whole words only (possessives included). Enter ticks or unticks one; **a** ticks all, **n** none; **p** replaces the
ticked ones; Esc renames only the entity. Links never break: they hold the entity's id, not its name.

**F** fixes names written in the wrong capitals ("Locked box" becomes "a locked box"), with a preview.

### Universe settings

Press **s**: the universe's genre leanings (they shape everything rolled here), tags to exclude, lists to exclude, tag boosts (`tag=1.5`)
and how strongly its own names are preferred in rolls (blank means your default from Settings > Universes). A universe can also have its
own word lists in its `lists` folder; Words can add words to them.

### Stories

- **Open a story:** Enter or click it in the Stories list. Its outline fills the Story panel.
- **A new story without the Wheel:** **T** (or +Story) opens the story form: a title, then Format, Structure and Genres, each picked
  from a list (Enter or click), and a target length (words, or pages for a screenplay). Ctrl+S or Create saves; Esc cancels. A story
  made with a structure gets its beats as empty rows in the outline.
- **Change format, structure, genres or target:** **m** opens the same form. It warns when the Writer would then open a different file
  (prose and screenplay files are kept side by side).
- **Edit the outline:** in the Outline tab a click selects a row and the wheel scrolls; **right-click** or **e** edits the selected row
  (one beat, one setting line, the premise...). The Settings row opens the story's settings.
- **Repeatable beats:** on a beat, **A** adds another of it (rolled for this universe and protagonist), **X** removes one.
- **Story settings:** **S** opens the story's own font, column width, daily goal, short title for page headers, paragraph indent,
  typewriter mode, invisibles, spellcheck and US/UK spelling. Leave a box as it is to follow your Settings; type `true` or `false`
  in the yes/no boxes.
- **Scenes:** the Scenes tab lists them; Enter or a click opens the Writer at that scene; **+Scene** adds one at the end.
- **A screenplay:** **P** writes script.fountain from the outline (a title page; each beat as a section and a synopsis, which never
  print). An existing script with scenes is never replaced.
- **Delete a story:** `d` with the Stories list focused; asks, then moves it to `.trash`.

In the Outline, **`f` rolls the beat under the cursor again** (the way `A` rolls a new one), and **`e` or right-click edits** a row. The
entity keys (Space, `R`, `+`/`-`, `n`, `d`, `r`, `c`) do nothing there except say so; they belong to the cards. (Fixed: ISSUES #3.)

> With no story open, Write (`w`), Export (`x`) and Copy (`C`) quietly use the universe's first story. Open the story first. (ISSUES #15.)

### Writing, exporting, copying, backups

- **w** (or Write) opens the open story in the Writer. **F3** does the same from anywhere.
- **x** (or Export) asks for a format and exports; see Chapter 6.
- **C** copies the manuscript as plain text.
- **b** (with the Stories list focused) or **Backups…** lists the story's backups with a preview; **r** or Enter restores one after
  asking, and the version it replaces is kept aside first.
- **G** edits your name and address for manuscripts (the same as Settings > You, without the surname).

### Files storywheel did not make

If another tool left a file in a story's manuscript folder (a copy, say), it is never part of the manuscript: not counted, not
exported. The Scenes tab names it with three buttons: Open (read-only), Delete (to `.trash`) and Ignore.

### Leaving

`q` goes back to where you came from; `Q` quits after asking.

---

## Chapter 3. The Writer: writing the story

### What it is for

The Writer is a full-screen, distraction-free writing room: a centered column of text and nothing else, which knows your story's
scenes, its outline and its universe's names. It is Neovim underneath, set up so it behaves like an ordinary editor (this is
"notepad mode", on by default): you are always typing, and Escape does nothing.

### Opening and leaving

- Open: **F3** from any mode, **w** in the Builder, or Enter on a scene in the Builder's Scenes tab (opens at that scene).
- Leave: **F2** (or Ctrl+Q) saves everything and goes back to the Builder; **F1** to the Wheel, **F4** to Settings, **F5** to Words
  (carrying the word under the cursor). **Alt+Q** quits storywheel after asking.
- The Writer remembers the open scene, the cursor and your toggles for each story.

F3 **from the Wheel** opens the draft you are looking at, once it has been sent to the Builder. A draft that was never sent has no
manuscript, so F3 says "This draft has no manuscript yet: send it to the Builder first (B)" and opens nothing; it never guesses another
story. The Writer always shows the story's title: first on the status line ("The Last Clause · words: in this scene…") and in the
terminal window title. (Fixed: ISSUES #4.)

Inside kitty (Settings > Writer: "Open the Writer in its own kitty window"), the Writer opens in its own window with your writing font,
size, line height, padding and opacity.

### Typing

- **One line is one paragraph.** Enter starts the next paragraph. Each paragraph is shown indented; the file has no spaces in front.
  Blank lines are allowed and mean nothing.
- **Italic and bold:** Alt+I and Alt+B (Ctrl+B too) wrap the selection, or start and end italic or bold where you are typing. Under
  kitty, Ctrl+I works too (Alt+K checks what your terminal sends). The `*` marks are hidden and the text shows in italic or bold.
- **Scene breaks:** Alt+S inserts one (`***` by default, Settings > Writer); typing `***` and Enter works too. `*** The Letter` names
  the scene that starts there. Breaks show centered on screen and export as a centered `#`.
- **Centered lines:** Alt+C (or Ctrl+E) centers the line or the selected lines (stored as `>text<`).
- **Selecting:** Shift+arrows, Shift+Home / Shift+End (the visible line), Ctrl+A for everything, or drag with the mouse; typing
  replaces the selection.
- **Clipboard:** Ctrl+C, Ctrl+X, Ctrl+V. Pasted text is cleaned: no leading spaces, no empty lines.
- **Undo / redo:** Ctrl+Z / Ctrl+Y. **Save now:** Ctrl+S (it saves on its own anyway).
- **Delete a word:** Ctrl+Backspace (or Ctrl+H) back, Ctrl+Delete forward. **Join lines** into one paragraph: select them, Alt+J.
- **Home / End** go to the start / end of the visible line; Home again goes to the paragraph's start.
- **Names:** type three letters of any word of a character's or place's name and matching names are offered; Tab moves to the next
  one, Enter accepts it.
- **Find:** Ctrl+F, then Ctrl+G (next) and Alt+G (previous). **Find and replace:** Ctrl+R (below).

The cursor never rests on a scene-break line (`* * *` or `* * * Title`): arrowing or clicking onto one moves on to the nearest line that
is not a break (the way you were going, else the other way; a break at the very end gets an empty line after it), so typing can't turn a
break into a paragraph. Rename a scene from the sidebar (`r`). Typing `***` and Enter still makes a break. (Fixed: ISSUES #11.)

Alt with a letter that has no job types nothing (it used to type the letter). Alt+F in a prose story says "The flip test is for
screenplays." (Fixed: ISSUES #10.)

### The status line

`The Last Clause · words: in this scene 312 · in the story 4,120 / 5,000 words · 82% · today 640 / 500 words · 128%`. It starts with the story's title (cut at 30 characters), so you always know which story you are in. The target is the story's target
length (the story form, `m` in the Builder); the daily goal is in Settings > Goals. A screenplay shows `p. 12 of ~15` instead.

### The Writer menu: F12 or Alt+M

A list in groups: **Edit** (undo, redo, find, find and replace, join, spellcheck, add a word to the dictionary, grammar on/off, next
and list of grammar problems, invisibles, typewriter), **Look up** (the word under the cursor, a typed word, peek, Words), **Story**
(scenes sidebar, story outline, new scene, word counts, exports, copy as plain text, restore from a backup), **Leave** (Settings,
Builder, Wheel, quit) and **More** (help; use Vim keys for now). Up/Down and Enter, a click, or the number keys 1–9 run an item;
Esc or `q` closes.

### The right-click menu

Right-click in the text: Undo, Redo, Cut, Copy, Paste, Fix Spelling… (on a misspelled word), Look Up, Add to Dictionary, and More…
(the Writer menu). On a grammar problem, right-click shows that problem's message and fixes instead.

The menu is storywheel's own small floating list (not Neovim's pop-up), opened at the pointer. **Only a left-click or Enter runs an
item.** A second right-click, Esc or `q` closes it and runs nothing, and so does letting go of the right button over an item. Up/Down
(or `j`/`k`) move the highlight. In a short window it is cut to fit and scrolls. Right-clicking inside the F12 menu, the help or any
other float opens no menu. (Fixed: ISSUES #2.)

### Scenes

- **The sidebar:** F9 shows the scenes down the left with their first lines. Enter (or a double-click) jumps to a scene, `a` adds one,
  `r` renames it, `J` / `K` move it down or up within the file, `q` or Esc closes. Also in the menu: Story > Scenes sidebar.
- **New scene:** Alt+N, or `a` in the sidebar.
- **In the Builder:** the Scenes tab lists the same scenes; Enter on one opens the Writer there.

> **Watch out, important:** the sidebar's keys don't work right after **F9** (you get "E21: Cannot make changes"), and after you jump
> to a scene or close the sidebar, the next letters you type are taken as Vim commands: typing `dd` deleted a paragraph in testing.
> Until it is fixed: after F9 press **Esc** once (then the sidebar's keys work), and after jumping or closing press **F12 then Esc**
> to get back to typing. If text vanished, **Ctrl+Z** brings it back. (ISSUES #1.)

### Looking things up while you write

- **Peek (F8):** a card with the character or place under the cursor; it closes when you move. F8 again lets you scroll a long card.
- **Story outline (Ctrl+O):** the title, premise, every beat, the twist, the protagonist, the setting and the rumor in a floating
  window. Scroll it; Esc, `q` or Ctrl+O close it.
- **Dictionary card (F7 on a word, F6 for a word you type):** meanings, similar words and opposites. Enter looks up the word under
  the card's cursor (`b` back, `n` forward), **r** replaces the word you were on (in the same form: running → sprinting, keeping
  capitals), **i** inserts at the cursor, **c** copies, `/` filters, Esc or `q` closes.
- **Words (F5):** the full Words mode, with the word under the cursor already looked up; "Use in Writer" there brings your choice
  back and replaces the word.
- **Help (F3):** this program's help in tabs (the guide for this story's format, Writing basics, Keys, Export). Tab / Shift+Tab, the
  number keys or a click switch tabs; `/` searches; F3, Esc or `q` close.

The help, the outline, the F12 menu and the other floats are drawn from their own left edge: only the manuscript gets the paragraph
indent. (Fixed: ISSUES #5.)

The outline no longer repeats a Story Spine opener ("Once upon a time. Once upon a time, …") for stories promoted by older versions: a
stored label is dropped when the sentence already starts with it, as in the Builder's Outline. (Fixed: ISSUES #6.)

The help's tab bar shows every tab's name (shortened to fit a narrow window, down to the numbers) and its key hints are on the
window's bottom border; headings are coloured, not underlined with dashes. The outline's wrapped beats hang under their text, its
protagonist's values line up, the rumor starts with a capital, and the window is as tall as the wrapped text needs. (Fixed: ISSUES #7.)

The peek card lists the fields in the card's own order (name, role, age, job, trait, want...), is as tall as its wrapped text needs, and,
if that is taller than the window, **F8 a second time** takes the focus so you can scroll it (arrows, PageUp/PageDown or the wheel); Esc,
`q` or F8 closes it and you are typing again. (Fixed: ISSUES #12.)

### Find and replace: Ctrl+R

A small box with two lines, Find and Replace. Enter on Find finds the next match; Tab switches lines; Enter on Replace (or Alt+R)
replaces the match you are on; **Alt+A** replaces all (one undo step); Alt+C toggles match case, Alt+W whole words; Alt+N / Alt+P next
and previous; Esc closes. It matches plain text in the current file.

### Spelling and grammar

- Spellcheck is on (Alt+L toggles). Red wavy = not a word; blue = a capital is missing; pink = a rare word; cyan = another region's
  spelling (Settings > Spelling softens or hides the last three). Your universe's names are known. Right-click > **Fix Spelling…**
  offers corrections; **Add to Dictionary** teaches a word to every story in this universe.
- Autocorrect fixes common slips as you finish a word (i → I, dont → don't).
- The manuscript keeps straight quotes so spelling works; the export makes them curly.
- **Grammar** (optional, off): install LanguageTool once with `storywheel grammar install`, then turn it on in the menu or Settings >
  Grammar. Changed paragraphs are checked a moment after you stop; problems get an orange underline; right-click one for the message,
  fixes, Ignore this one, Turn off this rule. **F10** jumps to the next problem; **Shift+F10** lists them.

### The other toggles

Alt+V shows invisibles (dots for spaces, a mark at paragraph ends); Alt+T typewriter mode (the line you are on stays in the middle);
Alt+W word counts; Alt+Y copies the whole manuscript as plain text; Alt+E exports (docx; a screenplay: PDF); Alt+U opens this story's
settings file (saving it applies the changes); Alt+K checks what your terminal sends for Ctrl+I.

All of these shortcuts can be changed in Settings > Keys.

### Restoring from a backup

F12 > Story > Restore from a backup… lists every backup with a preview. Enter restores one after asking; the version you have now is
kept aside first, so you can undo a restore. See Chapter 7.

### Writing a screenplay

A story whose format is Screenplay is one Fountain file, `script.fountain`. Start it with **P** in the Builder (from the outline), or
just open it in the Writer (you get a title page and FADE IN:).

- A **scene heading** starts INT., EXT., EST. or I/E. (or a dot) on its own line. A **character cue** is a name in capitals after a
  blank line with the speech straight under it; a **parenthetical** is a line in brackets inside a speech; a **transition** is a capital
  line ending in TO:. `> THE END <` is centered; `===` starts a new page.
- **Tab** cycles the line you are on: action, character, parenthetical, dialogue, transition (fixing the blank lines around it).
- **Enter** after a cue or parenthetical starts the dialogue; after dialogue, action or a heading it leaves a blank line for the next
  element.
- Headings are capitalized when you leave them, and a cue when you press Enter on a name the script or universe knows. Names and
  places complete.
- The page is approximated on screen (cues, dialogue and transitions indented); the file stays plain Fountain.
- **Alt+F** runs the flip test: long action blocks, long speeches, camera directions, too many CUT TO:, and the length against the
  target. Enter on a line jumps there.
- Export makes a standard PDF (US Letter, Courier Prime 12), a Final Draft file (.fdx) or a .fountain file.

### Vim keys

If you prefer Vim, turn notepad mode off in Settings > Writer (or F12 > More > Use Vim keys for now, until you leave). Then Space
starts the Writer's commands in Normal mode: Space n sidebar, p peek, a new scene, i invisibles, t typewriter, s spellcheck, w word
counts, c copy, e export, S settings, k key check, ? help; `]]` and `[[` move between scenes; `:q` leaves for the Builder. The Keys tab
of the help lists every action with both keys.

---

## Chapter 4. Settings

### What it is for

One place for who you are and how storywheel works. Everything is saved the moment you change it (a number only when it is a valid
number; folders, keys and colors when you press Enter). Open with **F4**; **q** goes back.

Move between tabs by clicking them, or Tab into the tab bar and use Left/Right. (When Settings opens nothing has the focus yet; press
Tab.)

### The tabs

- **You:** legal name (top left of page 1), byline / pen name, surname for page headers (blank: the last word of your name),
  address (one line per line), email, phone. Without a name, exports are anonymous and say so.
- **Goals:** daily word goal (0 turns it off).
- **Appearance:** transparent background, text color, accent color (a name like `cream` or `amber`, or `#e8e1d0`; Enter).
- **Writer:** don't count pasted text; notepad mode; open the Writer in its own kitty window, with its font, size, line height
  (100 normal, 140 typewriter-like, 200 double), padding and opacity; space between paragraphs; the scene break written by Alt+S;
  column width; paragraph indent; typewriter mode; invisibles. The line at the bottom says whether kitty and Neovim are found.
- **Spelling:** spellcheck; know the dictionary's words; accept words built from known words (gunsmithing); US or UK spelling;
  spelling marks (all / subtle / misspellings only); autocorrect.
- **Grammar:** grammar checking on or off, each category (grammar, punctuation, capitals, confused words, meaning, other on; spelling,
  typography, style, redundancy, plain English, colloquialisms, repeated words off), turned-off rules, the pause before checking, the
  memory limit. Java and LanguageTool status at the bottom.
- **Export:** manuscript font (Times New Roman or Courier New), default format for new stories, default export type, title in bold,
  page header (full title or keyword), always export anonymously, one space after periods, curly quotes, screenplays' automatic
  (CONT'D), and the manuscripts folder.
- **Keys:** every Writer shortcut. Type a key like `Alt+I`, `Ctrl+B` or `F9` and press Enter; a key the Writer needs, or one already
  used, is refused with the reason. Changes apply the next time the Writer starts.
- **Universes:** how much more likely a universe's own names are in rolls (1.5 by default; a universe can set its own with `s` in the
  Builder).
- **Library:** the library folder (changing it moves nothing; your universes stay where they were).
- **Updates:** a git remote, used by `storywheel update` only if the folder storywheel was installed from is gone.
- **Stats:** today, your streak, days written, words recorded, words in all manuscripts; a table of words per day (**e** edits a
  day's total, **0** resets it, each after a confirm) and a table per story (**R** forgets a story's recorded history; its manuscript
  is untouched).
- **Help:** a search box over every help page; pick a result to read it.

A story can override the Writer and Goals settings with **S** in the Builder (or Alt+U in the Writer).

---

## Chapter 5. Words: finding the right word

### What it is for

An offline dictionary and thesaurus, and tools for finding a better word, learning new ones, and seeing what your story actually
uses. Open with **F5** from anywhere. From the Writer, the word under the cursor comes with you, and **Use in Writer** (`u`) sends your
choice back to replace it in the same form ("running" → "sprinting", capitals kept).

### Lookup

1. Type a word and press Enter. Plurals, past tenses and misspellings work.
2. The answer is in five boxes: **Meanings** (by part of speech, with examples), **Similar**, **Opposites** (and, marked as such,
   opposites of similar words), **Rhymes** (perfect, then near, by syllables; the two boxes at its top limit the syllables and add
   names and rare words) and **Related** (wider and narrower words, parts, related forms). On a narrow screen they are tabs.
3. Enter or a click on any word looks it up. **b** / **n** (or ◀ Back / Forward ▶) walk your path. **/** filters every box.
4. On a word: **u** Use in Writer, **a** (or `l`) learn it (★), **w** put it on this universe's generator list (pick the slot: job,
   thing, place…), **c** copy.

### Suggestions

Choose a list: **For this story** (words that fit its genres and are not in it yet), **For your characters and places** (words the
dictionary relates to your jobs, things and places), or **Fresh alternatives** (replacements for your most overused words). Pick a part
of speech. Enter looks a word up; `l` learns it; `c` copies; `u` uses it in the Writer; `w` puts it on a generator list.

### Vocabulary

Words worth learning, twenty at a time. Choose how rare (uncommon like "lantern", rare like "serendipity", very rare like "gallivant"),
the part of speech and the subject, then **New batch**. **l** marks a word ★ Learning, **k** ✓ Known (never offered again). The first
box switches to your ★ Learning list (`k` Known, `d` remove, `f` flashcards: Space shows the meaning, `k` you know it, `n` next) or the
✓ Known list. Type a word of your own in the box and press Enter to learn it. **Start over** forgets what you have been shown (your
Known and Learning words stay). A word any of your manuscripts uses is marked Known on its own.

### Story words

Pick a story (or the whole universe) and see the names and odd words it uses, with counts: ◆ a name from your universe, ? a word the
dictionary doesn't know (invented names, jargon, typos), ≈ a look-alike ("Glass Water" for "Glasswater"). Enter shows where each is;
Enter on a place opens the Writer there. **s** adds the word to the spelling list, **e** makes it a character, place or thing, **r**
renames it everywhere (with the usual preview). The second box switches to **Often used**: your most frequent words and words repeated
close together. At the bottom: words you put on this universe's generator lists (`d` removes one).

### Genre words

Every noun, verb, adjective or adverb in the dictionary, ranked by how well it fits one or more genres (Genres…): ●●● strong, ●●○, ●○○,
··· none; nothing is hidden. Narrow by how common, order by fit, commonness or A to Z, and search as you type. Enter looks a word up,
`l` learns it, `c` copies, `u` uses it in the Writer, `w` puts it on a generator list. Under "From the Wheel" are the generator's own
names, jobs, places and things: **e** adds one to the universe, **m** invents more names in the genres' style.

`l` and `a` (both "learn this word") and `k` (Known) act on **the word you are on**, whichever tab you are in: Lookup, Suggestions,
Vocabulary or Genre words. In Story words they say they need a dictionary word. (Fixed: ISSUES #14.)

---

## Chapter 6. Sending it out: exports

### How

- From the Builder: **x** (or Export) on the open story, then pick a format.
- From the Writer: **Alt+E** (Word), or F12 > Story > Export…
- From a terminal: `storywheel exports make UNIVERSE/STORY` (the story's default format) or
  `storywheel manuscript export UNIVERSE/STORY --format docx`.

### What you get

- **Word (.docx), Shunn manuscript format** (for a short story): 12-point Times New Roman or Courier New, double-spaced, 1-inch
  margins, half-inch first-line indents, your legal name, address, email and phone at the top left of page 1 and the word count
  (rounded to the nearest hundred) at the right, the title halfway down with the byline, a header of surname / short title / page
  number from page 2, a centered `#` at every scene break, END after the last line, italics kept and quotes made curly.
- **Anonymous .docx:** no name, contact block, byline or surname; the header reads Title / page. (Settings > Export can make every
  export anonymous; with no name set, exports are anonymous anyway and say so.)
- **OpenDocument (.odt)** and **PDF:** made from the .docx by LibreOffice, if installed.
- **Markdown (.md)** and **plain text (.txt).**
- **Fountain (.fountain)** from prose: the story as action, a start for adapting it.
- **A screenplay:** a PDF in standard script pages (with an anonymous version), Final Draft (.fdx) or Fountain.
- A **novel** puts each chapter on a new page (the full novel layout isn't done yet).

### Where

In your manuscripts folder: `~/Writing/<Story Title>/<Story Title> <date>.docx`. A second export on the same day adds "-2". Nothing is
ever written into your library. `storywheel exports status` lists every story with its last export and whether the manuscript changed
since.

---

## Chapter 7. Keeping your work safe: saving, backups, the trash

- **Saving:** the Builder saves every change at once. The Writer saves when you stop typing, when you leave a scene or the window, and
  when you leave the Writer. Wheel drafts are saved as you keep steps (a draft with nothing kept isn't saved, and old empty ones are
  tidied into `~/.storywheel/.trash`).
- **Backups:** while you write, a copy of the manuscript is made at most every 15 minutes, into the story's `.backups/<date>/`
  folder; 30 days are kept. Conversions (old scene files merged into one, quotes made straight, paragraphs made one line) also back up
  the old files first.
- **Restoring:** Builder: open the story, Backups… (or `b` in the Stories list). Writer: F12 > Story > Restore from a backup….
  Terminal: `storywheel backups list UNIVERSE/STORY`, then `restore`. A restore first copies the current version aside, so it can be
  undone.
- **Deleting:** a universe, story, entity or extra file goes to the library's `.trash` folder after a confirm. A Wheel draft you delete
  goes to `.trash` in your storywheel home, also after a confirm.
- **Undo:** in the Writer, Ctrl+Z goes back word by word.

---

## Appendix A. The command line

Most writers never need these; they are for scripts and for checking things.

| Command | Does |
|---|---|
| `storywheel` | Opens where you left off |
| `storywheel --plain` | The Wheel as a simple prompt |
| `storywheel new` / `wheel` / `resume [N]` | The Wheel on a new draft / the last one / draft N |
| `storywheel builder` / `settings` / `writer UNIVERSE STORY` | Open that mode |
| `storywheel list` / `show [N]` | Wheel drafts / one as plain text (`--json` for both) |
| `storywheel export N --out DIR` | Copy a draft's markdown somewhere |
| `storywheel promote N --new NAME` (or `--universe SLUG`, `--dry-run`) | Bring a draft into a universe |
| `storywheel sample western "fairy tale" -n 5 [--seed 1]` | Sample ideas; nothing is saved |
| `storywheel report` | The lines you rated down most, and why |
| `storywheel universes [new NAME]` | List or make universes |
| `storywheel entity list UNIVERSE [--type character]` | A universe's entities |
| `storywheel story list [UNIVERSE]` / `story show UNIVERSE/STORY` | Stories |
| `storywheel names fix UNIVERSE [--apply]` | Fix names written in the wrong capitals |
| `storywheel manuscript export UNIVERSE/STORY --format docx` / `manuscript text …` | Export, or print the manuscript |
| `storywheel exports status` / `exports make UNIVERSE/STORY [--format F]` | Export records / export one |
| `storywheel backups list|show|restore UNIVERSE/STORY [ID]` | Backups |
| `storywheel define|thesaurus|lookup WORD` | Dictionary from the terminal |
| `storywheel dictionary install|status` | Get the dictionary / check it |
| `storywheel grammar install|status|start|stop|rule-off ID|ignored STORY` | LanguageTool |
| `storywheel help [TOPIC]` / `help -s WORDS` | The help pages / search them |
| `storywheel setup [--again]` | The questionnaire |
| `storywheel update [--check]` | Update from the folder storywheel was installed from |
| `storywheel kitty [--print]` | storywheel in its own kitty window |
| `storywheel migrate` | Bring old data up to date |
| `storywheel --version` | The version |

---

## Appendix B. Where the in-app help disagrees with this manual

The help pages are in `storywheel/data/help/`. Their key tables are made from the real key bindings and are correct; the free text is
where they drift. Each line: the page and section, what it says, and what actually happens.

1. **wheel › Past stories:** "p and s send its protagonist or setting to the current story". They send it **into a universe you
   choose**. (Fixed with ISSUES #13: the help, the Keys tab, the buttons and the footer now all say "→ universe".)
2. **wheel › The universe panel:** "e to edit it, d to delete it (with a confirm), n to add a new one". The preview has only Use and
   Close; there is no e, d or n in the panel.
3. **wheel › Keys:** `U` is "Remove the selected value from your universe". It only tells you to delete in the Builder.
4. **wheel › Mouse:** the button row is listed as "Roll, Keep, Back, Skip, Flavor, +Beat, -Beat"; it also has Send to Builder and New
   draft.
5. **backups › Deleted things:** "a draft with nothing kept goes to .trash. Nothing is destroyed." (Now true for a draft you delete
   yourself as well: ISSUES #8.)
6. **genres-and-flavor › Genres:** "Heist, coming-of-age and adventure still run on general atoms until their lists are written." They
   were written in batch 14 and are full genres; the list of written genres also leaves them out.
7. **writer › Leaving:** ":q works too". Only with Vim keys on; in notepad mode you can't type a `:` command.
8. **writer › Keys (key_sidebar)** and **writing-prose › The scene sidebar** and **screenplays › Writing Fountain:** "Enter jumps, a
   adds, r renames, J and K move". These keys don't work straight after F9 (ISSUES #1).
9. **writer › Mouse:** "Right-click opens the everyday menu". (Fixed with ISSUES #2: the menu is now our own, and the help says how it
   closes.)
10. **words › Keys:** `k` "Mark the word ✓ Known" worked only in Vocabulary; `a` "Learn this word" and `l` are two keys for the same
    thing. (Fixed with ISSUES #14: both work on the word you are on, on every tab.)
11. **words › Keys:** `a` "Learn this word" learned the word in the hidden Lookup tab outside Lookup. (Fixed with ISSUES #14; `a` is
    no longer pinned to the footer.)
12. **keys › Footers:** "at most three keys that matter most". A focused list adds its own keys (Past stories shows four more).
13. **builder › Keys (start_script)** is right, but the program's own message for a prose story says "Set its format to screenplay (S,
    story settings)"; the format is on the story form (`m`). And right-clicking the Structure row says "The structure was set in the
    Wheel", though `m` changes it.
14. **builder › Mouse:** "In the Outline a click selects, the wheel scrolls and right-click edits". True, but `f`, Space, `R`, `+`/`-`,
    `n` and `d` pressed in the Outline act on the entity card (ISSUES #3).
15. **settings › Moving around:** "left and right on the tab bar switch tabs"; true once the tab bar has the focus, but nothing has it
    when Settings opens.
16. **exports › Other formats:** doesn't mention the "Fountain (.fountain): the prose as action" export the Builder offers for prose.
17. **structures › About:** "Pick one in the Wheel's Structure step" leaves out the Builder's story form (`m`, +Story), where a story's
    structure is also picked or changed.

The README, which is not an in-app page, is further out of date: ISSUES #22 lists it.
