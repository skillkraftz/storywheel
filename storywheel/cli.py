"""
storywheel - roll a story one piece at a time.

    storywheel              start a new story
    storywheel list         list your stories
    storywheel resume [N]   pick up a story (number from list, or newest)
    storywheel export N     write a story's markdown somewhere else (--out DIR)
    storywheel universe     show what you've saved to your universe
    storywheel sample G...  print sample stories for a genre mix (-n 10, --seed 1, --structure three-act)
"""
import argparse
import os
import random
import re
import shlex
import subprocess
import sys
import tempfile
import textwrap

from . import paths, store
from .engine import Engine
from . import threads as T
from .refs import carry_threads, inherit, reroll_field, substitute, with_field
from . import structures
from .steps import STEPS, public, steps_for

try:
    import readline                      # arrow keys + pre-filled edits on Linux/Mac
except ImportError:                      # pragma: no cover (Windows)
    readline = None

TTY = sys.stdout.isatty()
def _style(code):
    return (lambda s: f"\033[{code}m{s}\033[0m") if TTY else (lambda s: s)
bold, dim, cyan = _style("1"), _style("2"), _style("36")

_engine = None

def get_engine():
    """One engine per run. It remembers recent picks, in ~/.storywheel/recent.json, so
    the same lines don't turn up session after session."""
    global _engine
    if _engine is None:
        _engine = Engine(user_dir=paths.HOME, persist=True)
    return _engine

def _save(story):
    """Save the story and the memory of recent picks."""
    path = store.save(story)
    get_engine().save_memory()
    return path

UNIVERSE_CHANCE = 0.35       # how often "mix" mode pulls from your universe
SOURCE_TAGS = {"edited": " (your edit)", "universe": " (from your universe)", "kept": " (kept)"}

HELP = """
  enter / r     roll again
  k             keep this one and move on
  f [field]     reroll just one field, e.g.  f flaw  or  f 3
  e [field]     edit a field in place (single-field steps skip the question)
  E             edit the whole thing in your $EDITOR (nano by default)
  w             write your own from scratch
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

def show(step, i, hist, cur, total=len(STEPS)):
    cand = hist[cur]
    fields = public(cand)
    print("\n" + bold(cyan(f"── {step.label.upper()}  ({i + 1}/{total}) ")) + cyan("─" * 30))
    print(dim(textwrap.fill(step.hint, 72, initial_indent="  ", subsequent_indent="  ")))
    print(bold(f"\n  #{cur + 1} of {len(hist)}") + dim(SOURCE_TAGS.get(cand.get("_src"), "")))
    if step.single:
        print(textwrap.fill(next(iter(fields.values())), 72,
                            initial_indent="    ", subsequent_indent="    "))
    else:
        width = max(len(k) for k in fields) + 2
        for n, (k, v) in enumerate(fields.items(), 1):
            label = f"  {n} {k.replace('_', ' '):<{width}}"
            print(textwrap.fill(v, 76, initial_indent=label,
                                subsequent_indent=" " * len(label)))
    opts = "[enter] roll  [k]eep  " + ("" if step.single else "[f]ield  ") + \
           "[e]dit  [w]rite  [p]ick #  [h]istory  [u]/[U]niverse  [b]ack  [x] skip  [q]uit  [?]"
    if step.key == "structure":
        found = structures.find(fields["structure"])
        print(dim("\n  " + textwrap.fill(found.blurb if found else
                                          "Not one of the known structures; the Story Spine will be used.",
                                          72, subsequent_indent="  ")))
    if cand.get("_threads"):
        print(dim("\n  threads  " + T.describe(cand["_threads"])))
    print(dim("\n  " + opts))

def summary(step, cand):
    vals = list(public(cand).values())
    text = vals[0] if step.single else " · ".join(vals[:3])
    return text if len(text) < 70 else text[:67] + "..."


# --- the roll loop ---------------------------------------------------------------------------

def fresh_candidate(make, hist, tries=6):
    """Call make() until it gives something not already in this step's history."""
    seen = [public(c) for c in hist]
    for _ in range(tries):
        cand = make()
        if public(cand) not in seen:
            break
    return cand

