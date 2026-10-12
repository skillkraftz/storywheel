# Grammar checking
Optional, off by default. A local LanguageTool server checks the paragraphs you change in the Writer. Nothing is sent anywhere.
## Setting it up
Needs Java 11 or newer (sudo apt install default-jre-headless). Then storywheel grammar install (downloads LanguageTool, about 200 MB, the only network use besides the dictionary) or storywheel grammar install --from FILE.zip. Turn it on in the Writer menu or Settings > Grammar. storywheel grammar status says what is missing; start and stop run the server by hand (it starts when the Writer needs it and stops when the Writer closes).
## Using it
A moment after you stop typing, the paragraph you changed is checked. Problems have an orange wavy underline. Right-click one for the message, the fixes, Ignore this one (kept per story) and Turn off this rule. F10 jumps to the next problem and Shift+F10 lists them (change the keys in Settings > Keys).
## What it is not
It is LanguageTool's free rules, not the Premium rules of the Google Docs extension. Without the optional n-gram data (below) the confused-word checks that need it are missing. Style, typo and typography categories are off by default; each category is a switch in Settings > Grammar.
## The n-gram data (optional)
LanguageTool can use word-frequency data (n-grams) to tell their from there, your from you're, then from than, by weighing which one the sentence needs. The English set is about 8 GB zipped and 15 GB unpacked, so it is optional and belongs to one computer: the folder is the machine-only setting grammar_ngrams_dir (settings.local.toml, shown in Settings > Grammar with its status). It wants an SSD: status warns when the folder is on an SD card (/dev/mmcblk), which is allowed but slow.
storywheel grammar ngrams install downloads it (the only time the download happens; --from ZIP uses a zip you copied over, --dir FOLDER chooses where it goes). It checks the free disk space before downloading and again before unpacking, and sets the folder that contains en/. storywheel grammar ngrams status says whether it is in use, and storywheel grammar ngrams remove deletes it (after asking). When it is set the server starts with --languageModel and the Confused words switch in Settings > Grammar stays on, since the n-gram rules live in that category.
## Memory
The server needs about 760 MB with the default 512 MB heap; the memory limit and port are machine settings.
