# Structures
A structure is the shape of a story's body: an ordered list of beats, each filled from its own templates. Pick one in the Wheel's Structure step, or on the Builder's story form (+ Story, or m on a story), where a story's structure is also changed.
## The ones that ship
The Story Spine ("Once upon a time... Every day... Until one day... Because of that... Until finally..."), a Three-Act Outline, and Kishotenketsu (introduction, development, twist, conclusion), for a short story or a novel (the Story Spine and Kishotenketsu also for flash fiction), and, for particular lengths:
- **Novel:** Save the Cat (15 beats), the Hero's Journey (12), Seven-Point (7).
- **Short story and novel:** Freytag's Pyramid (the tragic shape: exposition, rising action, climax, falling action, catastrophe, denouement).
- **Flash fiction and short story:** Single Moment (before, the moment, after), Circular Story (it ends where it began, at the opening image, changed) and In Medias Res (start in the thick of it, go back, return to the moment).
They reuse the Three-Act frames wherever a beat means the same; Theme stated, Debate, the mentor (also Save the Cat's B story), the Hero's reward, the circular opening and echo, and the in-the-thick opening have frames of their own.
## Repeatable beats
Some beats can repeat: the Story Spine's "Because of that" 1 to 4 times, the Three-Act trials 1 to 4, Kishotenketsu's development 1 to 3. In the Wheel press A on the story body to add another of the beat under the cursor and X to remove one (the +Beat and -Beat buttons do the same); in the Builder's outline use A and X on a beat. Threads (a person, thing, message or disaster introduced in one beat) keep working across the new beats.
## Screen structures
Feature Film (three acts in eight sequences, about 110 pages) and Short Film (about 12 pages) are for screenplays. They fit only their format: in the Wheel's structure step choose the format first (click it, or f or e on it: short story, novel, screenplay as a feature film or a short film), then roll or pick (e) a structure among those that fit it. In the Builder the story form (+ Story, or m on a story) works the same way. A story on a screen structure becomes a screenplay when it reaches the Builder, and P there starts its script from the outline. See the Screenplays page.
## Your own
Structures are JSON files in ~/.storywheel/structures/ with the same shape as the ones in the package (data/structures). A beat can say how many times it may repeat with "repeat": {"min": 1, "max": 3}.
## In the Builder and the Writer
A promoted story keeps its beats in its outline. In the Writer, Ctrl+O shows the outline (title, premise, structure, beats, twist) in a floating window.