def roll(step, story, fresh=True):
    entries = store.load_universe().get(step.key, [])
    mode = story.get("universe_mode", "n")
    if entries and (mode == "o" or (mode == "m" and random.random() < UNIVERSE_CHANCE)):
        return dict(random.choice(entries), _src="universe")
    return step.roll(get_engine(), story, fresh=fresh)

def choose_field(step, arg):
    names = list(step.fields)
    if step.single:
        return names[0]
    arg = arg or ask("  which field? (name or number) ").strip()
    if arg.isdigit() and 1 <= int(arg) <= len(names):
        return names[int(arg) - 1]
    if arg.replace(" ", "_") in names:
        return arg.replace(" ", "_")
    print(f"  No field '{arg}'. Fields: {', '.join(names)}")
    return None

def short(text, n=60):
    return text if len(text) <= n else text[:n - 3] + "..."

def pick_from_list(count):
    """Ask for a number from a list just shown. Returns a 0-based index or None."""
    choice = ask(dim("\n  pick # (enter to go back) ")).strip()
    if choice.isdigit() and 1 <= int(choice) <= count:
        return int(choice) - 1
    return None

def show_history(step, hist, cur):
    """Whole candidates. For multi-field steps, show only what changed each time."""
    print()
    for n, c in enumerate(hist):
        marker = "→" if n == cur else " "
        if step.single or n == 0:
            text = summary(step, c)
        else:
            prev = public(hist[n - 1])
            changed = [k for k, v in public(c).items() if prev.get(k) != v]
            if not changed:
                text = "(same as previous)"
            elif len(changed) > 2:
                text = summary(step, c)
            else:
                text = "; ".join(f"{k.replace('_', ' ')}: {short(c[k], 70 // len(changed))}" for k in changed)
        print(f"  {marker} #{n + 1:<3}{text}" + dim(SOURCE_TAGS.get(c.get("_src"), "")))
    if not step.single:
        print(dim("\n  Tip: h 3 lists every value field 3 has had."))
    return pick_from_list(len(hist))

def show_field_history(step, hist, cand, field):
    """Every distinct value one field has had, so you can bring back an old one."""
    values = []
    for c in hist:
        if c.get(field) and c[field] not in values:
            values.append(c[field])
    print(f"\n  every {field.replace('_', ' ')} so far:")
    for n, v in enumerate(values, 1):
        marker = "→" if v == cand.get(field) else " "
        print(textwrap.fill(v, 76, initial_indent=f"  {marker} {n:<3}", subsequent_indent=" " * 8))
    idx = pick_from_list(len(values))
    return None if idx is None else values[idx]

