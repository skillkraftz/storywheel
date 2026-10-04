# Backups
Your writing is never lost: the Writer autosaves, and keeps rolling backups of the manuscript.
## What is kept
Copies named HHMM-<scene>.md in <story>/.backups/<date>/, made when the manuscript changed and at least 15 minutes after the previous copy; 30 days of folders are kept. Other tools that change files (a one-file migration, quotes made straight, paragraphs made one line each) copy the old files into .backups first.
## Restoring
Builder: select a story and press b (or the Backups… button). Writer: the menu's Backups item. Command line: storywheel backups list UNIVERSE/STORY, then restore. A restore first copies the version you have now to .backups/restore-<date>-<time>/, so a restore can itself be undone.
## Deleted things
Deleting a universe, story or entity moves it to <library>/.trash/; a draft with nothing kept goes to <storywheel home>/.trash/. Nothing is destroyed.
