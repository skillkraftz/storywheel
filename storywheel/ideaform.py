"""The +Idea form: a title and a few lines, and a format picked from a list (flash fiction by default, or a short story).

    IdeaFormScreen(heading)    returns {"title", "text", "format"}, or None when cancelled

The lines become the story's logline (the first) and its notes (all of them). Nothing else is asked: an idea has no structure."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static, TextArea

from . import formats, ideas


class IdeaFormScreen(ModalScreen):
    BINDINGS = [Binding("escape", "cancel", "Cancel"), Binding("ctrl+s", "save", "Save", show=False)]
    DEFAULT_CSS = """
    IdeaFormScreen { align: center middle; }
    IdeaFormScreen > Vertical { width: 84; height: auto; max-height: 90%; border: round $accent; background: $surface; padding: 1 2; }
    IdeaFormScreen Label { margin-top: 1; color: $text-muted; }
    IdeaFormScreen TextArea { height: 7; }
    IdeaFormScreen RadioSet { height: auto; border: none; background: $surface; }
    IdeaFormScreen #error { color: $error; height: auto; }
    IdeaFormScreen Horizontal { height: 1; margin-top: 1; }
    IdeaFormScreen #dlg Button { height: 1 !important; border: none !important; min-width: 10; margin-right: 2; }
    """

    def __init__(self, heading="A new idea"):
        super().__init__()
        self.heading = heading

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(self.heading, markup=False)
            yield Label("Title")
            yield Input("", id="title", placeholder="the idea's title")
            yield Label("A few lines (the first is its logline; all of them are kept as its notes)")
            yield TextArea("", id="lines")
            yield Label("Format")
            with RadioSet(id="format"):
                for key in ideas.IDEA_FORMATS:
                    yield RadioButton(formats.get(key).label, value=key == "flash", id="fmt-" + key)
            yield Static("", id="error", markup=False)
            with Horizontal():
                yield Button("Add", id="save", variant="success")
                yield Button("Cancel", id="cancel")
            yield Static("tab: next box     ctrl+s: add     esc: cancel     (w writes it at once)", markup=False)

    def on_mount(self):
        for b in self.query(Button):
            b.can_focus = True
        self.query_one("#title", Input).focus()

    def chosen_format(self):
        for key in ideas.IDEA_FORMATS:
            if self.query_one("#fmt-" + key, RadioButton).value:
                return key
        return "flash"

    def values(self):
        return {"title": self.query_one("#title", Input).value.strip(), "text": self.query_one("#lines", TextArea).text.strip(),
                "format": self.chosen_format()}

    def action_save(self):
        v = self.values()
        if not v["title"]:
            self.query_one("#error", Static).update("A title, please.")
            return
        self.dismiss(v)

    def action_cancel(self):
        self.dismiss(None)

    def on_input_submitted(self, event):
        self.query_one("#lines", TextArea).focus()

    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == "save":
            self.action_save()
        else:
            self.action_cancel()
