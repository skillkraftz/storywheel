# The Universe Builder
The Builder is where a kept idea grows into a world: characters, places, things, groups and notes, with the generator on hand to fill any field. It should feel like a desk covered in index cards. Open a universe on the left, pick a story to see its outline, scenes and notes, and open it in the Writer (F3) when you want to write.
## Keys
### BuilderScreen | Everywhere in the Builder
roll_blank: Roll every blank field of the selected entity (never changes what you wrote)
roll_field: Roll the highlighted field with the generator
write_field: Write the highlighted field by hand
new_entity: New entity of the type on the current tab (starts blank)
delete_entity: Delete the entity (asks first; it goes to the library's .trash)
rename: Rename the entity; shows every match in your notes, outlines and manuscripts first
reroll_all: Roll the whole entity again (asks first)
custom_field: Add your own field to this entity (write-only)
rate(1): Like the value (liked wording is used more in later rolls); - dislikes it (used less)
rate(-1): Dislike the value (used less)
tab(0): Show the Characters tab
tab(1): Show the Places tab
tab(2): Show the Things tab
tab(3): Show the Groups tab
tab(4): Show the Notes (entity type) tab
rtab('outline'): Story panel: the Outline tab
rtab('scenes'): Story panel: the Scenes tab (Enter on a scene opens the Writer there)
rtab('notes'): Story panel: the story's own notes
new_universe: New universe
universe_settings: Universe settings: genre leanings, exclusions, boosts, its own word lists
story_settings: Story settings: what this story sets for itself (the rest follows Settings; the format is on the story form, m)
global_settings: Your details (author, address...): opens Settings > You
overview: Show the universe overview in the top box
fix_names: Fix names written in the wrong capitals ("Locked box" to "a locked box"), with a preview
writer: Write the open story in the Writer
export: Export the open story (docx, odt, pdf, md, txt)
copy_manuscript: Copy the manuscript to the clipboard as plain text
new_story: New story (no Wheel draft behind it): a form with its title, format, structure, genres and target length, all picked from lists
story_form: Change the open story's format, structure, genres and target length (the same form; it warns when the Writer would open a different file)
entity_notes: Edit the selected entity's own notes, under its card
add_beat: On the outline: add another of the beat under the cursor, where the structure lets it repeat
remove_beat: On the outline: remove one of the repeated beat
start_script: A screenplay: start script.fountain from the outline (the beats become sections and synopses, which do not print); an existing script with scenes is left alone
new_version: New version of the open story in another format (a short story AND a screenplay), from the same outline: a form with what to copy
version(1): Move to the next version of the open story (] ; stories made as versions of one another)
version(-1): Move to the previous version of the open story ([)
focus_card: Back to the card
toggle_story: On a narrow terminal: take turns between the Story panel and the cards
### StoryOptions | The stories list
act('write'): Write the story in the Writer
act('delete'): Delete the story (asks first)
act('export'): Export the story
act('backups'): Look at the story's backups, and restore one
act('form'): Format, structure, genres and target length of this story
act('version'): New version of this story in another format
### UniverseList | The universes list
act('new'): New universe
act('rename'): Rename the universe
act('delete'): Delete the universe and everything in it (asks first)
## Mouse
- Click a field: roll it. Right-click: write it. Scroll over a field: step through its earlier values.
- ▲ ▼ at the end of a value rate it; ✎ marks a field the generator can't fill, so write it yourself.
- In the Outline (Story panel) a click selects, the wheel scrolls, right-click or e edits the selected row and f rolls the beat again. The entity keys (Space, R, + and -, n, d) do nothing there. A click on a scene (Scenes tab) opens the Writer there.
## Entities
The tabs (keys 1 to 5) are Characters, Places, Things, Groups and Notes. Every field has a history; the wheel steps through it. Roll results use the universe's genre leanings, the entity's other fields and the existing entities (a rival, owner, parent place or leader can be a real entity). Links hold the other entity's id, so renaming never breaks them.
## Stories
The left column lists the universe's stories. +Story makes a blank one; a Wheel story arrives from the Wheel (Send to Builder). The large Story panel under the list has the outline (title, premise, structure, beats, twist, settings), the scenes (with their first lines and word counts) and the story's own notes. On a narrow terminal (under 150 columns) the left column shows only a short summary of the story, and the Story panel takes turns with the cards, at full width: 6 7 8 or backslash show it, Esc or 1-5 bring the cards back.
## Versions
The same story can exist in several formats: a short story AND a screenplay, say. A version is a separate story in the same universe, in its own folder with its own manuscript; the versions of one story share a family id in story.md. Press v (or the New version button under the stories list) for the form: a title, the format, a target length and a checklist of what to copy: the outline sections, the story notes, the Wheel draft it came from (seed.json), the genres and the structure with its beats (all ticked), and the manuscript (not ticked). Characters, places, things, groups and notes belong to the universe, so every version already shares them. What is ticked is copied once, and after that the versions are separate: editing one outline changes nothing in the other.

If the structure of the story doesn't fit the new format (a Story Spine for a feature film), its beats are copied as they are and the new format's own structure is added with blank beats, so nothing is lost and you map the beats by hand.

Copying the manuscript is always a rough start. Prose to prose copies the files. Prose to a screenplay writes every paragraph into script.fountain as action, with a forced scene heading for each scene break, and a note at the top. A screenplay to prose turns each scene heading into a named scene and the action and dialogue into prose paragraphs ("Words," Name said.). Expect to rewrite them.

The stories list shows a family under one title, with a row for each format and its words or pages. ] and [ move to the next and previous version of the open story. From the command line: `storywheel story version UNIVERSE/STORY --format KEY`. Renaming or deleting one version never touches the others (a delete goes to .trash).
## Extra files
A file in a story's manuscript folder that storywheel did not make (a copy from another tool) is never part of the manuscript. The Scenes tab shows it with Open, Delete (to .trash) and Ignore.
## Leaving
q goes back to the mode you came from. Q quits storywheel (asks first).
