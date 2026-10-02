"""
The Settings mode (F4): who you are, goals, the Writer's preferences, export defaults, universe boost, where the
library lives, and your writing statistics. It edits ~/.storywheel/settings.toml; every change is saved as you make it.
"""
import os

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Footer, Header, Input, Label, Select, Static, Switch, TabbedContent, TabPane, TextArea

from . import paths, settings, vault, writing_stats

MODE_KEYS = "F1 Wheel   F2 Builder   F3 Writer   F4 Settings"

# (tab title, [(key, label, kind, extra, hint)])   kinds: text, multiline, int, float, bool, choice, path
SECTIONS = [
    ("You", [
        ("legal_name", "Legal name", "text", None, "Printed top left of a manuscript's first page."),
        ("author_name", "Byline / pen name", "text", None, "The 'by ...' under the title (blank: your legal name)."),
        ("surname", "Surname for page headers", "text", None, "Blank: the last word of your name."),
        ("address", "Address", "multiline", None, "One line per line; printed on the first page."),
        ("email", "Email", "text", None, ""),
        ("phone", "Phone", "text", None, ""),
    ]),
    ("Goals", [
        ("daily_goal", "Daily word goal", "int", None, "Shown in the Writer's status line and the Builder's stats box. 0 turns it off."),
    ]),
    ("Writer", [
        ("notepad_mode", "Notepad mode", "bool", None, "On: type like in an ordinary editor (Escape does not change modes). Off: Vim behavior."),
        ("neovide", "Use Neovide", "bool", None, "A window with real fonts, if Neovide is installed (otherwise the terminal is used and you are told)."),
        ("writer_font", "Font in Neovide", "text", None, "Blank: Neovide's default monospace font."),
        ("writer_font_size", "Font size in Neovide", "int", None, "Points."),
        ("line_spacing", "Extra line spacing in Neovide", "int", None, "Pixels; about the font size looks double spaced."),
        ("paragraph_spacing", "Terminal: blank lines between paragraphs", "int", None, "The closest a terminal gets to double spacing (shown, not typed)."),
        ("column_width", "Column width", "int", None, "Characters."),
        ("indent_display", "Show a paragraph indent", "bool", None, ""),
        ("typewriter", "Typewriter mode", "bool", None, "Keep the current line in the middle of the screen."),
        ("invisibles", "Show invisibles", "bool", None, ""),
        ("spellcheck", "Spellcheck", "bool", None, ""),
    ]),
    ("Export", [
        ("font", "Manuscript font", "choice", ["Times New Roman", "Courier New"], "Shunn allows either."),
        ("format", "Default format", "choice", ["short-story", "novel", "screenplay"], "A story can choose its own."),
        ("export_format", "Quick export file type", "choice", ["docx", "odt", "pdf", "md", "txt"], ""),
    ]),
    ("Universes", [
        ("atom_boost", "How much likelier a universe's own people and places are", "float", None,
         "Your default for every universe (1.5 is a strong genre list's share); a universe can set its own."),
    ]),
    ("Library", [
        ("library", "Library folder", "path", None, "Where universes, stories and manuscripts live. Changing it does not move anything."),
    ]),
]

HELP = f"""\
[b]Settings[/b]        {MODE_KEYS}

  Everything is saved as you change it, to ~/.storywheel/settings.toml.
  [b]tab[/b] / [b]shift+tab[/b]  next / previous box        [b]left right[/b] on the tabs  switch tab
  [b]q[/b]  leave settings and go back to where you were    [b]F1 F2 F3[/b]  another mode
  The Stats tab shows words per day, your streaks, and per-story totals (what the Writer recorded).
"""


def parse(kind, text):
    """(ok, value) for what was typed into a box."""
    text = text.strip()
    if kind == "int":
        return (text.lstrip("-").isdigit() and int(text) >= 0), (int(text) if text.lstrip("-").isdigit() else None)
    if kind == "float":
        try:
            v = float(text)
            return v > 0, v
        except ValueError:
            return False, None
    return True, text


