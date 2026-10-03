"""
storywheel - roll a story one piece at a time.

    storywheel              start a new story (a full-screen app; --plain for a prompt)
    storywheel list         list your stories
    storywheel resume [N]   pick up a story (number from list, or newest)
    storywheel show [N]     print a story as plain text   (--json on list, show, export, sample)
    storywheel export N     write a story's markdown somewhere else (--out DIR)
    storywheel universe     show what you've saved to your universe
    storywheel sample G...  print sample stories for a genre mix (-n 10, --seed 1, --structure three-act)
    storywheel report       the worst-rated lines and the frames that produced them
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import textwrap

from . import paths, store, structures
from . import ratings as ratings_mod
from . import threads as T
from .engine import Engine
from .session import Session
from .steps import STEPS, public

try:
    import readline                      # arrow keys + pre-filled edits on Linux/Mac
except ImportError:                      # pragma: no cover (Windows)
    readline = None

TTY = sys.stdout.isatty()
def _style(code):
    return (lambda s: f"\033[{code}m{s}\033[0m") if TTY else (lambda s: s)
bold, dim, cyan, yellow = _style("1"), _style("2"), _style("36"), _style("33")

_engine = None

def get_ratings():
    return ratings_mod.Ratings.load(paths.HOME)

def get_engine():
    """One engine per run. It remembers recent picks, in ~/.storywheel/recent.json, so the
    same lines don't turn up session after session, and it leans away from what you rated -."""
    global _engine
    if _engine is None:
        _engine = Engine(user_dir=paths.HOME, persist=True, ratings=get_ratings())
    return _engine

HELP = """
  enter / r     roll again
  k             keep this one and move on
  f [field]     reroll just one field, e.g.  f flaw  or  f 3
  e [field]     edit a field in place (single-field steps skip the question)
  E             edit the whole thing in your $EDITOR (nano by default)
  w             write your own from scratch
  + / -         like / dislike a field (or the whole thing on a one-field step);
                disliked frames and atom pairs come up a little less. Same key clears it.
  a             update a stale candidate to what you have kept
  i             ignore the stale warning (the candidate stays as it is)
  p N           pick an earlier candidate, e.g.  p 2
  h             list every roll for this step (shows what changed), then pick one
  h [field]     list every value one field has had, then pick one, e.g.  h 6
  u             save this one to your universe (for future stories)
  U             remove this one from your universe
  b             go back a step
  x             skip this step
  q             save and quit (resume later with: storywheel resume)
"""


# --- input helpers ---------------------------------------------------------------------

class Quit(Exception):
    pass

def ask(prompt, prefill=""):
    """input() with optional pre-typed text you can edit."""
    try:
        if prefill and readline and sys.stdin.isatty():
            readline.set_startup_hook(lambda: readline.insert_text(prefill))
            try:
                return input(prompt)
            finally:
                readline.set_startup_hook()
        if prefill:
            print(dim(f"  (current: {prefill})"))
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        raise Quit

def edit_in_editor(fields):
    editor = shlex.split(os.environ.get("EDITOR", "nano"))
    with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as f:
        f.write("# Edit the values, save, and close. One field per line: name: value\n")
        for k, v in fields.items():
            f.write(f"{k}: {v}\n")
        path = f.name
    try:
        subprocess.call(editor + [path])
        result, current = dict(fields), None
        for line in open(path):
            if line.startswith("#") or not line.strip():
                continue
            m = re.match(r"^(\w+):\s?(.*)$", line.rstrip("\n"))
            if m and m.group(1) in fields:
                current = m.group(1)
                result[current] = m.group(2).strip()
            elif current:                               # wrapped onto another line
                result[current] += " " + line.strip()
        return result
    except FileNotFoundError:
        print(f"  Couldn't find the editor '{editor[0]}'. Set $EDITOR, or use [e].")
        return fields
    finally:
        os.unlink(path)


# --- display -------------------------------------------------------------------------------

