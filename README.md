# storywheel

A personal writing program for one writer, covering the whole path from "I have nothing" to "a manuscript ready to
submit":

1. **The Wheel**: roll a story idea piece by piece. Keep what clicks, edit what almost works, and every piece you keep
   feeds the next roll.
2. **The Universe Builder**: grow a kept idea into a world of characters, places, things, groups and notes, with the
   generator on hand to fill any field.
3. **The Writer**: a full-screen, distraction-free Neovim setup for drafting, aware of the world, that exports a
   properly formatted (Shunn) manuscript.

One key moves between them: **F1 Wheel, F2 Builder, F3 Writer** (and F2 in Neovim comes back to the Builder).
`storywheel` with no arguments reopens exactly where you left off.

Everything you keep is plain files: markdown with YAML frontmatter, so the library folder is also a valid Obsidian vault.

## Install

### A new machine (Debian, Ubuntu, Raspberry Pi OS; x86_64 or arm64)

    ./install.sh              (from this folder; add --dry-run to see what it would do, --yes to accept the defaults)

It checks for, and installs when missing, Python 3.9+, pipx, git and **Neovim 0.10 or newer** (the distribution's package is often older: it then
fetches the official release into `~/.local`), offers LibreOffice (only for .odt and .pdf export) and Neovide (a window of its own for the
Writer), installs storywheel, and runs `storywheel setup`.

### By hand

You need Python 3.9+ with pipx and **Neovim 0.10 or newer**. From the folder containing `pyproject.toml`:

    pipx install .

No pipx? `sudo apt install pipx` first, or use a virtualenv and `pip install .`
To tinker with the word lists and see changes immediately, install it editable: `pipx install --editable .`

### Setup, version and updates

- `storywheel setup` is a short questionnaire: your details for the manuscript's first page, the library and manuscripts folders, terminal or
  Neovide, transparency and fetching the dictionary, and the update remote. It remembers what it asked; running it again asks only what is new
  (`--again` asks everything, `--defaults` asks nothing). Every answer can be changed later in Settings (F4).
