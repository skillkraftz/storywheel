"""Moving the old single pool (~/.storywheel/universe.json) into a universe called "Loose Ends"."""
import datetime
import json
import shutil

from . import paths, schemas, vault

LOOSE = "Loose Ends"
# which old step key becomes what
CHARACTER_KEYS = {"protagonist"}
PLACE_KEYS = {"setting"}


def migrate_manuscripts():
    """Old stories kept one file per scene; a short story now has one manuscript file with scene markers.
    Merges every such story (originals go to the story's .backups folder). Returns report lines."""
    lines = []
    for u in vault.list_universes():
        for s in u.stories():
            for message in (s.migrate_manuscript(), s.migrate_paragraphs()):
                if message:
                    lines.append(f"{u.name} / {s.title}: {message}")
    return lines


def migrate_exports():
    """Exports used to sit in each story's folder inside the library. Move them to the manuscripts folder (one folder per
    story, named '<Title> <date>.<ext>', the date being the file's own) and say so. Returns report lines."""
    import datetime
    from . import export, paths
    moved = 0
    notes = []
    for u in vault.list_universes():
        for s in u.stories():
            old = s.exports_dir
            files = [f for f in old.iterdir() if f.is_file()] if old.is_dir() else []
            if not files:
                continue
            try:
                dest = export.export_folder(s)
            except export.ExportError as e:
                notes.append(f"{s.title}: exports left where they are ({e})")
                continue
            for f in sorted(files):
                day = datetime.date.fromtimestamp(f.stat().st_mtime).isoformat()
                stem = export.unique_stem(dest, f"{export.clean_name(s.title)} {day}", [f.suffix.lstrip(".")])
                f.replace(dest / (stem + f.suffix))
                moved += 1
            try:
                old.rmdir()
            except OSError:
                pass
    if moved:
        notes.insert(0, f"Moved {moved} export{'s' if moved != 1 else ''} out of your library to {paths.tilde(paths.manuscripts_root())} "
                        "(one folder per story).")
    return notes


def migrate_universe_json():
    """Returns a short report (a list of lines), or [] when there was nothing to do.
    The old file is kept as universe.json.migrated-<date>; running again does nothing."""
    old = paths.home() / "universe.json"
    if not old.exists():
        return []
    try:
        pool = json.loads(old.read_text(encoding="utf-8"))
    except ValueError:
        return [f"{old} is not valid JSON; left alone."]
    if not any(pool.values()):
        return []
    u = next((x for x in vault.list_universes() if x.name == LOOSE), None) or vault.create_universe(
        LOOSE, notes="Pieces saved in the old single universe, brought over by storywheel.")
    made = {"character": 0, "place": 0, "note": 0}
    for key, entries in pool.items():
        for entry in entries:
            if not isinstance(entry, dict) or not entry:
                continue
            if key in CHARACTER_KEYS:
                e = u.new_entity("character", entry.get("name", ""), {k: v for k, v in entry.items()
                                                                  if k in schemas.field_keys("character")})
                e.fields["role"] = e.fields.get("role") or "protagonist"
                u.save_entity(e)
                made["character"] += 1
            elif key in PLACE_KEYS:
                fields = {"name": entry.get("place", "")}
                for k, ek in (("era", "era"), ("landmark", "feature"), ("rumor", "rumor")):
                    if entry.get(k):
                        fields[ek] = entry[k]
                u.new_entity("place", fields["name"], fields)
                made["place"] += 1
            else:
                title = next(iter(entry.values()), key)
                body = "\n\n".join(f"**{k.replace('_', ' ').title()}.** {v}" for k, v in entry.items())
                note = u.new_entity("note", f"{key.title()}: {str(title)[:40]}", {"body": body})
                made["note"] += 1
    stamp = datetime.date.today().isoformat()
    backup = old.with_name(f"universe.json.migrated-{stamp}")
    n = 1
    while backup.exists():
        n += 1
        backup = old.with_name(f"universe.json.migrated-{stamp}-{n}")
    shutil.move(str(old), str(backup))
    return [f"Moved your old universe into the '{LOOSE}' universe: {made['character']} character(s), "
            f"{made['place']} place(s), {made['note']} note(s).", f"The old file is kept as {backup}."]
