# The Wheel
The Wheel rolls a story idea one piece at a time: genre and mood, structure, title, protagonist, setting, premise, the story body and a twist. Roll a step, keep what clicks, reroll or write any single field yourself. Later steps read what earlier steps kept. When you have something worth keeping, send it to the Universe Builder (F2) to grow it into a world.
## Keys
### MainScreen | Everywhere in the Wheel
roll: Roll the step again (fills every field that is not locked by a keep)
keep: Keep this step and move on
edit: Edit the selected field by hand
reroll_field: Reroll just the selected field (Enter does the same)
write: Write the whole step yourself
rate(1): Like the selected line (liked wording comes up more); - dislikes it (disliked wording comes up less; press again to clear)
rate(-1): Dislike the selected line (disliked wording comes up less); press again to clear
history: Switch the history between every roll and the selected field's earlier values
mix: Flavor: which kinds of material this story leans toward or avoids
focus_universe: Go to the universe panel (bottom left)
send: Send this story to the Universe Builder (the "Belongs to" universe, or a new one)
add_beat: On the story body: add another of the beat under the cursor, where the structure lets it repeat
remove_beat: On the story body: remove one of the repeated beat under the cursor
copy_story: Copy the story so far to the clipboard as plain text
update_inputs: Update a stale candidate to what you have kept since
ignore: Dismiss a stale-candidate warning (the candidate stays as it is)
pick_format: Change the draft's format (flash fiction, short story, novel, screenplay); a structure that no longer fits is swapped, and the screen says so
new_draft: Start a new draft (asks which universe it belongs to; the one you leave is saved)
copy_draft: Make an editable copy of a promoted draft (promoted drafts are read-only)
back: Go back one step
skip: Skip this step (later steps invent stand-ins, marked as such)
universe_add: Save the selected value into a universe
universe_remove: Where to remove a value from a universe (it points you to the Builder, F2)
editor: Edit the whole step in your $EDITOR
focus_card: Back to the card from a list
### MixScreen | The flavor editor
close: Close and keep the changes
toggle: Exclude or include the highlighted tag or list
boost(1): Boost the highlighted tag; - boosts it less
boost(-1): Boost it less
boost_reset: Remove the boost
switch: Switch between tags and lists
reset: Reset to the genre's defaults
### StoryList | Past stories (bottom left)
act('delete'): Delete the story (asks first)
act('protagonist'): Use its protagonist in the draft you are on (a new candidate), or send it to a universe you choose
act('setting'): Use its setting in the draft you are on (a new candidate), or send it to a universe you choose
act('promote'): Promote the draft into a universe
### UniverseChecklist | Universe panel: which universes the generator may draw from
toggle: Tick or untick the universe
mode: Whole characters and places from these universes: no / sometimes / only
### UniverseTree | Universe panel: entries
mode: Whole characters and places from these universes: no / sometimes / only
use: Use the entry in this story (as a new candidate; nothing is kept until you press k)
## Mouse
- Click a field: reroll just that field. Right-click a field: edit it. Scroll over a field: step through its earlier values.
- ▲ ▼ at the end of a line: like or dislike it.
- Buttons under the card: Roll, Keep, Back, Skip, Flavor, +Beat, -Beat, Send to Builder (Open in Builder once sent) and New draft. Click a step to jump to it, a history row to pick it.
- To select text with the mouse while this app has it, hold Shift and drag (some terminals: Alt, or Option on a Mac).
## Format and structure
**Format first.** A new draft asks what you are writing before anything else: Flash fiction, Short story, Novel, Screenplay (feature film) or Screenplay (short film), starting on your default from Settings (Esc takes it). The card's frame always shows the format (`Genre & mood · Short story (F: format)`), and F changes it at any time: if the structure you kept no longer fits, it is swapped for the format's usual one, the story body is dropped to be rolled again, and the screen says so.
The structure step has two lines. The format is picked from a list: click it, or f or e on it. The structure is rolled (f, a click) or picked (e, right-click) among the ones that fit the format: a novel gets Save the Cat, the Hero's Journey and Seven-Point as well; a short story gets Freytag's Pyramid, Single Moment, Circular Story and In Medias Res; flash fiction gets the Story Spine, Kishotenketsu and the last three; the screen structures only for a screenplay. Nothing here is typed, so a typo can't turn into the Story Spine; a structure typed at the plain prompt must be one of the list or it is refused with the list. A story promoted to the Builder keeps its format, with that format's usual target length, and its focus and ending when they are not the usual ones. The plain prompt (`--plain`) does not ask the format first: it starts on your default, and `e format` on the structure step changes it.
## Focus and ending
Focus and ending are two more lines on the Genre step, picked from lists (click, f, or e on them), never rolled. The focus is who or what the story is about: one protagonist (the default), two leads (the Protagonist step also makes a partner), an ensemble (it also makes a company of three), a place, or no one (a mood piece). A place or no one has no protagonist: the Protagonist step is skipped (the screen says so; b goes back to it), and where the protagonist would be the story says "everyone in" the place, or "someone". Frames that read the protagonist's own job, traits, want or need are set aside for such a story. The ending is any (the default), triumph, bittersweet, tragic or open: with one picked, climax and resolution frames written for other endings are never drawn, and about six draws in ten come from frames written for the one you picked. Change either after the body is kept and the screen says which beats to reroll.
## Moving around
up and down move within a list; Tab goes to the next list (steps, card, history); Enter on the card rerolls the field, in the history picks that roll, on a step jumps there; Esc goes back to the card.
## Stand-ins and stale candidates
If you roll a step before the ones it builds on are kept (say the story body before the protagonist), it invents stand-ins and the card says so. When you later keep those steps, a candidate built on a stand-in shows a banner, "Built for Mark; your protagonist is now Stacie Anderson", with Update (swap the kept values into a copy), Reroll and Ignore (dismiss the banner; the candidate stays as it is). Rerolling one field always uses what you have kept.
## Markers on the steps
✓ kept   – skipped   ▶ current   · to do.  A yellow ● means kept, but built on a stand-in or on something that changed. A red ✗ means it refers to something that no longer exists. The right-hand column says what is wrong.
## The universe panel
Bottom left. Entries are grouped by kind; Enter opens or closes a group. "Belongs to" chooses the universe this draft will be promoted into. Tick universes the generator may draw characters, places and things from. Press Enter on an entry to preview it, then Enter or u to use it in this story (as a new candidate; nothing is kept until you press k). Editing, deleting and adding entries is done in the Builder (F2). Press Esc to close.
## Past stories
Bottom left: Enter opens one, d deletes it (asks first; it goes to the .trash folder in your storywheel home), p and s (Use protagonist, Use setting) ask what to do with its protagonist or setting: use it in the draft you are on, as a new candidate for that step (press k to keep it), or send it to a universe you choose (kept there as a character or place), P promotes it. "5/8" means five steps kept, "done" a finished one.
## Promotion and versions
The preview you see before a story is brought into a universe ends with "Also start as": the other formats (flash fiction, short story, novel, screenplay as a feature film or a short film). Enter or a click ticks one. Each tick makes another version of the story in the same universe, from the same outline, with its own manuscript; the characters, places and things are made once and shared. The story's own format is not offered. More about versions is in the Builder's help.
## Leaving
q goes back to the mode you came from (the draft is saved). Q quits storywheel: it asks whether to keep or delete the story and offers to send it to the Builder.
