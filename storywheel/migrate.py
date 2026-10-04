"""Moving the old single pool (~/.storywheel/universe.json) into a universe called "Loose Ends"."""
import datetime
import json
import shutil
from pathlib import Path

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
            for message in (s.migrate_manuscript(), s.migrate_paragraphs(), s.migrate_quotes()):
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


# Items an earlier version could replace with symbolic links into a folder shared between machines (`storywheel sync link`, removed in 0.4.1).
OLD_LINKED = ("settings.toml", "ratings.json", "vocabulary.json", "recent.json", "genres.json", "lists", "structures", "stories", "entities")


def migrate_sync_links():
    """Turn any of those links back into real files in the app storage. The folder they pointed into is left exactly as it was."""
    import os
    import shutil
    home, lines = paths.home(), []
    for name in OLD_LINKED:
        link = home / name
        if not link.is_symlink():
            continue
        target = Path(os.path.realpath(link))
        link.unlink()
        if target.is_dir():
            shutil.copytree(target, link)
        elif target.exists():
            shutil.copy2(target, link)
        else:
            lines.append(f"{name} was a link to {target}, which is gone; nothing was copied back.")
            continue
        lines.append(f"{name} was a link into {paths.tilde(target.parent)}; it is a real file in {paths.tilde(home)} again "
                     "(the copy it pointed to was left as it was).")
    return lines + _forget_sync_folder()


def _forget_sync_folder():
    """Drop the `sync_folder` setting an earlier version kept."""
    import re
    lines = []
    for name in ("settings.local.toml", "settings.toml"):
        f = paths.home() / name
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        new = re.sub(r"(?m)^sync_folder\s*=.*\n", "", text)
        if new != text:
            f.write_text(new, encoding="utf-8")
            lines.append("The old sync_folder setting was removed (storywheel no longer syncs anything).")
    return lines


NEOVIDE_KEYS = ("neovide", "neovide_opacity", "line_spacing")


def migrate_settings():
    """Neovide is gone: its settings become the kitty Writer's. `neovide = true` turns writer_kitty on, `neovide_opacity` becomes
    `writer_opacity`, and the old pixel `line_spacing` becomes a `writer_line_height` percent. Done once per settings file."""
    import re
    lines = []
    files = [paths.home() / "settings.toml", paths.home() / "settings.local.toml"]
    try:
        for u in vault.list_universes():
            files += [s.path / "settings.toml" for s in u.stories()]
    except OSError:
        pass
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        if not re.search(r"(?m)^(neovide|neovide_opacity|line_spacing)\s*=", text):
            continue
        values = {k: v.strip() for k, v in re.findall(r"(?m)^(neovide|neovide_opacity|line_spacing)\s*=\s*(.+)$", text)}
        size = re.search(r"(?m)^writer_font_size\s*=\s*([\d.]+)", text)
        new = re.sub(r"(?m)^(neovide|neovide_opacity|line_spacing)\s*=.*\n", "", text)
        add = []
        if values.get("neovide") == "true" and not re.search(r"(?m)^writer_kitty\s*=", new):
            add.append("writer_kitty = true")
        if "neovide_opacity" in values and not re.search(r"(?m)^writer_opacity\s*=", new):
            add.append(f"writer_opacity = {values['neovide_opacity']}")
        if "line_spacing" in values and not re.search(r"(?m)^writer_line_height\s*=", new):
            try:
                px, pt = float(values["line_spacing"]), float(size.group(1)) if size else 15.0
                add.append(f"writer_line_height = {int(max(100, min(300, round(100 + 100 * px / (pt * 1.5)))))}")
            except ValueError:
                pass
        body = new.split("\n")
        at = 0
        while at < len(body) and (body[at].startswith("#") or not body[at].strip()):
            at += 1                                              # (after the file's leading comment)
        body[at:at] = add
        f.write_text("\n".join(body), encoding="utf-8")
        lines.append(f"Neovide settings in {paths.tilde(f)} became kitty Writer settings" + (f" ({', '.join(a.split(' =')[0] for a in add)})." if add else "."))
    return lines