- `storywheel --version` shows the version; CHANGELOG.md lists what each version added.
- `storywheel update` compares the **installed** version with the version in the folder it was installed from (pip records that folder; an editable
  install runs from it). If that folder is a git checkout with a remote (the typewriter's pulls from `xps:projects/storywheel`) it is fetched and
  fast-forwarded first; with no remote (xps) it is just read. If the versions differ it reinstalls (pipx, or pip in a plain environment; an editable
  install needs none), then runs migrations and rebuilds the dictionary index and spelling lists. It says what it compared: `Installed: 0.5.0. Source
  ~/projects/storywheel: 0.6.0. Reinstalling.` Local changes are never overwritten. It also remembers the commit it installed, so a fix committed without a version bump still reinstalls (`Same version number, but the source is at commit …`). `storywheel update --check` only says whether there is something new.
  The *Git remote to update from* setting (Settings > Updates) is optional: it is used only if the source folder is gone, for a temporary clone.

### Two computers

storywheel does not sync anything and knows nothing about syncing: your library and manuscripts are plain files, so any tool outside this
project can carry them. What is kept per machine is in `~/.storywheel/settings.local.toml` (folders, Neovide, fonts, the update remote, what
setup asked); `settings.toml` holds the rest and can be copied between machines.

## Use

    storywheel              start a new story (a full-screen app)
    storywheel --plain      the same, with a simple prompt instead of the app
    storywheel list         list your stories
    storywheel show [N]     print a story as plain text
    storywheel resume [N]   pick up where you left off (N from list; default newest)
    storywheel export N --out ~/vault/Stories     copy a story's markdown somewhere
    storywheel sample western "fairy tale" -n 10   print sample stories for a genre mix
    storywheel report       the worst-rated lines and the frames that produced them
    storywheel universe     show what you've saved to your universe
    storywheel universe rm KEY N   remove an entry, e.g.  universe rm spine 1

`list`, `show`, `export` and `sample` take `--json` (one JSON document on stdout, nothing
else) so another program, such as a Neovim plugin, can drive the engine. Each story has
`id`, `title`, `genre`, `mood`, `structure`, `kept` (every kept step's fields), `text`
(plain text), `markdown`, `path`, `step`/`steps`/`done` and `resume`. `storywheel show 1
--json`, `storywheel sample western -n 3 --seed 1 --json` and `storywheel list --json` are
the three shapes; a seeded `sample` is repeatable. `show` exits 1 with `{"error": ...}`
when there is no such story.

### The app

It is meant for a full-screen desktop terminal (it needs room for three columns).

    +--------------+--------------------------+----------------------+
    | Steps        |  card: the candidate     | The story so far     |
    |  ✓ Genre     |    name  Wade Hollis ▲▼  |  ● Spine was built   |
    |  ● Spine     |    job   drover      ▲▼  |    on a stand-in ... |
    |  ▶ Premise   |  [Roll][Keep][Back]...   |                      |
    | Universe     +--------------------------+  THE LANTERN OF ...  |
    |  ▶ Setting   |  History: every roll     |  PROTAGONIST         |
    | Past stories |   #1 ... #2 job: ...     |    Name  Wade ...    |
    +--------------+--------------------------+----------------------+
     space Roll  k Keep  q Quit  ? Help  f Field  e Edit  ...  c Copy story

**Left:** the steps, your universe, and your past stories. **Middle:** the card and its
history. **Right:** the story so far, kept content only, as plain text, with problems
listed at the top.

Step markers: `✓` kept, `–` skipped, `▶` current, `·` still to do, **yellow `●`**
kept but built on a stand-in or on something that has since changed, **red `✗`** it
refers to something that no longer exists (say the protagonist was skipped after the
body was kept). Click a flagged step, or press Enter on it, to go there; the right
column says what is wrong.

The card shows the current candidate; up and down select a field. The history lists
every roll of the step and what changed in each; Tab moves between the lists, and Enter
on a history row picks that one. Select a field and press `h` and the history becomes
**that field's own history**, so you can bring an old value back without losing the rest
(`h` again returns to every roll).

    space / enter   roll again          k      keep it and move on
    f               reroll the field    e      edit the field in place
    E               edit in $EDITOR     w      write your own
    + / -           like / dislike      u / U  save to / remove from your universe
    h               history             m      the mix editor
    v               universe panel      enter  reroll the selected field
    c               copy the story so far to the clipboard, as plain text
    b               go back a step      x      skip this step
    q               quit (asks)         ?      help

**Past stories** (bottom left): Enter opens one (the story you leave is saved), `d`
deletes one after asking, `p` / `s` send its protagonist / setting to your universe.
Buttons do the same.

**Quitting:** `q` asks "Keep this story or delete it?". Keep saves it; after the app
closes it prints the story as plain text, then the markdown path and the command to
resume it. Delete removes the story and its markdown file (your universe is untouched).

**Clipboard:** `c` copies the story so far, as plain text, with `wl-copy`, `xclip`,
`xsel`, `pbcopy` or `clip.exe` (whichever the machine has), else through the terminal's
own clipboard escape (OSC 52).

You go through the steps in order: genre & mood, structure, title, protagonist,
setting, premise, story body, twist. Things carry forward. The title's motif (the
thing it's "about") turns up in the premise, body and twist. A name or place invented
inside a title usually becomes your protagonist or setting. Genre nudges later steps
toward fitting ideas. If you go back and change something, later steps get the new
name or place swapped in automatically. Rerolling or editing one field also updates
other fields in the same item that mentioned it, so a new landmark changes the rumor
about it too.

### Stand-ins and stale candidates

The sidebar lets you jump ahead. If you roll a step before the ones it builds on are
kept (the story body before the protagonist, say), it invents **stand-ins** (a first
name, a job, a place) and the card says so. Each candidate remembers which earlier
fields it was built from. When you later keep those steps, a candidate built on a
stand-in shows a banner, "Built for Mark; your protagonist is now Stacie Anderson",
with **Update** (`a`: swap the kept values into a copy), **Reroll**, and **Ignore** (dismiss the banner; the candidate stays as it is).
Stale rows in the history are marked. A single-field reroll always uses what you have
kept, never an old stand-in. If you keep a step that was built on a stand-in and then
keep the real one, the kept text is updated for you.

### The mouse

The app has the mouse (over SSH too, in most terminals). On the card:

    click a field        reroll just that field (like f)
    right-click a field  edit it in place (like e)
    scroll over a field  step through that field's earlier values
    click ▲ or ▼         rate that line (like + and -)

Enter on a highlighted field rerolls that field, the same as a click; space rolls the
whole step. A row of buttons under the card does Roll, Keep, Back, Skip and Mix. Click a
step to jump to it and a history row to pick it. While the app has the mouse, select
text in the terminal by holding **Shift** while you drag (some terminals use Alt, or
Option on a Mac).

### The universe panel

The bottom half of the left column holds your universe, grouped by kind (Protagonist,
Setting, ...); Enter or a click opens and closes a group. `v` moves the keyboard there.

    enter / click an entry   preview it
      in the preview:  enter or u = use in this story,  e = edit,  d = delete (asks first)
    n or [+ New]             write a new entry from scratch, in that kind's fields
    t or [Use: ...]          for this story: no / mix it in / only from the universe

"Use in this story" adds the entry as a new candidate for its step (jumping there if you
are elsewhere). Nothing is kept until you press `k`, and kept steps never change. Blank
boxes in a hand-written entry are filled in with an ordinary roll when it is used.

### The mix editor

Press `m` for this story's mix: every tag with its genre default, your boost, and its
weight now, and (Tab) every list. `e` excludes a tag or list, `+`/`-` boost or soften a
tag, `0` clears a boost, `r` resets to the genre defaults. **It edits this story only**
and says so on screen: the genre profiles never change, and it affects future rolls,
not what you have kept.

### Ratings

Press `+` or `-` on a line (the selected field; on a one-field step, the whole thing).
A ▲ or ▼ marks it. Each rating is saved in `~/.storywheel/ratings.json` with the frame
(template) and atoms that produced the line. Over time the tool leans away from what
keeps getting `-`, gently: one dislike is no evidence at all; a frame, or a pair of
atoms ("buried" + "a mule"), with a net score of -2 is drawn a fifth less often, and so
on down to a floor of 25%, never to zero. A single atom is only touched at net -3, and
less. Press the same key again to clear a rating. `storywheel report` lists the
worst-rated lines, the frames that produced them (and how far each is down-weighted),
and the atom pairs that keep getting `-`. A seeded `storywheel sample` ignores ratings,
so it stays repeatable.

### The plain prompt

`storywheel --plain` (also used automatically when there is no terminal, as in a
pipe) is the original prompt loop. It works on a dumb terminal over a slow link:

    enter / r   roll again              k        keep it and move on
    f [field]   reroll one field        e [field]  edit a field in place
    E           edit in $EDITOR         w        write your own
    + / - [field]  like / dislike       p N      pick earlier roll #N
    h           every roll so far (what changed), pick one
    h [field]   every value one field has had, pick one
    u / U       save to / remove from your universe
    b           go back a step
    x           skip this step          q        save and quit
    ?           help

Commands work with or without a space: `f 4` and `f4` both reroll field 4.

## The whole program

### Where things live

    ~/Writing/storywheel/                      the library (STORYWHEEL_LIBRARY): plain files, an Obsidian vault
      universes/the-thornwood/
        universe.md                            name, genre leanings, mix changes, notes
        characters/ places/ things/ groups/ notes/     one .md per entity (fields in the frontmatter, notes in the body)
        lists/                                 your own atom lists for this world
        stories/the-last-clause/
          story.md                             the outline (premise, setting, beats, twist)
          seed.json                            the Wheel draft it came from
          settings.toml                        format, font, column width, daily goal...
          manuscript/01-opening.md ...         the prose, one file per scene
          stats.json  exports/  .backups/
      .trash/                                  everything you delete goes here first
    ~/.storywheel/                             app storage (STORYWHEEL_HOME)
      stories/ (Wheel drafts)  state.json  settings.toml  ratings.json  recent.json  nvim/

`~/.storywheel/settings.toml` holds who you are (legal name, byline, address, email, phone), which goes on the first page
of a manuscript. Edit it in the Builder with `G`, or by hand.

### From the Wheel to a universe

Leave the Wheel (`q`) with something kept and it says you are about to bring the story into the Universe Builder: into a
**new universe**, an **existing** one, or **not now** (it stays a draft; promote it later with `P` in Past stories).
The preview lists what will be created: the protagonist becomes a character, the rival a stub, the town and the
landmark places, the motif a thing or a character, the story's threads stubs, and the title, premise, beats and twist
the story's outline. Same-name entities are offered as merges (blank fields filled, nothing overwritten).
`storywheel promote N --new NAME` does the same from the command line.

### The Universe Builder (F2)

Left: universes (create, rename, delete after a confirm) and their stories. Middle: the universe overview or a story's
outline, then tabs for Characters, Places, Things, Groups and Notes with the selected entity as a card. Right: its notes
(edit as you type), its links both ways, and the stories it appears in. The keys are listed with `?`.

A new entity starts blank. **Click a field (or `f`) to roll it, right-click (or `e`) to write it, `space` rolls every
blank field**, the wheel steps through a field's history. Rolls use the universe's genre leanings, the entity's other
fields, and the people and places already there (a rival, an owner, a parent place, a leader can be real entities).
Fields marked ✎ are write-only; `c` adds your own. **Renaming** (`r`, or rolling/writing a new name) shows every match
of the old name in this universe's notes, outlines and manuscripts first; you choose what to replace. `s` edits the
universe's genre leanings, exclusions, boosts and its own `lists/` folder; `S` the story's settings.

`w` or **F3** opens the story in the Writer; `x` exports it; `C` copies the manuscript as plain text.

### Universes in the Wheel

The Wheel's universe panel is a checklist: tick the universes the generator may draw from for this draft (saved with
it). Their characters, places and things become atoms in the matching slots, boosted (`atom_boost` in the universe's
settings), and their genre leanings join the mix. `Use: no / mix / only` decides whether whole protagonist and setting
candidates can come from them. `u` saves a piece into a universe.

### The Writer (F3)

Neovim, with its own config shipped in the package (it never touches your personal one): a centered column, soft wrap,
nothing else on screen. Keys, with `Space ?` in the Writer for the full list:

    Alt+I / Alt+B   italic / bold (Ctrl+B too; Ctrl+I only where your terminal can send it: Space k checks)
    Enter           a new paragraph (blank line between, shown with an indent)
    Alt+S           scene break (* * * in the file, centered on screen)
    Space n         scene sidebar (Enter jump, a add, r rename, J/K move)       ]] / [[  next / previous scene
    Space p / F8    peek at the character or place under the cursor            Tab  complete names from the universe
    Space i t s     show invisibles / typewriter mode / spellcheck             Space w  word counts
    Space e         export .docx          Space c  copy manuscript as plain text
    F2              save everything and go back to the Builder       F1  to the Wheel

Everything is saved as you go, with rolling backups in the story's `.backups/` folder. The status line shows words in
the scene, in the manuscript, and today against your goal (`stats.json` keeps a record).

### Export

`x` in the Builder, `Space e` in the Writer, or `storywheel manuscript export UNIVERSE/STORY --format docx`.
The **.docx** follows Shunn's proper manuscript format for a short story: 12 pt Times New Roman (or Courier New), double
spaced, 1 inch margins, half-inch indents, your name and address at the top left of page 1 with the rounded word count
at the right, the title halfway down, a header "Surname / Keyword / page" from page 2, a centered `#` for scene breaks,
a centered END, italics kept. Also `md`, `txt`, `odt` and `pdf` (those two need LibreOffice). Novel layout is partial;
screenplay is a marked stub (a `.fountain` file).

### Writing in kitty (a typewriter-style setup)

[kitty](https://sw.kovidgoyal.net/kitty/) is a good home for the Writer, especially on a Raspberry Pi where Neovide is not available (it has no arm64
build; Settings and setup say so and the terminal is used).

    storywheel kitty                                      a new kitty window with storywheel, using Settings > Writer's font and size
    storywheel kitty --font "Courier Prime" --size 17 --line-height 160
    storywheel kitty --print                              show the command (put it in a launcher or an alias)

`--line-height` is a percent (kitty's `modify_font cell_height`; 140 by default) and gives the taller, typewriter-like lines. A desktop launcher:
`~/.local/share/applications/storywheel.desktop` with `Exec=storywheel kitty --font "Courier Prime" --size 17`, `Terminal=false`.

**Ctrl+I** reaches Neovim distinctly under kitty's keyboard protocol (kitty sends `CSI 105;5u`, Neovim reads it as `<C-i>`, not Tab). This was
checked by sending those exact bytes to a real terminal-mode Neovim (`tests/test_kitty_keys.py`), so Ctrl+I toggles italics automatically when
`KITTY_WINDOW_ID` or a kitty `TERM` is present; Alt+I always works, and `Space k` (`:SWKeyCheck`) tests your own terminal.

### Grammar checking (optional, off by default)

The Writer can check grammar with a **local LanguageTool** server. Nothing runs unless you turn it on.

    storywheel grammar install                   download LanguageTool (about 200 MB), once
    storywheel grammar install --from LT.zip     or unpack LanguageTool-stable.zip that you copied over (a typewriter rarely has internet)
    storywheel grammar status                    Java, LanguageTool's version, memory it wants, whether the server runs

It needs Java 11 or newer (`sudo apt install default-jre-headless`; the message says so when it is missing). Turn checking on in Settings > Grammar or
the Writer's F12 menu: storywheel starts the server (on 127.0.0.1 only, with the memory limit you set, 512 MB by default; the first start can take a
minute on a Raspberry Pi) and stops it when you turn checking off or leave the Writer.

- **When:** a moment after you stop typing, only the paragraphs (lines) that changed since they were last checked. Answers are remembered per story
  (`.grammar-cache.json`), so reopening a story does not check it all again. Markdown markup (`*`) is taken out before checking and the answers are
  mapped back onto your text, so the underlines land on the right letters (also after emoji and quotes).
- **Looks:** problems have an orange wavy underline, distinct from spelling's red/dotted marks; the status line says how many there are.
- **Right-click a problem:** LanguageTool's message, the suggested fixes (click one to apply it), *Ignore this one* (remembered for this story only, in
  `grammar-ignore.json`; list or forget them with `storywheel grammar ignored UNIVERSE/STORY [--clear]`), *Turn off this rule* (saved in Settings).
  **F10** jumps to the next problem; **Shift+F10** lists every problem in the story (Enter jumps). Both keys are in Settings > Keys.
- **Settings > Grammar:** on/off, which categories to check, turned-off rules, the pause, the memory limit. The picky categories (style, redundancy,
  plain English, colloquialisms, repeated words) and LanguageTool's own spelling and typography start **off**: fiction and dialogue trip them
  constantly, and Neovim's spellcheck already knows your universe's names.
- **What this is not:** the local version has LanguageTool's free rules, not the Premium rules of the Google Docs extension, and the large n-gram
  data is not used (some confused-word checks that need it are missing).

### Look and feel (Settings > Appearance)

By default the background is your terminal's own, so a translucent terminal (kitty `background_opacity 0.85`...) shows through in every
mode and in the Writer. Turn it off for solid colors. You can set a text color and an accent color (a name like `cream` or `amber`, or a
hex color), and Neovide's window opacity.

### Switching between modes

The Wheel (F1), Builder (F2), Settings (F4) and Words (F5) are screens of **one** Textual app. Each is built the first time you open it and then kept,
so switching back is instant and the mode is exactly as you left it (the selected entity, the open tab, the word you were looking up, the Wheel's step).
Anything another mode changed (a promoted story, new settings, new words) is shown when you come back. The Writer (F3) is Neovim, started from the same
app: the screen is cleared on the way in and out, so your shell prompt never shows between modes. `q` goes back along the modes you came through; `Q` quits.
`STORYWHEEL_CLASSIC=1 storywheel` uses the older loop (one app per mode) if you ever need it. `python tools/measure_switch.py [hub]` times the switches on
your machine; `python tools/screens.py 190x50` prints each mode as text at a given size, for checking layouts.

On a narrow terminal (under 150 columns, such as a small kitty window on a Raspberry Pi) the side columns get thinner, the Wheel's buttons wrap into a
grid, and in the Builder the right column (Outline, Scenes, Entity notes: keys 6 7 8, or backslash) takes turns with the cards; Esc or 1-5 bring the cards back.

### Spelling

Spellcheck is on. The manuscript keeps straight quotes (`'` and `"`), because the spellchecker can't read `’` in "couldn’t"; typed or pasted
curly marks become straight, and the export makes them curly (Settings > Export). Autocorrect fixes common slips as you finish a word
(`i` → `I`, `im` → `I'm`, `dont` → `don't`; `wont` and `cant` are real words and stay). The universe's names (people, places, things, and the
proper nouns in the story's outline) are known to the spellchecker; right-click > **Add to Dictionary** teaches it more, for every story in
that universe.

With the dictionary installed (below) the spellchecker also knows **every word in it** and its plurals and -s, -ed, -ing, -er, -est forms
(`storywheel/spelldict.py` writes the list and a headless Neovim compiles it; it is rebuilt when the dictionary index changes). A second,
**lenient** list (Settings > Spelling, on by default) accepts a known word with a common ending or beginning (-ing, -ed, -er, -ers, -ly, -ness,
-less, -ful, un-, re-), so "gunsmithing" passes. These are plain Neovim spell files, so Neovim does the checking.

The marks: **red wavy** = not a word. **Blue** = a lowercase letter where a capital belongs (SpellCap). **Pink** = a rare word (SpellRare).
**Cyan** = another region's spelling (SpellLocal). Settings > Spelling > *Spelling marks* shows the last three as a faint dotted line
(`subtle`, the default), as before (`all`), or not at all (`misspellings only`).

**Names** in the Writer: type three letters of any word of a character's or place's name, in any case, and it is offered (accepting inserts the
name's own capitals); a finished word that is a known name in the wrong case ("gise ") is corrected like autocorrect, unless the lowercase
word is an ordinary word ("hope"). Names that are descriptions ("a locked box", "the sheriff") are not completed.

### Names and capitals

An entity records whether its name is **proper** (a person or a named place: Title Case) or a **description** (an object, a role, an unnamed
landmark: lowercase, with the article a sentence uses, "a locked box", "the sheriff"). Promotion and the generator use what they know about the
text; a hand-written name stays as typed. Entities made earlier can be repaired: `storywheel names fix UNIVERSE` shows what would change,
`--apply` changes it (in the Builder: **F**, with a preview). Ids stay the same; mentions in notes and manuscripts are not rewritten.

### Dictionary and thesaurus

Look up any word without leaving the program, offline: meanings by part of speech, examples, similar words and opposite words.
Inflected forms work ("running" finds "run", "geese" finds "goose"); a word that isn't there comes back with close spellings.

One-time setup (the only time storywheel uses the network, and only when you ask): `storywheel dictionary install` downloads
Open English WordNet (CC BY 4.0) and the Moby Thesaurus (public domain), about 36 MB, and builds a 28 MB index in
`~/.storywheel/dictionary.sqlite`. The downloaded files are kept in `~/.storywheel/dictionary-sources/`, so a newer index format is rebuilt
from them offline (with a one-line message); it only downloads again if they are missing. Sources and licenses are in SOURCES.md.

- **Words (F5)** is a mode of its own, reachable from every mode, including the Writer (which hands over the word under the cursor):
  - *Lookup*: meanings, every similar and opposite word (and the opposites of similar words, labelled as indirect), wider and narrower
    words ("a kind of" / "types of it"), parts, related forms. Enter or a click on a word looks it up; back and forward remember your
    path; `/` filters. **Use in Writer** (`u`) goes back to the Writer and replaces the word you were on with the one you picked, in
    the same form (running → sprinting, geese → swans, happier → gladder), keeping capital letters.
  - *Vocabulary*: words worth **learning** (not everyday, not obscure), a fresh batch of twenty at a time, each with its part of speech and
    a one-line meaning. Choose how rare (uncommon / rare / very rare), the part of speech and the subject. Enter opens the full entry in
    Lookup; `l` marks a word *Learning* (it goes to My words), `k` marks it *Known* (never offered again). How common a word is comes from the
    offline `wordfreq` package.
  - *My words*: the words you are learning, with their meanings; Enter looks one up, `k` Known, `d` remove, `f` flashcards (the word first,
    Space shows the meaning).
  - *Add to this universe's word list* (`w` on any word in Lookup or My words): pick the slot (job, thing, place...) and the word goes on the
    universe's own list, so the Wheel and the Builder roll with it.
  - *Overused*: a story's most frequent words (everyday words left out) and words repeated close together, with where they are;
    Enter on a place opens the Writer there.
- **Writer card:** **F7** on the word under the cursor (or a selection) opens a card grouped by meaning, then the full list of
  similar words, scrollable, with a filter (`/`). Enter looks a word up (`b` back, `n` forward); **`r` replaces** the word you were
  on (same form, capitals kept), **`i` inserts** the word at the cursor, **`c` copies** it. **F6** looks up a typed word and works
  the same way. Also in the F12 menu and the right-click menu.
- **Find and replace:** **Ctrl+R** in the Writer (match case, whole word, replace one or all, a count). Keys are in Settings > Keys.
- **Keys in the Writer:** Ctrl+Z / Ctrl+Y undo and redo (also in the right-click menu), Ctrl+Backspace (Ctrl+H) deletes the previous
  word, Shift+Home / Shift+End select to the start / end of the visible line. The other Ctrl keys of Neovim's Insert mode (Ctrl+U, W, T, D,
  O, K, E...) and unused function keys do nothing, so they can't delete or type anything by accident.
- Command line: `storywheel define WORD`, `storywheel thesaurus WORD`, `storywheel lookup WORD`, each with `--json`.

### Command line (all with `--json` where it makes sense)

    storywheel                       reopen where you left off        storywheel wheel | builder | writer
    storywheel universes             list universes (new NAME)        storywheel entity list UNIVERSE --json
    storywheel story list|show       stories in your universes        storywheel promote N --new NAME
    storywheel manuscript export|text UNIVERSE/STORY

## The Wheel in detail

### Wheel storage

- Stories: `~/.storywheel/stories/` (one JSON file each)
- Ratings: `~/.storywheel/ratings.json`; recent picks: `~/.storywheel/recent.json`
- Markdown: `~/storywheel/`, rewritten on every keep

Point the markdown straight into your vault so stories show up in Obsidian as
you roll (add this to `~/.bashrc`):

    export STORYWHEEL_OUT=~/path/to/vault/Stories

## Your universes

The old single pool (`~/.storywheel/universe.json`) is gone: when you first start, it is moved into a universe called
"Loose Ends" (characters from protagonist entries, places from setting entries, notes for the rest), and the old file is
kept as `universe.json.migrated-DATE`. Universes now live in the library (see "The whole program" above): tick them in the
Wheel's panel to let the generator draw from them, and press `u` to save a piece into one.

## Make it yours

Stories are **assembled from parts**, not dealt from a deck of ready-made ideas. Two
kinds of file, both plain JSON:

* **Atoms** (`storywheel/data/lists/<slot>/<name>.json`) are short pieces: a noun
  phrase, a verb, a prize, a deadline, a motive. Five words at most, no full clauses.
* **Templates** (`storywheel/data/templates/<slot>/<name>.json`) are generic sentence
  frames with at least two slots, like `{first} {ACT_PERSON} {SOMEONE} {MANNER}`. A
  template may not hold more than six fixed words in a row, so the ideas come from
  the atoms and not from the frame.

One template with three slots over pools of fifty atoms is over a hundred thousand
sentences. Add atoms freely; they improve every template that uses them. Genre
lives on the atoms (a `western` verb, a `fairy tale` prize), so a template written once
reads right in any genre.

Your own files go in `~/.storywheel/lists/<slot>/`, `~/.storywheel/templates/<slot>/` and
`~/.storywheel/structures/`. They are merged with the built-in ones, and a file at the
same path as a built-in one replaces it. Run `pipx install --editable .` to edit the
built-in files and see changes at once.

`pytest` includes a lint that enforces those rules on every file, so a line that is too
long, a clause where an atom should be, or a frozen template fails the build.

### An atom list

    { "_note": "anything you like",
      "slot": "act_person",
      "tags": ["general"],
      "entries": ["trusted", "lied to", "teamed up with",
                  {"text": "outdrew", "tags": ["western"]}] }

* `slot` is the kind of part: `someone`, `thing`, `message`, `disaster`, `hiding`, `close`,
  `landmark`, verbs (`act_person`, `act_thing`, `act_place`, `act_message`, `act_event` in
  the past tense; `do_thing`, `do_person` in the base form; `habit_thing`, `habit_person`,
  `habit_place` in the present), and abstractions (`prize`, `deadline`, `motive`, `vice`,
  `value`, `temptation`, `feeling`, `manner`, `topic`, `crime`, `loss`). Many lists can share
  a slot. Verbs take their object directly ("trusted" + a person), and atoms never say
  "their" or "them", because they are reused in many sentences.
* `tags` describe the list's flavor. Plain strings inherit them. An entry written as
  `{"text": ..., "tags": [...]}` carries its own tags instead.
* A list can say `"generator": "faker.city"` instead of `entries`; it is then made up
  at run time. Built in: `faker.first_name`, `faker.last_name`, `faker.city`, `faker.job`,
  `wonderwords.adjective`, `wonderwords.noun`, `wonderwords.verb`. (Faker lists are
  tagged `modern`.)
* Invented names skip anything under four letters and ordinary dictionary words
  (no "Thistle" or "Bell" from a surname list).
* A list of names can say `"markov": 0.5`: that share of picks is then a new name
  invented by a small Markov-chain name maker trained on the list's own entries (so
  `Calloway, Hollis, Pruitt` can yield `Callis` or `Pruden`); the rest are the real
  entries. Good for name lists with 40+ entries.
* Place names can be built from parts. A `place` entry may contain slots, e.g.
  `"{PLACE_ADJ} {PLACE_FEATURE}"`, so a few dozen words make thousands of towns.

### A template

    { "slot": "reaction", "tags": ["general"],
      "entries": ["{ACT_PERSON} {SOMEONE} {MANNER}",
                  "made a deal with {SOMEONE} for {PRIZE}",
                  {"text": "saddled up and rode to {landmark} {MANNER}", "tags": ["western"]}] }

* `{UPPERCASE}` is an atom slot: a fresh draw from the slot of the same name every time
  it appears (`{SOMEONE}` draws from the `someone` lists). `{ODDITY}` (a random
  adjective and noun) and `{ALLITERATION}` are built in.
* `{lowercase}` refers to what the story has already kept (`{first}`, `{name}`, `{place}`,
  `{landmark}`, `{motif}`, `{rival}`, `{want}`, `{need}`, `{flaw}`, `{secret}`...) and stays
  the same throughout. If the story doesn't have it yet, it's invented on the spot from
  the slot of that name. `want`, `need`, `flaw`, `secret` and `rumor` are themselves
  template slots, so even the character's inner life is assembled.
* The template slots are `title`, `premise`, `twist`, `want`, `need`, `flaw`, `secret`,
  `rumor`, and the beats of each structure (below).

### Making sentences make sense: features and frames

Random parts can be grammatical and still meaningless ("enchanted the wicked stepmother",
"the hot springs was built over a black stallion"). So atoms carry a few **features**, and
frames **require** them. The whole vocabulary is small and lives in `storywheel/frames.py`:

| | Feature | Means |
|---|---|---|
| things | `portable` | one person can carry it (the default) |
| | `buryable` | can be buried or hidden underground (the default) |
| | `magic` | magical; for a person, able to do magic |
| | `valuable` | worth money |
| | `living` | an animal: not buried, burned or locked in a box |
| | `bulky` | too big for a pocket or a small hiding place |
| | `paper` | letters, maps, deeds, books: can be forged or copied |
| people | `human` | a person (the default for `someone`) |
| | `creature` | not human: a talking fox, a troll |
| | `friendly`, `threatening` | kindly, or dangerous |
| | `authority` | holds office or power: a sheriff, a queen |
| places | `built`, `natural` | a made structure, or not |
| | `indoor`, `outdoor` | roofed, or open air (the default for landmarks) |
| | `diggable` | has ground something can be buried in |
| disasters | `manmade` | caused by people (a robbery, a feud) |
| | `strikes` | can hit a place (weather, plague, war), unlike "the death of the king" |
| messages | `physical` | something you can hold (the default for messages) |
| prizes | `material`, `social`, `inner` | owned, a standing among people, or not something to be given |
| verbs | `mundane` | an everyday action: what routines are made of |
| | `gentle` | a kind or reconciling act, for endings |
| | `stows`, `trades` | puts something somewhere; gives something up for something |
| manners | `speech`, `carrying`, `feeling` | a spoken manner ("in whispers"), one that needs something in hand ("with drawn steel"), a state of mind ("in silent dread"). Drawn only where a frame asks for it, e.g. `{MANNER:speech}` |
| anything | `plural` | takes "are" and "were": "the stockyards", "two scarred brothers" |

An atom lists its own features (a list sets defaults for its entries); anything not listed
gets its slot's default:

    {"text": "a black stallion", "features": ["living", "valuable"]}

**Verbs say what they need** of whoever does them and whoever they are done to. Requirements
are lists: `"buryable"` has it, `"!living"` must not, `"magic|authority"` either:

    {"text": "buried",    "object": ["buryable"]}
    {"text": "enchanted", "subject": ["magic"]}
    {"text": "hid",       "object": ["!living"], "features": ["stows"]}

The frame doesn't say which slots those are; the order of the sentence does. A verb's subject
is the nearest person before it who isn't already some other verb's object (the opener's
`{first}` counts) and its object is the next slot after it of the right kind (a person, thing,
place, message or disaster). A hiding place's subject is the thing it hides. So
`{first} {ACT_THING} {THING} {HIDING}` can only ever say "buried a locked box in a hollow
oak", never "buried a mule in a boot".

**Frames can demand features of any slot**, with a colon:

    {THING:buryable}     {CLOSE:human}     {PRIZE:!inner}     {SOMEONE:authority}
    {ACT_THING:mundane}  {landmark:built}  {the_thing:!living}

A frame whose requirement the story can't meet (a `{landmark:built}` frame in a story whose
landmark is a lake) is simply set aside for that story. Character fields are strict this way:
a **want** is something a person could actually get (`{PRIZE:!inner}`), a **need** is an inner
lesson only (`{DO_PERSON:inner}`: forgive, trust, make peace with), a **routine** uses only
`mundane` verbs, and a **secret** is something a person could hide.

