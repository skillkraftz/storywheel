"""Story ideas: a title and a few lines, put on a shelf (usually a collection) with no structure and no promotion screen.

    new_idea(universe, title, text="", fmt="flash")       a new idea story: the lines are its logline (the first) and its notes (all of them)
    send_draft(draft, universe)                           a Wheel draft's title and premise as a new idea story; returns the story
    split_lines(text)                                     (logline, notes) from what was typed

An idea is an ordinary story in every way (outline, notes, settings, an empty manuscript the Writer opens at once): it just starts small.
Flash fiction is the default format; a short story can be chosen."""
from . import formats, store, vault

IDEA_FORMATS = ("flash", "short-story")


def split_lines(text):
    """(logline, notes): the first non-empty line is the logline; all the lines, as typed, are the notes."""
    lines = [l.rstrip() for l in str(text or "").strip().splitlines()]
    first = next((l.strip() for l in lines if l.strip()), "")
    return first, "\n".join(lines).strip()


def new_idea(universe, title, text="", fmt="flash", status=None, extra=None):
    """Make the idea. The format is flash or short-story (or any format key); the story has no structure and an empty outline apart
    from the logline and, when there is text, the notes."""
    title = (title or "").strip()
    if not title:
        raise ValueError("An idea needs a title.")
    key = formats.find(fmt) or "flash"
    logline, notes = split_lines(text)
    meta = {"format": key}
    if logline:
        meta["logline"] = logline
    if status:
        if status not in vault.STATUSES:
            raise ValueError(f"Unknown status '{status}'. Choose one of: {', '.join(vault.STATUSES)}")
        meta["status"] = status
    meta.update(extra or {})
    story = universe.new_story(title, meta)
    if notes:
        story.save_notes(notes)
    return story


def send_draft(draft, universe):
    """The draft's title and premise as a new idea story in `universe`. Returns the story. The draft itself is not promoted or changed
    except for a note of where it went (`ideas`), so it can still be promoted later."""
    kept = draft.get("kept") or {}
    title = store.title_of(draft)
    premise = " ".join(((kept.get("premise") or {}).get("premise") or "").split())
    key = formats.of_draft(draft)
    story = new_idea(universe, title, premise, key if key in IDEA_FORMATS else "flash",
                     extra={"idea_from": draft.get("id", "")} if draft.get("id") else None)
    if premise:
        story.set_section("Premise", premise)
    draft.setdefault("ideas", []).append({"universe": universe.slug, "story": story.slug})
    return story
