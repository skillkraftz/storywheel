"""One Textual app for the four screens modes (Wheel, Builder, Settings, Words), each built once and kept, so F1/F2/F4/F5 are instant
and every mode keeps its place (selection, scroll, open tab). The Writer (Neovim) runs from this app too, with the screen cleared on the way
in and out instead of showing your shell.

Each mode's screen was written for a small "host" object that provides what the standalone apps provide (`go`, `remember`, `back`...). Here
the hosts are thin handles on the hub. Heavy modules (the Words screen and with it the dictionary and wordfreq, the Settings screen, the
grammar settings) are imported the first time their mode is opened, not at start-up.
"""
import os
import sys
from contextlib import contextmanager

from textual.app import App

from . import appearance, modes, paths, state as state_mod, store, vault

MODE_NAMES = ("wheel", "builder", "settings", "words")
ALT_SCREEN_OFF = "\x1b[?1049l"


@contextmanager
def quiet_suspend(app):
    """Like App.suspend(), but the terminal never shows your shell: the screen is cleared and kept (still the alternate screen) while the
    other program runs, and cleared again before this app paints. (Neovim switches the alternate screen itself.)"""
    driver = app._driver
    if driver is None:
        yield
        return
    real_write = driver.write

    def keep_alt_screen(data):
        real_write("\x1b[2J\x1b[H" if data == ALT_SCREEN_OFF else data)

    driver.write = keep_alt_screen
    try:
        with app.suspend():
            driver.write = real_write                       # (only the leave-alt-screen of suspending needed hiding)
            try:
                yield
            finally:
                try:                                          # Neovim left the alternate screen on exit: go back in and clear, before Textual paints
                    os.write(sys.__stdout__.fileno(), b"\x1b[?1049h\x1b[2J\x1b[H")
                except OSError:
                    pass
    finally:
        driver.write = real_write


class Handle:
    """What the Settings and Words screens use as `self.b`."""

    def __init__(self, hub, mode):
        self.hub, self.mode = hub, mode
        self.back = "builder"
        self.payload = {}

    @property
    def state_store(self):
        return self.hub.st

    def go(self, where, payload=None):
        self.hub.go(where, payload or {})

    def remember(self):
        try:
            self.hub.st.update(mode=self.mode, back=self.back)
        except OSError:
            pass


def _builder_handle_class():
    from . import builder

    class BuilderHandle(builder.BuilderHooks):
        """What the Builder screen uses as `self.b`, backed by the hub."""

        def __init__(self, hub):
            self.hub = hub
            self.engine_factory = None
            self.ratings = hub.ratings
            self.changed = False
            self.next = None

        @property
        def state_store(self):
            return self.hub.st

        def go(self, where, payload=None):
            self.hub.go(where, payload or {})

        def run_writer(self, screen, story, scene, note):
            self.hub.open_writer({"universe": story.universe.slug, "story": story.slug, "scene": scene, "note": note})

        def __getattr__(self, name):                          # push_screen, suspend, refresh, copy_to_clipboard...: the hub's
            return getattr(self.hub, name)

    return BuilderHandle


