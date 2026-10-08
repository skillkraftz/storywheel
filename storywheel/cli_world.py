"""Commands for the library: universes, entities and stories (all with --json for other programs)."""
import argparse
import json
import os
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
        out["order"] = [f["key"] for f in schemas.get(e.type)["fields"]]          # the schema's order, for the peek card
    if e.type == "note":
        out["notes"] = e.fields.get("body", "")
    return out


def story_json(s):
    meta, sections = s.load_outline()
    return {"id": s.slug, "universe": s.universe.slug, "universe_name": s.universe.name, "title": s.title,
            "meta": meta, "outline": sections, "scenes": [e["title"] for e in s.scene_list()], "files": [p.name for p in s.files()], "extra_files": [p.name for p in s.extra_files()], "words": s.word_count(),
            "path": str(s.path), "manuscript": str(s.manuscript_dir), "settings": settings.load_story(s.path),
            "author": {k: v for k, v in settings.load_global().items()
                       if k in ("author_name", "legal_name", "address", "email", "phone")},
            "screenplay": s.is_screenplay(), "script": str(s.script_path),
            "target_pages": _target_pages(s), "format_key": _formats().of_story(s), "target_words": _target_words(s)}


def _formats():
    from . import formats
    return formats


def _target_words(s):
    number, unit = _formats().target(s)
    return number if unit == "words" else None


def _target_pages(s):
    if not s.is_screenplay():
        return None
    from . import screenplay
    return screenplay.target_pages(s)


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


def kitty_command(font="", size=0, extra=()):
    """The kitty command line that opens storywheel in its own window, with kitty's normal spacing (the Writer's tall lines belong to the
    Writer's own window, see writer.kitty_command). A font and size are only used if you give them."""
    argv = ["kitty", "--class", "storywheel", "--title", "storywheel", "-o", "remember_window_size=no", "--start-as=maximized"]
    if size:
        argv += ["-o", f"font_size={size}"]
    if font:
        argv += ["-o", f"font_family={font}"]
    return argv + list(extra) + ["storywheel"]


def kitty_probe(run=None):
    """What this kitty can do for switching in place, from the installed kitty: its version and, if remote control is switched on for this
    window, which remote commands it knows. Returns lines of text. (Nothing here is needed by storywheel.)"""
    import shutil
    import subprocess
    run = run or (lambda argv: subprocess.run(argv, capture_output=True, text=True, timeout=10))
    exe = shutil.which("kitty")
    if not exe:
        return [tools.missing("kitty")]
    lines = []
    try:
        lines.append(run([exe, "--version"]).stdout.strip() or "kitty (version unknown)")
    except (OSError, subprocess.SubprocessError) as e:
        return [f"Could not run kitty: {e}"]
    kitten = shutil.which("kitten")
    if not kitten:
        lines.append("kitten (kitty's helper) was not found, so remote control cannot be tried.")
        return lines
    if not os.environ.get("KITTY_LISTEN_ON"):
        lines.append("Remote control is not switched on for this window (no KITTY_LISTEN_ON). To try it, start kitty with:")
        lines.append("  kitty -o allow_remote_control=socket-only --listen-on unix:/tmp/storywheel-kitty")
        return lines
    try:
        out = run([kitten, "@", "--help"]).stdout
    except (OSError, subprocess.SubprocessError) as e:
        lines.append(f"kitten @ failed: {e}")
        return lines
    for cmd in ("set-font-size", "set-spacing", "set-background-opacity", "resize-os-window", "load-config", "launch"):
        lines.append(f"  kitten @ {cmd}: {'yes' if cmd in out else 'no'}")
    return lines


def cmd_kitty(args):
    import os
    import shutil
    if args.probe:
        print("\n".join("  " + l if not l.startswith("  ") else l for l in kitty_probe()))
        return
    argv = kitty_command(args.font, args.size)
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


def _story_of(target):
    uni, _, slug = (target or "").partition("/")
    u = _universe(uni)
    s = u.story(slug)
    if not s:
        sys.exit(f"No story '{slug}' in {u.slug}")
    return s