def show(sess):
    step, i, cand = sess.step, sess.i, sess.cand
    fields = public(cand)
    total = len(sess.steps)
    print("\n" + bold(cyan(f"── {step.label.upper()}  ({i + 1}/{total}) ")) + cyan("─" * 30))
    print(dim(textwrap.fill(step.hint, 72, initial_indent="  ", subsequent_indent="  ")))
    stale = sess.stale_banner()
    if stale:
        print(yellow(f"\n  ! {stale}.") + dim("  [a] update this, [enter] reroll it, [i] ignore it, or [k]eep it as is."))
    print(bold(f"\n  #{sess.cur + 1} of {len(sess.hist)}") + dim(sess.source_tag(sess.cur)))
    if step.single:
        print(textwrap.fill(next(iter(fields.values())), 72, initial_indent="    ", subsequent_indent="    "))
    else:
        width = max(len(k) for k in fields) + 2
        for n, (k, v) in enumerate(fields.items(), 1):
            label = f"  {n} {k.replace('_', ' '):<{width}}"
            print(textwrap.fill(v, 76, initial_indent=label, subsequent_indent=" " * len(label)))
    opts = "[enter] roll  [k]eep  " + ("" if step.single else "[f]ield  ") + \
           "[e]dit  [w]rite  [p]ick #  [h]istory  [+/-] rate  [u]/[U]niverse  [b]ack  [x] skip  [q]uit  [?]"
    if step.key == "structure":
        found = structures.find(fields["structure"])
        print(dim("\n  " + textwrap.fill(found.blurb if found else
                                          "Not one of the known structures; the Story Spine will be used.",
                                          72, subsequent_indent="  ")))
    if cand.get("_threads"):
        print(dim("\n  threads  " + T.describe(cand["_threads"])))
    if sess.standin_line():
        print(dim("\n  " + textwrap.fill(sess.standin_line(), 72, subsequent_indent="  ")))
    print(dim("\n  " + opts))

def _summary(step, entry):
    vals = list(public(entry).values())
    text = vals[0] if step.single else " · ".join(vals[:3])
    return text if len(text) < 70 else text[:67] + "..."


# --- the plain prompt loop ---------------------------------------------------------------------

def choose_field(sess, arg):
    names = sess.field_names
    if sess.step.single:
        return names[0]
    arg = arg or ask("  which field? (name or number) ").strip()
    if arg.isdigit() and 1 <= int(arg) <= len(names):
        return names[int(arg) - 1]
    if arg.replace(" ", "_") in names:
        return arg.replace(" ", "_")
    print(f"  No field '{arg}'. Fields: {', '.join(names)}")
    return None

def pick_from_list(count):
    """Ask for a number from a list just shown. Returns a 0-based index or None."""
    choice = ask(dim("\n  pick # (enter to go back) ")).strip()
    if choice.isdigit() and 1 <= int(choice) <= count:
        return int(choice) - 1
    return None

def show_history(sess):
    """Whole candidates. For multi-field steps, show only what changed each time."""
    print()
    for n in range(len(sess.hist)):
        marker = "→" if n == sess.cur else " "
        print(f"  {marker} #{n + 1:<3}{sess.change_summary(n)}" + dim(sess.source_tag(n)) + yellow(sess.stale_tag(n)))
    if not sess.step.single:
        print(dim("\n  Tip: h 3 lists every value field 3 has had."))
    return pick_from_list(len(sess.hist))

def show_field_history(sess, field):
    values = sess.field_values(field)
    print(f"\n  every {field.replace('_', ' ')} so far:")
    for n, v in enumerate(values, 1):
        marker = "→" if v == sess.cand.get(field) else " "
        print(textwrap.fill(v, 76, initial_indent=f"  {marker} {n:<3}", subsequent_indent=" " * 8))
    idx = pick_from_list(len(values))
    return None if idx is None else values[idx]