def run_step(story, i):
    """Roll one step until the user keeps, skips, goes back or quits.
    Returns the next step index."""
    step = steps_for(story)[i]
    hist = story["history"].setdefault(step.key, [])
    kept = story["kept"].get(step.key)
    if kept and (not hist or public(hist[-1]) != public(kept)):
        hist.append(dict(public(kept), _src="kept"))
    if not hist:
        hist.append(roll(step, story, fresh=False))     # first roll may reuse seeds
    cur = len(hist) - 1

    while True:
        for note in get_engine().take_notices():
            print(dim(f"  Note: {note}"))
        show(step, i, hist, cur)
        raw = ask(bold("  > ")).strip()
        m = re.match(r"^([A-Za-z?])\s*(.*)$", raw)
        cmd, arg = (m.group(1), m.group(2).strip()) if m else (raw, "")
        cand = hist[cur]

        if cmd in ("", "r"):
            hist.append(fresh_candidate(lambda: roll(step, story), hist))
            cur = len(hist) - 1

        elif cmd == "k":
            old = story["kept"].get(step.key)
            new = public(cand)
            if step.key == "structure" and structures.find(new["structure"]):
                new["structure"] = structures.find(new["structure"]).label     # "kishotenketsu" -> "Kishōtenketsu"
            for k, v in cand.get("_made", {}).items():
                story["seeds"].setdefault(k, v)
            story["kept"][step.key] = new
            if step.key == "structure" and old and structures.get(old["structure"]) is not structures.get(new["structure"]):
                for gone in ("spine",):                 # the old body doesn't fit the new shape
                    story["kept"].pop(gone, None)
                    story["history"].pop(gone, None)
                    story["atoms"].pop(gone, None)
                story["threads"] = {}
                print(dim("  New structure: the story body will be rolled again when you get to it."))
            if old and old != new:
                n = substitute(story, i, old, new)
                if step.threads:
                    n += carry_threads(story, i, story.get("threads"), cand.get("_threads"))
                if n:
                    print(dim(f"  Updated {n} mention(s) in later steps."))
            if step.threads:
                story["threads"] = cand.get("_threads", {})
            story["atoms"][step.key] = [a for lst in cand.get("_atoms", {}).values() for a in lst]
            story["step"] = max(story["step"], i + 1)
            _save(story)
            return i + 1

        elif cmd == "f" and not step.single:
            field = choose_field(step, arg)
            if field:
                new = fresh_candidate(lambda: reroll_field(step, get_engine(), story, cand, field), hist)
                hist.append(new)
                cur = len(hist) - 1

        elif cmd == "e":
            field = choose_field(step, arg)
            if field:
                text = ask(f"  {field}: ", prefill=cand[field]).strip()
                if text and text != cand[field]:
                    hist.append(with_field(cand, field, text, src="edited"))
                    cur = len(hist) - 1

        elif cmd == "E":
            new = edit_in_editor(public(cand))
            if new != public(cand):
                hist.append(inherit(dict(new, _src="edited"), cand))
                cur = len(hist) - 1

        elif cmd == "w":
            fields = public(cand)
            if not step.single:
                print(dim("  Type a new value for each field, or press enter to keep the current one."))
            new = {}
            for k, v in fields.items():
                label = f"  {k.replace('_', ' ')}" + ("" if step.single else dim(f" [{v}]"))
                new[k] = ask(label + ": ").strip() or v
            if new != fields:
                hist.append(inherit(dict(new, _src="edited"), cand))
                cur = len(hist) - 1

        elif cmd == "p":
            if arg.isdigit() and 1 <= int(arg) <= len(hist):
                cur = int(arg) - 1
            else:
                print(f"  Pick a number from 1 to {len(hist)}, e.g.  p 2")

        elif cmd == "h":
            if arg and not step.single:
                field = choose_field(step, arg)
                value = field and show_field_history(step, hist, cand, field)
                if value and value != cand[field]:
                    hist.append(with_field(cand, field, value))
                    cur = len(hist) - 1
            else:
                idx = show_history(step, hist, cur)
                cur = cur if idx is None else idx

        elif cmd == "u":
            n, added = store.add_to_universe(step.key, cand)
            what = f"{n} {step.label.lower()} entr{'y' if n == 1 else 'ies'}"
            print(dim(f"  {'Saved to' if added else 'Already in'} your universe ({what}). U removes it."))

        elif cmd == "U":
            removed = store.remove_from_universe(step.key, cand)
            print(dim("  Removed from your universe." if removed else "  This one isn't in your universe."))

        elif cmd == "b":
            if i == 0:
                print("  This is the first step.")
            else:
                _save(story)
                return i - 1

        elif cmd == "x":
            story["kept"].pop(step.key, None)
            if step.threads:
                story["threads"] = {}
            story["atoms"].pop(step.key, None)
            story["step"] = max(story["step"], i + 1)
            _save(story)
            return i + 1

        elif cmd == "q":
            raise Quit

        elif cmd == "?":
            print(HELP)
            ask(dim("  (enter to continue) "))

        else:
            print(f"  Unknown command '{raw}'. Type ? for help.")


def ask_universe_mode(story):
    universe = store.load_universe()
    total = sum(len(v) for v in universe.values())
    if not total:
        return
    print(f"\n  You have {total} thing(s) saved in your universe.")
    answer = ask("  Pull from it? [n]o / [m]ix it in / [o]nly from it: ").strip().lower()[:1]
    story["universe_mode"] = answer if answer in ("m", "o") else "n"

def run(story):
    i = story["step"] if story["step"] < len(STEPS) else 0
    try:
        while i < len(STEPS):
            i = run_step(story, i)
    except Quit:
        path = _save(story)
        print(f"\n  Saved. Resume with:  storywheel resume {story['id']}")
        if path:
            print(f"  Markdown: {path}")
        return
    path = _save(story)
    print(bold(f"\n  Done: {store.title_of(story)}"))
    if path:
        print(f"  Markdown: {path}")
    print(dim(f"  Change anything later with:  storywheel resume {story['id']}"))


