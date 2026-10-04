"""
The three modes and the hotkeys between them (F1 Wheel, F2 Builder, F3 Writer), and where you left off.

`run()` keeps going until you quit: each mode runs, says where it wants to go next, and the loop takes it there. What
you were doing is kept in ~/.storywheel/state.json, so plain `storywheel` reopens exactly there.
"""
import os
import sys

from . import paths, state as state_mod, store, vault, writer


TRAIL = []          # the modes you came through, most recent last: q goes back along it


def can_go_back():
    return bool(TRAIL)


def _arrive(came_from, mode):
    """Update the trail for a move from `came_from` to `mode` (a mode already on the trail cuts it back to there instead of growing it)."""
    if mode == came_from:
        return
    if mode in TRAIL:
        del TRAIL[len(TRAIL) - 1 - TRAIL[::-1].index(mode):]
        return
    TRAIL.append(came_from)
    del TRAIL[:-20]


def _resolve_story(st, payload):
    """(universe, story) to write, from the payload or from where you were last."""
    uni = payload.get("universe") or st.get("universe")
    slug = payload.get("story") or st.get("story")
    u = vault.get_universe(uni) if uni else None
    story = u.story(slug) if (u and slug) else None
    if not story and u and u.stories():
        story = u.stories()[0]
    return u, story


def run_wheel(st, payload, get_engine, plain=False):
    from .tui import run_app
    cleaned = store.cleanup_empty_drafts()
    notice = (f"Tidied up: {cleaned} draft{'s' if cleaned != 1 else ''} with nothing kept {'were' if cleaned != 1 else 'was'} "
              "moved to the .trash folder in your storywheel home.") if cleaned else ""
    story = None
    if payload.get("new"):
        story = store.new_story()
        if payload.get("universe"):
            story["universes"] = [payload["universe"]]
            story["home"] = payload["universe"]
    elif payload.get("story_id"):
        story = store.load(payload["story_id"])
    elif st.get("draft"):
        try:
            story = store.load(st.get("draft"))
        except (OSError, ValueError):
            story = None
    if story is None:
        story = store.new_story()
        if payload.get("universe"):
            story["universes"] = [payload["universe"]]
            story["home"] = payload["universe"]
    st.update(mode="wheel", draft=story["id"])
    return run_app(story, get_engine(), st, notice)


def run_builder(st, payload, get_ratings):
    from . import builder
    st.update(mode="builder")
    app = builder.run_builder(payload.get("universe") or st.get("universe"), payload.get("story") or st.get("story"),
                              get_ratings(), st, tab=st.get("tab"), entity=st.get("entity"), rtab=st.get("rtab"))
    return app.next


def run_writer(st, payload):
    u, story = _resolve_story(st, payload)
    if not story:
        print("  There is no story to write yet. Promote a Wheel story into a universe first (leave the Wheel with q).")
        return ("builder" if vault.list_universes() else "wheel", {})
    problem = writer.check()
    if problem:
        print("  " + problem)
        return ("builder", {"universe": u.slug})
    st.update(mode="writer", universe=u.slug, story=story.slug)
    note = writer.kitty_note(story)
    if note:
        print("  " + note)
    where = writer.run(story, payload.get("scene"), payload.get("replace"))
    st.update(mode="builder" if where not in ("wheel", "words") else where)
    if where == "words":                                   # F5 in the Writer: the word under the cursor goes along
        return ("words", {"universe": u.slug, "story": story.slug, "handover": writer.run.handover, "back": "writer"})
    return (where or "builder", {"universe": u.slug, "story": story.slug})


def run_settings(st, payload):
    from . import settings_app
    back = payload.get("back") or st.get("back") or ("builder" if vault.list_universes() else "wheel")
    return settings_app.run_settings(st, back)


def run_words(st, payload):
    from . import words_app
    back = payload.get("back") or st.get("back") or ("builder" if vault.list_universes() else "wheel")
    if not payload.get("universe"):
        payload = dict(payload, universe=st.get("universe"), story=st.get("story"))
    return words_app.run_words(st, back, payload)


def run(start=None, get_engine=None, get_ratings=None):
    """Run the modes until the writer quits: one Textual app holds them all (hub.py). `run_classic` is the older loop that closes one
    app and starts the next; STORYWHEEL_CLASSIC=1 uses it."""
    if os.environ.get("STORYWHEEL_CLASSIC"):
        return run_classic(start, get_engine, get_ratings)
    from . import hub
    st = state_mod.State()
    return hub.run(start or (st.get("mode") or "wheel", {}), get_engine, get_ratings)


def run_classic(start=None, get_engine=None, get_ratings=None):
    """Run modes until the writer quits. `start` is (mode, payload) or None (use the saved state)."""
    st = state_mod.State()
    mode, payload = start or (st.get("mode") or "wheel", {})
    while mode in ("wheel", "builder", "writer", "settings", "words"):
        if mode == "wheel":
            nxt = run_wheel(st, payload, get_engine)
        elif mode == "builder":
            nxt = run_builder(st, payload, get_ratings)
        elif mode == "writer":
            nxt = run_writer(st, payload)
        elif mode == "words":
            nxt = run_words(st, payload)
        else:
            nxt = run_settings(st, payload)
        if nxt and nxt[0] == "back":                          # q: back to the mode you came from
            target = TRAIL.pop() if TRAIL else (nxt[1].get("fallback") or ("builder" if vault.list_universes() else "wheel"))
            nxt = (target, nxt[1])
        elif nxt and nxt[0] in ("wheel", "builder", "writer", "settings", "words"):
            _arrive(mode, nxt[0])
        if not nxt or nxt[0] not in ("wheel", "builder", "writer", "settings", "words"):
            break
        came_from = mode
        mode, payload = nxt
        if mode in ("settings", "words") and "back" not in payload:
            payload = dict(payload, back=came_from)         # q in Settings or Words goes back to where F4 / F5 was pressed
