# Foundation sweep: report

_Updated after each area. Status: **Works** / **Partial** / **Stub** / **Not started**._

## 1. Checklist

### Storage and universes (tag `foundation-storage`)
| Item | Status | Notes |
|---|---|---|
| Library folder (STORYWHEEL_LIBRARY, default ~/Writing/storywheel) | Works | `paths.library_root()` reads the environment on every call |
| Universes as folders; entities as markdown + YAML frontmatter | Works | own small YAML reader/writer (no dependency); Obsidian-readable |
| Entity schemas as data | Works | `data/entities/*.json`; add types in `~/.storywheel/entities/` |
| Links between entities by stable id | Works | placeholder ids (`character-1`) become real ones once named, links follow |
| Migration of universe.json into "Loose Ends" | Works | old file kept as `universe.json.migrated-DATE`; runs from `storywheel universes` (and, later, at app start) |
| Global settings in settings.toml | Works | author, address, email, phone, font, goals; story settings fall back to them |
| (extra) `universes`, `entity`, `story` commands with `--json` | Works | for the Writer's Lua side and other programs |

### Promotion (Wheel -> Builder) (tag `foundation-promotion`)
| Item | Status | Notes |
|---|---|---|
| Leaving the Wheel with a kept story shows the "bringing this into the Universe Builder" message: new / existing / not now | Works | in the app (QuitScreen) and in `--plain`; a story with nothing kept just asks Keep or Delete; Delete the draft is also offered |
| Promotion creates entities + outline per the table, with a preview, merge offers for same-name duplicates | Works | preview lists every item; Enter on a yellow duplicate row switches merge / create another; merge only fills blank fields |
| Past stories show which drafts were promoted and can promote later | Works | `⇢universe` marker, `P` key / Promote button; a draft can only be promoted once |
| (extra) `storywheel promote N --new NAME / --universe SLUG [--dry-run] [--json]` | Works | |

Not done here: after promotion the app records `app.next = ("builder", ...)`, but there is no Builder to go to yet (next area).
### Universe Builder (tag `foundation-builder`)
| Item | Status | Notes |
|---|---|---|
| Left: universes (create, rename, delete with confirm) and their stories | Works | delete moves to `.trash`; story list opens an outline, `w` writes (Writer not connected yet) |
| Middle: overview / outline boxes + tabs Characters, Places, Things, Groups, Notes with entity cards | Works | the tabs are a `Tabs` bar over one list + card (keys 1-5); boxes are editable (right-click / e) |
| Right: notes (editable, saved as you type), links both ways, appearances | Works | appearances = recorded at promotion, or a whole-word name match in the outline/manuscript |
| New entities blank; click/f rolls, right-click/e writes, space rolls blanks, per-field history + wheel | Works | history is kept for the session (not saved to disk) |
| Rolls use the universe's mix, the entity's other fields, and existing entities | Works | rival / owner / parent / leader link to real entities; universe entities as *atoms in the Wheel* is the next area |
| Write-only fields marked; custom per-entity fields | Works | ✎ marks write-only; `c` adds a field |
| Rename with a preview (notes, outlines, manuscripts), confirm all or one at a time | Works | matches are toggled one by one (Enter), `a` all, `n` none, `p` apply; case-sensitive whole-word, possessives handled; any name change (rolled, scrolled, written) goes through it |
| Universe settings: genre leanings, exclusions/boosts, own lists folder | Works | `s`; own lists are files you drop in `<universe>/lists/` (used by Builder rolls); no in-app list editor |
| Ratings on entity fields | Partial | recorded (+/-, ▲▼) but do not yet affect Builder rolls (no frame/atom provenance for entity fields) |
| Entry point | Partial | `storywheel builder [universe] [story]`; plain `storywheel` still opens the Wheel until the switching area |
### Universes in the Wheel (tag `foundation-universes-wheel`)
| Item | Status | Notes |
|---|---|---|
| Universe panel becomes a checklist of universes to draw from, saved per draft | Works | `v` focuses it; Enter / space / click ticks; stored as `story["universes"]`; a draft started from the Builder (`W`) starts with that universe ticked; no startup question any more |
| Selected universes' entities become atoms in matching slots, boosted | Works | characters -> `someone`, `close`, `rival`, `first_name`, `last_name`; places -> `place` / `landmark`; things -> `thing`; tagged `universe:<slug>` and boosted by the universe's `atom_boost` (default 1.5, editable in universe settings); their genre leanings blend into the mix; a protagonist taken from a universe is not also drawn as a stranger |
| no / mix / only whole-step candidates from selected universes | Works | protagonist <- characters, setting <- places; blanks are completed with an ordinary roll; the panel still previews an entity and "use in this story" adds a candidate without touching kept steps |
| `u` saves a piece into a universe | Works | protagonist -> character, setting -> place (+ landmark), other -> note; merges by name |
| Past stories: send protagonist / setting to a universe | Works | asks which universe |

