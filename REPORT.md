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
### Universe Builder -- Not started
### Universes in the Wheel -- Not started
### Writer (Neovim) -- Not started
### Switching and state -- Not started
### Export -- Not started

## 2. Tests added

| Area | Tests |
|---|---|
| Storage (`tests/test_storage.py`) | 25 |
| Promotion logic and CLI (`tests/test_promote.py`) | 12 |
| Promotion in the app (`tests/test_promote_ui.py`) | 10 |

## 3. Manual test script
_(filled in as areas land)_

## 4. Known issues, decisions, open questions
- Deleting a universe, entity or story moves it to `<library>/.trash/` rather than destroying it (see Decisions log in CLAUDE.md).
