"""
Roll whole stories without an interactive session, to judge how well a genre
mix is doing:  storywheel sample western "fairy tale" -n 10

Nothing is saved. Each step keeps its first roll, the way pressing [k] would.
"""
import textwrap

from . import store, structures
from .mix import sync_base
from .steps import STEPS, public, roll_mood, steps_for
from .text import fix_articles
from .threads import describe


def build_story(engine, genres, exclude_tags=(), structure=None, focus=None, format=None, ending=None):
    """A complete story for the given genres, every step rolled and kept once.
    The structure is picked at random unless one is given (by name or label); a `focus` (focus.py: one, two, ensemble, place, none) and a
    `format` (formats.py) may be given too. A story with no protagonist has no Protagonist step."""
    from . import endings as endings_mod, focus as focus_mod, formats as formats_mod
    story = store.new_story()
    if ending:
        key = endings_mod.find(ending)
        if key is None:
            raise ValueError(f"No ending called '{ending}'. Known: " + ", ".join(e.key for e in endings_mod.ENDINGS))
        story["ending"] = key
    if focus:
        key = focus_mod.find(focus)
        if key is None:
            raise ValueError(f"No focus called '{focus}'. Known: " + ", ".join(f.key for f in focus_mod.FOCUSES))
        story["focus"] = key
    if format:
        key = formats_mod.find(format)
        if key is None:
            raise ValueError(f"No format called '{format}'. Known: " + ", ".join(f.key for f in formats_mod.FORMATS))
        story["format"] = key
    steps = steps_for(story)
    story["kept"]["genre"] = {"genre": " / ".join(genres), "mood": "", "focus": focus_mod.get(focus_mod.of_draft(story)).label,
                              "ending": endings_mod.get(endings_mod.of_draft(story)).label}
    sync_base(story)
    story["mix"]["exclude_tags"] = [t.lower() for t in exclude_tags]
    story["kept"]["genre"]["mood"] = roll_mood(engine, story, genres)
    if structure:
        found = structures.find(structure)
        if not found:
            raise ValueError(f"No structure called '{structure}'. Known: "
                             + ", ".join(s.name for s in structures.registry().values()))
        story["kept"]["structure"] = {"structure": found.label}
    else:
        story["kept"]["structure"] = {"structure": steps[1].roll(engine, story, fresh=False)["structure"]}
    for step in steps_for(story)[2:]:
        if step.key == "protagonist" and not focus_mod.is_person(focus_mod.of_draft(story)):
            continue
        cand = step.roll(engine, story, fresh=False)
        for k, v in cand.get("_made", {}).items():      # what keeping does
            story["seeds"].setdefault(k, v)
        story["kept"][step.key] = public(cand)
        story["atoms"][step.key] = [a for lst in cand.get("_atoms", {}).values() for a in lst]
        if step.key == "spine":
            story["threads"] = cand["_threads"]
    return story


def _with_article(rival):
    """'sheriff' -> 'the sheriff'; a proper name ('Sheriff Lund') stands alone."""
    return rival if rival[:1].isupper() else f"the {rival}"


def render(story, number=None, width=78):
    k = story["kept"]

    def wrap(text, indent="    "):
        return textwrap.fill(text, width, initial_indent=indent, subsequent_indent=" " * len(indent))

    p, s = k.get("protagonist"), k["setting"]
    shape = structures.get((k.get("structure") or {}).get("structure"))
    head = f"{number}. " if number else ""
    out = [f"{head}{k['title']['title'].upper()}   (motif: {k['title']['motif']})",
           f"   {k['genre']['genre']} · {k['genre']['mood']} · {shape.label}",
           "",
           wrap(fix_articles(f"{p['name']}, {p['age']}, a {p['trait']} {p['job']}. ")
                + f"Wants {p['want']}. Needs {p['need']}. Flaw: {p['flaw']}. "
                f"Secret: {p['secret']}. Rival: {_with_article(p['rival'])}." + (f" Partner: {p['partner']}." if p.get("partner") else "")
                + (f" Company: {p['company']}." if p.get("company") else ""), "  * ") if p else
           wrap(f"No protagonist: {k['genre'].get('focus', 'a story about a place').lower()}.", "  * "),
           wrap(f"{s['place']} · {s['era']} · {s['season']}. Landmark: {s['landmark']}. "
                f"Rumor: {s['rumor']}.", "  * "),
           "",
           wrap(k["premise"]["premise"]),
           ""]
    labels = shape.labels
    out += [wrap((f"{labels[key]} — " if shape.show_labels else "") + text, "    ")
            for key, text in k["spine"].items()]
    out += ["", wrap("Twist: " + k["twist"]["twist"])]
    if story.get("threads"):
        out.append(wrap("Threads: " + describe(story["threads"]), "    "))
    return "\n".join(out)


def sample(engine, genres, n, out=print, structure=None, focus=None, format=None, ending=None):
    unknown = [g for g in genres if g.lower() not in engine.library.profiles]
    if unknown:
        out(f"(No profile for {', '.join(unknown)}: treated as a plain tag. "
            f"Known genres: {', '.join(engine.library.genre_names)})\n")
    for i in range(1, n + 1):
        out(render(build_story(engine, [g.lower() for g in genres], structure=structure, focus=focus, format=format, ending=ending), i))
        out("")
    for note in engine.take_notices():
        out(f"Note: {note}")
