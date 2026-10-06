"""The story form: format, structure, genres and target length, chosen from lists (nothing typed but the title and a number).

    StoryFormScreen(title, values, new=True, has_writing=False)

`values` is {"title", "format", "structure", "genres", "target"}; the screen returns the same dict (or None when cancelled). The format
row offers the four formats (formats.FORMATS); the structure row only the structures that fit the format (and, for a story, "None");
the genres row is a multiple choice; the target is a number in words for prose and pages for a script. Changing the format moves the
structure and target to ones that fit. Used by the Builder's + Story and its "Format, structure, genres…" (both new and existing stories).
"""
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from . import formats, paths, structures

NO_STRUCTURE = "None: a blank outline"


def genre_names():
    """Every genre the generator knows (the built-in profiles and your own genres.json), in the file's order."""
    from .library import DATA, _read_profiles
    names = list(_read_profiles(DATA / "genres.json")[0])
    mine = paths.HOME / "genres.json"
    if mine.exists():
        names += [n for n in _read_profiles(mine)[0] if n not in names]
    return names


def structure_choices(fmt, allow_none=True):
    out = [(f"{s.label}: {s.blurb}", s.label) for s in formats.structures_for(fmt)]
    return ([(NO_STRUCTURE, "")] if allow_none else []) + out


