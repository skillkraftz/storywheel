"""
The three modes and the hotkeys between them (F1 Wheel, F2 Builder, F3 Writer), and where you left off.

`run()` keeps going until you quit: each mode runs, says where it wants to go next, and the loop takes it there. What
you were doing is kept in ~/.storywheel/state.json, so plain `storywheel` reopens exactly there.
"""
import sys

from . import paths, state as state_mod, store, vault, writer


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
    story = None
    if payload.get("new"):
        story = store.new_story()
        if payload.get("universe"):
            story["universes"] = [payload["universe"]]
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
    elif story["step"] >= len(store.steps_for(story)):
        story["step"] = 0                      # a finished draft: start from the top so things can be changed
    st.update(mode="wheel", draft=story["id"])
    return run_app(story, get_engine(), st)


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
    where = writer.run(story)
    st.update(mode="builder" if where != "wheel" else "wheel")
    return (where or "builder", {"universe": u.slug, "story": story.slug})


def run_settings(st, payload):
    from . import settings_app
    back = payload.get("back") or st.get("back") or ("builder" if vault.list_universes() else "wheel")
    return settings_app.run_settings(st, back)


def run(start=None, get_engine=None, get_ratings=None):
    """Run modes until the writer quits. `start` is (mode, payload) or None (use the saved state)."""
    st = state_mod.State()
    mode, payload = start or (st.get("mode") or "wheel", {})
    while mode in ("wheel", "builder", "writer", "settings"):
        if mode == "wheel":
            nxt = run_wheel(st, payload, get_engine)
        elif mode == "builder":
            nxt = run_builder(st, payload, get_ratings)
        elif mode == "writer":
            nxt = run_writer(st, payload)
        else:
            nxt = run_settings(st, payload)
        if not nxt or nxt[0] not in ("wheel", "builder", "writer", "settings"):
            break
        came_from = mode
        mode, payload = nxt
        if mode == "settings":
            payload = dict(payload, back=came_from)         # q in Settings goes back to where F4 was pressed