def cmd_script(args):
    """Screenplays: script ensure|start UNIVERSE/STORY, script check|pages|scenes FILE."""
    from pathlib import Path
    from . import fountain, screenplay, screenplay_pdf
    if args.action in ("ensure", "start"):
        s = _story_of(args.target)
        if not s.is_screenplay():
            sys.exit(f"'{s.title}' is not a screenplay (its format is set in the story's settings).")
        if args.action == "ensure":
            path = screenplay.ensure_script(s)
            emit({"path": str(path)}) if args.json else print(path)
            return
        try:
            path = screenplay.start_from_outline(s, replace=args.replace)
        except screenplay.ScriptExists as e:
            sys.exit(str(e))
        emit({"path": str(path)}) if args.json else print(f"  Started {path} from the outline.")
        return
    path = Path(args.target or "")
    if not path.is_file():
        sys.exit(f"No file {path}")
    text = path.read_text(encoding="utf-8")
    if args.action == "check":
        found = screenplay.flip_test(text, args.target_pages)
        if args.json:
            emit({"problems": found, "pages": screenplay_pdf.estimate_pages(text)})
        else:
            for d in found:
                print(f"  {d['line']:5d}  {d['message']}")
            if not found:
                print("  Nothing to flag.")
    elif args.action == "pages":
        pages = screenplay_pdf.estimate_pages(text)
        emit({"pages": pages}) if args.json else print(pages)
    else:
        emit(fountain.scenes(text)) if args.json else print("\n".join(f"  {d['line']:5d}  {d['title']}" for d in fountain.scenes(text)))


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


def need_terminal(what, instead):
    """Refuse to start a full-screen program when stdin or stdout is not a terminal: it would print escape codes and wait for keys."""
    if sys.stdin.isatty() and sys.stdout.isatty():
        return
    sys.exit(f"storywheel {what} is a full-screen program and needs a terminal. For scripts use {instead}.")


def cmd_writer(args):
    from . import modes
    need_terminal("writer", "`storywheel manuscript text UNIVERSE/STORY`, `story show UNIVERSE/STORY --json`")
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


def cmd_help(args):
    """storywheel help [TOPIC]: the same pages the help screens show. No topic lists them; -s WORDS searches all of them."""
    from . import helpdoc
    if args.search:
        hits = helpdoc.search(" ".join(args.search))
        if args.json:
            emit([{"page": n, "section": h, "line": snip} for n, h, snip in hits])
        elif not hits:
            print("  Nothing in the help matches that.")
        for n, h, snip in ([] if args.json else hits):
            print(f"  {n}: {h}\n      {snip}")
        return
    if not args.topic:
        if args.json:
            emit([{"name": n, "title": t, "kind": k} for n, t, k in helpdoc.titles()])
            return
        print("  Help pages (storywheel help NAME):\n")
        for kind in ("mode", "topic"):
            for n, t, k in helpdoc.titles():
                if k == kind:
                    print(f"    {n:<20} {t}")
            print()
        print("  storywheel help -s WORDS  searches all of them.")
        return
    name = helpdoc.resolve(args.topic)
    if not name:
        sys.exit(f"No help page called '{args.topic}'. Try:  storywheel help   (lists them)  or  storywheel help -s {args.topic}")
    if getattr(args, "tabs", False):
        out = [{"title": t, "text": helpdoc.tab_text(secs, args.width or None)[0]} for t, secs in helpdoc.tabs(name, args.format)]
        if args.json:
            emit(out)
        else:
            for tab in out:
                print(f"[{tab['title']}]\n\n{tab['text']}")
        return
    if args.json:
        emit({"name": name, "title": helpdoc.load(name).title, "sections": [{"heading": h, "text": b} for h, b in helpdoc.sections(name)]})
    else:
        print(helpdoc.text(name, args.width or None), end="")


def find_story(target):
    """A story from "universe/story" (its id), or from a story slug that is unique across the universes. Exits with a plain message otherwise."""
    uni, sep, slug = (target or "").partition("/")
    if sep:
        story = _universe(uni).story(slug)
        if not story:
            sys.exit(f"No story '{slug}' in {uni}")
        return story
    found = [st for u in vault.list_universes() for st in u.stories() if st.slug == uni]
    if len(found) == 1:
        return found[0]
    if not found:
        sys.exit(f"No story '{uni}'. Use universe/story. Known: " + ", ".join(f"{u.slug}/{st.slug}" for u in vault.list_universes() for st in u.stories()))
    sys.exit(f"'{uni}' is a story in several universes ({', '.join(f'{st.universe.slug}/{st.slug}' for st in found)}): use universe/story")


