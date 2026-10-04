# Grammar checking
Optional, off by default. A local LanguageTool server checks the paragraphs you change in the Writer. Nothing is sent anywhere.
## Setting it up
Needs Java 11 or newer (sudo apt install default-jre-headless). Then storywheel grammar install (downloads LanguageTool, about 200 MB, the only network use besides the dictionary) or storywheel grammar install --from FILE.zip. Turn it on in the Writer menu or Settings > Grammar. storywheel grammar status says what is missing; start and stop run the server by hand (it starts when the Writer needs it and stops when the Writer closes).
## Using it
A moment after you stop typing, the paragraph you changed is checked. Problems have an orange wavy underline. Right-click one for the message, the fixes, Ignore this one (kept per story) and Turn off this rule. F10 jumps to the next problem and Shift+F10 lists them (change the keys in Settings > Keys).
## What it is not
It is LanguageTool's free rules, not the Premium rules of the Google Docs extension, and without its large n-gram data. Style, typo and typography categories are off by default; each category is a switch in Settings > Grammar.
## Memory
The server needs about 760 MB with the default 512 MB heap; the memory limit and port are machine settings.