# --- subcommands ---------------------------------------------------------------------------

def cmd_new(args):
    story = store.new_story()
    print(bold("\n  storywheel") + dim("  ·  type ? at any prompt for help"))
    try:
        ask_universe_mode(story)
    except Quit:
        return
    run(story)

def cmd_list(args):
    stories = store.all_stories()
    if not stories:
        print("  No stories yet. Run  storywheel  to start one.")
        return
    for n, s in enumerate(stories, 1):
        done = "done" if s["step"] >= len(STEPS) else f"step {s['step'] + 1}/{len(STEPS)}"
        print(f"  {n:>3}  {s['id']}  {store.title_of(s):<40} {dim(done)}")

def cmd_resume(args):
    story = store.find(args.target)
    if not story:
        print("  Couldn't find that story. Try  storywheel list")
        return
    if story["step"] >= len(STEPS):
        print(dim("  This story is finished; starting from the first step so you can change things."))
        story["step"] = 0
    try:
        ask_universe_mode(story)
    except Quit:
        return
    run(story)

def cmd_export(args):
    story = store.find(args.target)
    if not story:
        print("  Couldn't find that story. Try  storywheel list")
        return
    print(f"  Wrote {store.export(story, args.out)}")

def cmd_universe(args):
    if args.action == "rm":
        if len(args.rest) != 2 or not args.rest[1].isdigit():
            print("  Usage:  storywheel universe rm STEP NUMBER   (e.g. rm spine 1)")
            return
        entry = store.remove_universe_entry(args.rest[0], int(args.rest[1]) - 1)
        print("  Removed." if entry else "  No such entry. Run  storywheel universe  to see numbers.")
        return
    universe = store.load_universe()
    if not any(universe.values()):
        print("  Your universe is empty. Press [u] while rolling to save something to it.")
        return
    labels = {s.key: s for s in STEPS}
    for key, entries in universe.items():
        if not entries:
            continue
        step = labels.get(key)
        print(bold(f"\n  {step.label if step else key}") + dim(f"  ({len(entries)})  key: {key}"))
        for n, e in enumerate(entries, 1):
            print(f"    {n:>2}  {summary(step, e) if step else e}")
    print(dim("\n  Remove one with:  storywheel universe rm KEY NUMBER   (e.g. rm spine 1)"))
    print(dim(f"  Or edit {store.UNIVERSE} by hand."))

def cmd_sample(args):
    from .sample import sample
    if args.structure and not structures.find(args.structure):
        names = ", ".join(s.name for s in structures.registry().values())
        sys.exit(f"  No structure called '{args.structure}'. Choose one of: {names}")
    sample(Engine(seed=args.seed, user_dir=paths.HOME), args.genres, args.n, structure=args.structure)

def main():
    parser = argparse.ArgumentParser(prog="storywheel", description="Roll a story one piece at a time.")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("new", help="start a new story (the default)")
    sub.add_parser("list", help="list your stories")
    p = sub.add_parser("resume", help="pick up a story")
    p.add_argument("target", nargs="?", help="number from 'list' or a story id (default: newest)")
    p = sub.add_parser("export", help="write a story's markdown somewhere else")
    p.add_argument("target", help="number from 'list' or a story id")
    p.add_argument("--out", help="folder to write into (e.g. your Obsidian vault)")
    p = sub.add_parser("sample", help="print sample stories for a genre mix (nothing is saved)")
    p.add_argument("genres", nargs="+", help='e.g.  western "fairy tale"')
    p.add_argument("-n", type=int, default=5, help="how many stories (default 5)")
    p.add_argument("--seed", type=int, help="make the run repeatable")
    p.add_argument("--structure", help="force a story structure (story-spine, three-act, kishotenketsu); "
                                       "by default each story gets one at random")
    p = sub.add_parser("universe", help="show your universe, or: universe rm KEY NUMBER")
    p.add_argument("action", nargs="?", choices=["rm"])
    p.add_argument("rest", nargs="*")
    args = parser.parse_args()
    {"list": cmd_list, "resume": cmd_resume, "export": cmd_export,
     "universe": cmd_universe, "sample": cmd_sample}.get(args.command, cmd_new)(args)


if __name__ == "__main__":
    main()
