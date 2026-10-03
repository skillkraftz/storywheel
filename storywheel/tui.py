"""
The full-screen app (Textual). It drives a Session (session.py), the same engine room the
plain prompt uses, so the keys do exactly what they do there.

    steps (left)        which are kept, skipped, current; Enter or a click jumps to one
    universe (left)     what you have saved, by kind; Enter previews, v focuses it
    card (middle)       the current candidate; up/down select a field
    buttons             Roll, Keep, Back, Skip, Flavor
    history (below)     every roll and what changed; with h, the selected field's own history
    footer              the keys

Tab moves between the lists. Space rolls; k keeps; f (or Enter) rerolls the selected field;
e edits it; E opens $EDITOR; w writes your own; + and - rate; u / U universe; m flavor (what this story leans toward);
h history; b back a step; x skip; q back to the previous mode; Q quit storywheel; ? help.

The mouse works on the card too: click a field to reroll it, right-click to edit it, scroll
over it to step through its earlier values, click its ▲ or ▼ to rate it.
"""
import re

from rich.style import Style
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen, Screen
from . import appearance, navigation, tools
from .footer import FitFooter
from .header import QuietHeader
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, OptionList, Static, Tree
from textual.widgets.option_list import Option

from . import clipboard, store, structures, universe_atoms
from . import threads as T
from .session import Session
from .steps import public, steps_for

BOOST_LADDER = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]
MARKS = {"kept": ("✓", "green"), "skipped": ("–", "yellow"), "current": ("▶", "bold cyan"), "pending": ("·", "dim"),
         "changed": ("●", "bold yellow"), "broken": ("✗", "bold red")}

HELP = """\
[b]Keys[/b]

  [b]space[/b]   roll again
  [b]k[/b]       keep this and move on
  [b]f[/b]       reroll the selected field (so does enter)
  [b]e[/b]       edit the selected field
  [b]E[/b]       edit it all in $EDITOR
  [b]w[/b]       write your own
  [b]+[/b] [b]-[/b]     like / dislike the selected line. Disliked frames
          and atom pairs come up a little less. Again clears it.
  [b]u[/b] [b]U[/b]     save to / remove from your universe
  [b]h[/b]       history: every roll  or  the selected field's values
  [b]B[/b]       send this story to the Universe Builder (the button under the card; F2 offers it too)
  [b]F1[/b] [b]F2[/b] [b]F3[/b] [b]F4[/b]   Wheel (this), Universe Builder, Writer, Settings
  [b]v[/b]       the universe panel (see below)
  [b]c[/b]       copy the story so far to the clipboard (plain text)
  [b]i[/b]       ignore a stale warning
  [b]a[/b]       update a stale candidate (see below)
  [b]m[/b]       flavor: which kinds of material this story leans toward or avoids (the mix editor)
  [b]b[/b]       go back a step
  [b]x[/b]       skip this step
  [b]q[/b]       back to the mode you came from (the draft is saved)
  [b]Q[/b]       Quit storywheel: asks to keep this story or delete it (and offers to send it to the Builder)
  [b]F1-F5[/b]   the modes: Wheel, Builder, Writer, Settings, Words (the footer says so)
  [b]?[/b]       this help

[b]Moving around[/b]

  [b]up down[/b]  move within a list
  [b]tab[/b]      next list: steps, card, history
  [b]enter[/b]    card: reroll the field.  history: pick that one.
          steps: jump there.  universe: preview an entry.
  [b]esc[/b]      back to the card

[b]Stand-ins and stale candidates[/b]

  If you roll a step before the ones it builds on are kept (say the story body before the
  protagonist), it invents [b]stand-ins[/b] and the card says so. When you later keep those
  steps, a candidate built on a stand-in shows a banner, "Built for Mark; your protagonist is
  now Stacie Anderson", with [b]Update[/b] (swap the kept values into a copy), [b]Reroll[/b] and
  [b]Ignore[/b] (dismiss the banner; the candidate stays as it is). Stale rows in the history are marked. Rerolling one field always uses
  what you have kept.

[b]Mouse[/b]

  [b]click[/b] a field       reroll just that field (like f)
  [b]right-click[/b] a field edit it (like e)
  [b]scroll[/b] over a field step through its earlier values
  [b]▲ ▼[/b] at the end of a line rate it (like + and -)
  buttons under the card: Roll, Keep, Back, Skip, Flavor
  click a step to jump to it, a history row to pick it

  To select text with the mouse while this app has it,
  hold [b]Shift[/b] and drag (some terminals: Alt, or Option on a Mac).

[b]Markers on the steps[/b]

  ✓ kept   – skipped   ▶ current   · to do
  [b]yellow ●[/b]  kept, but built on a stand-in or on something that changed
  [b]red ✗[/b]     refers to something that no longer exists
  The right-hand column says what is wrong. Click the step to go there.

[b]Past stories[/b] (bottom left): enter opens one, d deletes it (asks first),
  p / s send its protagonist / setting to your universe.

[b]Universe panel[/b] (bottom left; press v)

  Entries are grouped by kind; enter opens or closes a group.
  [b]enter[/b]  preview an entry: then enter or u uses it in this story
          (as a new candidate; nothing is kept until you press k),
          e edits it, d deletes it (with a confirm)
  [b]n[/b]      add a new entry from scratch    [b]t[/b]  whole characters/places from these universes: no / sometimes / only, for this story

Press esc to close.
"""


def _row(label, value, rating=0):
    """One line of the card. It ends in clickable ▲ ▼ (the click is recognised by the meta on them)."""
    text = Text()
    if label:
        text.append(label, style="bold cyan")
        text.append("  ")
    text.append(value)
    text.append(" ")
    text.append(" ▲ ", style=Style(color="green" if rating > 0 else "grey50", bold=rating > 0, meta={"rate": 1}))
    text.append(" ▼ ", style=Style(color="red" if rating < 0 else "grey50", bold=rating < 0, meta={"rate": -1}))
    return text


class CardList(OptionList):
    """The card's lines. A click is not 'select': left-click rerolls the field, right-click edits it,
    the wheel steps through its earlier values, and the ▲ ▼ rate it. (Enter still selects.)"""

    class Field(Message):
        def __init__(self, index, button, source=None):
            super().__init__()
            self.index, self.button, self.source = index, button, source

    class Rate(Message):
        def __init__(self, index, value, source=None):
            super().__init__()
            self.index, self.value, self.source = index, value, source

    class Scrolled(Message):
        def __init__(self, index, direction, source=None):
            super().__init__()
            self.index, self.direction, self.source = index, direction, source

    def on_click(self, event):
        event.stop()
        event.prevent_default()                       # not the base class's "click means select"
        meta = event.style.meta
        index = meta.get("option")
        if index is None:
            return
        self.highlighted = index
        if meta.get("rate"):
            self.post_message(self.Rate(index, meta["rate"], self))
        else:
            self.post_message(self.Field(index, event.button, self))

    history_wheel = True              # the wheel steps through a field's values; off, it just scrolls the list

    def _wheel(self, event, direction):
        if not self.history_wheel:
            return
        event.stop()
        event.prevent_default()
        index = event.style.meta.get("option")
        if index is None:
            index = self.highlighted
        if index is not None:
            self.highlighted = index
            self.post_message(self.Scrolled(index, direction, self))

    def on_mouse_scroll_up(self, event):
        self._wheel(event, -1)                        # up: older values

    def on_mouse_scroll_down(self, event):
        self._wheel(event, 1)


# --- dialogs ----------------------------------------------------------------------------------------

