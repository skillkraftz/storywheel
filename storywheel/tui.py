"""
The full-screen app (Textual). It drives a Session (session.py), the same engine room the
plain prompt uses, so the keys do exactly what they do there.

    steps (left)        which are kept, skipped, current; Enter jumps to one
    card (middle)       the current candidate; up/down select a field
    history (below)     every roll and what changed; with h, the selected field's own history
    footer              the keys

Tab moves between the three lists. Space rolls; k keeps; f rerolls the selected field;
e edits it; E opens $EDITOR; w writes your own; + and - rate; u / U universe; m mix editor;
h history; b back; x skip; q saves and quits; ? help.
"""
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Footer, Header, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from . import structures
from . import threads as T
from .session import Session
from .steps import public

BOOST_LADDER = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]
MARKS = {"kept": ("✓", "green"), "skipped": ("–", "yellow"), "current": ("▶", "bold cyan"), "pending": ("·", "dim")}

HELP = """\
[b]Keys[/b]

  [b]space[/b]   roll again
  [b]k[/b]       keep this and move on
  [b]f[/b]       reroll the selected field
  [b]e[/b]       edit the selected field
  [b]E[/b]       edit it all in $EDITOR
  [b]w[/b]       write your own
  [b]+[/b] [b]-[/b]     like / dislike the selected line. Disliked frames
          and atom pairs come up a little less. Again clears it.
  [b]u[/b] [b]U[/b]     save to / remove from your universe
  [b]h[/b]       history: every roll  or  the selected field's values
  [b]m[/b]       mix editor: what this story favors
  [b]b[/b]       go back a step
  [b]x[/b]       skip this step
  [b]q[/b]       save and quit
  [b]?[/b]       this help

[b]Moving around[/b]

  [b]up down[/b]  move within a list
  [b]tab[/b]      next list: steps, card, history
  [b]enter[/b]    card: roll.  history: pick that one.  steps: jump there.
  [b]esc[/b]      back to the card

Press esc to close.
"""


def _row(label, value, rating=0):
    text = Text()
    if label:
        text.append(label, style="bold cyan")
        text.append("  ")
    text.append(value)
    if rating:
        text.append("  ▲" if rating > 0 else "  ▼", style="bold green" if rating > 0 else "bold red")
    return text


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

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.title_text)
            with VerticalScroll():
                for name, value in self.fields.items():
                    yield Label(name.replace("_", " "))
                    yield Input(value, id=f"in-{name}")
            yield Label("enter: next / done     esc: cancel")

    def on_mount(self):
        self.query(Input).first().focus()

    def on_input_submitted(self, event):
        inputs = list(self.query(Input))
        i = inputs.index(event.input)
        if i + 1 < len(inputs):
            inputs[i + 1].focus()
        else:
            self.dismiss({name: self.query_one(f"#in-{name}", Input).value for name in self.fields})

    def action_cancel(self):
        self.dismiss(None)