**Agreement**: `{is}`, `{was}`, `{has}` and `{does}` agree with the noun before them ("the
stockyards **were** built over..."), and `{lies|lie}` picks its first form for a singular
subject, the second for a plural one. Present-tense verbs take only singular subjects.

The solver fills the nouns first, then picks verbs that fit the nouns it got, and starts
over when a verb has nothing to fit. **`pytest` checks every frame in the data**: each
slot can be satisfied by at least 3 atoms, and at least half of all draws succeed first time,
so a restriction can never starve a slot. A further test re-verifies every choice the
solver makes across thousands of real stories.

A **reframing** beat (kishotenketsu's *ten*) goes further: it may only reinterpret something
already established, so its templates use threads and the story's own fields, never a fresh
person, object or event.

### Nothing repeats

* **Within a story, no atom is used twice.** Each kept step records the atoms it used;
  later steps and rerolls avoid them (and a reroll avoids what the rest of its own item
  uses). Only if a list truly runs out does the rule relax.
* **Across sessions, recent picks are remembered** in `~/.storywheel/recent.json`: an
  entry isn't offered again until about half its list has been used, even next week.
  (`storywheel sample` never reads or writes it, so a seed always means the same stories.)

### Structures

A story's body is shaped by a **structure**: an ordered list of beats, each with its own
templates, built from the same atoms. Three ship in `storywheel/data/structures/`:

* **Story Spine**: Once upon a time, Every day, One day, Because of that (twice), Until
  finally, Ever since then. The fixed openers are the only frozen text anywhere.
* **Three-Act Outline**: setup, inciting incident, first turn; rising action, midpoint,
  crisis; climax, resolution.
* **Kishōtenketsu**: introduction, development, a surprising turn, reconciliation. No
  conflict required.

In a session, the **Structure** step comes right after Genre & mood; roll to see another,
`k` to keep. Changing it later rolls the story body again. `storywheel sample` picks one
at random per story; force one with `--structure three-act`.

A structure is a small file, so you can add your own:

    { "name": "five-beats", "label": "Five Beats", "blurb": "One line about its shape.",
      "show_labels": true, "order": 4,
      "beats": [ {"key": "hook", "slot": "five_hook", "label": "The hook"},
                 {"key": "dig", "slot": "five_dig"}, ... ] }

Each beat's `slot` names a template list (`templates/five_hook/*.json`). A beat may also
have an `"opening"` ("Once upon a time, ") and a `"closing"` (default `"."`).

### Threads

When a spine beat draws a {THING}, {SOMEONE}, {MESSAGE} or {DISASTER}, the story
remembers it as a **thread**. Later beats can say `{the_thing}`,
`{the_someone}`, `{the_message}` or `{the_disaster}`, which come out as "the
locked box", "the stranger": the same one, now definite. A template that uses a
thread is six times likelier while that thread exists, and never used when it
doesn't, so what "One day" brings in comes back in "Because of that" and "Until
finally". Threads are listed on the spine card, saved in the story file, and
written to the markdown under "Threads".

Rerolling the beat that introduced a thread (`f`) keeps the story straight: if
the new beat brings in a new one of that kind, the thread is updated and every
mention of the old one is swapped; if not, the old one lives on as long as a
later beat still mentions it (that mention turns back into an introduction) and
is retired when none does.

### Motif kinds

A title noun can say what kind of thing it is, so the story doesn't try to
"find the marshal" or "bury the mesa":

    "entries": ["lantern", {"text": "marshal", "kind": "person"},
                {"text": "raven", "kind": "creature"}, {"text": "mesa", "kind": "place"},
                {"text": "curse", "kind": "idea"}]

Kinds are `object` (the default), `person`, `creature`, `place`, `idea`; a whole
list can have a `"kind"` too. In templates, `{the_motif}` is "the lantern" when
the motif is an object, and otherwise falls back to the story's thing (or a fresh
{THING}). Plain `the {motif}` is for places where any kind will do. A person or
creature motif is sometimes offered as a {SOMEONE} ("the marshal rode in").

### Genres, tags and the story mix

`genres.json` gives each genre default weights for tags:

    "western": { "western": 3, "historical": 2, "rural": 1, "general": 1, "modern": 0.2 }

When you keep a genre (or two), their profiles are averaged into **this
story's mix**. Rolling a slot then works in two stages:

1. **Pick a list**, weighted by the mix. A list's weight is the *largest*
   weight among its tags (not the sum, so carrying many tags isn't an
   advantage).
2. **Pick an entry** from it, avoiding recent repeats (nothing comes back until
   about half the list has been used). Plain entries weigh 1; an entry with its
   own tags weighs what those tags weigh in the mix, so a `western` entry is
   much likelier in a western story.

**Wildcard floor:** a list the mix doesn't mention still gets a small slice of
each pick (12%, `_floor` in `genres.json`), so off-genre surprises still turn
up. Slots that repeat all through a story (rival, job, place, names, landmark)
get a lower one, 4%, set per slot under `_floors`, so an off-genre rival doesn't
appear in half the sentences. **Exclusion is absolute:** a tag or list you exclude gets weight
zero and the floor never brings it back. (One exception so rolls never come
up empty: if *every* list for a slot is excluded, the exclusions are ignored
for that slot.)

A genre name that has no profile still works: it becomes a tag with weight 3,
so `steampunk` will favor lists tagged `steampunk`. You can add profiles in
`~/.storywheel/genres.json`.

Each story keeps its own copy of the adjustments (excluded tags, excluded
lists, boosts) in its JSON file under `"mix"`. They never change the genre
profiles, so the next story in the same genre starts from the defaults.

`storywheel/steps.py` holds the step list (`steps_for`). Reorder it to change the flow,
or add a new `Step` with its own fields.

### Trying a genre mix

    storywheel sample western "fairy tale" -n 10 --seed 1

prints whole stories (title, protagonist, setting, premise, spine, twist) for
that mix without an interactive session and without saving anything. It's the
quickest way to judge a list you've just written. `--seed` makes it repeatable.

Which words belong to which genre is spelled out in `SOURCES.md`, along with
where every list came from and its license.

### Is it assembled, or dealt?

    python tools/repetition_report.py western "fairy tale" -n 200 --seed 101

rolls 200 stories in memory and reports the entries picked far more often than their
fair share, the rendered lines seen again and again (names blanked out), and any
frozen templates or over-long atoms. A healthy run has no line seen five times. The
same check runs in the test suite.

## Development

    pip install -e '.[dev]'
    pytest

### Building lists

Hand-writing a list straight into `storywheel/data/lists/` is often best. For
broad pools, scripts in `tools/` fetch raw candidates into `data/raw/` (never at
run time); trim them by hand, put the cleaned result in `storywheel/data/lists/`,
and note it in `SOURCES.md`. Check a source's license before using anything from
it. For example, `python tools/fetch_corpora.py` gets two files from the CC0
corpora repository.