class StoryFormScreen(ModalScreen):
    """A story's format, structure, genres and target, each from a picker."""
    BINDINGS = [Binding("escape", "cancel", "Cancel"), Binding("ctrl+s", "save", "Save", show=False)]
    DEFAULT_CSS = """
    StoryFormScreen { align: center middle; }
    StoryFormScreen > Vertical { width: 84; height: auto; max-height: 90%; border: round $accent; background: $surface; padding: 1 2; }
    StoryFormScreen Label { margin-top: 1; color: $text-muted; }
    StoryFormScreen #rows { height: auto; max-height: 8; }
    StoryFormScreen #note { color: $warning; height: auto; }
    StoryFormScreen #error { color: $error; height: auto; }
    StoryFormScreen Horizontal { height: 1; margin-top: 1; }
    StoryFormScreen #dlg Button { height: 1 !important; border: none !important; min-width: 10; margin-right: 2; }
    """
    ROWS = ("format", "structure", "genres")

    def __init__(self, heading, values, new=True, has_writing=False):
        super().__init__()
        self.heading, self.new, self.has_writing = heading, new, has_writing
        v = dict(values or {})
        self.fmt = v.get("format") if formats.known(v.get("format")) else formats.global_default()
        self.original_fmt = self.fmt
        self.structure = v.get("structure") or ""
        self.genres = [g for g in (v.get("genres") or []) if g]
        target = v.get("target")
        self.target = int(target) if str(target or "").isdigit() else formats.get(self.fmt).target
        self.title_value = v.get("title") or ""

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(self.heading, markup=False)
            yield Label("Title")
            yield Input(self.title_value, id="title", placeholder="the story's title")
            yield Label("Enter or click a line to choose")
            yield OptionList(id="rows")
            yield Label(self._target_label(), id="target-label")
            yield Input(str(self.target), id="target", type="integer")
            yield Static("", id="note")
            yield Static("", id="error")
            with Horizontal():
                yield Button("Create" if self.new else "Save", id="save", variant="success")
                yield Button("Cancel", id="cancel")
            yield Static("tab: next box     ctrl+s: save     esc: cancel", markup=False)

    def on_mount(self):
        for b in self.query(Button):
            b.can_focus = True
        self.refill()
        self.query_one("#title", Input).focus()

    # --- what is shown --------------------------------------------------------------------------------------------------------

    def _target_label(self):
        unit = formats.get(self.fmt).unit
        return f"Target length in {unit} (the Writer's status line" + (" and the flip test)" if unit == "pages" else ")")

    def refill(self):
        lst = self.query_one("#rows", OptionList)
        keep = lst.highlighted
        shape = structures.find(self.structure)
        rows = {"format": formats.get(self.fmt).label,
                "structure": shape.label if shape else NO_STRUCTURE,
                "genres": ", ".join(self.genres) if self.genres else "none chosen"}
        lst.clear_options()
        for key in self.ROWS:
            t = Text()
            t.append(f"{key.capitalize():<10} ", style="bold")
            t.append(rows[key])
            lst.add_option(Option(t, id=key))
        lst.highlighted = keep if keep is not None else 0
        self.query_one("#target-label", Label).update(self._target_label())
        self.query_one("#note", Static).update(self.format_warning())

    def format_warning(self):
        """What changing the format does to a story that already has writing in it."""
        if self.new or not self.has_writing:
            return ""
        before, after = formats.is_script(self.original_fmt), formats.is_script(self.fmt)
        if before == after:
            return ""
        if after:
            return ("This story already has prose. As a screenplay the Writer opens manuscript/script.fountain (started empty, or from the "
                    "outline with P); your prose files stay where they are, untouched, and come back if you change the format back.")
        return ("This story already has a script. As prose the Writer opens the manuscript files instead; script.fountain stays where it is, "
                "untouched, and comes back if you change the format back.")

    # --- choosing ------------------------------------------------------------------------------------------------------------

    def on_option_list_option_selected(self, event):
        if event.option_list.id != "rows":
            return
        from .tui import ChoiceScreen
        key = event.option.id
        if key == "format":
            self.app.push_screen(ChoiceScreen("Format", formats.choices()), self._format_chosen)
        elif key == "structure":
            self.app.push_screen(ChoiceScreen(f"Structure ({formats.get(self.fmt).label})", structure_choices(self.fmt, True)),
                                 self._structure_chosen)
        elif key == "genres":
            self.app.push_screen(ChoiceScreen("Genres (space or click toggles; d finishes)", [(g, g) for g in genre_names()], True,
                                              self.genres), self._genres_chosen)

    def _format_chosen(self, key):
        if key is None or key == self.fmt:
            return
        old = formats.get(self.fmt)
        self.fmt = key
        shape = structures.find(self.structure)
        if shape is not None and not formats.fits(shape, key):
            fit = formats.default_structure(key)
            self.structure = fit.label if fit is not None and formats.is_script(key) else ""
        elif shape is None and formats.is_script(key):
            fit = formats.default_structure(key)
            self.structure = fit.label if fit is not None else ""
        box = self.query_one("#target", Input)
        if old.unit != formats.get(key).unit or str(box.value).strip() in ("", str(old.target)):
            box.value = str(formats.get(key).target)                     # (a new unit, or the old default: the new format's usual length)
        self.refill()

    def _structure_chosen(self, label):
        if label is None:
            return
        self.structure = label
        self.refill()

    def _genres_chosen(self, chosen):
        if chosen is None:
            return
        order = genre_names()
        self.genres = sorted(chosen, key=lambda g: order.index(g) if g in order else len(order))
        self.refill()

    # --- done ----------------------------------------------------------------------------------------------------------------

    def values(self):
        return {"title": self.query_one("#title", Input).value.strip(), "format": self.fmt, "structure": self.structure,
                "genres": list(self.genres), "target": formats.parse_target(self.query_one("#target", Input).value)}

    def action_save(self):
        v = self.values()
        problems = []
        if not v["title"]:
            problems.append("A title, please.")
        if v["target"] is None or (formats.get(self.fmt).unit == "pages" and v["target"] < 1):
            problems.append(f"The target is a whole number of {formats.get(self.fmt).unit}.")
        if problems:
            self.query_one("#error", Static).update(" ".join(problems))
            return
        self.dismiss(v)

    def action_cancel(self):
        self.dismiss(None)

    def on_input_submitted(self, event):
        if event.input.id == "title":
            self.query_one("#rows", OptionList).focus()
        else:
            self.action_save()

    def on_button_pressed(self, event):
        if event.button.id == "save":
            self.action_save()
        else:
            self.action_cancel()