Rough edges: a character used in the `rival` slot reads as "the Sheriff Lund" (the templates say "the {rival}"); removing an entity from a universe is done in the Builder only (`U` says so).
### Writer (Neovim) (tag `foundation-writer`)
| Item | Status | Notes |
|---|---|---|
| Self-contained config via NVIM_APPNAME, shipped in the package | Works | `storywheel/nvim/` linked (or copied) into `~/.storywheel/nvim/config/storywheel-writer`; data/state/cache folders are under `~/.storywheel/nvim/`; no plugins at all; needs Neovim 0.10+ and says so if missing |
| Full screen, centered column, minimal statusline, soft wrap, mouse | Works | tests check the layout numbers; the *look* is in the manual script (two blank pad windows make the margins) |
| Ctrl+I / Ctrl+B italic and bold, markup concealed | Partial | Ctrl+B and Alt+B bold, Alt+I italic work everywhere; **Ctrl+I only where the terminal reports it apart from Tab** (kitty, foot, WezTerm, ghostty are assumed; anything else is not mapped, so Tab stays Tab). `Space k` / `:SWKeyCheck` asks your terminal and remembers the answer. This machine's terminal is a VTE one (GNOME Terminal family), which sends Ctrl+I as Tab, so expect to use Alt+I |
| Virtual first-line paragraph indent; Enter starts a new paragraph | Works | the indent is virtual text (nothing typed); Enter inserts a blank line and never stacks them |
| Scene break key (`* * *` stored, centered) | Works | Alt+S; centered with a virtual-text overlay |
| Show invisibles, typewriter, spellcheck toggles | Works | `Space i / t / s`; remembered between visits; defaults from settings.toml |
| Scene sidebar with first lines: jump, add, rename, reorder | Works | `Space n` / F9; `* * *` sections appear as sub-entries |
| World peek card for the name under the cursor; name completion | Works | `Space p` / F10; completion pops up as you type a capitalised name, Tab moves through it |
| Stats: scene / manuscript / today vs goal in the statusline; stats.json | Works | words per day and per session |
| Autosave plus rolling backups | Works | on leaving insert mode, focus loss, idle, quitting; copies in `<story>/.backups/<date>/HHMM-<scene>.md` when changed, at most every 15 minutes, 30 days kept |
| Story settings read from settings.toml, editable from the Builder | Works | the Writer reads them through `storywheel story show --json`; saving settings.toml inside the Writer applies it at once; the Builder's `S` edits them |
| (extra) copy manuscript as plain text; `:SWExport` | Partial | copy works; `:SWExport` calls the export command, which arrives in the Export area |
### Switching and state (tag `foundation-switching`)
| Item | Status | Notes |
|---|---|---|
| Builder hotkey suspends the app and opens the story in the Writer; a Neovim hotkey saves and returns; the Builder refreshes | Works | F3 (or `w`) in the Builder -> Neovim; F2 in Neovim saves everything and quits back; the Builder reloads its counts and says "Back from the Writer". Tested for real in a pseudo-terminal (Builder -> Neovim -> typed text -> F2 -> Builder) |
| Neovim restores open scenes and cursor per story | Works | per-story JSON under `~/.storywheel/nvim/state/.../sw/` (not Vim sessions) |
| state.json; plain `storywheel` reopens exactly where I left off | Works | mode, draft and step, universe, story, tab, entity; `storywheel` with no arguments in a terminal reopens it (the Wheel the first time); `wheel`, `new`, `builder`, `writer` commands reach each mode directly; without a terminal `storywheel` is still the plain prompt |
| Consistent mode keys (F1 Wheel / F2 Builder / F3 Writer) in every help screen | Works | Wheel help, Builder help, Writer help; promotion and a Writer "F1" carry on into the next mode |

Not tested for real: the *look* of the terminal handing over between the Textual app and Neovim (flicker, scrollback) -- see the manual script.
### Export -- Not started

## 2. Tests added

| Area | Tests |
|---|---|
| Storage (`tests/test_storage.py`) | 25 |
| Promotion logic and CLI (`tests/test_promote.py`) | 12 |
| Promotion in the app (`tests/test_promote_ui.py`) | 10 |
| Filling fields and renames (`tests/test_fill_rename.py`) | 17 |
| Builder in the app (`tests/test_builder.py`) | 28 |
| Universes in the Wheel (`tests/test_universes_wheel.py`) | 32 |
| Writer, headless Neovim plus one real-terminal run (`tests/test_writer.py`) | 55 |
| Switching and state, including real-terminal hand-overs (`tests/test_switching.py`) | 21 |
| (removed) the old global-pool panel tests, replaced by the above | -14 |

## 3. Manual test script
_(filled in as areas land)_

## 4. Known issues, decisions, open questions
- Deleting a universe, entity or story moves it to `<library>/.trash/` rather than destroying it (see Decisions log in CLAUDE.md).