def default_format(story):
    from . import settings
    st = settings.load_story(story.path)
    fmt = str(st.get("export_format") or settings.load_global().get("export_format") or "docx").lower()      # (the story's own, else yours)
    if str(st.get("format", "")).lower() == "screenplay":
        return fmt if fmt in ("pdf", "fountain", "fdx") else "pdf"            # (a screenplay exports as a script)
    return fmt


def exports_status():
    """One dict per story: its words now, what its last export was made from, whether the manuscript changed since, the default format, the folder."""
    from . import export, settings
    out = []
    for u in vault.list_universes():
        for story in u.stories():
            text = export.compile_text(story)
            words, digest = vault.count_words(text), export.content_hash(story)
            last = export.last_export(story)
            if last is None:
                state = "never exported"
            else:
                state = "up to date" if last["hash"] == digest else "changed"
            out.append({"story": export.story_id(story), "title": story.title, "words": words, "hash": digest,
                        "last_export": ({"file": last["file"], "format": last["format"], "date": last["date"], "words": last["words"],
                                         "hash": last["hash"]} if last else None),
                        "state": state, "changed": None if last is None else last["hash"] != digest,
                        "default_format": default_format(story), "anonymous": bool(settings.load_story(story.path).get("export_anonymous")),
                        "folder": last["folder"] if last else (str(export.export_folder(story, create=False) or ""))})
    return out


def cmd_exports(args):
    from . import export, paths
    if args.action == "status":
        rows = exports_status()
        if args.json:
            emit(rows)
            return
        if not rows:
            print("  No stories yet.")
            return
        for r in rows:
            last = r["last_export"]
            print(f"  {r['story']}  \"{r['title']}\"\n    words now: {r['words']:,}   state: {r['state']}   default format: {r['default_format']}"
                  + (" (anonymous)" if r["anonymous"] else ""))
            if last:
                print(f"    last export: {last['words']:,} words on {last['date']} as {last['file']}")
            print(f"    export folder: {paths.tilde(r['folder']) if r['folder'] else '(none yet)'}")
        return
    if not args.target:
        sys.exit("exports make needs a story:  exports make UNIVERSE/STORY [--format F]")
    story = find_story(args.target)
    fmt = args.format or default_format(story)
    try:
        result = export.export(story, fmt)
    except export.ExportError as e:
        if args.json:
            emit({"error": str(e)})
        else:
            print("  " + str(e))
        raise SystemExit(1)
    result["story"] = export.story_id(story)
    result["hash"] = export.content_hash(story)
    if args.json:
        emit(result)
    else:
        print(result["path"])
        for w in result["warnings"]:
            print(f"  Note: {w}", file=sys.stderr)


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


def _rhymes_line():
    from . import rhymes
    st = rhymes.status()
    if not st["installed"]:
        return "Rhymes: " + rhymes.not_installed_message()
    lic = st["license"].strip()
    return f"{st['name']} (rhymes)" + (("\n  License of the CMU Pronouncing Dictionary:\n    " + lic.replace("\n", "\n    ")) if lic else "\n  (no license text was saved with it)")


def cmd_dictionary(args):
    from . import dictionary, dictionary_build, paths
    if args.action == "status":
        st = dictionary.status()
        emit(st) if args.json else print(
            f"  Installed: {paths.tilde(st['path'])}  ({st['size'] // 1048576} MB)\n  {st.get('wordnet', '')}\n  {st.get('moby', '')}\n  {_rhymes_line()}" if st["installed"]
            else f"  {dictionary.NOT_INSTALLED}")
        return
    dest = dictionary.index_path()
    try:
        if args.action == "install":
            print("  This downloads Open English WordNet (CC BY 4.0), the Moby Thesaurus (public domain) and the CMU Pronouncing Dictionary (for rhymes), about 40 MB,")
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
    if args.action == "install":
        from . import rhymes
        if rhymes.status()["installed"]:
            print("  Rhymes are installed.")
        else:
            print("  Rhymes were NOT installed. " + (rhymes.failure() or "The CMU Pronouncing Dictionary is missing.")
                  + "\n  Everything else works. Run  storywheel dictionary install  again to retry the rhymes.")