class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape,question_mark,q", "close", "Close")]
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    HelpScreen > Static { width: 90; height: auto; border: round $accent; background: $surface; padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Static(HELP)

    def action_close(self):
        self.dismiss(None)


class SettingsScreen(Screen):
    BINDINGS = [
        Binding("f1", "mode('wheel')", "Wheel", key_display="F1"),
        Binding("f2", "mode('builder')", "Builder", key_display="F2"),
        Binding("f3", "mode('writer')", "Writer", key_display="F3"),
        Binding("f4", "noop", "Settings", key_display="F4"),
        Binding("question_mark", "help", "Help", key_display="?"),
        Binding("q", "leave", "Back"),
    ]
    DEFAULT_CSS = """
    SettingsScreen VerticalScroll { padding: 1 2; }
    SettingsScreen .row { height: auto; margin-bottom: 1; }
    SettingsScreen .label { text-style: bold; }
    SettingsScreen .hint { color: $text-muted; }
    SettingsScreen Input, SettingsScreen Select { width: 70; }
    SettingsScreen TextArea { width: 70; height: 6; }
    SettingsScreen #status { height: 1; padding: 0 1; background: $boost; }
    SettingsScreen DataTable { height: 1fr; min-height: 8; }
    SettingsScreen #summary { padding: 0 1; height: auto; }
    SettingsScreen .title { background: $primary-darken-2; padding: 0 1; height: 1; }
    """

    def __init__(self, app_ref):
        super().__init__()
        self.b = app_ref
        self.values = {}

    # --- layout ---------------------------------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        g = settings.load_global()
        g["library"] = str(paths.library_root())
        self.values = g
        with TabbedContent(id="tabs"):
            for title, fields in SECTIONS:
                with TabPane(title, id=f"t-{title.lower()}"):
                    with VerticalScroll():
                        for key, label, kind, extra, hint in fields:
                            with Vertical(classes="row"):
                                yield Label(label, classes="label")
                                yield from self.control(key, kind, extra, g.get(key))
                                if hint:
                                    yield Static(hint, classes="hint", markup=False)
                        if title == "Library":
                            yield Static(f"App storage: {paths.home()}\nSettings file: {settings.global_path()}", markup=False)
            with TabPane("Stats", id="t-stats"):
                yield Static("", id="summary", markup=False)
                yield Static("Words per day (newest first)", classes="title")
                yield DataTable(id="days")
                yield Static("Per story", classes="title")
                yield DataTable(id="stories")
        yield Static("", id="status", markup=False)
        yield Footer()

    def control(self, key, kind, extra, value):
        wid = f"f-{key}"
        if kind == "bool":
            return [Switch(bool(value), id=wid)]
        if kind == "choice":
            options = [(o, o) for o in extra]
            if value and value not in extra:
                options.append((str(value), str(value)))
            return [Select(options, value=value if value else extra[0], allow_blank=False, id=wid)]
        if kind == "multiline":
            return [TextArea(str(value or ""), id=wid)]
        return [Input("" if value is None else str(value), id=wid)]

    def on_mount(self):
        self.app.title = "storywheel · Settings"
        self.app.sub_title = "saved as you go"
        self.refresh_stats()
        self.b.remember()

    def say(self, message):
        self.query_one("#status", Static).update(message)

    # --- saving ----------------------------------------------------------------------------------------------

    def kind_of(self, key):
        for _t, fields in SECTIONS:
            for k, _l, kind, _x, _h in fields:
                if k == key:
                    return kind
        return "text"

    def save(self, key, value):
        if key == "library":
            return self.save_library(value)
        g = settings.load_global()
        g[key] = value
        settings.save_global(g)
        self.say(f"Saved: {key} = {value!r}")

    def save_library(self, text):
        new = text.strip()
        if not new:
            return
        from pathlib import Path
        target = Path(new).expanduser()
        old = paths.library_root()
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.say(f"Can't use that folder: {e}")
            return
        g = settings.load_global()
        g["library"] = str(target)
        settings.save_global(g)
        if target != old:
            message = f"The library is now {target}. Nothing was moved: your universes are still in {old}."
        else:
            message = f"The library is {target}."
        if "STORYWHEEL_LIBRARY" in os.environ:
            message += "  (STORYWHEEL_LIBRARY is set in your environment and wins.)"
        self.say(message)

    def on_input_changed(self, event):
        key = (event.input.id or "")[2:]
        kind = self.kind_of(key)
        if kind == "path":
            return                                              # saved on Enter, not on every keystroke
        ok, value = parse(kind, event.value)
        if not ok:
            self.say({"int": "Needs a whole number (0 or more).", "float": "Needs a number above 0."}.get(kind, "?"))
            return
        if self.values.get(key) == value:
            return
        self.values[key] = value
        self.save(key, value)

    def on_input_submitted(self, event):
        key = (event.input.id or "")[2:]
        if self.kind_of(key) == "path":
            self.save_library(event.value)

    def on_switch_changed(self, event):
        key = (event.switch.id or "")[2:]
        if self.values.get(key) != event.value:
            self.values[key] = event.value
            self.save(key, bool(event.value))

    def on_select_changed(self, event):
        key = (event.select.id or "")[2:]
        if event.value is not Select.BLANK and self.values.get(key) != event.value:
            self.values[key] = event.value
            self.save(key, event.value)

    def on_text_area_changed(self, event):
        key = (event.text_area.id or "")[2:]
        if self.values.get(key) != event.text_area.text:
            self.values[key] = event.text_area.text
            self.save(key, event.text_area.text)

    def on_tabbed_content_tab_activated(self, event):
        if event.pane.id == "t-stats":
            self.refresh_stats()

    # --- the Stats tab ----------------------------------------------------------------------------------------

    def refresh_stats(self):
        per_day = writing_stats.days()
        cur, best = writing_stats.streak(per_day)
        today = per_day.get(writing_stats.datetime.date.today().isoformat(), 0)
        goal = int(settings.load_global().get("daily_goal") or 0)
        total = sum(per_day.values())
        rows = writing_stats.per_story()
        lines = [f"Today  {today:,}" + (f" / {goal:,} words   {writing_stats.bar(today, goal)}" if goal else " words"),
                 f"Streak  {cur} day{'s' if cur != 1 else ''}   (best {best})",
                 f"Days written  {sum(1 for w in per_day.values() if w > 0)}     Words recorded  {total:,}"
                 f"     Words in all manuscripts  {sum(r[2] for r in rows):,}"]
        self.query_one("#summary", Static).update("\n".join(lines))
        days = self.query_one("#days", DataTable)
        days.clear(columns=True)
        days.add_columns("Date", "Words", "")
        top = max(per_day.values(), default=0) or 1
        for date, words in writing_stats.history(90):
            days.add_row(date, f"{words:,}", "█" * max(1 if words else 0, int(30 * words / top)))
        stories = self.query_one("#stories", DataTable)
        stories.clear(columns=True)
        stories.add_columns("Universe", "Story", "Words", "Today")
        for uni, title, words, t in rows:
            stories.add_row(uni, title, f"{words:,}", f"{t:,}" if t else "")

    # --- actions ----------------------------------------------------------------------------------------------

    def action_noop(self):
        self.say("You are in Settings.")

    def action_help(self):
        self.app.push_screen(HelpScreen())

    def action_mode(self, which):
        self.b.go(which)

    def action_leave(self):
        self.b.go(self.b.back)


class SettingsApp(App):
    TITLE = "storywheel · Settings"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = []

    def __init__(self, state_store=None, back="builder"):
        super().__init__()
        self.state_store = state_store
        self.back = back
        self.next = None

    def on_mount(self):
        self.push_screen(SettingsScreen(self))

    def remember(self):
        if self.state_store is not None:
            try:
                self.state_store.update(mode="settings", back=self.back)
            except OSError:
                pass

    def go(self, where):
        self.next = (where, {})
        self.exit()


def run_settings(state_store=None, back="builder"):
    app = SettingsApp(state_store, back)
    app.run()
    return app.next
