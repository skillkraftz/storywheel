"""Commands for the library: universes, entities and stories (all with --json for other programs)."""
import argparse
import json
import sys
from pathlib import Path

from . import migrate, schemas, settings, tools, vault


def emit(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def entity_json(e, universe=None):
    out = {"id": e.id, "type": e.type, "name": e.name, "fields": e.fields, "custom": e.custom, "notes": e.body,
           "universe": universe.slug if universe else None, "proper": e.proper}
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
            "meta": meta, "outline": sections, "scenes": [e["title"] for e in s.scene_list()], "files": [p.name for p in s.files()], "words": s.word_count(),
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


def cmd_names(args):
    """names fix UNIVERSE [--apply]: names written in the wrong capitals; without --apply only a preview is shown."""
    from . import names
    u = _universe(args.universe)
    fixes = names.scan(u)
    if not fixes:
        print(f"Every name in {u.name} already reads right.")
        return
    print(f"{len(fixes)} name(s) in {u.name} would change:")
    for f in fixes:
        print("  " + f.line())
    if args.apply:
        print(f"Changed {names.apply(u, fixes)}. (The ids stay; mentions in notes and manuscripts are not rewritten.)")
    else:
        print("Nothing was changed. Add --apply to change them.")


def cmd_setup(args):
    from . import setup_wizard
    setup_wizard.run(again=args.again, defaults=args.defaults)


def cmd_update(args):
    from . import update
    try:
        if args.record:
            update.record_current(print)
            return
        update.update(print, check_only=args.check)
    except update.UpdateError as e:
        print("  " + str(e))
        raise SystemExit(1)


def cmd_post_update(args):
    from . import update
    update.post_update()


def kitty_command(font="", size=0, line_height=140, extra=()):
    """The kitty command line that opens storywheel in its own window: a chosen font and taller lines (modify_font cell_height).
    Font and size default to the Writer's own settings (Settings > Writer)."""
    g = settings.load_global()
    font = font or g.get("writer_font") or ""
    size = size or g.get("writer_font_size") or 15
    argv = ["kitty", "--class", "storywheel", "--title", "storywheel", "-o", f"font_size={size}",
            "-o", f"modify_font=cell_height {int(line_height)}%", "-o", "remember_window_size=no", "--start-as=maximized"]
    if font:
        argv += ["-o", f"font_family={font}"]
    return argv + list(extra) + ["storywheel"]


def cmd_kitty(args):
    import os
    import shutil
    argv = kitty_command(args.font, args.size, args.line_height)
    if args.print:
        print(" ".join(f'"{a}"' if " " in a else a for a in argv))
        return
    if not shutil.which("kitty"):
        sys.exit(tools.missing("kitty"))
    os.execvp(argv[0], argv)


def cmd_grammar(args):
    from . import grammar, paths
    act = args.action
    try:
        if act == "install":
            v = grammar.install(args.from_file, lambda m: print("  " + m))
            print(f"  LanguageTool {v} is installed in {paths.tilde(grammar.install_dir())}.")
            st = grammar.status()
            for p in st["problems"]:
                print("  " + p)
            print("  Turn grammar checking on in Settings (F4) > Grammar, or from the Writer's menu.")
        elif act == "status":
            st = grammar.status()
            if args.json:
                emit(st)
                return
            print(f"  Java: {st['java'] or 'not found'}" + (f" (version {st['java_version']})" if st["java_version"] else ""))
            print(f"  LanguageTool: {('version ' + st['version'] + ' in ' + paths.tilde(st['path'])) if st['installed'] else 'not installed'}")
            print(f"  Server: {'running at ' + st['url'] if st['running'] else 'not running (the Writer starts it when grammar checking is on)'}")
            mem = f"{st['memory_available_mb']} MB free of {st['memory_total_mb']} MB" if st["memory_total_mb"] else "unknown"
            print(f"  Memory: wants about {st['memory_needed_mb']} MB ({st['memory_limit_mb']} MB heap + Java); this machine has {mem}")
            print(f"  {grammar.HELP_NOTE}")
            for p in st["problems"]:
                print("  ! " + p)
        elif act == "start":
            url = grammar.start()
            print(json.dumps({"ok": True, "url": url}) if args.json else f"  Running at {url}")
        elif act == "stop":
            stopped = grammar.stop()
            print(json.dumps({"ok": True, "stopped": stopped}) if args.json else ("  Stopped." if stopped else "  It was not running."))
        elif act == "config":
            emit(grammar.config())
        elif act == "rule-off":
            if not args.target:
                sys.exit("Give the rule id, e.g.  storywheel grammar rule-off COMMA_COMPOUND_SENTENCE")
            rules = grammar.turn_off_rule(args.target)
            print(json.dumps({"ok": True, "rules": rules}) if args.json else f"  Turned off {args.target}. Turned-off rules: {', '.join(rules)}")
        elif act == "ignored":
            if not args.target:
                sys.exit("Give the story:  storywheel grammar ignored UNIVERSE/STORY [--clear]")
            u, _, s = args.target.partition("/")
            story = _universe(u).story(s)
            if story is None:
                sys.exit(f"No story {args.target}")
            if args.clear:
                print(f"  Forgot {grammar.forget_ignored(story.path)} ignored item(s).")
            else:
                items = grammar.ignored(story.path)
                emit(items) if args.json else print("\n".join(f"  {i['rule']}: {i.get('text', '')}" for i in items) or "  Nothing is ignored in this story.")
    except grammar.GrammarError as e:
        print("  " + str(e))
        raise SystemExit(1)


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


def cmd_manuscript(args):
    from . import export
    uni, _, slug = (args.target or "").partition("/")
    u = _universe(uni)
    story = u.story(slug)
    if not story:
        sys.exit(f"No story '{slug}' in {u.slug}")
    if args.action == "text":
        print(export.plain_text(story))
        return
    try:
        result = export.export(story, args.format, args.out, True if args.anonymous else None)
    except export.ExportError as e:
        if args.json:
            emit({"error": str(e)})
        else:
            print("  " + str(e))
        raise SystemExit(1)
    emit(result) if args.json else print(f"  Wrote {result['path']}  ({result['words']:,} words)" +
                                          "".join(f"\n  Note: {w}" for w in result["warnings"]))


def cmd_lookup(args):
    """define / thesaurus / lookup WORD [--json]: meanings, similar words and opposite words, from the offline dictionary."""
    from . import dictionary
    try:
        result = dictionary.lookup(" ".join(args.word))
    except dictionary.DictionaryMissing as e:
        if args.json:
            emit({"error": str(e), "installed": False})
        else:
            print("  " + str(e))
        raise SystemExit(1)
    kind = args.command
    if args.json:
        out = dict(result)
        if kind == "define":
            out["entries"] = [{k: e[k] for k in ("word", "form_of", "parts", "related_forms")} for e in result["entries"]]
        elif kind == "thesaurus":
            out["entries"] = [{"word": e["word"], "form_of": e["form_of"], "close_synonyms": e["close_synonyms"],
                               "wide_synonyms": e["wide_synonyms"], "synonyms": e["synonyms"], "antonyms": e["antonyms"],
                               "indirect_antonyms": e["indirect_antonyms"],
                               "kind_of": sorted({k for p in e["parts"] for s in p["senses"] for k in s["kind_of"]})} for e in result["entries"]]
        emit(out)
        return
    if kind == "thesaurus" and result["found"]:
        for e in result["entries"]:
            print(f"  {e['word']}" + (f"  (from '{e['form_of']}')" if e["form_of"] else ""))
            print("    similar:  " + (", ".join(e["synonyms"]) or "-"))
            print("    opposite: " + (", ".join(e["antonyms"]) or "-"))
            if e["indirect_antonyms"]:
                print("    opposite (indirect): " + ", ".join(f"{a['word']} (of {a['via']})" for a in e["indirect_antonyms"]))
        return
    print("\n".join("  " + l for l in dictionary.card_lines(result)))


def cmd_inflect(args):
    """inflect ORIGINAL BASE WORD: WORD in the same form as ORIGINAL is of BASE (running, run, sprint -> sprinting)."""
    from . import dictionary, inflect
    try:
        db = dictionary.connect()
    except dictionary.DictionaryMissing:
        db = None
    word = inflect.reinflect(args.original, args.base, args.word, args.pos, db=db)
    emit({"word": word, "kind": inflect.classify(args.original, args.base)}) if args.json else print(word)


def cmd_backups(args):
    """backups list|show|restore UNIVERSE/STORY [ID]: browse a story's backups and put one back."""
    from . import backups
    uni, _, slug = (args.target or "").partition("/")
    u = _universe(uni)
    story = u.story(slug)
    if not story:
        sys.exit(f"No story '{slug}' in {u.slug}")
    if args.action == "list":
        rows = backups.list_backups(story)
        if args.json:
            emit(rows)
        else:
            for r in rows:
                print(f"  {r['id']:<44} {r['when']}  {r['what']:<32} {r['words']:>7,} words")
            if not rows:
                print("  No backups yet.")
        return
    if not args.id:
        sys.exit("Which backup? Give its id (see:  backups list).")
    entry = backups.find(story, args.id)
    if entry is None:
        sys.exit(f"There is no backup '{args.id}'.")
    if args.action == "show":
        print(backups.preview(entry, lines=args.lines))
        return
    result = backups.restore(story, args.id)
    emit(result) if args.json else print(f"  Restored {result['restored']} ({result['words']:,} words)."
                                         + (f" The version it replaced is in {result['kept']}." if result["kept"] else ""))


def cmd_dictionary(args):
    from . import dictionary, dictionary_build, paths
    if args.action == "status":
        st = dictionary.status()
        emit(st) if args.json else print(
            f"  Installed: {paths.tilde(st['path'])}  ({st['size'] // 1048576} MB)\n  {st.get('wordnet', '')}\n  {st.get('moby', '')}" if st["installed"]
            else f"  {dictionary.NOT_INSTALLED}")
        return
    dest = dictionary.index_path()
    try:
        if args.action == "install":
            print("  This downloads Open English WordNet (CC BY 4.0) and the Moby Thesaurus (public domain), about 36 MB,")
            print("  and builds the index. It is the only time storywheel uses the network.")
            counts = dictionary_build.install(dest, None, lambda m: print("  " + m))
        else:
            counts = dictionary_build.build(args.oewn, args.moby, dest, lambda m: print("  " + m))
    except dictionary_build.DictionaryBuildError as e:
        print("  " + str(e))
        raise SystemExit(1)
    dictionary.forget()
    from . import genrefit, spelldict, writer
    note = spelldict.ensure(writer.nvim_exe(), lambda m: print("  " + m))
    if note:
        print("  " + note)
    note = genrefit.ensure(lambda m: print("  " + m))
    if note:
        print("  " + note)
    print(f"  Dictionary ready at {paths.tilde(dest)}: {counts['words']:,} words, {counts['synsets']:,} meanings, "
          f"{counts['moby_roots']:,} thesaurus entries.")


def cmd_migrate(args):
    lines = migrate.migrate_universe_json() + migrate.migrate_manuscripts() + migrate.migrate_exports() + migrate.migrate_sync_links()
    print("\n".join("  " + l for l in lines) if lines else "  Nothing to migrate.")


def cmd_settings(args):
    from . import modes
    from .cli import get_engine, get_ratings
    modes.run(("settings", {"back": "builder" if vault.list_universes() else "wheel"}), get_engine, get_ratings)


def cmd_builder(args):
    from . import builder, state
    from .cli import get_ratings
    for line in migrate.migrate_universe_json() + migrate.migrate_manuscripts() + migrate.migrate_exports() + migrate.migrate_sync_links():
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
    p = sub.add_parser("names", help="fix names written in the wrong capitals:  names fix UNIVERSE [--apply]")
    p.add_argument("action", choices=["fix"])
    p.add_argument("universe")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("setup", help="a short questionnaire for this machine (asks only what is new)")
    p.add_argument("--again", action="store_true", help="ask every question again")
    p.add_argument("--defaults", action="store_true", help="accept every default without asking")
    p = sub.add_parser("update", help="pull the newest storywheel from your git remote, reinstall if the version changed, migrate")
    p.add_argument("--check", action="store_true", help="only say whether there is something new")
    p.add_argument("--record", action="store_true", help="after installing by hand: remember which source commit is installed")
    sub.add_parser("post-update", help=argparse.SUPPRESS)
    p = sub.add_parser("kitty", help="open storywheel in its own kitty window with a chosen font and taller lines")
    p.add_argument("--font", default="", help="font family (default: Settings > Writer > font)")
    p.add_argument("--size", type=float, default=0, help="font size (default: Settings > Writer)")
    p.add_argument("--line-height", type=int, default=140, help="line height as a percent of the font's (kitty modify_font cell_height); default 140")
    p.add_argument("--print", action="store_true", help="only show the command")
    p = sub.add_parser("grammar", help="optional grammar checking with a local LanguageTool:  grammar install [--from FILE.zip] | status | start | stop | rule-off ID | ignored STORY [--clear]")
    p.add_argument("action", choices=["install", "status", "start", "stop", "config", "rule-off", "ignored"])
    p.add_argument("target", nargs="?")
    p.add_argument("--from", dest="from_file", help="install: unpack this LanguageTool .zip instead of downloading")
    p.add_argument("--clear", action="store_true")
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
    p = sub.add_parser("manuscript", help="manuscript export:  manuscript export UNIVERSE/STORY --format docx | manuscript text UNIVERSE/STORY")
    p.add_argument("action", choices=["export", "text"])
    p.add_argument("target", help="universe/story")
    p.add_argument("--format", default="docx", help="docx (default), odt, pdf, md, txt or fountain")
    p.add_argument("--out", help="folder to write into (default: the manuscripts folder)")
    p.add_argument("--anonymous", action="store_true", help="no name, contact block, byline or surname (header: Title / page)")
    p.add_argument("--json", action="store_true")
    for name, text in (("define", "meanings of a word (offline dictionary)"), ("thesaurus", "similar and opposite words"),
                       ("lookup", "meanings, similar and opposite words")):
        p = sub.add_parser(name, help=text)
        p.add_argument("word", nargs="+")
        p.add_argument("--json", action="store_true")

    p = sub.add_parser("backups", help="a story's backups:  backups list|show|restore UNIVERSE/STORY [ID]")
    p.add_argument("action", choices=["list", "show", "restore"])
    p.add_argument("target", help="universe/story")
    p.add_argument("id", nargs="?", help="the backup's id (from list)")
    p.add_argument("--lines", type=int, default=14)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("inflect", help="a word in the same form as another (inflect running run sprint -> sprinting)")
    p.add_argument("original")
    p.add_argument("base")
    p.add_argument("word")
    p.add_argument("--pos", choices=["noun", "verb", "adjective", "adverb"])
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("dictionary", help="the offline dictionary and thesaurus:  dictionary install | status | build --oewn FILE --moby FILE")
    p.add_argument("action", choices=["install", "status", "build"])
    p.add_argument("--oewn", help="build: the Open English WordNet .xml or .xml.gz")
    p.add_argument("--moby", help="build: mthesaur.txt")
    p.add_argument("--json", action="store_true")
    sub.add_parser("migrate", help="bring old data up to date (the old universe.json, scene files -> one manuscript file)")
    sub.add_parser("settings", help="open Settings (who you are, goals, Writer preferences, export, library, stats)")
    p = sub.add_parser("builder", help="open the Universe Builder")
    p.add_argument("universe", nargs="?")
    p.add_argument("story", nargs="?")
    p = sub.add_parser("writer", help="open a story in the Writer (Neovim)")
    p.add_argument("universe", nargs="?")
    p.add_argument("story", nargs="?")
    return {"define": cmd_lookup, "thesaurus": cmd_lookup, "inflect": cmd_inflect, "backups": cmd_backups, "lookup": cmd_lookup, "dictionary": cmd_dictionary, "migrate": cmd_migrate, "settings": cmd_settings, "manuscript": cmd_manuscript, "writer": cmd_writer, "builder": cmd_builder, "universes": cmd_universes, "entity": cmd_entity, "story": cmd_story, "promote": cmd_promote, "names": cmd_names, "grammar": cmd_grammar, "kitty": cmd_kitty, "setup": cmd_setup, "update": cmd_update, "post-update": cmd_post_update}