def cmd_migrate(args):
    lines = migrate.migrate_universe_json() + migrate.migrate_manuscripts() + migrate.migrate_exports() + migrate.migrate_sync_links() + migrate.migrate_settings()
    print("\n".join("  " + l for l in lines) if lines else "  Nothing to migrate.")


def cmd_settings(args):
    from . import modes
    need_terminal("settings", "`storywheel --version` and the files in ~/.storywheel (settings.toml)")
    from .cli import get_engine, get_ratings
    modes.run(("settings", {"back": "builder" if vault.list_universes() else "wheel"}), get_engine, get_ratings)


def cmd_builder(args):
    from . import builder, state
    need_terminal("builder", "`storywheel universes`, `entity list UNIVERSE --json` and `story list --json`")
    from .cli import get_ratings
    for line in migrate.migrate_universe_json() + migrate.migrate_manuscripts() + migrate.migrate_exports() + migrate.migrate_sync_links() + migrate.migrate_settings():
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
    p = sub.add_parser("kitty", help="open storywheel in its own kitty window (normal spacing; the Writer opens its own tall-lined window from there)")
    p.add_argument("--font", default="", help="font family for storywheel's own window (default: your kitty font)")
    p.add_argument("--size", type=float, default=0, help="font size for storywheel's own window (default: your kitty size)")
    p.add_argument("--probe", action="store_true", help="say what the installed kitty could do for switching windows in place (kitty remote control); changes nothing")
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
    p = sub.add_parser("script", help="screenplays:  script ensure|start UNIVERSE/STORY [--replace] | script check|pages|scenes FILE [--target-pages N]")
    p.add_argument("action", choices=["ensure", "start", "check", "pages", "scenes"])
    p.add_argument("target", help="universe/story (ensure, start) or a .fountain file (check, pages, scenes)")
    p.add_argument("--replace", action="store_true", help="start: replace a script that already has scenes (it is backed up first)")
    p.add_argument("--target-pages", dest="target_pages", type=int, help="check: the length the script aims at")
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
    p.add_argument("--format", default="docx", help="docx (default), odt, pdf, md, txt, fountain or fdx (a screenplay: pdf, fountain or fdx)")
    p.add_argument("--out", help="folder to write into (default: the manuscripts folder)")
    p.add_argument("--anonymous", action="store_true", help="no name, contact block, byline or surname (header: Title / page)")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("help", help="print a help page:  help [TOPIC] | help -s WORDS (search)")
    p.add_argument("topic", nargs="?", help="a mode (wheel, builder, writer, settings, words) or a topic (universes, structures, exports...)")
    p.add_argument("-s", "--search", nargs="+", metavar="WORD", help="search every help page")
    p.add_argument("--width", type=int, default=88, help="wrap lines at this width (0: no wrapping)")
    p.add_argument("--tabs", action="store_true", help="the page as the help screens show it: in tabs (the Writer: --format picks the guide)")
    p.add_argument("--format", help="with --tabs on writer: the story's format (short-story, novel, screenplay, feature-film, short-film)")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("exports", help="exports:  exports status [--json] | exports make UNIVERSE/STORY [--format F] [--json]")
    p.add_argument("action", choices=["status", "make"])
    p.add_argument("target", nargs="?", help="universe/story (or a story slug that is in one universe only)")
    p.add_argument("--format", help="docx, odt, pdf, md, txt, fountain or fdx (default: the story's own export format; a screenplay: pdf)")
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
    return {"define": cmd_lookup, "thesaurus": cmd_lookup, "inflect": cmd_inflect, "backups": cmd_backups, "lookup": cmd_lookup, "dictionary": cmd_dictionary, "migrate": cmd_migrate, "settings": cmd_settings, "manuscript": cmd_manuscript, "exports": cmd_exports, "help": cmd_help, "writer": cmd_writer, "builder": cmd_builder, "universes": cmd_universes, "entity": cmd_entity, "story": cmd_story, "script": cmd_script, "promote": cmd_promote, "names": cmd_names, "grammar": cmd_grammar, "kitty": cmd_kitty, "setup": cmd_setup, "update": cmd_update, "post-update": cmd_post_update}
