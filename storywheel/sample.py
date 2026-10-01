"""
Roll whole stories without an interactive session, to judge how well a genre
mix is doing:  storywheel sample western "fairy tale" -n 10

Nothing is saved. Each step keeps its first roll, the way pressing [k] would.
"""
import textwrap

from . import store
from .mix import sync_base
from .steps import STEPS, public
from .text import fix_articles


def build_story(engine, genres, exclude_tags=()):
    """A complete story for the given genres, every step rolled and kept once."""
    story = store.new_story()
    mood = STEPS[0].roll(engine, story, fresh=False)["mood"]
    story["kept"]["genre"] = {"genre": " / ".join(genres), "mood": mood}
    sync_base(story)
    story["mix"]["exclude_tags"] = [t.lower() for t in exclude_tags]
    for step in STEPS[1:]:
        cand = step.roll(engine, story, fresh=False)
        for k, v in cand.get("_made", {}).items():      # what keeping does
            story["seeds"].setdefault(k, v)
        story["kept"][step.key] = public(cand)
    return story


def render(story, number=None, width=78):
    k = story["kept"]

    def wrap(text, indent="    "):
        return textwrap.fill(text, width, initial_indent=indent, subsequent_indent=" " * len(indent))

    p, s = k["protagonist"], k["setting"]
    head = f"{number}. " if number else ""
    out = [f"{head}{k['title']['title'].upper()}   (motif: {k['title']['motif']})",
           f"   {k['genre']['genre']} · {k['genre']['mood']}",
           "",
           wrap(fix_articles(f"{p['name']}, {p['age']}, a {p['trait']} {p['job']}. ")
                + f"Wants {p['want']}. Needs {p['need']}. Flaw: {p['flaw']}. "
                f"Secret: {p['secret']}. Rival: the {p['rival']}.", "  * "),
           wrap(f"{s['place']} · {s['era']} · {s['season']}. Landmark: {s['landmark']}. "
                f"Rumor: {s['rumor']}.", "  * "),
           "",
           wrap(k["premise"]["premise"]),
           ""]
    out += [wrap(text) for text in k["spine"].values()]
    out += ["", wrap("Twist: " + k["twist"]["twist"])]
    return "\n".join(out)


def sample(engine, genres, n, out=print):
    unknown = [g for g in genres if g.lower() not in engine.library.profiles]
    if unknown:
        out(f"(No profile for {', '.join(unknown)}: treated as a plain tag. "
            f"Known genres: {', '.join(engine.library.genre_names)})\n")
    for i in range(1, n + 1):
        out(render(build_story(engine, [g.lower() for g in genres]), i))
        out("")
    for note in engine.take_notices():
        out(f"Note: {note}")