class EditScreen(ModalScreen):
    """Edit one or more fields, each in its own box, starting from what is there now."""
    BINDINGS = [Binding("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    EditScreen { align: center middle; }
    EditScreen > Vertical { width: 80%; max-width: 100; height: auto; max-height: 90%;
                            border: round $accent; background: $surface; padding: 1 2; }
    EditScreen Label { margin-top: 1; color: $text-muted; }
    """

    def __init__(self, title, fields):
        super().__init__()
        self.title_text, self.fields = title, fields
        # widget ids may not hold spaces or brackets, so name the boxes from the field names, made safe
        self.ids = {name: "in-" + re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-") for name in fields}

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.title_text)
            with VerticalScroll():
                for name, value in self.fields.items():
                    yield Label(name.replace("_", " "))
                    yield Input(value, id=self.ids[name])
            yield Label("enter: next / done     esc: cancel")

    def on_mount(self):
        self.query(Input).first().focus()

    def on_input_submitted(self, event):
        inputs = list(self.query(Input))
        i = inputs.index(event.input)
        if i + 1 < len(inputs):
            inputs[i + 1].focus()
        else:
            self.dismiss({name: self.query_one("#" + self.ids[name], Input).value for name in self.fields})

    def action_cancel(self):
        self.dismiss(None)


class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape,question_mark,q", "close", "Close")]
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    HelpScreen > VerticalScroll { width: 78; max-width: 100%; height: auto; max-height: 100%;
                                  border: round $accent; background: $surface; padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(HELP)

    def action_close(self):
        self.dismiss(None)


class DoneScreen(ModalScreen):
    BINDINGS = [Binding("Q,enter", "quit_app", "Quit storywheel"), Binding("q,escape", "keep_going", "Back: keep editing")]
    DEFAULT_CSS = """
    DoneScreen { align: center middle; }
    DoneScreen > Static { width: 70; height: auto; border: round $success; background: $surface; padding: 1 2; }
    """

    def __init__(self, title, path):
        super().__init__()
        self.title_text, self.path = title, path

    def compose(self) -> ComposeResult:
        where = f"\n\nMarkdown: {self.path}" if self.path else ""
        yield Static(f"[b]Done: {self.title_text}[/b]{where}\n\n  [b]Q[/b] / enter   quit storywheel\n  [b]q[/b] / esc     back: keep editing")

    def action_quit_app(self):
        self.dismiss("quit")

    def action_keep_going(self):
        self.dismiss("stay")


class ConfirmScreen(ModalScreen):
    BINDINGS = [Binding("y", "answer(True)", "Yes"), Binding("n,escape", "answer(False)", "No")]
    DEFAULT_CSS = """
    ConfirmScreen { align: center middle; }
    ConfirmScreen > Vertical { width: 60; height: auto; border: round $error; background: $surface; padding: 1 2; }
    ConfirmScreen Horizontal { height: 1; margin-top: 1; }
    ConfirmScreen #dlg Button { height: 1 !important; border: none !important; margin-right: 2; min-width: 8; }
    """

    def __init__(self, question):
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(self.question, markup=False)
            with Horizontal():
                yield _quiet(Button("Yes (y)", id="yes", variant="error"))
                yield _quiet(Button("No (n)", id="no"))

    def on_button_pressed(self, event):
        self.dismiss(event.button.id == "yes")

    def action_answer(self, yes):
        self.dismiss(yes)


class UniverseEntryScreen(ModalScreen):
    """A look at one entity of a universe, and the one thing to do with it here: use it in this story."""
    BINDINGS = [Binding("enter,u", "choose('use')", "Use in this story"), Binding("escape,q", "choose(None)", "Close")]
    DEFAULT_CSS = """
    UniverseEntryScreen { align: center middle; }
    UniverseEntryScreen > Vertical { width: 80%; max-width: 90; height: auto; max-height: 90%;
                                     border: round $accent; background: $surface; padding: 1 2; }
    UniverseEntryScreen Horizontal { height: 1; margin-top: 1; }
    UniverseEntryScreen #dlg Button { height: 1 !important; border: none !important; margin-right: 1; min-width: 8; }
    UniverseEntryScreen .keys { color: $text-muted; }
    """

    def __init__(self, label, fields, source=""):
        super().__init__()
        self.label, self.fields, self.source = label, fields, source

    def compose(self) -> ComposeResult:
        text = Text()
        text.append(f"{self.label}" + (f", from the universe {self.source}" if self.source else "") + "\n\n", style="bold")
        for k, v in self.fields.items():
            text.append(k.replace("_", " ") + "  ", style="bold cyan")
            text.append(f"{v}\n")
        with Vertical(id="dlg"):
            yield Static(text)
            with Horizontal():
                yield _quiet(Button("Use in this story", id="use", variant="primary"))
                yield _quiet(Button("Close", id="close"))
            yield Static("enter: use as a new candidate   esc: close", classes="keys")

    def on_button_pressed(self, event):
        self.dismiss(None if event.button.id == "close" else event.button.id)

    def action_choose(self, what):
        self.dismiss(what)


def _quiet(button):
    """A button for the mouse only: it never takes the keyboard focus (keys do the same things)."""
    button.can_focus = False
    return button


PROMOTE_MESSAGE = ("This story is about to be brought into the Universe Builder, where it grows into a "
                   "world of characters, places and things, and into a manuscript.\n\n"
                   "Bring it into a new universe, into an existing one, or not now (it stays a draft; "
                   "you can promote it later from Past stories).")


class QuitScreen(ModalScreen):
    """On the way out: keep this story or delete it. A story with something kept is also offered
    promotion into a universe."""
    BINDINGS = [Binding("k,enter", "choose('keep')", "Not now / keep"), Binding("d", "choose('delete')", "Delete"),
                Binding("n", "choose('new')", "New universe"), Binding("e", "choose('existing')", "Existing universe"),
                Binding("escape,c", "choose(None)", "Cancel")]
    DEFAULT_CSS = """
    QuitScreen { align: center middle; }
    QuitScreen > Vertical { width: 64; height: auto; border: round $accent; background: $surface; padding: 1 2; }
    QuitScreen Horizontal { height: 1; margin-top: 1; }
    QuitScreen #dlg Button { height: 1 !important; border: none !important; margin-right: 2; min-width: 8; }
    """

    def __init__(self, title, promotable=False):
        super().__init__()
        self.title_text, self.promotable = title, promotable

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            if self.promotable:
                yield Static(f"Bringing this story into the Universe Builder\n\n{self.title_text}\n\n"
                             f"{PROMOTE_MESSAGE}", markup=False)
                with Horizontal():
                    yield _quiet(Button("New universe (n)", id="new", variant="success"))
                    yield _quiet(Button("Existing universe (e)", id="existing", variant="primary"))
                    yield _quiet(Button("Not now (k)", id="keep"))
                with Horizontal():
                    yield _quiet(Button("Delete the draft (d)", id="delete", variant="error"))
                    yield _quiet(Button("Cancel (esc)", id="cancel"))
            else:
                yield Static(f"Keep this story or delete it?\n\n{self.title_text}", markup=False)
                with Horizontal():
                    yield _quiet(Button("Keep (k)", id="keep", variant="success"))
                    yield _quiet(Button("Delete (d)", id="delete", variant="error"))
                    yield _quiet(Button("Cancel (esc)", id="cancel"))

    def on_button_pressed(self, event):
        self.dismiss(None if event.button.id == "cancel" else event.button.id)

    def action_choose(self, what):
        if what in ("new", "existing") and not self.promotable:
            return
        self.dismiss(what)


class PickUniverseScreen(ModalScreen):
    """Choose an existing universe."""
    BINDINGS = [Binding("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    PickUniverseScreen { align: center middle; }
    PickUniverseScreen > Vertical { width: 60; height: auto; max-height: 80%; border: round $accent;
                                    background: $surface; padding: 1 2; }
    PickUniverseScreen OptionList { height: auto; max-height: 20; }
    """

    def __init__(self, universes):
        super().__init__()
        self.universes = universes

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Bring it into which universe?  (enter picks, esc cancels)", markup=False)
            yield OptionList(*[Option(f"{u.name}   ({len(u.entities())} entities)", id=u.slug) for u in self.universes])

    def on_mount(self):
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event):
        self.dismiss(event.option.id)

    def action_cancel(self):
        self.dismiss(None)


class PromotePreviewScreen(ModalScreen):
    """What promotion will create, before it does. Enter (or a click) on a duplicate switches between
    merging into the existing entity and creating another."""
    BINDINGS = [Binding("p", "go", "Promote"), Binding("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    PromotePreviewScreen { align: center middle; }
    PromotePreviewScreen > Vertical { width: 90%; max-width: 110; height: auto; max-height: 90%; border: round $accent;
                                      background: $surface; padding: 1 2; }
    PromotePreviewScreen OptionList { height: auto; max-height: 24; }
    PromotePreviewScreen Horizontal { height: 1; margin-top: 1; }
    PromotePreviewScreen #dlg Button { height: 1 !important; border: none !important; margin-right: 2; min-width: 8; }
    """

    def __init__(self, plan):
        super().__init__()
        self.plan = plan

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static("Here is what will be created. Nothing is written until you press Promote.", markup=False)
            yield OptionList(id="plan")
            yield Static("", id="plan-note", markup=False)
            with Horizontal():
                yield _quiet(Button("Promote (p)", id="go", variant="success"))
                yield _quiet(Button("Cancel (esc)", id="cancel"))

    def on_mount(self):
        self.rebuild()
        self.query_one("#plan", OptionList).focus()

    def rebuild(self):
        lst = self.query_one("#plan", OptionList)
        keep = lst.highlighted
        lst.clear_options()
        rows = []
        if self.plan.new_universe_name:
            rows.append(Option(Text(f"New universe '{self.plan.new_universe_name}'"
                                    + (f", leaning {' / '.join(self.plan.genres)}" if self.plan.genres else ""),
                                    style="bold"), disabled=True))
        rows.append(Option(Text(f"Story '{self.plan.story_title}': outline, settings, empty manuscript", style="bold"),
                           disabled=True))
        for n, item in enumerate(self.plan.items):
            style = "yellow" if item.existing else ""
            rows.append(Option(Text(("  ↔ " if item.existing else "  + ") + item.line(), style=style), id=str(n)))
        lst.add_options(rows)
        if keep is not None:
            lst.highlighted = min(keep, len(rows) - 1)
        note = "Yellow rows are same-name duplicates: enter switches merge / create another." if self.plan.duplicates() else ""
        self.query_one("#plan-note", Static).update(note)

    def on_option_list_option_selected(self, event):
        item = self.plan.items[int(event.option.id)]
        if item.existing:
            item.merge = not item.merge
            self.rebuild()

    def on_button_pressed(self, event):
        self.dismiss(event.button.id == "go")

    def action_go(self):
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)


class ChoiceScreen(ModalScreen):
    """Pick one of some options (or several): returns the value, a list for multi, or None if cancelled."""
    BINDINGS = [Binding("escape", "cancel", "Cancel"), Binding("space", "toggle", "Toggle", show=False),
                Binding("d", "done", "Done", show=False)]
    DEFAULT_CSS = """
    ChoiceScreen { align: center middle; }
    ChoiceScreen > Vertical { width: 64; height: auto; max-height: 80%; border: round $accent;
                              background: $surface; padding: 1 2; }
    ChoiceScreen OptionList { height: auto; max-height: 22; }
    ChoiceScreen Horizontal { height: 1; margin-top: 1; }
    ChoiceScreen #dlg Button { height: 1 !important; border: none !important; min-width: 8; margin-right: 2; }
    """

    def __init__(self, title, options, multi=False, selected=()):
        super().__init__()
        self.title_text, self.options, self.multi = title, list(options), multi
        self.selected = list(selected)

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(self.title_text, markup=False)
            yield OptionList(id="choices")
            if self.multi:
                yield Static("space or click toggles; d (or Done) finishes", markup=False)
                with Horizontal():
                    yield _quiet(Button("Done (d)", id="done", variant="success"))

    def on_mount(self):
        self.refill()
        self.query_one("#choices", OptionList).focus()

    def refill(self):
        lst = self.query_one("#choices", OptionList)
        keep = lst.highlighted
        lst.clear_options()
        rows = []
        for n, (label, value) in enumerate(self.options):
            mark = ("[x] " if value in self.selected else "[ ] ") if self.multi else ""
            rows.append(Option(Text(mark + label), id=str(n)))
        lst.add_options(rows)
        lst.highlighted = min(keep, len(rows) - 1) if keep is not None else 0

    def on_option_list_option_selected(self, event):
        value = self.options[int(event.option.id)][1]
        if not self.multi:
            self.dismiss(value)
        else:
            self.selected = [v for v in self.selected if v != value] if value in self.selected else self.selected + [value]
            self.refill()

    def action_toggle(self):
        lst = self.query_one("#choices", OptionList)
        if self.multi and lst.highlighted is not None:
            value = self.options[lst.highlighted][1]
            self.selected = [v for v in self.selected if v != value] if value in self.selected else self.selected + [value]
            self.refill()

    def action_done(self):
        if self.multi:
            self.dismiss(self.selected)

    def on_button_pressed(self, event):
        self.dismiss(self.selected)

    def action_cancel(self):
        self.dismiss(None)


class StoryList(OptionList):
    """Past stories: Enter opens one; d deletes (asks first); p / s send its protagonist / setting
    to your universe."""
    BINDINGS = [Binding("d", "act('delete')", "Delete"), Binding("p", "act('protagonist')", "+Protagonist"),
                Binding("s", "act('setting')", "+Setting"), Binding("P", "act('promote')", "Promote")]

    def action_act(self, what):
        self.screen.story_act(what)


class UniverseTree(Tree):
    """Entities of the selected universes, by kind. Enter on a kind opens or closes it; on an entity, previews it."""
    BINDINGS = [Binding("t", "mode", "No/mix/only"), Binding("u", "use", "Use in this story")]

    def action_mode(self):
        self.screen.universe_mode()

    def action_use(self):
        self.screen.universe_act("use")


class UniverseChecklist(OptionList):
    """Universes the generator may draw from for this draft: Enter, space or a click ticks one."""
    BINDINGS = [Binding("space", "toggle", "Tick"), Binding("t", "mode", "No/mix/only")]

    def action_toggle(self):
        self.action_select()

    def action_mode(self):
        self.screen.universe_mode()


# --- the mix editor ----------------------------------------------------------------------------------

class MixScreen(Screen):
    """This story's mix: which tags and lists it favors. It edits only this story."""
    BINDINGS = [
        Binding("escape,q", "close", "Back"),
        Binding("e,space", "toggle", "Exclude"),
        Binding("plus,equals_sign", "boost(1)", "Boost", key_display="+/-"),
        Binding("minus", "boost(-1)", "Less", show=False),
        Binding("0", "boost_reset", "Unboost"),
        Binding("tab,l", "switch", "Tags/Lists"),
        Binding("r", "reset", "Reset to genre defaults"),
    ]
    DEFAULT_CSS = """
    MixScreen #warn { background: $warning-darken-2; color: $text; padding: 0 1; height: auto; }
    MixScreen #sub { padding: 0 1; color: $text-muted; height: auto; }
    MixScreen DataTable { height: 1fr; }
    MixScreen #msg { padding: 0 1; height: 1; color: $accent; }
    """

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.view = "tags"

    def compose(self) -> ComposeResult:
        yield QuietHeader()
        yield Static("FLAVOR: THIS STORY ONLY. Changes here never touch the genre profiles, and only "
                     "affect future rolls (nothing you have kept changes).", id="warn", markup=False)
        yield Static("", id="sub", markup=False)
        yield DataTable(id="mix", cursor_type="row", zebra_stripes=True)
        yield Static("", id="msg", markup=False)
        yield FitFooter()

    def on_mount(self):
        self.app.sub_title = "Flavor of this story (the mix; this story only)"
        self.rebuild()
        self.query_one("#mix", DataTable).focus()

    # --- showing the mix ---------------------------------------------------------------------------

    def mix(self):
        return self.session.mix()

    def tag_rows(self):
        mix = self.mix()
        base, now = mix.blended(), mix.weights()
        tags = sorted(set(self.session.engine.library.all_tags()) | set(mix.data["boost"]) | set(mix.data["exclude_tags"]),
                      key=lambda t: (-base.get(t, 0.0), t))
        rows = []
        for t in tags:
            excluded = mix.is_tag_excluded(t)
            boost = mix.data["boost"].get(t, 1.0)
            weight = 0.0 if excluded else now.get(t, 0.0)
            rows.append((t, ("✗" if excluded else ""), t, f"{base.get(t, 0.0):g}",
                         f"×{boost:g}" if boost != 1.0 else "", "excluded" if excluded else f"{weight:g}",
                         "█" * min(24, round(weight * 4))))
        return rows

    def list_rows(self):
        mix = self.mix()
        weights = mix.weights()
        rows = []
        for wl in sorted(self.session.engine.library.lists.values(), key=lambda w: (w.slot, w.id)):
            excluded = mix.is_list_excluded(wl)
            weight = mix.list_weight(wl, weights)
            how = "excluded" if excluded else (f"{weight:g}" if weight > 0 else "wildcard")
            rows.append((wl.id, "✗" if excluded else "", wl.id, wl.slot, ", ".join(wl.tags), how))
        return rows

    def rebuild(self, keep=None):
        table = self.query_one("#mix", DataTable)
        row = table.cursor_row if keep is None else keep
        table.clear(columns=True)
        genres = " / ".join(self.mix().data["base"]) or "no genre kept yet"
        if self.view == "tags":
            self.query_one("#sub", Static).update(
                f"Tags for {genres}.  Genre default is the blend of the genre profiles; Now includes your boosts "
                "and exclusions.   [e] exclude  [+/-] boost  [0] unboost  [tab] lists  [r] reset")
            table.add_columns("", "Tag", "Default", "Boost", "Now", "")
            for key, *cells in self.tag_rows():
                table.add_row(*cells, key=key)
        else:
            self.query_one("#sub", Static).update(
                "Lists. 'wildcard' lists are not in the mix but still turn up now and then.   "
                "e: exclude (never used in this story)   tab: tags   r: reset")
            table.add_columns("", "List", "Slot", "Tags", "Weight")
            for key, *cells in self.list_rows():
                table.add_row(*cells, key=key)
        if table.row_count:
            table.move_cursor(row=min(row, table.row_count - 1))

    def current_key(self):
        table = self.query_one("#mix", DataTable)
        if not table.row_count:
            return None
        return table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value

    def say(self, message):
        self.query_one("#msg", Static).update(message)

    # --- actions ---------------------------------------------------------------------------------------

    def action_toggle(self):
        key = self.current_key()
        if key is None:
            return
        mix = self.mix()
        if self.view == "tags":
            on = not mix.is_tag_excluded(key)
            mix.exclude_tag(key, on)
        else:
            on = key not in mix.data["exclude_lists"]
            mix.exclude_list(key, on)
        self.say(f"{'Excluded' if on else 'Allowed again'}: {key} (this story only)")
        self.rebuild()

    def action_boost(self, direction):
        if self.view != "tags":
            return
        key = self.current_key()
        mix = self.mix()
        current = mix.data["boost"].get(key, 1.0)
        i = min(range(len(BOOST_LADDER)), key=lambda n: abs(BOOST_LADDER[n] - current))
        new = BOOST_LADDER[max(0, min(len(BOOST_LADDER) - 1, i + int(direction)))]
        mix.set_boost(key, new)
        self.say(f"Boost for {key}: ×{new:g} (this story only)")
        self.rebuild()

    def action_boost_reset(self):
        if self.view == "tags" and self.current_key():
            self.mix().set_boost(self.current_key(), 1.0)
            self.say("Boost cleared.")
            self.rebuild()

    def action_switch(self):
        self.view = "lists" if self.view == "tags" else "tags"
        self.rebuild(keep=0)

    def action_reset(self):
        self.mix().reset()
        self.say("Back to the genre defaults for this story. Kept pieces are unchanged.")
        self.rebuild()

    def action_close(self):
        self.session.save()
        self.dismiss(None)


# --- the main screen ----------------------------------------------------------------------------------

class MainScreen(Screen):
    # Footer order matters: the keys you can't live without come first (the footer clips on narrow terminals).
    BINDINGS = [
        Binding("space", "roll", "Roll"),
        Binding("k", "keep", "Keep"),
        navigation.back_binding(),
        navigation.quit_binding(),
        *navigation.mode_bindings("wheel"),
        Binding("question_mark", "help", "Help", key_display="?"),
        Binding("f", "reroll_field", "Field"),
        Binding("e", "edit", "Edit"),
        Binding("w", "write", "Write"),
        Binding("plus,equals_sign", "rate(1)", "Rate", key_display="+/-"),
        Binding("minus", "rate(-1)", "Dislike", show=False),
        Binding("h", "history", "Hist"),
        Binding("m", "mix", "Flavor"),
        Binding("v", "focus_universe", "Universe"),
        Binding("B", "send", "Send to Builder", key_display="B"),
        Binding("c", "copy_story", "Copy story"),
        Binding("a", "update_inputs", "Update", show=False),
        Binding("i", "ignore", "Ignore", show=False),
        Binding("C", "copy_draft", "Copy as new", show=False),
        Binding("b", "back", "Back"),
        Binding("x", "skip", "Skip"),
        Binding("u", "universe_add", "Univ", key_display="u/U"),
        Binding("U", "universe_remove", "Remove", show=False),
        Binding("E", "editor", "$EDITOR"),
        Binding("escape", "focus_card", "", show=False),
    ]
    DEFAULT_CSS = """
    MainScreen #body { height: 1fr; }
    MainScreen #left { width: 46; }
    MainScreen .box { border: round $primary-darken-2; border-title-color: $accent; border-title-style: bold; padding: 0 1; }
    MainScreen #steps-box { height: auto; }
    MainScreen #uni-box { height: 2fr; min-height: 10; }
    MainScreen #stories-box { height: 2fr; min-height: 8; }
    MainScreen #right { width: 48; border: round $primary-darken-2; }
    MainScreen #sofar-box { height: 1fr; }
    MainScreen #issues { padding: 0 1; height: auto; }
    MainScreen #sofar { padding: 0 1; height: auto; }
    MainScreen #stories { height: 1fr; min-height: 3; }
    MainScreen #story-buttons, MainScreen #story-buttons2 { height: 1; }
    MainScreen #story-buttons Button, MainScreen #story-buttons2 Button { height: 1 !important; border: none !important; min-width: 4; padding: 0; margin-right: 1; }
    MainScreen #steps { height: auto; max-height: 10; }
    MainScreen #uni-buttons, MainScreen #uni-buttons2 { height: 1; }
    MainScreen #uni-mode-label { width: auto; }
    MainScreen #uni-buttons Button, MainScreen #uni-buttons2 Button { height: 1 !important; border: none !important; min-width: 6; margin-right: 1; padding: 0; }
    MainScreen #universe { height: 1fr; min-height: 3; }
    MainScreen #uni-check { height: auto; max-height: 8; }
    MainScreen #banner { background: $warning 30%; color: $text; padding: 0 1; height: auto; }
    MainScreen #banner-buttons { height: 1; padding: 0 1; }
    MainScreen #banner-buttons Button { height: 1 !important; border: none !important; min-width: 8; margin-right: 1; padding: 0; }
    MainScreen #buttons { height: 1; padding: 0 1; }
    MainScreen #buttons Button { height: 1 !important; border: none !important; min-width: 8; margin-right: 1; padding: 0; }
    MainScreen #main { width: 1fr; }
    MainScreen #card-box { height: 3fr; border: round $primary; }
    MainScreen #hist-box { height: 2fr; border: round $primary-darken-2; }
    MainScreen .title { background: $boost; color: $accent; text-style: bold; padding: 0 1; height: 1; }
    MainScreen #hint { color: $text-muted; padding: 0 1; height: auto; max-height: 4; }
    MainScreen #meta { padding: 0 1; height: 1; color: $accent; }
    MainScreen #extra { color: $text-muted; padding: 0 1; height: auto; }
    MainScreen OptionList { height: 1fr; border: none; }
    MainScreen #status { height: 1; padding: 0 1; background: $boost; color: $text; }
    MainScreen OptionList:focus { border: none; }
    """

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.hist_mode = "rolls"          # or "field": the selected field's own history
        self._busy = False

    # --- layout ----------------------------------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield QuietHeader()
        with Horizontal(id="body"):
            with Vertical(id="left"):
                with Vertical(id="steps-box", classes="box") as box:
                    box.border_title = "Steps"
                    yield OptionList(id="steps")
                with Vertical(id="uni-box", classes="box") as box:
                    box.border_title = "Universes to draw from"
                    yield UniverseChecklist(id="uni-check")
                    with Horizontal(id="uni-buttons"):
                        yield Static("Whole characters/places from these: ", id="uni-mode-label", markup=False)
                        yield _quiet(Button("no       ", id="uni-mode"))
                    with Horizontal(id="uni-buttons2"):
                        yield _quiet(Button("Open in the Builder", id="uni-builder"))
                    yield UniverseTree("Universe", id="universe")
                with Vertical(id="stories-box", classes="box") as box:
                    box.border_title = "Past stories"
                    yield StoryList(id="stories")
                    with Horizontal(id="story-buttons"):
                        yield _quiet(Button("Open", id="st-open"))
                        yield _quiet(Button("Del", id="st-delete"))
                        yield _quiet(Button("Promote", id="st-promote"))
                    with Horizontal(id="story-buttons2"):
                        yield _quiet(Button("Use protagonist", id="st-protagonist"))
                        yield _quiet(Button("Use setting", id="st-setting"))
            with Vertical(id="main"):
                with Vertical(id="card-box"):
                    yield Static("", id="hint", markup=False)
                    yield Static("", id="banner", markup=False)
                    with Horizontal(id="banner-buttons"):
                        yield _quiet(Button("Update", id="ban-update", variant="warning"))
                        yield _quiet(Button("Reroll", id="ban-reroll"))
                        yield _quiet(Button("Ignore", id="ban-ignore"))
                    yield Static("", id="meta", markup=False)
                    yield CardList(id="card")
                    yield Static("", id="extra", markup=False)
                    yield Static("▲ ▼ like or dislike a line: liked wording is used more, disliked less in later rolls.", id="legend", markup=False)
                    with Horizontal(id="buttons"):
                        for label, name in (("Roll", "roll"), ("Keep", "keep"), ("Back", "back"),
                                            ("Skip", "skip"), ("Flavor", "mix"), ("Send to Builder", "send")):
                            yield _quiet(Button(label, id=f"btn-{name}"))
                with Vertical(id="hist-box"):
                    yield Static("History", id="hist-title", markup=False, classes="title")
                    yield OptionList(id="history")
            with Vertical(id="right"):
                yield Static("The story so far", classes="title", markup=False)
                with VerticalScroll(id="sofar-box"):
                    yield Static("", id="issues", markup=False)
                    yield Static("", id="sofar", markup=False)
        yield Static("", id="status", markup=False)
        yield FitFooter()

    def on_mount(self):
        self.session.enter(store.open_step(self.session.story))
        self.query_one("#universe", Tree).show_root = False
        self.refresh_all()
        self.query_one("#card", OptionList).focus()
        self.say(self.app.notice or self.opening_note())

    def opening_note(self):
        story = self.session.story
        if story.get("promoted"):
            return ("This draft was promoted, so the Builder holds the real story and the Wheel shows it read-only. "
                    "C makes an editable copy as a new draft.")
        if store.progress(story)[2]:
            return "This story is finished. You are on the last step; pick a step on the left to change one."
        return ""

    def locked(self):
        """A promoted draft is read-only here (see CLAUDE.md): say so, and offer the copy."""
        if self.session.story.get("promoted"):
            self.say("Read-only: this draft was promoted, and edits here would drift from the Builder. "
                     "Press C to make an editable copy as a new draft.")
            return True
        return False

    def action_copy_draft(self):
        story = self.session.story
        if not story.get("promoted"):
            self.say("Only a promoted draft needs a copy; this one is already editable.")
            return
        new = store.copy_as_new(story)
        store.save_draft(new)
        self.switch_story(new)
        self.say(f"Made an editable copy of '{store.title_of(story)}'. The promoted original is untouched.")

    # --- showing the session --------------------------------------------------------------------------------

    @property
    def card(self):
        return self.query_one("#card", OptionList)

    @property
    def history(self):
        return self.query_one("#history", OptionList)

    @property
    def steps_list(self):
        return self.query_one("#steps", OptionList)

    def card_field(self):
        """The field highlighted on the card (None on a one-field step)."""
        s = self.session
        if s.step.single:
            return None
        i = self.card.highlighted
        names = s.field_names
        return names[i] if i is not None and i < len(names) else names[0]

    def say(self, message):
        self.query_one("#status", Static).update(message)

    def refresh_all(self):
        self._busy = True
        try:
            self.refresh_steps()
            self.refresh_card()
            self.refresh_history()
            self.refresh_universe()
            self.refresh_stories()
            self.refresh_sofar()
        finally:
            self._busy = False
        notes = self.session.take_notes()
        if notes:
            self.say("  ".join(notes))
        title = self.session.story["kept"].get("title", {}).get("title")
        self.refresh_send_button()
        self.app.remember(self.session)
        self.app.title = f"storywheel · {title}" if title else "storywheel"
        self.app.sub_title = f"{self.session.step.label}  ({self.session.i + 1}/{len(self.session.steps)})"

    def on_screen_resume(self):
        """Coming back from another mode: the draft is as it was; only the title bar needs doing again."""
        title = self.session.story["kept"].get("title", {}).get("title")
        self.app.title = f"storywheel · {title}" if title else "storywheel"
        self.app.sub_title = f"{self.session.step.label}  ({self.session.i + 1}/{len(self.session.steps)})"
        self.app.remember(self.session)

    def refresh_steps(self):
        s = self.session
        lst = self.steps_list
        lst.clear_options()
        rows = []
        for n, step in enumerate(s.steps):
            state = s.marker(n)
            if state == "kept":
                state = s.flag(n) or state
            mark, style = MARKS[state]
            t = Text()
            t.append(f"{mark} ", style=style)
            t.append(f"{n + 1} {step.label}", style="bold" if n == s.i else "")
            rows.append(Option(t, id=str(n)))
        lst.add_options(rows)
        lst.highlighted = s.i

    def refresh_sofar(self):
        """The right column: problems with kept steps on top, then the kept story as plain text."""
        s = self.session
        issues = Text()
        for severity, message in s.issues():
            mark, style = MARKS[severity]
            issues.append(f"{mark} ", style=style)
            issues.append(message + "\n\n")
        self.query_one("#issues", Static).update(issues)
        self.query_one("#issues", Static).display = bool(issues.plain)
        text = store.to_plain(s.story, width=42)
        self.query_one("#sofar", Static).update(text or "(nothing kept yet)")

    def refresh_stories(self):
        s = self.session
        lst = self.stories_list
        previous = lst.highlighted
        lst.clear_options()
        rows = []
        for story in store.all_stories():
            t = Text()
            here = story["id"] == s.story["id"]
            t.append("▶ " if here else "  ", style="bold cyan")
            t.append(f"{store.title_of(story)[:22]:<22}", style="bold" if here else "")
            kept, total, done = store.progress(story)
            t.append(f" {story['created'][5:10]} " + ("done" if done else f"{kept}/{total}"), style="dim")
            if story.get("promoted"):
                t.append(f" ⇢{story['promoted']['universe'][:10]}", style="green")
            rows.append(Option(t, id=story["id"]))
        if not rows:
            rows.append(Option(Text("(no saved stories yet)", style="dim"), id="", disabled=True))
        lst.add_options(rows)
        if previous is not None:                                  # keep your place in the list
            lst.highlighted = min(previous, len(rows) - 1)

    @property
    def stories_list(self):
        return self.query_one("#stories", OptionList)

    def story_act(self, action):
        """Open, delete, or send the protagonist / setting of the highlighted past story."""
        i = self.stories_list.highlighted
        option = self.stories_list.get_option_at_index(i) if i is not None else None
        if option is None or not option.id:
            self.say("Select a story in the Past stories list first.")
            return
        try:
            story = store.load(option.id)
        except (OSError, ValueError):
            self.say("Couldn't read that story.")
            self.refresh_stories()
            return
        here = story["id"] == self.session.story["id"]
        title = store.title_of(story)
        if action == "open":
            if here:
                self.say("That is the story you are in.")
            else:
                self.switch_story(store.load(story["id"]))
        elif action == "promote":
            if story.get("promoted"):
                self.say(f"'{title}' was already promoted to the universe '{story['promoted']['universe']}'.")
            elif not story["kept"]:
                self.say(f"'{title}' has nothing kept yet, so there is nothing to promote.")
            else:
                if here:
                    self.session.save()
                    story = self.session.story
                self.promote_flow(story, None, "ask")
        elif action == "delete":
            if here:
                self.say("That is the story you are in: quit (q) and choose Delete to remove it.")
                return
            self.app.push_screen(ConfirmScreen(f"Delete the story '{title}'?\n\nThis can't be undone "
                                               "(your universe is not touched)."),
                                 lambda yes: self._story_deleted(story, yes))
        else:
            piece = story["kept"].get(action)
            if not piece:
                self.say(f"'{title}' has no kept {action}.")
                return
            unis = self.session.available_universes()
            if not unis:
                self.say("There is no universe yet. Promote a story or make one in the Builder (F2).")
                return
            self.app.push_screen(ChoiceScreen(f"Send the {action} of '{title}' to which universe?",
                                              [(u.name, u.slug) for u in unis]),
                                 lambda slug: self._sent_piece(story, action, piece, slug))

    def _sent_piece(self, story, action, piece, slug):
        from . import universe_atoms, vault
        if not slug:
            return
        step = next(st for st in steps_for(story) if st.key == action)
        _e, message = universe_atoms.save_piece(vault.get_universe(slug), action, step.label, public(piece))
        self.say(message)
        self.refresh_universe()

    def _story_deleted(self, story, yes):
        if yes:
            store.delete(story)
            self.say(f"Deleted '{store.title_of(story)}'.")
        self.refresh_stories()

    def switch_story(self, story):
        """Leave this story (saved) and open another."""
        old = self.session
        old.save()
        session = Session(story, self.app.engine, ratings=self.app.engine.ratings)
        session.enter(store.open_step(story))
        self.session = self.app.session = session
        self.hist_mode = "rolls"
        self.refresh_all()
        self.say(self.opening_note() or f"Opened '{store.title_of(story)}'. The story you left was saved.")
        self.card.focus()

    def refresh_card(self, keep_field=True):
        s = self.session
        previous = self.card.highlighted if keep_field else 0
        step, fields = s.step, s.fields
        self.query_one("#hint", Static).update(step.hint)
        self.query_one("#meta", Static).update(
            f"#{s.cur + 1} of {len(s.hist)}{s.source_tag(s.cur)}")
        rows = []
        if step.single:
            rows.append(Option(_row("", next(iter(fields.values())), s.rating()), id="only"))
        else:
            width = max(len(k) for k in fields)
            for k, v in fields.items():
                rows.append(Option(_row(k.replace("_", " ").ljust(width), v, s.rating(k)), id=k))
        self.card.clear_options()
        self.card.add_options(rows)
        self.card.highlighted = min(previous or 0, len(rows) - 1)
        banner = s.stale_banner()
        self.query_one("#banner", Static).update(banner + "   (a: update, or choose below)" if banner else "")
        self.query_one("#banner", Static).display = bool(banner)
        self.query_one("#banner-buttons").display = bool(banner)
        extra = []
        if s.standin_line():
            extra.append(s.standin_line())
        if step.key == "structure":
            found = structures.find(fields["structure"])
            extra.append(found.blurb if found else "Not one of the known structures; the Story Spine will be used.")
        if s.cand.get("_threads"):
            extra.append("threads: " + T.describe(s.cand["_threads"]))
        self.query_one("#extra", Static).update("\n".join(extra))

    def refresh_history(self):
        s = self.session
        field = self.card_field() if self.hist_mode == "field" else None
        if self.hist_mode == "field" and field is None:
            self.hist_mode = "rolls"
        lst = self.history
        lst.clear_options()
        rows = []
        if self.hist_mode == "rolls":
            self.query_one("#hist-title", Static).update("History: every roll (what changed)   h: this field's values")
            for n in range(len(s.hist)):
                t = Text()
                t.append("▶ " if n == s.cur else "  ", style="bold cyan")
                t.append(f"#{n + 1}  ", style="dim")
                t.append(s.change_summary(n, 90), style="bold" if n == s.cur else "")
                t.append(s.source_tag(n), style="dim")
                t.append(s.stale_tag(n), style="bold yellow")
                rows.append(Option(t, id=str(n)))
            lst.add_options(rows)
            lst.highlighted = s.cur
        else:
            self.query_one("#hist-title", Static).update(
                f"History of: {field.replace('_', ' ')}   (enter brings one back)   h: every roll")
            current = s.cand.get(field)
            for n, v in enumerate(s.field_values(field)):
                t = Text()
                t.append("▶ " if v == current else "  ", style="bold cyan")
                t.append(v, style="bold" if v == current else "")
                rows.append(Option(t, id=str(n)))
            lst.add_options(rows)
            values = s.field_values(field)
            lst.highlighted = values.index(current) if current in values else len(values) - 1

    MODE_WORDS = {"n": "no", "m": "sometimes", "o": "only"}

    def refresh_universe(self):
        """The universe panel: a checklist of universes to draw from, the mode for whole-step candidates, and
        the entities of the ticked universes (characters offer the protagonist step, places the setting step)."""
        s = self.session
        chosen = set(s.story.get("universes", []))
        unis = s.available_universes()
        check = self.query_one("#uni-check", OptionList)
        keep = check.highlighted
        check.clear_options()
        rows = []
        for u in unis:
            on = u.slug in chosen
            t = Text()
            t.append("☑ " if on else "☐ ", style="bold green" if on else "dim")
            t.append(u.name, style="bold" if on else "")
            t.append("\n    " + universe_atoms.counts_text(u), style="dim")
            rows.append(Option(t, id=u.slug))
        if not rows:
            rows.append(Option(Text("(no universes yet: promote a story)", style="dim"), id="", disabled=True))
        check.add_options(rows)
        check.highlighted = min(keep, len(rows) - 1) if keep is not None else (0 if unis else None)
        self.query_one("#uni-box").border_title = f"Universes to draw from ({len(chosen)} ticked)"
        button = self.query_one("#uni-mode", Button)
        button.label = f"{self.MODE_WORDS[s.universe_mode]:<9}"          # same width every time
        button.refresh(layout=True)
        tree = self.query_one("#universe", UniverseTree)
        if not hasattr(self, "_open_groups"):
            self._open_groups = set()
        tree.clear()
        ticked = s.selected_universes()
        for type_, label, step_key in universe_atoms.GROUPS:
            entries = [(u, e) for u in ticked for e in universe_atoms.named(u, type_)]
            if not entries:
                continue
            group = tree.root.add(f"{label} ({len(entries)})", data=("group", type_), expand=type_ in self._open_groups)
            for u, e in entries:
                prefix = f"{u.name}: " if len(ticked) > 1 else ""
                group.add_leaf(prefix + e.name, data=("entity", step_key or "", u.slug, e.id, type_))
        if not chosen:
            tree.root.add_leaf("(tick a universe above to see its people and places)", data=("none",))
        elif not tree.root.children:
            tree.root.add_leaf("(nothing in the ticked universes yet)", data=("none",))

    def on_tree_node_collapsed(self, event):
        if event.node.data and event.node.data[0] == "group":
            self._open_groups.discard(event.node.data[1])

    def on_tree_node_expanded(self, event):
        if event.node.data and event.node.data[0] == "group":
            self._open_groups.add(event.node.data[1])

    def on_tree_node_selected(self, event):
        data = event.node.data
        if data and data[0] == "entity":
            self.universe_act(None, data)

    def _chosen_entry(self):
        node = self.query_one("#universe", UniverseTree).cursor_node
        data = node.data if node else None
        return data if data and data[0] == "entity" else None

    def universe_act(self, action, data=None):
        """Preview (action None), or use, the highlighted entity."""
        data = data or self._chosen_entry()
        if not data:
            self.say("Select a person or place in the universe panel first.")
            return
        _tag, step_key, slug, eid, type_ = data
        from . import vault
        u = vault.get_universe(slug)
        e = u.entity(eid) if u else None
        if not e:
            return
        usable = next(((uu, ee, f) for uu, ee, f in self.session.universe_entries(step_key) if uu.slug == slug and ee.id == eid), None) \
            if step_key else None
        fields = usable[2] if usable else {k: v for k, v in e.fields.items() if v and isinstance(v, str)}
        if action is None:
            label = self.session.universe_label(step_key) if usable else type_.title()
            self.app.push_screen(UniverseEntryScreen(label, fields, u.name),
                                 lambda what: self.universe_act(what, data) if what else None)
        elif action == "use":
            if not usable:
                self.say(f"A {type_} here is not a whole step: its name and details turn up in rolls (boosted) while the universe is ticked."
                         + (" Landmarks and buildings can't be a setting on their own; pick the town they are in." if type_ == "place" else ""))
            elif self.session.use_universe_entry(step_key, fields):
                self.hist_mode = "rolls"
                self.after()
                self.card.focus()
            else:
                self.after()

    def universe_mode(self):
        mode = self.session.cycle_universe_mode()
        self.refresh_universe()
        self.say({"n": "Whole-step candidates never come from your universes (their people and places still appear in rolls).",
                  "m": "Mixing universe characters and places in as whole candidates (about a third of rolls).",
                  "o": "Whole-step candidates come only from the ticked universes."}[mode])

    def toggle_universe_row(self, slug):
        on = self.session.toggle_universe(slug)
        self.refresh_universe()
        names = [u.name for u in self.session.selected_universes()]
        self.say((f"Drawing from: {', '.join(names)}." if names else "Not drawing from any universe.")
                 + ("" if not on else " Their people, places and things are boosted in the next rolls."))

    def action_ignore(self):
        self.session.ignore_stale()
        self.after()

    def action_update_inputs(self):
        self.session.update_inputs()
        self.after()

    def action_focus_universe(self):
        self.query_one("#uni-check", OptionList).focus()

    def refresh_send_button(self):
        """'Send to Builder' is there from the first kept step; once sent it becomes 'Open in Builder'."""
        story = self.session.story
        button = self.query_one("#btn-send", Button)
        sent = bool(story.get("promoted"))
        button.label = "Open in Builder" if sent else "Send to Builder"
        button.disabled = not story["kept"]
        button.tooltip = ("Nothing is kept yet: keep a step first." if not story["kept"] else
                          "Bring this story into a universe and open the Universe Builder (key: B)")

    def action_send(self):
        """Bring this draft into a universe and go to the Builder (or just open it, if it was sent already)."""
        s = self.session
        story = s.story
        if not story["kept"]:
            self.say("Nothing is kept yet, so there is nothing to send. Keep a step first (k).")
            return
        if story.get("promoted"):
            s.save()
            self.app.go("builder", dict(story["promoted"]))
            return
        s.save()
        self.app.push_screen(ChoiceScreen("Send this story to the Universe Builder: into…",
                                          [("a new universe", "new"), ("an existing universe", "existing")]),
                             lambda c: self.promote_flow(story, c, "exit") if c else None)

    def action_mode(self, which):
        """F1 / F2 / F3: save this draft and leave for another mode. F2 from a draft with kept steps offers to send it first."""
        story = self.session.story
        if which == "builder" and story["kept"] and not story.get("promoted"):
            self.app.push_screen(ChoiceScreen("This draft has kept steps that are not in the Builder yet.",
                                              [("Send it to the Builder first (new or existing universe)", "send"),
                                               ("Just go to the Builder; leave the draft as it is", "go")]),
                                 lambda c: self.action_send() if c == "send" else (self._leave("builder") if c == "go" else None))
            return
        self._leave(which)

    def _leave(self, which):
        self.session.save()
        slug = (self.session.story.get("universes") or [None])[0]
        self.app.go(which, {"universe": slug})

    def on_button_pressed(self, event):
        event.stop()
        name = event.button.id or ""
        if name.startswith("st-"):
            self.story_act(name[3:])
            return
        if name == "uni-mode":
            self.universe_mode()
            return
        if name == "uni-builder":
            self.action_mode("builder")
            return
        if name.startswith("ban-"):
            {"ban-update": self.action_update_inputs, "ban-reroll": self.action_roll,
             "ban-ignore": self.action_ignore}[name]()
            self.card.focus()
            return
        if name.startswith("btn-"):
            getattr(self, f"action_{name[4:]}")()
            if name != "btn-mix":
                self.card.focus()

    # --- the mouse on the card ---------------------------------------------------------------------------

    def _field_at(self, index):
        names = self.session.field_names
        return None if self.session.step.single else names[min(index, len(names) - 1)]

    def on_card_list_field(self, event):
        if event.button == 3:
            self.action_edit()
        else:
            self.action_reroll_field()

    def on_card_list_rate(self, event):
        self.session.rate(event.value, self._field_at(event.index))
        self.after()
        self.card.highlighted = min(event.index, len(self.session.field_names) - 1)

    def on_card_list_scrolled(self, event):
        s = self.session
        field = self._field_at(event.index) or s.field_names[0]
        if s.step_value(field, event.direction):
            self.after()
            self.card.highlighted = s.field_names.index(field) if not s.step.single else 0
        else:
            self.say("That is the " + ("oldest" if event.direction < 0 else "newest") + " value this field has had.")

    def after(self, message=None):
        """Show the new state; say something if there is something to say."""
        self.refresh_all()
        if message:
            self.say(message)

    # --- list events --------------------------------------------------------------------------------------------

    def on_option_list_option_highlighted(self, event):
        if self._busy:
            return
        if event.option_list.id == "card" and self.hist_mode == "field":
            self.refresh_history()

    def on_option_list_option_selected(self, event):
        lst = event.option_list.id
        s = self.session
        if lst == "uni-check":
            if event.option.id:
                self.toggle_universe_row(event.option.id)
        elif lst == "stories":
            self.story_act("open")
        elif lst == "card":
            self.action_reroll_field()
        elif lst == "steps":
            s.jump(int(event.option.id))
            self.hist_mode = "rolls"
            self.after()
            self.card.focus()
        elif lst == "history":
            if self.locked():
                return
            index = int(event.option.id)
            if self.hist_mode == "rolls":
                s.pick(index)
            else:
                field = self.card_field()
                s.pick_value(field, s.field_values(field)[index])
            self.after()

    # --- actions --------------------------------------------------------------------------------------------------

    def action_roll(self):
        if self.locked():
            return
        self.session.roll()
        self.after()

    def action_keep(self):
        if self.locked():
            return
        s = self.session
        s.keep()
        self.hist_mode = "rolls"
        if s.done:
            path = s.save()
            self.refresh_all()
            self.app.push_screen(DoneScreen(self.session.story["kept"].get("title", {}).get("title", "Untitled"), path),
                                 self._after_done)
        else:
            self.after()
            self.card.highlighted = 0

    def _after_done(self, choice):
        if choice == "quit":
            self.action_quit_app()
        else:
            self.session.enter(len(self.session.steps) - 1)
            self.after()

    def action_reroll_field(self):
        if self.locked():
            return
        field = self.card_field()
        if field is None:
            self.session.roll()
            self.after("This step has one field, so f rolls the whole thing.")
        else:
            self.session.reroll_field(field)
            self.after()
            self.card.highlighted = self.session.field_names.index(field)
            if self.hist_mode == "field":
                self.refresh_history()

    def action_edit(self):
        if self.locked():
            return
        s = self.session
        field = self.card_field() or s.field_names[0]
        self.app.push_screen(EditScreen(f"Edit {field.replace('_', ' ')}", {field: s.cand[field]}),
                             lambda out: self._edited(field, out))

    def _edited(self, field, out):
        if out is not None and self.session.edit_field(field, out[field]):
            self.after()

    def action_write(self):
        if self.locked():
            return
        s = self.session
        self.app.push_screen(EditScreen("Write your own (each box starts as it is now)", dict(s.fields)), self._written)

    def _written(self, out):
        if out is not None and self.session.replace_fields({k: v.strip() or self.session.fields[k] for k, v in out.items()}):
            self.after()

    def action_editor(self):
        if self.locked():
            return
        from .cli import edit_in_editor
        with self.app.suspend():
            new = edit_in_editor(public(self.session.cand))
        if self.session.replace_fields(new):
            self.after()
        else:
            self.say("No changes.")

    def action_rate(self, value):
        s = self.session
        field = self.card_field()
        s.rate(int(value), field)
        self.after()

    def action_universe_add(self):
        """Save the showing candidate into a universe: the ticked one if there is just one, else ask."""
        s = self.session
        unis = s.available_universes()
        if not unis:
            self.say("There is no universe yet. Promote a story (leave with q) or make one in the Builder (F2).")
            return
        ticked = s.selected_universes()
        if len(ticked) == 1:
            s.save_to_universe(ticked[0])
            self.after()
            return
        self.app.push_screen(ChoiceScreen("Save to which universe?", [(u.name, u.slug) for u in unis]),
                             self._saved_to)

    def _saved_to(self, slug):
        if slug:
            from . import vault
            self.session.save_to_universe(vault.get_universe(slug))
            self.after()

    def action_universe_remove(self):
        self.say("To remove a person or place from a universe, open it in the Builder (F2): deleting is done there, with a confirm.")

    def action_history(self):
        if self.hist_mode == "rolls" and self.card_field() is not None:
            self.hist_mode = "field"
        else:
            self.hist_mode = "rolls"
        self.refresh_history()
        self.history.focus()

    def action_mix(self):
        self.app.push_screen(MixScreen(self.session), lambda _: self.after("Flavor saved for this story."))

    def action_back(self):
        self.session.back()
        self.hist_mode = "rolls"
        self.after()

    def action_skip(self):
        if self.locked():
            return
        s = self.session
        s.skip()
        self.hist_mode = "rolls"
        if s.done:
            self.action_keep_done()
        else:
            self.after()

    def action_keep_done(self):
        path = self.session.save()
        self.refresh_all()
        self.app.push_screen(DoneScreen(self.session.story["kept"].get("title", {}).get("title", "Untitled"), path),
                             self._after_done)


    def action_help(self):
        self.app.push_screen(HelpScreen())

    def action_focus_card(self):
        self.card.focus()

    def action_noop_mode(self):
        self.say("You are in the Wheel.")

    def action_back_mode(self):
        """q: back to the mode you came from (the draft is saved)."""
        from . import modes
        if not modes.can_go_back():
            self.say(navigation.NO_BACK)
            return
        self._leave("back")

    def action_quit_program(self):
        self.action_quit_app()

    def action_quit_app(self):
        s = self.session
        kept = bool(s.story["kept"])
        promotable = kept and not s.story.get("promoted")
        title = store.title_of(s.story) if kept else "this story"
        self.app.push_screen(QuitScreen(title, promotable), self._quit_chosen)

    def _quit_chosen(self, choice):
        s = self.session
        if choice == "keep":
            self._finish()
        elif choice in ("new", "existing"):
            self.promote_flow(s.story, choice, "exit")
        elif choice == "delete":
            store.delete(s.story)
            self.app.exit(f"Deleted '{store.title_of(s.story)}'. Nothing was kept.")

    def _finish(self, extra=None):
        """Save the story and leave, printing it as plain text, then where it went."""
        s = self.session
        path = s.save()
        after, self._after_promotion = getattr(self, "_after_promotion", None), None
        parts = [store.to_plain(s.story)]
        if extra:
            parts.append(extra)
        if path:
            parts.append(f"Markdown: {path}")
        parts.append(f"Resume with:  storywheel resume {s.story['id']}")
        full = "\n\n".join(p for p in parts if p)
        if after:                                       # promoted: carry on into the Builder (its status line says what was made)
            self.app.go(after[0], after[1], message=extra, full=full)
            return
        self.app.exit(full)

    # --- promotion: bringing a draft into a universe -------------------------------------------------------

    def promote_flow(self, draft, choice, then):
        """choice: 'new', 'existing' or None (ask). then: 'exit' to leave after, 'ask'/'stay' to remain."""
        from . import vault
        if choice is None or choice == "ask":
            self.app.push_screen(QuitScreen(store.title_of(draft), True), lambda c: self._promote_choice(draft, c, then)
                                 if c in ("new", "existing") else None)
            return
        if choice == "new":
            self.app.push_screen(EditScreen("Name the new universe", {"name": store.title_of(draft)}),
                                 lambda out: self._promote_named(draft, out, then))
        else:
            unis = vault.list_universes()
            if not unis:
                self.say("There is no universe yet, so this one will go into a new universe.")
                return self.promote_flow(draft, "new", then)
            self.app.push_screen(PickUniverseScreen(unis), lambda slug: self._promote_picked(draft, slug, then))

    def _promote_choice(self, draft, c, then):
        self.promote_flow(draft, c, then)

    def _promote_named(self, draft, out, then):
        if out is None:
            return
        self._preview(draft, None, out["name"].strip() or store.title_of(draft), then)

    def _promote_picked(self, draft, slug, then):
        from . import vault
        if slug:
            self._preview(draft, vault.get_universe(slug), None, then)

    def _preview(self, draft, universe, new_name, then):
        from . import promote
        plan = promote.build_plan(draft, universe, self.app.engine, new_name)
        self.app.push_screen(PromotePreviewScreen(plan), lambda go: self._promote_go(draft, plan, universe, go, then))

    def _promote_go(self, draft, plan, universe, go, then):
        from . import promote
        if not go:
            self.say("Not promoted. The draft is as it was.")
            return
        story, report = promote.apply_plan(plan, universe, draft)
        u = story.universe
        store.save_draft(draft)
        if then == "exit":
            self._after_promotion = ("builder", {"universe": u.slug, "story": story.slug})
        message = f"Promoted into the universe '{u.name}' as the story '{story.title}'.\n" + "\n".join(report)
        if then == "exit":
            self._finish(message)
        else:
            self.say(f"Promoted into '{u.name}'.")
            self.refresh_stories()

    def action_copy_story(self):
        text = store.to_plain(self.session.story)
        if not text:
            self.say("Nothing is kept yet, so there is nothing to copy.")
            return
        how = clipboard.copy(text, self.app)
        self.say(f"Copied the story so far ({len(text)} characters) via {how}." if how
                 else tools.missing("clipboard"))


class StorywheelApp(App):
    TITLE = "storywheel"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = []

    def __init__(self, story, engine, state_store=None, notice=""):
        super().__init__()
        appearance.apply(self)
        self.story, self.engine = story, engine
        self.state_store = state_store
        self.session = Session(story, engine, ratings=engine.ratings)
        self.main = MainScreen(self.session)
        self.next = None                  # where to go after the app closes: ("builder", {...}) or None
        self.notice = notice              # said once, on the status line, when the Wheel opens

    def go(self, where, payload=None, message=None, full=None):
        """Leave the Wheel for another mode (the standalone app closes and says where; the hub just switches)."""
        self.next = (where, payload or {})
        self.exit(full or message)

    def remember(self, session):
        """Record where we are (state.json), so plain `storywheel` comes back here."""
        if self.state_store is not None:
            try:
                self.state_store.update(mode="wheel", draft=session.story["id"], step=session.i)
            except OSError:
                pass

    def on_mount(self):
        self.push_screen(self.main)


def run_app(story, engine, state_store=None, notice=""):
    """Run the app on a story; prints where it was saved when you quit. Returns where to go next, if the writer
    asked for another mode: ("builder", {...}), ("writer", {...}) or None."""
    app = StorywheelApp(story, engine, state_store, notice)
    message = app.run()
    if message:
        print("\n  " + str(message).replace("\n", "\n  "))
    return app.next
