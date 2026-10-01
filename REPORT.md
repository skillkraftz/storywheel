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

### Promotion (Wheel -> Builder) -- Not started
### Universe Builder -- Not started
### Universes in the Wheel -- Not started
### Writer (Neovim) -- Not started
### Switching and state -- Not started
### Export -- Not started

## 2. Tests added

| Area | Tests |
|---|---|
| Storage (`tests/test_storage.py`) | 25 |

## 3. Manual test script
_(filled in as areas land)_

## 4. Known issues, decisions, open questions
- Deleting a universe, entity or story moves it to `<library>/.trash/` rather than destroying it (see Decisions log in CLAUDE.md).
