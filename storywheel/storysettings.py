"""The Builder's story settings box (S): the settings a story can set for itself, with switches and choices like Settings (F4), and for each one
whether it is this story's own or follows your default. "Your default" stores nothing in the story's settings.toml."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from . import settings

DEFAULT = "__default__"
FONTS = ["Times New Roman", "Courier New"]
# (key, label, kind, choices)   kinds: choice, bool, int, text
FIELDS = [
    ("font", "Font", "choice", FONTS),
    ("column_width", "Column width (characters)", "int", None),
    ("daily_goal", "Daily word goal", "int", None),
    ("title_keyword", "Short title for page headers", "text", None),
    ("indent_display", "Show a paragraph indent", "bool", None),
    ("typewriter", "Typewriter mode", "bool", None),
    ("invisibles", "Show invisibles", "bool", None),
    ("spellcheck", "Spellcheck", "bool", None),
    ("spell_region", "English spelling", "choice", ["US", "UK"]),
]
ON, OFF = "on", "off"


def shown(value, kind):
    return (ON if value else OFF) if kind == "bool" else str(value)


class StorySettingsScreen(ModalScreen):
    """Dismisses with (set, clear): the values the story keeps for itself and the keys that go back to following your defaults."""
    BINDINGS = [Binding("escape", "cancel", "Cancel"), Binding("ctrl+s", "save", "Save", priority=True)]
    DEFAULT_CSS = """
    StorySettingsScreen { align: center middle; }
    StorySettingsScreen > Vertical { width: 90%; max-width: 110; height: auto; max-height: 90%; border: round $accent; background: $surface; padding: 1 2; }
    StorySettingsScreen .line { height: 1; margin-top: 1; }
    StorySettingsScreen .name { width: 32; }
    StorySettingsScreen .line Select, StorySettingsScreen .line Input { width: 34; }
    StorySettingsScreen .note { width: 1fr; padding-left: 2; color: $text-muted; }
    StorySettingsScreen #buttons { height: 1; margin-top: 1; }
    StorySettingsScreen #buttons Button { height: 1 !important; border: none !important; margin-right: 2; min-width: 10; }
    """

    def __init__(self, story):
        super().__init__()
        self.story = story
        self.own = settings.story_own(story.path)
        self.inherited = settings.story_inherited()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"Story settings: {self.story.title}")
            yield Static("Leave a box on “your default” to follow Settings (F4). The Writer reads these on its next start. "
                         "Format, structure and target length: m.", markup=False)
            with VerticalScroll():
                for key, label, kind, choices in FIELDS:
                    with Horizontal(classes="line"):
                        yield Label(label, classes="name")
                        yield from self.control(key, kind, choices)
                        yield Static("", id=f"note-{key}", classes="note", markup=False)
            with Horizontal(id="buttons"):
                yield Button("Save (ctrl+s)", id="save", variant="success")
                yield Button("Cancel (esc)", id="cancel")

    def default_text(self, key, kind):
        return f"your default ({shown(self.inherited.get(key, ''), kind)})" if kind != "text" else "no short title"

    def control(self, key, kind, choices):
        mine = key in self.own and (self.own[key] != "" or kind == "text")
        value = self.own.get(key)
        if kind in ("bool", "choice"):
            options = [(self.default_text(key, kind), DEFAULT)]
            options += [(ON, ON), (OFF, OFF)] if kind == "bool" else [(c, c) for c in choices]
            current = DEFAULT
            if mine:
                current = (ON if value else OFF) if kind == "bool" else str(value)
                if current not in [v for _t, v in options]:
                    options.append((current, current))
            return [Select(options, value=current, allow_blank=False, id=f"f-{key}", compact=True)]
        placeholder = self.default_text(key, kind)
        return [Input("" if not mine else str(value), placeholder=placeholder, id=f"f-{key}", compact=True,
                      type="integer" if kind == "int" else "text")]

    def on_mount(self):
        for key, _l, kind, _c in FIELDS:
            self.note(key, kind)
        self.query(Select).first().focus()

    def raw(self, key, kind):
        w = self.query_one(f"#f-{key}")
        v = w.value
        if kind in ("bool", "choice"):
            return None if v == DEFAULT else v
        v = (v or "").strip()
        return v or None

    def note(self, key, kind):
        v = self.raw(key, kind)
        self.query_one(f"#note-{key}", Static).update(
            f"follows your default: {shown(self.inherited.get(key, ''), kind)}" if v is None and kind != "text"
            else ("not set" if v is None else "this story's own"))

    def on_select_changed(self, event):
        key = (event.select.id or "")[2:]
        kind = next((k for n, _l, k, _c in FIELDS if n == key), None)
        if kind:
            self.note(key, kind)

    def on_input_changed(self, event):
        key = (event.input.id or "")[2:]
        kind = next((k for n, _l, k, _c in FIELDS if n == key), None)
        if kind:
            self.note(key, kind)

    def on_input_submitted(self, event):
        inputs = list(self.query("Select, Input"))
        i = inputs.index(event.input)
        if i + 1 < len(inputs):
            inputs[i + 1].focus()
        else:
            self.action_save()

    def action_save(self):
        out, clear = {}, []
        for key, _l, kind, _c in FIELDS:
            v = self.raw(key, kind)
            if v is None:
                if key in self.own:
                    clear.append(key)
            elif kind == "bool":
                out[key] = v == ON
            elif kind == "int":
                out[key] = int(v)
            else:
                out[key] = v
        self.dismiss((out, clear))

    def action_cancel(self):
        self.dismiss(None)

    def on_button_pressed(self, event):
        if event.button.id == "save":
            self.action_save()
        else:
            self.action_cancel()
