"""The help screen every mode opens (? or the key of the mode you are in): the mode's help page from storywheel/data/help in tabs (the mode's
guide, Keys, Topics: helpdoc.tabs), scrollable, with a search box that narrows every tab to the sections that match."""
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Static, Tab, Tabs

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
    """A help page in tabs (helpdoc.tabs): a mode's guide, Keys, Topics (the Writer has its own float). Tab / Shift+Tab, the number keys or a
    click switch tabs; / searches every tab of the page; it opens on the first tab (the mode you are in), or on the tab holding `section`."""
    BINDINGS = [Binding("escape", "escape", "Close"), Binding("question_mark,q", "close", "Close", show=False),
                Binding("slash", "search", "Search"),
                Binding("tab", "step_tab(1)", "Next tab", show=False, priority=True),
                Binding("shift+tab", "step_tab(-1)", "Previous tab", show=False, priority=True),
                *[Binding(str(n), f"show_tab({n - 1})", f"Tab {n}", show=False) for n in range(1, 10)],
                *[Binding(key, f"mode_key('{key}')", name, show=False) for key, _m, name in navigation.MODES]]
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    HelpScreen > Vertical { width: 104; max-width: 100%; height: 90%; border: round $accent; background: $surface; padding: 0 2; }
    HelpScreen #help-head { height: 1; color: $text-muted; }
    HelpScreen #help-tabs { height: 2; }
    HelpScreen #help-search { margin: 0; }
    HelpScreen #help-scroll { height: 1fr; }
    """
    HEAD = "Tab / Shift+Tab, 1-{n} or a click: tabs   ·   / searches every tab   ·   ↑ ↓ PgUp PgDn scroll   ·   Esc, q, ? or this mode's key closes"

    def __init__(self, name, section=None, fmt=None):
        super().__init__()
        self.name_, self.section = name, section
        self.tabs = helpdoc.tabs(name, fmt)
        self.current = 0
        if section:
            self.current = next((i for i, (_t, secs) in enumerate(self.tabs) if any(h == section for h, _b in secs)), 0)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.HEAD.format(n=len(self.tabs)), id="help-head", markup=False)
            yield Tabs(*[Tab(f"{i + 1} {title}", id=f"help-tab-{i}") for i, (title, _s) in enumerate(self.tabs)], id="help-tabs",
                       active=f"help-tab-{self.current}")
            yield Input(placeholder="search every tab of this page", id="help-search")
            with VerticalScroll(id="help-scroll"):
                yield Static("", id="help-text", markup=False)

    def on_mount(self):
        self.query_one("#help-tabs", Tabs).can_focus = False
        self.render_page("")
        self.query_one("#help-scroll").focus()
        if self.section:
            lines = helpdoc.tab_text(self.tabs[self.current][1])[0].splitlines()
            line = next((i for i in range(len(lines) - 1) if lines[i] == self.section and lines[i + 1].startswith("---")), 0)
            self.call_after_refresh(lambda: self.query_one("#help-scroll").scroll_to(y=line, animate=False))

    @property
    def title_now(self):
        return self.tabs[self.current][0]

    def render_page(self, query):
        if query.strip():
            parts, found = [], 0
            for title, secs in self.tabs:
                text, n = helpdoc.tab_text(secs, None, query)
                if n:
                    found += n
                    parts += [f"[{title}]", text]
            text = "\n".join(parts) if found else f"Nothing on this page matches “{query}”. Settings > Help searches every page.\n"
            head = f"{found} section{'s' if found != 1 else ''} match “{query}” (in every tab)"
        else:
            text = helpdoc.tab_text(self.tabs[self.current][1])[0]
            head = self.HEAD.format(n=len(self.tabs))
        self.query_one("#help-text", Static).update(Text(text))
        self.query_one("#help-head", Static).update(head)
        self.query_one("#help-scroll").scroll_home(animate=False)

    def on_tabs_tab_activated(self, event):
        if event.tabs.id != "help-tabs" or event.tab is None:
            return
        self.current = int(event.tab.id.rsplit("-", 1)[1])
        self.render_page(self.query_one("#help-search", Input).value)

    def action_show_tab(self, n):
        if 0 <= n < len(self.tabs):
            self.query_one("#help-tabs", Tabs).active = f"help-tab-{n}"

    def action_step_tab(self, step):
        self.action_show_tab((self.current + step) % len(self.tabs))

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
