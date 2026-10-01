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
### Writer (Neovim) -- Not started
### Switching and state -- Not started
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
| (removed) the old global-pool panel tests, replaced by the above | -14 |

## 3. Manual test script
_(filled in as areas land)_

## 4. Known issues, decisions, open questions
- Deleting a universe, entity or story moves it to `<library>/.trash/` rather than destroying it (see Decisions log in CLAUDE.md).
