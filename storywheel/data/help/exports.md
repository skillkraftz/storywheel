# Exports
Export compiles the manuscript and applies the story's format. From the Builder press x on a story, from the Writer use the menu, or from a script run storywheel exports make.
## Shunn manuscript format
The .docx follows William Shunn's proper manuscript format for a short story: 12 pt Times New Roman or Courier New, double-spaced, 1 inch margins, half-inch first-line indents, your name and address at the top left of page 1 with the word count (rounded) at the right, the title halfway down with the byline, a header of surname, title keyword and page number from page 2, a centered # for scene breaks, a centered END, and italics kept.
## Other formats
md and txt need nothing. odt and pdf are made from the .docx by LibreOffice (soffice) if it is installed; without it you get the .docx and a message. A novel starts each chapter on a new page (partial). A screenplay exports as script pages (PDF), Final Draft (.fdx) or Fountain: see the Screenplays page. A prose story can also be exported as Fountain (.fountain), its prose as action, to start adapting it.
## Screenplays
A screenplay exports as standard script pages (PDF: US Letter, 12-point Courier Prime, (MORE) and (CONT'D) across pages, a title page from Settings > You), as Final Draft (.fdx) or as Fountain (.fountain). The Screenplays guide has the details.
## Where files go
~/Writing (the manuscripts folder, a setting), one folder per story, named "Title date.ext". Re-exports on the same day add -2. Never inside the library.
## Anonymous
Settings > Export, or per story: no name, contact block, byline or surname; the header reads Title / page. With no author name set, an export is anonymous and says so.
## What each export was made from
Beside the files, .storywheel-exports.json records every export (file, format, date, the manuscript's word count and a content hash). storywheel exports status lists every story, its last export, and whether the manuscript changed since (by hash); storywheel exports make STORY exports one in its default format.