def handle(sess, raw):
    """Do what one typed command says."""
    m = re.match(r"^([A-Za-z?+\-=])\s*(.*)$", raw)
    cmd, arg = (m.group(1), m.group(2).strip()) if m else (raw, "")
    step, cand = sess.step, sess.cand

    if cmd in ("", "r"):
        sess.roll()
    elif cmd == "k":
        sess.keep()
    elif cmd == "f" and not step.single:
        field = choose_field(sess, arg)
        if field:
            sess.reroll_field(field)
    elif cmd == "e":
        field = choose_field(sess, arg)
        if field:
            sess.edit_field(field, ask(f"  {field}: ", prefill=cand[field]))
    elif cmd == "a":
        sess.update_inputs()
    elif cmd == "i":
        sess.ignore_stale()
    elif cmd == "E":
        sess.replace_fields(edit_in_editor(public(cand)))
    elif cmd == "w":
        fields = public(cand)
        if not step.single:
            print(dim("  Type a new value for each field, or press enter to keep the current one."))
        new = {}
        for k, v in fields.items():
            label = f"  {k.replace('_', ' ')}" + ("" if step.single else dim(f" [{v}]"))
            new[k] = ask(label + ": ").strip() or v
        sess.replace_fields(new)
    elif cmd == "p":
        if not (arg.isdigit() and sess.pick(int(arg) - 1)):
            print(f"  Pick a number from 1 to {len(sess.hist)}, e.g.  p 2")
    elif cmd == "h":
        if arg and not step.single:
            field = choose_field(sess, arg)
            value = field and show_field_history(sess, field)
            if value:
                sess.pick_value(field, value)
        else:
            idx = show_history(sess)
            if idx is not None:
                sess.pick(idx)
    elif cmd in "+-=" and cmd:
        field = choose_field(sess, arg) if (arg or not step.single) else None
        if field or step.single:
            sess.rate(1 if cmd in "+=" else -1, field)
    elif cmd == "u":
        save_to_universe_plain(sess)
    elif cmd == "U":
        print("  To remove something from a universe, open the Builder:  storywheel builder")
    elif cmd == "b":
        sess.back()
    elif cmd == "x":
        sess.skip()
    elif cmd == "q":
        raise Quit
    elif cmd == "?":
        print(HELP)
        ask(dim("  (enter to continue) "))
    else:
        print(f"  Unknown command '{raw}'. Type ? for help.")


def save_to_universe_plain(sess):
    from . import vault
    unis = vault.list_universes()
    if not unis:
        print("  No universe yet. Promote a story when you leave, or:  storywheel universes new NAME")
        return
    ticked = sess.selected_universes()
    if len(ticked) == 1:
        target = ticked[0]
    else:
        for n, u in enumerate(unis, 1):
            print(f"    {n}. {u.name}")
        pick = ask("  Save to which universe? ").strip()
        if not (pick.isdigit() and 1 <= int(pick) <= len(unis)):
            return
        target = unis[int(pick) - 1]
    sess.save_to_universe(target)


def ask_universe_mode(story):
    """Which universes may the generator draw from for this draft? (None by default.)"""
    from . import vault
    unis = vault.list_universes()
    if not unis or story.get("universes"):
        return
    print(f"\n  You have {len(unis)} universe(s). The generator can draw their people, places and things into this story.")
    for n, u in enumerate(unis, 1):
        print(f"    {n}. {u.name}")
    answer = ask("  Draw from which? (numbers like '1 2', or enter for none): ").strip()
    picks = [unis[int(w) - 1].slug for w in answer.replace(",", " ").split() if w.isdigit() and 1 <= int(w) <= len(unis)]
    story["universes"] = picks
    if picks:
        mode = ask("  Whole candidates too? [n]o / [m]ix them in / [o]nly from them: ").strip().lower()[:1]
        story["universe_mode"] = mode if mode in ("m", "o") else "n"


def offer_promotion(story):
    """On leaving the plain prompt with something kept: the same three choices as in the app."""
    if not story["kept"] or story.get("promoted"):
        return
    from . import promote, vault
    print(bold("\n  Bringing this story into the Universe Builder"))
    print(dim(textwrap.fill("It grows into a world of characters, places and things, and into a manuscript.",
                            72, initial_indent="  ", subsequent_indent="  ")))
    try:
        answer = ask("  [n]ew universe / [e]xisting universe / [l]ater (not now): ").strip().lower()[:1]
    except Quit:
        return
    universe, new_name = None, None
    if answer == "e" and vault.list_universes():
        unis = vault.list_universes()
        for n, u in enumerate(unis, 1):
            print(f"    {n}. {u.name}")
        pick = ask("  which? ").strip()
        if not (pick.isdigit() and 1 <= int(pick) <= len(unis)):
            print("  Not promoted.")
            return
        universe = unis[int(pick) - 1]
    elif answer in ("n", "e"):
        new_name = ask(f"  name for the new universe [{store.title_of(story)}]: ").strip() or store.title_of(story)
    else:
        return
    plan = promote.build_plan(story, universe, get_engine(), new_name)
    print("\n".join("  " + l for l in plan.lines()))
    if ask("  Go ahead? [Y/n] ").strip().lower() in ("n", "no"):
        print("  Not promoted.")
        return
    saved, report = promote.apply_plan(plan, universe, story)
    store.save_draft(story)
    print("\n".join("  " + l for l in report))