class Hub(App):
    TITLE = "storywheel"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = []

    def __init__(self, start=None, get_engine=None, get_ratings=None, state=None):
        super().__init__()
        appearance.apply(self)
        self.st = state or state_mod.State()
        self._get_engine, self._get_ratings = get_engine, get_ratings
        self._engine = None
        self.ratings = get_ratings() if get_ratings else None
        self.start_at = start or (self.st.get("mode") or "wheel", {})
        self.mode_name = None
        self.notice = ""
        self.start_message = self.start_note()               # one line at start when the Writer could be nicer (not in kitty)
        self.session = None
        self.exit_message = None
        self.screens_built = {}                                # mode -> screen, once built
        self._payload = {}
        self.timings = []                                      # (mode, milliseconds) for each switch: tools/measure_switch.py reads this
        self._handles = {}
        for name in MODE_NAMES:
            self.add_mode(name, self._factory(name))

    def start_note(self):
        from . import writer
        return writer.kitty_start_note() or ""

    def take_start_message(self):
        message, self.start_message = self.start_message, ""
        return message

    # --- things the screens ask the app for ------------------------------------------------------------------------------------------

    @property
    def engine(self):
        if self._engine is None:
            self._engine = self._get_engine() if self._get_engine else None
        return self._engine

    def remember(self, session):
        """The Wheel records where it is (state.json), so plain `storywheel` comes back here."""
        try:
            self.st.update(mode="wheel", draft=session.story["id"], step=session.i)
        except OSError:
            pass

    # --- building the screens, the first time ------------------------------------------------------------------------------------------

    def _factory(self, name):
        def make():
            screen = getattr(self, "_build_" + name)(self._payload.get(name, {}))
            self.screens_built[name] = screen
            return screen
        return make

    def _build_wheel(self, payload):
        from .tui import MainScreen
        from .session import Session
        story = self._wheel_story(payload)
        self.notice = self.notice or self._tidy_notice() or self.take_start_message()
        self.session = Session(story, self.engine, ratings=self.engine.ratings)
        self.st.update(mode="wheel", draft=story["id"])
        return MainScreen(self.session)

    def _tidy_notice(self):
        cleaned = store.cleanup_empty_drafts()
        return (f"Tidied up: {cleaned} draft{'s' if cleaned != 1 else ''} with nothing kept {'were' if cleaned != 1 else 'was'} "
                "moved to the .trash folder in your storywheel home.") if cleaned else ""

    def _wheel_story(self, payload):
        story = None
        if payload.get("new"):
            story = store.new_story()
        elif payload.get("story_id"):
            story = store.load(payload["story_id"])
        elif self.st.get("draft"):
            try:
                story = store.load(self.st.get("draft"))
            except (OSError, ValueError):
                story = None
        if story is None:
            story = store.new_story()
            new = True
        else:
            new = bool(payload.get("new"))
        if new and payload.get("universe"):
            story["universes"] = [payload["universe"]]
            story["home"] = payload["universe"]
        return story

    def _build_builder(self, payload):
        from . import builder
        handle = _builder_handle_class()(self)
        self._handles["builder"] = handle
        slug = payload.get("universe") or self.st.get("universe")
        story = payload.get("story") or self.st.get("story")
        screen = builder.BuilderScreen(handle, slug, story)
        screen.apply_start(self.st.get("tab"), self.st.get("rtab"), self.st.get("entity"))
        handle.screen_ref = screen
        return screen

    def _build_settings(self, payload):
        from . import settings_app
        handle = self._handles["settings"] = Handle(self, "settings")
        handle.back = payload.get("back") or "builder"
        return settings_app.SettingsScreen(handle)

    def _build_words(self, payload):
        from . import words_app
        handle = self._handles["words"] = Handle(self, "words")
        handle.back = payload.get("back") or "builder"
        handle.payload = payload
        if not payload.get("universe"):
            payload = dict(payload, universe=self.st.get("universe"), story=self.st.get("story"))
            handle.payload = payload
        return words_app.WordsScreen(handle, payload)

    # --- starting and moving --------------------------------------------------------------------------------------------------------------

    def on_mount(self):
        mode, payload = self.start_at
        if mode == "writer":
            self.mode_name = "builder"
            self.show("builder", {"universe": payload.get("universe"), "story": payload.get("story")})
            self.call_after_refresh(self.open_writer, payload)
        else:
            self.show(mode if mode in MODE_NAMES else "wheel", payload)
            if mode not in ("wheel", None) and mode in MODE_NAMES and self.start_message:
                self.call_after_refresh(self._say_start_message)

    def _say_start_message(self):
        try:
            self.say(self.take_start_message())
        except Exception:                                    # (the screen has no status line yet: the note is simply not shown)
            pass

    def say(self, message):
        screen = self.screen
        if hasattr(screen, "say") and message:
            screen.say(message)

    def go(self, where, payload=None, message=None, full=None):
        """Move to another mode ('wheel', 'builder', 'settings', 'words', 'writer'), 'back' along the trail, or 'quit'."""
        payload = dict(payload or {})
        came = self.mode_name
        if where == "back":
            where = modes.TRAIL.pop() if modes.TRAIL else (payload.get("fallback") or ("builder" if vault.list_universes() else "wheel"))
        elif where in MODE_NAMES or where == "writer":
            modes._arrive(came, where)
        if where not in MODE_NAMES and where != "writer":
            self.exit(self.exit_message)
            return
        if where in ("settings", "words") and "back" not in payload:
            payload["back"] = came                           # q in Settings or Words goes back to where F4 / F5 was pressed
        if where == "writer":
            self.open_writer(payload)
        else:
            self.show(where, payload, message)

    def show(self, name, payload, message=None):
        """Switch to a mode: build it the first time, otherwise tell the screen it is back (with anything it was handed)."""
        import time
        t = time.perf_counter()
        screen = self.screens_built.get(name)
        if screen is None:
            self._payload[name] = payload
        else:
            self._enter(name, screen, payload)
        self.mode_name = name
        if name not in ("wheel",):
            try:
                self.st.update(mode=name)
            except OSError:
                pass
        self.switch_mode(name)
        if message:
            first = message.strip().splitlines()[0] if message.strip() else ""
            self.call_after_refresh(lambda: self.say(first))
        self.timings.append((name, (time.perf_counter() - t) * 1000))

    def _enter(self, name, screen, payload):
        if name == "wheel":
            self._enter_wheel(screen, payload)
        elif name == "builder":
            screen.enter(payload)
        elif name == "settings":
            self._handles["settings"].back = payload.get("back") or self._handles["settings"].back
            screen.enter(payload)
        elif name == "words":
            handle = self._handles["words"]
            handle.back = payload.get("back") or handle.back
            payload = dict(payload)
            if not payload.get("universe"):
                payload["universe"] = self.st.get("universe")
                payload["story"] = payload.get("story") or self.st.get("story")
            handle.payload = payload
            screen.enter(payload)

    def _enter_wheel(self, screen, payload):
        """Back in the Wheel: the draft is as it was. A new draft (from the Builder) or a named one replaces it, the old one saved."""
        if payload.get("new") or payload.get("story_id"):
            screen.switch_story(self._wheel_story(payload))
        elif payload.get("universe"):
            pass                                              # (F1 from the Builder names a universe only to start a draft in it: not needed here)

    # --- the Writer -------------------------------------------------------------------------------------------------------------------------

    def open_writer(self, payload):
        """Run Neovim on a story, from any mode. The screen is cleared on the way in and out; where the Writer asks to go next decides what shows."""
        from . import writer
        u, story = modes._resolve_story(self.st, payload)
        came = self.mode_name or "builder"
        if not story:
            self.say("There is no story to write yet. Promote a Wheel story into a universe first (leave the Wheel with F2, then Send to Builder).")
            return
        problem = writer.check()
        if problem:
            self.say(problem)
            return
        story.manuscript_dir.mkdir(parents=True, exist_ok=True)
        note = payload.get("note") or writer.kitty_note(story)
        self.st.update(mode="writer", universe=u.slug, story=story.slug)
        self.mode_name = "writer"
        with quiet_suspend(self):
            where = writer.run(story, payload.get("scene"), payload.get("replace"))
        handover = getattr(writer.run, "handover", None)
        if where == "words":                                   # F5 in the Writer: the word under the cursor goes along
            self.go("words", {"universe": u.slug, "story": story.slug, "handover": handover, "back": "writer"})
            return
        if where in ("wheel", "settings", "quit"):
            self.go(where, {"universe": u.slug, "story": story.slug})
            return
        self.st.update(mode="builder")
        self.go("builder", {"universe": u.slug, "story": story.slug},
                message=f"Back from the Writer ({story.word_count()} words in {story.title})." + (f"  {note}" if note else ""))


def run(start=None, get_engine=None, get_ratings=None):
    """Run the hub until the writer quits. Prints what the Wheel says on quitting (the story as plain text), like the standalone Wheel did."""
    app = Hub(start, get_engine, get_ratings)
    message = app.run()
    if message:
        print("\n  " + str(message).replace("\n", "\n  "))