class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape,question_mark,q", "close", "Close")]
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    HelpScreen > Static { width: 78; height: auto; border: round $accent; background: $surface; padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Static(HELP)

    def action_close(self):
        self.dismiss(None)


class UniverseScreen(ModalScreen):
    """Whether to pull from your universe in this story."""
    BINDINGS = [Binding("n", "pick('n')", "No"), Binding("m", "pick('m')", "Mix it in"),
                Binding("o", "pick('o')", "Only from it"), Binding("escape", "pick('n')", "No")]
    DEFAULT_CSS = """
    UniverseScreen { align: center middle; }
    UniverseScreen > Static { width: 60; height: auto; border: round $accent; background: $surface; padding: 1 2; }
    """

    def __init__(self, total):
        super().__init__()
        self.total = total

    def compose(self) -> ComposeResult:
        yield Static(f"You have {self.total} thing(s) saved in your universe.\n\nPull from it?\n\n"
                     "  [b]n[/b]  no\n  [b]m[/b]  mix it in (about a third of rolls)\n  [b]o[/b]  only from it")

    def action_pick(self, answer):
        self.dismiss(answer)


class DoneScreen(ModalScreen):
    BINDINGS = [Binding("q,enter", "quit_app", "Quit"), Binding("escape", "keep_going", "Keep editing")]
    DEFAULT_CSS = """
    DoneScreen { align: center middle; }
    DoneScreen > Static { width: 70; height: auto; border: round $success; background: $surface; padding: 1 2; }
    """

    def __init__(self, title, path):
        super().__init__()
        self.title_text, self.path = title, path

    def compose(self) -> ComposeResult:
        where = f"\n\nMarkdown: {self.path}" if self.path else ""
        yield Static(f"[b]Done: {self.title_text}[/b]{where}\n\n  [b]q[/b] / enter   quit\n  [b]esc[/b]         keep editing")

    def action_quit_app(self):
        self.dismiss("quit")

    def action_keep_going(self):
        self.dismiss("stay")


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
        yield Header()
        yield Static("MIX: THIS STORY ONLY. Changes here never touch the genre profiles, and only "
                     "affect future rolls (nothing you have kept changes).", id="warn", markup=False)
        yield Static("", id="sub", markup=False)
        yield DataTable(id="mix", cursor_type="row", zebra_stripes=True)
        yield Static("", id="msg", markup=False)
        yield Footer()

    def on_mount(self):
        self.app.sub_title = "Mix editor (this story only)"
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
        Binding("q", "quit_app", "Quit"),
        Binding("question_mark", "help", "Help", key_display="?"),
        Binding("f", "reroll_field", "Field"),
        Binding("e", "edit", "Edit"),
        Binding("w", "write", "Write"),
        Binding("plus,equals_sign", "rate(1)", "Rate", key_display="+/-"),
        Binding("minus", "rate(-1)", "Dislike", show=False),
        Binding("h", "history", "Hist"),
        Binding("m", "mix", "Mix"),
        Binding("b", "back", "Back"),
        Binding("x", "skip", "Skip"),
        Binding("u", "universe_add", "Univ", key_display="u/U"),
        Binding("U", "universe_remove", "Remove", show=False),
        Binding("E", "editor", "$EDITOR"),
        Binding("escape", "focus_card", "", show=False),
    ]
    DEFAULT_CSS = """
    MainScreen #body { height: 1fr; }
    MainScreen #left { width: 24; border: round $primary-darken-2; }
    MainScreen #main { width: 1fr; }
    MainScreen #card-box { height: 3fr; border: round $primary; }
    MainScreen #hist-box { height: 2fr; border: round $primary-darken-2; }
    MainScreen .title { background: $primary-darken-2; color: $text; padding: 0 1; height: 1; }
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
        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="left"):
                yield Static("Steps", classes="title")
                yield OptionList(id="steps")
            with Vertical(id="main"):
                with Vertical(id="card-box"):
                    yield Static("", id="hint", markup=False)
                    yield Static("", id="meta", markup=False)
                    yield OptionList(id="card")
                    yield Static("", id="extra", markup=False)
                with Vertical(id="hist-box"):
                    yield Static("History", id="hist-title", markup=False, classes="title")
                    yield OptionList(id="history")
        yield Static("", id="status", markup=False)
        yield Footer()

    def on_mount(self):
        i = self.session.story["step"]
        self.session.enter(i if i < len(self.session.steps) else 0)
        self.refresh_all()
        self.query_one("#card", OptionList).focus()
        total = self.session.universe_total()
        if total and not self.session.story["kept"]:
            self.app.push_screen(UniverseScreen(total), self._universe_chosen)

    def _universe_chosen(self, answer):
        self.session.set_universe_mode(answer or "n")
        self.say("Pulling from your universe." if answer in ("m", "o") else "")

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
        finally:
            self._busy = False
        notes = self.session.take_notes()
        if notes:
            self.say("  ".join(notes))
        title = self.session.story["kept"].get("title", {}).get("title")
        self.app.title = f"storywheel · {title}" if title else "storywheel"
        self.app.sub_title = f"{self.session.step.label}  ({self.session.i + 1}/{len(self.session.steps)})"

    def refresh_steps(self):
        s = self.session
        lst = self.steps_list
        lst.clear_options()
        rows = []
        for n, step in enumerate(s.steps):
            mark, style = MARKS[s.marker(n)]
            t = Text()
            t.append(f"{mark} ", style=style)
            t.append(f"{n + 1} {step.label}", style="bold" if n == s.i else "")
            rows.append(Option(t, id=str(n)))
        lst.add_options(rows)
        lst.highlighted = s.i

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
        extra = []
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
        if lst == "card":
            self.action_roll()
        elif lst == "steps":
            s.jump(int(event.option.id))
            self.hist_mode = "rolls"
            self.after()
            self.card.focus()
        elif lst == "history":
            index = int(event.option.id)
            if self.hist_mode == "rolls":
                s.pick(index)
            else:
                field = self.card_field()
                s.pick_value(field, s.field_values(field)[index])
            self.after()

    # --- actions --------------------------------------------------------------------------------------------------

    def action_roll(self):
        self.session.roll()
        self.after()

    def action_keep(self):
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
        field = self.card_field()
        if field is None:
            self.session.roll()
            self.after("This step has one field, so f rolls the whole thing.")
        else:
            self.session.reroll_field(field)
            self.after()
            self.card.highlighted = self.session.field_names.index(field)

    def action_edit(self):
        s = self.session
        field = self.card_field() or s.field_names[0]
        self.app.push_screen(EditScreen(f"Edit {field.replace('_', ' ')}", {field: s.cand[field]}),
                             lambda out: self._edited(field, out))

    def _edited(self, field, out):
        if out is not None and self.session.edit_field(field, out[field]):
            self.after()

    def action_write(self):
        s = self.session
        self.app.push_screen(EditScreen("Write your own (each box starts as it is now)", dict(s.fields)), self._written)

    def _written(self, out):
        if out is not None and self.session.replace_fields({k: v.strip() or self.session.fields[k] for k, v in out.items()}):
            self.after()

    def action_editor(self):
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
        self.session.universe_add()
        self.after()

    def action_universe_remove(self):
        self.session.universe_remove()
        self.after()

    def action_history(self):
        if self.hist_mode == "rolls" and self.card_field() is not None:
            self.hist_mode = "field"
        else:
            self.hist_mode = "rolls"
        self.refresh_history()
        self.history.focus()

    def action_mix(self):
        self.app.push_screen(MixScreen(self.session), lambda _: self.after("Mix saved for this story."))

    def action_back(self):
        self.session.back()
        self.hist_mode = "rolls"
        self.after()

    def action_skip(self):
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

    def action_quit_app(self):
        path = self.session.save()
        self.app.exit(f"Saved. Resume with:  storywheel resume {self.session.story['id']}"
                      + (f"\nMarkdown: {path}" if path else ""))


class StorywheelApp(App):
    TITLE = "storywheel"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = []

    def __init__(self, story, engine):
        super().__init__()
        self.story, self.engine = story, engine
        self.session = Session(story, engine, ratings=engine.ratings)
        self.main = MainScreen(self.session)

    def on_mount(self):
        self.push_screen(self.main)


def run_app(story, engine):
    """Run the app on a story; prints where it was saved when you quit."""
    app = StorywheelApp(story, engine)
    message = app.run()
    if message:
        print("\n  " + str(message).replace("\n", "\n  "))
