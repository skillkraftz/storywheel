# storywheel

A personal writing program for one writer, from "I have nothing" to "a manuscript ready to submit", in one full-screen terminal program:

| Key | Mode | For |
|---|---|---|
| **F1** | The Wheel | Roll a story idea piece by piece; keep what clicks |
| **F2** | The Universe Builder | Grow it into a world of characters, places, things, groups, notes and stories |
| **F3** | The Writer | Write it in Neovim, set up as a quiet writing room; export a Shunn manuscript |
| **F4** | Settings | You, your goals, how everything looks and works |
| **F5** | Words | Dictionary, thesaurus, rhymes, words to learn, words your story uses |

`storywheel` with no arguments reopens exactly where you left off. Everything you keep is plain files (markdown with frontmatter), so the
library folder is also a valid Obsidian vault.

**To use it, read the manual: [docs/manual.md](docs/manual.md)** (it describes version 0.20.0). In the program, `?` opens the help for the
screen you are on, and `storywheel help` prints the same pages.

## Install

You need a Linux desktop terminal (kitty is best), Python 3.9+ with pipx, and **Neovim 0.10 or newer**. Everything else is optional and says
so when it is missing: LibreOffice (.odt and .pdf export), a clipboard tool (xclip, wl-copy), Java (grammar checking). pandoc is not needed.

On a new Debian, Ubuntu or Raspberry Pi OS machine (x86_64 or arm64), from this folder:

    ./install.sh              # --dry-run shows what it would do; --yes accepts the defaults

It installs what is missing (the official Neovim release goes into `~/.local` when the distribution's is older than 0.10), installs
storywheel, and runs `storywheel setup`: a short questionnaire for your details, folders, the Writer's kitty window and the dictionary.
By hand: `pipx install .` (or `pipx install --editable .` to edit the data files and see changes at once), then `storywheel setup`.

The dictionary (about 40 MB, the only time storywheel uses the network) comes with `storywheel dictionary install`. Without it, Words,
the Writer's lookup card and the big spelling list say so and do nothing.

## Update

`storywheel update` compares the installed version with the one in the folder storywheel was installed from (a git checkout with a remote is
fetched and fast-forwarded first), reinstalls when they differ, then runs migrations and rebuilds the dictionary index. It says what it
compared and never overwrites local changes. `storywheel update --check` only reports. `storywheel --version` shows the version; CHANGELOG.md
lists what each version added.

storywheel does not sync and knows nothing about syncing: your library and manuscripts are plain files that any tool can carry. What
belongs to one machine is in `~/.storywheel/settings.local.toml`; `settings.toml` can be copied between machines.

## Where things live

| What | Where |
|---|---|
| Library (universes, entities, stories, manuscripts) | `~/Writing/storywheel` (Settings > Library, or `STORYWHEEL_LIBRARY`) |
| Exports | `~/Writing/<Title>/` (Settings > Export, or `STORYWHEEL_MANUSCRIPTS`) |
| Wheel drafts, settings, ratings, dictionary, trash | `~/.storywheel` (`STORYWHEEL_HOME`) |
| Your own atom lists, templates and structures | `~/.storywheel/lists/`, `templates/`, `structures/` |

Deleting anything moves it to a `.trash` folder first; the Writer keeps rolling backups. See chapter 7 of the manual.

## The command line

Most of the work is done in the program. For scripts and checks there are commands such as `storywheel universes`, `entity list UNIVERSE --json`,
`story show UNIVERSE/STORY --json`, `manuscript export UNIVERSE/STORY --format docx`, `exports status` and `backups list`; Appendix A of the
manual lists them, and `storywheel --help` shows them all.

## Making the generator your own

Stories are assembled from short atoms and sentence frames kept as JSON in `storywheel/data/`. How to add lists, templates, structures and
genres is in [docs/generator.md](docs/generator.md).

## Development

One-time setup (`.venv/` is ignored by git):

    python3 -m venv .venv
    ./.venv/bin/pip install -e '.[dev]'

Then, from the repository root:

    ./.venv/bin/python -m pytest -m "not slow" tests/test_<area>.py    # while working: only the tests of what changed
    tools/fulltest.sh                                                   # end of a batch: everything, in parallel, then the serial tests

`tools/fulltest.sh` needs nothing else: it uses `./.venv/bin/python` when that exists and points `STORYWHEEL_HOME` and `STORYWHEEL_LIBRARY` at fresh
temporary folders unless you have set them, so it never touches `~/.storywheel` or `~/Writing`. Any other command that runs storywheel while
developing must set those variables (and `STORYWHEEL_MANUSCRIPTS`) first. Every test has a time limit (`pytest-timeout`, 10 minutes), so a hang
is a failure naming the test. Tests that start the Writer use the `nvim` on your path; `STORYWHEEL_NVIM=/path/to/nvim` picks another.

The project's rules and decisions are in CLAUDE.md; the feature inventory is FEATURES.md, known problems ISSUES.md, ideas BACKLOG.md, the
latest sweep's report REPORT.md, and data sources and licenses SOURCES.md.
