"""Commands for the library: universes, entities and stories (all with --json for other programs)."""
import json
import sys

from . import migrate, schemas, settings, vault


def emit(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def entity_json(e, universe=None):
    out = {"id": e.id, "type": e.type, "name": e.name, "fields": e.fields, "custom": e.custom, "notes": e.body,
           "universe": universe.slug if universe else None}
    if universe is not None:                    # link fields shown as names, for the Writer's peek card
        shown = {}
        for f in schemas.get(e.type)["fields"]:
            v = e.fields.get(f["key"])
            if f.get("kind") == "link" and v:
                t = universe.resolve(v)
                shown[f["key"]] = t.name if t else v
            elif f.get("kind") == "links" and v:
                shown[f["key"]] = ", ".join((universe.resolve(x).name if universe.resolve(x) else x) for x in v)
        out["display"] = shown
        out["labels"] = {f["key"]: f["label"] for f in schemas.get(e.type)["fields"]}
    if e.type == "note":
        out["notes"] = e.fields.get("body", "")
    return out


def story_json(s):
    meta, sections = s.load_outline()
    return {"id": s.slug, "universe": s.universe.slug, "universe_name": s.universe.name, "title": s.title,
            "meta": meta, "outline": sections, "scenes": [p.name for p in s.scenes()], "words": s.word_count(),
            "path": str(s.path), "manuscript": str(s.manuscript_dir), "settings": settings.load_story(s.path),
            "author": {k: v for k, v in settings.load_global().items()
                       if k in ("author_name", "legal_name", "address", "email", "phone")}}


def universe_json(u):
    s = u.settings()
    return {"slug": u.slug, "name": s["name"], "genres": s["genres"], "path": str(u.path),
            "counts": {t: len(u.entities(t)) for t in schemas.load()},
            "stories": [x.slug for x in u.stories()]}


def _universe(slug):
    u = vault.get_universe(slug) if slug else None
    if not u:
        msg = f"No universe '{slug}'. Known: " + ", ".join(x.slug for x in vault.list_universes())
        sys.exit(msg)
    return u


def cmd_universes(args):
    migrate_lines = migrate.migrate_universe_json()
    if args.action == "new":
        u = vault.create_universe(args.name or "Untitled Universe", args.genres or ())
        emit(universe_json(u)) if args.json else print(f"  Created {u.name} ({u.path})")
        return
    unis = vault.list_universes()
    if args.json:
        emit([universe_json(u) for u in unis])
        return
    for line in migrate_lines:
        print("  " + line)
    if not unis:
        print("  No universes yet. Promote a story from the Wheel, or:  storywheel universes new NAME")
    for u in unis:
        print(f"  {u.slug:<24} {u.name}   ({len(u.entities())} entities, {len(u.stories())} stories)")


def cmd_entity(args):
    u = _universe(args.universe)
    if args.action == "show":
        e = u.entity(args.id)
        if not e:
            sys.exit(f"No entity '{args.id}' in {u.slug}")
        emit(entity_json(e, u))
        return
    items = u.entities(args.type)
    if args.json:
        emit([entity_json(e, u) for e in items])
        return
    for e in items:
        print(f"  {e.type:<10} {e.id:<28} {e.name}")


def cmd_story(args):
    if args.action == "list":
        unis = [_universe(args.universe)] if args.universe else vault.list_universes()
        stories = [s for u in unis for s in u.stories()]
        if args.json:
            emit([story_json(s) for s in stories])
        else:
            for s in stories:
                print(f"  {s.universe.slug}/{s.slug:<28} {s.title}  ({s.word_count()} words)")
        return
    uni, _, slug = (args.target or "").partition("/")
    u = _universe(uni)
    s = u.story(slug)
    if not s:
        sys.exit(f"No story '{slug}' in {u.slug}")
    emit(story_json(s)) if args.json else print(json.dumps(story_json(s), indent=2, ensure_ascii=False))


def cmd_promote(args):
    from . import promote, store
    from .engine import Engine
    from . import paths
    draft = store.find(args.target)
    if not draft or not draft["kept"]:
        sys.exit("No such draft, or nothing kept in it.")
    universe = _universe(args.universe) if args.universe else None
    plan = promote.build_plan(draft, universe, Engine(user_dir=paths.home()), args.new)
    if args.dry_run:
        emit({"lines": plan.lines()}) if args.json else print("\n".join("  " + l for l in plan.lines()))
        return
    if not args.yes:
        print("\n".join("  " + l for l in plan.lines()))
        if input("  Promote? [y/N] ").strip().lower() != "y":
            return
    story, report = promote.apply_plan(plan, universe, draft)
    store.save_draft(draft)
    emit({"universe": story.universe.slug, "story": story.slug, "report": report}) if args.json else \
        print("\n".join("  " + l for l in report))


def cmd_writer(args):
    from . import modes
    from .cli import get_engine, get_ratings
    modes.run(("writer", {"universe": args.universe, "story": args.story}), get_engine, get_ratings)


def cmd_builder(args):
    from . import builder, state
    from .cli import get_ratings
    for line in migrate.migrate_universe_json():
        print("  " + line)
    from . import modes
    from .cli import get_engine
    modes.run(("builder", {"universe": args.universe, "story": args.story}), get_engine, get_ratings)


def add_parsers(sub):
    p = sub.add_parser("universes", help="list your universes (or: universes new NAME)")
    p.add_argument("action", nargs="?", choices=["list", "new"], default="list")
    p.add_argument("name", nargs="?")
    p.add_argument("--genres", nargs="*")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("entity", help="entities in a universe:  entity list UNIVERSE [--type character] --json")
    p.add_argument("action", choices=["list", "show"])
    p.add_argument("universe")
    p.add_argument("id", nargs="?")
    p.add_argument("--type", choices=list(schemas.TYPES))
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("story", help="stories in your universes:  story list [UNIVERSE] | story show UNIVERSE/STORY")
    p.add_argument("action", choices=["list", "show"])
    p.add_argument("target", nargs="?", help="for show: universe/story")
    p.add_argument("--universe")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("promote", help="bring a Wheel draft into a universe:  promote N --new NAME | --universe SLUG")
    p.add_argument("target", nargs="?", help="number from 'list' or a story id (default: newest)")
    p.add_argument("--universe", help="an existing universe (default: make a new one)")
    p.add_argument("--new", help="name for the new universe (default: the story's title)")
    p.add_argument("--dry-run", action="store_true", help="show what would be created")
    p.add_argument("--yes", action="store_true", help="don't ask")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("builder", help="open the Universe Builder")
    p.add_argument("universe", nargs="?")
    p.add_argument("story", nargs="?")
    p = sub.add_parser("writer", help="open a story in the Writer (Neovim)")
    p.add_argument("universe", nargs="?")
    p.add_argument("story", nargs="?")
    return {"writer": cmd_writer, "builder": cmd_builder, "universes": cmd_universes, "entity": cmd_entity, "story": cmd_story, "promote": cmd_promote}