def run_plain(story):
    sess = Session(story, get_engine(), ratings=get_engine().ratings)
    sess.enter(store.open_step(story))
    try:
        while not sess.done:
            for note in sess.take_notes():
                print(dim(f"  {note}"))
            show(sess)
            handle(sess, ask(bold("  > ")).strip())
    except Quit:
        path = sess.save()
        offer_promotion(story)
        print(f"\n  Saved. Resume with:  storywheel resume {story['id']}")
        if path:
            print(f"  Markdown: {path}")
        return
    path = sess.save()
    offer_promotion(story)
    print(bold(f"\n  Done: {store.title_of(story)}"))
    if path:
        print(f"  Markdown: {path}")
    print(dim(f"  Change anything later with:  storywheel resume {story['id']}"))


# --- choosing between the app and the prompt -------------------------------------------------------

def run(story, plain=False):
    """Roll a story: in the full-screen app when the terminal can, else with prompts."""
    if not plain and sys.stdin.isatty() and sys.stdout.isatty():
        try:
            from .tui import run_app
        except ImportError:
            print(dim("  (The full-screen app needs the 'textual' package; using the prompt instead.)"))
        else:
            from . import modes, state as state_mod
            st = state_mod.State()
            st.update(mode="wheel", draft=story["id"])
            nxt = run_app(story, get_engine(), st)
            if nxt:                                  # F2 / F3, or a promotion: carry on into the next mode
                modes.run(nxt, get_engine, get_ratings)
            return
    if not story["kept"]:
        print(bold("\n  storywheel") + dim("  ·  type ? at any prompt for help"))
    try:
        ask_universe_mode(story)
    except Quit:
        return
    run_plain(story)


# --- subcommands ---------------------------------------------------------------------------

def cmd_new(args):
    run(store.new_story(), plain=getattr(args, "plain", False))

def interactive():
    return sys.stdin.isatty() and sys.stdout.isatty()

def cmd_open(args):
    """Plain `storywheel`: back to exactly where you left off (the Wheel on a new draft the first time)."""
    if getattr(args, "plain", False) or not interactive():
        return cmd_new(args)
    try:
        import textual  # noqa: F401
    except ImportError:
        return cmd_new(args)
    from . import cli_world, migrate, modes
    for line in migrate.migrate_universe_json() + migrate.migrate_manuscripts() + migrate.migrate_exports():
        print("  " + line)
    modes.run(None, get_engine, get_ratings)

def cmd_wheel(args):
    if getattr(args, "plain", False) or not interactive():
        return cmd_new(args)
    from . import modes
    modes.run(("wheel", {}), get_engine, get_ratings)

