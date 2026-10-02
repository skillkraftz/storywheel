"""Wheel drafts: no file until something is kept, empty ones tidied to .trash, honest progress, finished drafts reopen where
they ended, and a promoted draft is read-only in the Wheel (with 'copy as new draft')."""
import asyncio
import json

from storywheel import modes, promote, store
from storywheel.engine import Engine
from storywheel.sample import build_story
from storywheel.session import Session
from conftest import make_engine


def finished(home):
    story = build_story(make_engine(home), ["western"])
    story["step"] = len(store.steps_for(story))                 # (a finished draft has walked past the last step)
    return story


def files():
    return sorted(p.name for p in store.STORIES.glob("*.json")) if store.STORIES.exists() else []


def test_an_untouched_draft_leaves_no_file(home):
    s = Session(store.new_story(), make_engine(home))
    s.enter(0)
    s.roll()
    s.roll()
    s.save()
    assert files() == []


def test_the_first_keep_creates_the_file(home):
    s = Session(store.new_story(), make_engine(home))
    s.enter(0)
    s.keep()
    assert len(files()) == 1 and store.load(s.story["id"])["kept"]


def test_cleanup_moves_empty_drafts_to_trash_and_counts_them(home):
    store.STORIES.mkdir(parents=True, exist_ok=True)
    empty = store.new_story()
    (store.STORIES / "a-empty.json").write_text(json.dumps(empty))
    (store.STORIES / "b-empty.json").write_text(json.dumps(dict(empty, id="b")))
    full = build_story(make_engine(home), ["western"])
    store.save(full)
    promoted_empty = dict(empty, id="p", promoted={"universe": "u", "story": "s"})
    (store.STORIES / "p.json").write_text(json.dumps(promoted_empty))
    assert store.cleanup_empty_drafts() == 2
    assert sorted(p.name for p in (store.HOME / ".trash").iterdir()) == ["a-empty.json", "b-empty.json"]
    assert sorted(p.stem for p in store.STORIES.glob("*.json")) == sorted([full["id"], "p"])
    assert store.cleanup_empty_drafts() == 0


def test_the_wheel_says_how_many_were_tidied(home):
    store.STORIES.mkdir(parents=True, exist_ok=True)
    (store.STORIES / "x.json").write_text(json.dumps(store.new_story()))
    from storywheel import tui
    seen = {}
    def fake_run_app(story, engine, st, notice=""):
        seen["notice"] = notice
    import storywheel.tui
    real = storywheel.tui.run_app
    storywheel.tui.run_app = fake_run_app
    try:
        modes.run_wheel({}, {"new": True}, lambda: make_engine(home))
    finally:
        storywheel.tui.run_app = real
    assert "1 draft with nothing kept was moved to the .trash" in seen["notice"]


def test_progress_counts_kept_steps_not_the_current_step(home):
    story = finished(home)
    kept, total, done = store.progress(story)
    assert (kept, total, done) == (total, total, True) and store.progress_text(story).endswith("done")
    story["kept"].pop("twist")
    story["step"] = 4
    assert store.progress(story)[:2] == (total - 1, total) and not store.progress(story)[2]
    fresh = store.new_story()
    assert store.progress(fresh) == (0, total, False)


def test_a_finished_draft_reopens_on_its_last_step_not_the_first(home):
    story = finished(home)
    n = len(store.steps_for(story))
    assert store.open_step(story) == n - 1
    story["step"] = 3
    assert store.open_step(story) == 3


def test_the_wheel_opens_a_finished_draft_on_the_last_step_and_keeps_its_progress(home):
    story = finished(home)
    store.save(story)
    from storywheel import tui
    async def go():
        app = tui.StorywheelApp(store.load(story["id"]), make_engine(home))
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            return app.main.session.i, app.main.session.story["step"], str(app.main.query_one("#status").content)
    i, step, status = asyncio.run(go())
    assert i == len(store.steps_for(story)) - 1 and step >= len(store.steps_for(story)) and "finished" in status


def test_past_stories_show_kept_progress(home):
    story = build_story(make_engine(home), ["western"])
    story["kept"].pop("twist")
    story["step"] = 2
    store.save(story)
    from storywheel import tui
    async def go():
        app = tui.StorywheelApp(store.load(story["id"]), make_engine(home))
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            lst = app.main.query_one("#stories")
            return str(lst.get_option_at_index(0).prompt)
    row = asyncio.run(go())
    total = len(store.steps_for(story))
    assert f"{total - 1}/{total}" in row and "2/" not in row.replace(f"{total - 1}/", "")


# --- promoted drafts are read-only in the Wheel ----------------------------------------------------------------------

def promoted_draft(home):
    d = build_story(make_engine(home), ["western"])
    plan = promote.build_plan(d, None, Engine(seed=1), "Thornwood")
    promote.apply_plan(plan, None, d)
    store.save_draft(d)
    return d


def test_a_promoted_draft_refuses_edits_in_the_wheel_and_nothing_changes(home):
    d = promoted_draft(home)
    from storywheel import tui
    before = json.dumps(store.load(d["id"])["kept"], sort_keys=True)
    async def go():
        app = tui.StorywheelApp(store.load(d["id"]), make_engine(home))
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            first = str(app.main.query_one("#status").content)
            msgs = []
            for key in ("space", "k", "f", "w", "x", "E"):
                await pilot.press(key)
                await pilot.pause()
                msgs.append(str(app.main.query_one("#status").content))
            return first, msgs, json.dumps(app.main.session.story["kept"], sort_keys=True)
    first, msgs, after = asyncio.run(go())
    assert "promoted" in first and "read-only" in first.lower() and "C makes an editable copy" in first
    assert all("Read-only" in m for m in msgs) and after == before


def test_copy_as_new_draft_is_editable_and_leaves_the_original_alone(home):
    d = promoted_draft(home)
    from storywheel import tui
    async def go():
        app = tui.StorywheelApp(store.load(d["id"]), make_engine(home))
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            await pilot.press("C")
            await pilot.pause()
            s = app.main.session
            new_id = s.story["id"]
            await pilot.press("space")                    # now rolls are allowed
            await pilot.pause()
            return new_id, s.story.get("promoted"), s.story["copied_from"]
    new_id, promoted, source = asyncio.run(go())
    assert new_id != d["id"] and promoted is None and source == d["id"]
    original, copy = store.load(d["id"]), store.load(new_id)
    assert original["promoted"] and original["kept"] == copy["kept"] and copy["id"] == new_id and "promoted" not in copy


def test_plain_resume_of_a_promoted_draft_offers_a_copy(home, monkeypatch, capsys):
    d = promoted_draft(home)
    from storywheel import cli
    ran = []
    monkeypatch.setattr(cli, "ask", lambda prompt, prefill="": "y")
    monkeypatch.setattr(cli, "run", lambda story, plain=False: ran.append(story))
    class A: target = d["id"]; plain = True
    cli.cmd_resume(A)
    assert ran and not ran[0].get("promoted") and ran[0]["id"] != d["id"]
    assert "read-only" in capsys.readouterr().out
