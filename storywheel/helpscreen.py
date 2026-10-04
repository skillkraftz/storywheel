"""The help screen every mode opens (? or the key of the mode you are in): the mode's help page from storywheel/data/help, scrollable, with a
search box that narrows the page to the sections that match."""
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from . import helpdoc, navigation


def page_text(name, query=""):
    """(text, matches): the page as plain text; with a query only the sections that contain every word of it (and how many)."""
    doc = helpdoc.load(name)
    words = [w for w in query.lower().split() if w]
    parts = [doc.title, "=" * len(doc.title), ""]
    found = 0
    for heading, body in helpdoc.sections(name):
        if words and not all(w in f"{heading} {body}".lower() for w in words):
            continue
        found += 1
        parts += [heading, "-" * len(heading), body, ""]
    if words and not found:
        parts += [f"Nothing on this page matches “{query}”. Settings > Help searches every page."]
    return "\n".join(parts).rstrip() + "\n", found


def line_of(name, heading):
    """The line where a section starts in page_text(name)."""
    lines = page_text(name)[0].splitlines()
    for i in range(len(lines) - 1):
        if lines[i] == heading and lines[i + 1].startswith("---"):
            return i
    return 0


class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape", "escape", "Close"), Binding("question_mark,q", "close", "Close", show=False),
                Binding("slash", "search", "Search"),
                *[Binding(key, f"mode_key('{key}')", name, show=False) for key, _m, name in navigation.MODES]]
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    HelpScreen > Vertical { width: 104; max-width: 100%; height: 90%; border: round $accent; background: $surface; padding: 0 2; }
    HelpScreen #help-head { height: 1; color: $text-muted; }
    HelpScreen #help-search { margin: 0; }
    HelpScreen #help-scroll { height: 1fr; }
    """

    def __init__(self, name, section=None):
        super().__init__()
        self.name_, self.section = name, section

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Search with /   ·   ↑ ↓ PgUp PgDn scroll   ·   Esc, q, ? or this mode's key closes", id="help-head", markup=False)
            yield Input(placeholder="search this page", id="help-search")
            with VerticalScroll(id="help-scroll"):
                yield Static("", id="help-text", markup=False)

    def on_mount(self):
        self.render_page("")
        self.query_one("#help-scroll").focus()
        if self.section:
            line = line_of(self.name_, self.section)
            self.call_after_refresh(lambda: self.query_one("#help-scroll").scroll_to(y=line, animate=False))

    def render_page(self, query):
        text, found = page_text(self.name_, query)
        self.query_one("#help-text", Static).update(Text(text))
        self.query_one("#help-head", Static).update(
            f"{found} section{'s' if found != 1 else ''} match “{query}”" if query.strip() else
            "Search with /   ·   ↑ ↓ PgUp PgDn scroll   ·   Esc, q, ? or this mode's key closes")
        self.query_one("#help-scroll").scroll_home(animate=False)

    def on_input_changed(self, event):
        self.render_page(event.value)

    def on_input_submitted(self, event):
        self.query_one("#help-scroll").focus()

    def action_search(self):
        self.query_one("#help-search", Input).focus()

    def action_escape(self):
        box = self.query_one("#help-search", Input)
        if box.value or box.has_focus:
            box.value = ""
            self.query_one("#help-scroll").focus()
        else:
            self.dismiss(None)

    def action_close(self):
        self.dismiss(None)

    def action_mode_key(self, key):
        """The key of the mode this help is about closes it (a toggle); the key of another mode closes it and goes there."""
        parent = self.app.screen_stack[-2] if len(self.app.screen_stack) > 1 else None
        mine = next((k for k, m, _n in navigation.MODES if m == self.name_), None)
        self.dismiss(None)
        if key == mine or parent is None:
            return
        action = next((b.action for b in type(parent).BINDINGS if hasattr(b, "key") and key in b.key.split(",")), None)
        if action:
            self.app.call_later(parent.run_action, action)