def emit(data):
    """Machine-readable output: one JSON document on stdout, nothing else."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_list(args):
    cleaned = store.cleanup_empty_drafts()
    if cleaned and not getattr(args, "json", False):
        print(dim(f"  Tidied up: {cleaned} draft{'s' if cleaned != 1 else ''} with nothing kept moved to .trash."))
    stories = store.all_stories()
    if getattr(args, "json", False):
        emit([dict(store.story_json(s), number=n) for n, s in enumerate(stories, 1)])
        return
    if not stories:
        print("  No stories yet. Run  storywheel  to start one.")
        return
    total = len(STEPS)
    for n, s in enumerate(stories, 1):
        print(f"  {n:>3}  {s['id']}  {store.title_of(s):<40} {dim(store.progress_text(s))}")

def cmd_resume(args):
    story = store.find(args.target)
    if not story:
        print("  Couldn't find that story. Try  storywheel list")
        return
    if story.get("promoted"):
        print(dim("  This draft was promoted into the Builder, so it is read-only in the Wheel (edits here would drift from the Builder)."))
        if ask("  Make an editable copy as a new draft? [Y/n] ").strip().lower() in ("n", "no"):
            return
        story = store.copy_as_new(story)
        store.save_draft(story)
    elif story["step"] >= len(STEPS):
        print(dim("  This story is finished; opening on its last step. Use 'back' to change an earlier one."))
    run(story, plain=getattr(args, "plain", False))

def cmd_export(args):
    story = store.find(args.target)
    if not story:
        print("  Couldn't find that story. Try  storywheel list")
        return
    path = store.export(story, args.out)
    if getattr(args, "json", False):
        emit(store.story_json(story, path))
        return
    print(f"  Wrote {path}")

def cmd_show(args):
    story = store.find(args.target)
    if not story:
        if getattr(args, "json", False):
            emit({"error": "no such story", "target": args.target})
        else:
            print("  Couldn't find that story. Try  storywheel list")
        raise SystemExit(1)
    if getattr(args, "json", False):
        emit(store.story_json(story))
    else:
        print(store.to_plain(story) or "  (nothing kept in that story yet)")

def cmd_universe(args):
    """The old single universe. Its contents live in the library now, as universes of entities."""
    from . import cli_world, migrate
    for line in migrate.migrate_universe_json():
        print("  " + line)
    print(dim("  The single universe is gone: universes are folders of characters, places and things now."))
    cli_world.cmd_universes(argparse.Namespace(action="list", json=False, name=None, genres=None))

def cmd_sample(args):
    from .sample import build_story, sample
    if args.structure and not structures.find(args.structure):
        names = ", ".join(s.name for s in structures.registry().values())
        sys.exit(f"  No structure called '{args.structure}'. Choose one of: {names}")
    if getattr(args, "json", False):
        engine = Engine(seed=args.seed, user_dir=paths.HOME)
        unknown = [g for g in args.genres if g.lower() not in engine.library.profiles]
        if unknown:
            print(f"(No profile for {', '.join(unknown)}: treated as a plain tag.)", file=sys.stderr)
        stories = []
        for _ in range(args.n):
            story = build_story(engine, [g.lower() for g in args.genres], structure=args.structure)
            story["id"], story["created"] = None, story["created"][:10]     # (a sample is not saved)
            stories.append(store.story_json(story))
        emit(stories)
        return
    sample(Engine(seed=args.seed, user_dir=paths.HOME), args.genres, args.n, structure=args.structure)

def cmd_report(args):
    print(ratings_mod.format_report(get_ratings(), args.n))

def main(argv=None):
    plain_parent = argparse.ArgumentParser(add_help=False)
    plain_parent.add_argument("--plain", action="store_true",
                              help="use the simple prompt instead of the full-screen app")
    parser = argparse.ArgumentParser(prog="storywheel", description="Roll a story one piece at a time.",
                                     parents=[plain_parent])
    from . import __version__
    parser.add_argument("--version", action="version", version=f"storywheel {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("new", parents=[plain_parent], help="start a new Wheel draft")
    sub.add_parser("wheel", parents=[plain_parent], help="open the Wheel (on the draft you were on)")
    p = sub.add_parser("list", help="list your stories")
    p.add_argument("--json", action="store_true", help="print the stories as JSON")
    p = sub.add_parser("resume", parents=[plain_parent], help="pick up a story")
    p.add_argument("target", nargs="?", help="number from 'list' or a story id (default: newest)")
    p = sub.add_parser("export", help="write a story's markdown somewhere else")
    p.add_argument("target", help="number from 'list' or a story id")
    p.add_argument("--out", help="folder to write into (e.g. your Obsidian vault)")
    p.add_argument("--json", action="store_true", help="print the story (with its markdown path) as JSON")
    p = sub.add_parser("show", help="print a story as plain text (or JSON)")
    p.add_argument("target", nargs="?", help="number from 'list' or a story id (default: newest)")
    p.add_argument("--json", action="store_true", help="print the story as JSON")
    p = sub.add_parser("sample", help="print sample stories for a genre mix (nothing is saved)")
    p.add_argument("genres", nargs="+", help='e.g.  western "fairy tale"')
    p.add_argument("-n", type=int, default=5, help="how many stories (default 5)")
    p.add_argument("--seed", type=int, help="make the run repeatable")
    p.add_argument("--json", action="store_true", help="print the stories as a JSON list")
    p.add_argument("--structure", help="force a story structure (story-spine, three-act, kishotenketsu); "
                                       "by default each story gets one at random")
    p = sub.add_parser("universe", help="show your universe, or: universe rm KEY NUMBER")
    p.add_argument("action", nargs="?", choices=["rm"])
    p.add_argument("rest", nargs="*")
    p = sub.add_parser("report", help="the worst-rated lines and the frames that produced them")
    p.add_argument("-n", type=int, default=10, help="how many of each (default 10)")
    from . import cli_world
    world = cli_world.add_parsers(sub)
    args = parser.parse_args(argv)
    if args.command in world:
        world[args.command](args)
        return
    {"list": cmd_list, "resume": cmd_resume, "export": cmd_export, "show": cmd_show, "universe": cmd_universe,
     "sample": cmd_sample, "report": cmd_report, "new": cmd_new, "wheel": cmd_wheel}.get(args.command, cmd_open)(args)


if __name__ == "__main__":
    main()
