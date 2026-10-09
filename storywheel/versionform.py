"""The New version form: the story form (title, format, target), prefilled from the story, plus a checklist of what to copy.

    VersionFormScreen(story, values)    returns {"title", "format", "target", "copy": [options]} or None when cancelled

Characters, places, things, groups and notes belong to the universe, so every version already shares them; the dialog says so. What is
ticked is copied once, and after that the versions are separate."""
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from . import formats, versions
from .storyform import StoryFormScreen

EXPLAIN = ("A version is another story in this universe, in another format, starting from the same outline. Its characters, places, things, "
           "groups and notes are the universe's, so they are already shared. Whatever you tick below is COPIED once; after that the two "
           "stories are separate: editing one changes nothing in the other.")


def manuscript_label(src_fmt, dst_fmt):
    """The checklist line for the manuscript, saying what the copy will be."""
    base = versions.COPY_LABELS["manuscript"]
    a, b = formats.is_script(src_fmt), formats.is_script(dst_fmt)
    how = {(False, False): "files copied as they are", (False, True): "prose written into the script as action",
           (True, False): "action and dialogue as prose paragraphs", (True, True): "script copied as it is"}[(a, b)]
    return f"{base}: {how}"


def next_format(story):
    """The format a new version starts as: the first of the four the family doesn't have yet (else the story's own)."""
    have = {formats.of_story(s) for s in versions.versions(story)}
    return next((f.key for f in sorted(formats.FORMATS, key=lambda f: f.key == "flash") if f.key not in have), formats.of_story(story))


class VersionFormScreen(StoryFormScreen):
    """StoryFormScreen with only the format row, and a checklist of what to copy."""
    ROWS = ("format",)
    DEFAULT_CSS = """
    VersionFormScreen #explain { color: $text-muted; height: auto; }
    VersionFormScreen #rows { max-height: 3; }
    VersionFormScreen #copy { height: auto; max-height: 8; }
    """

    def __init__(self, story, values=None):
        v = dict(values or {})
        v.setdefault("title", story.title)
        v.setdefault("format", next_format(story))
        v.setdefault("structure", "")
        super().__init__(f"New version of “{story.title}”", v, new=True)
        self.story = story
        self.source_fmt = formats.of_story(story)
        self.copy = list(v.get("copy") or versions.DEFAULT_COPY)

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(self.heading, markup=False)
            yield Static(EXPLAIN, id="explain", markup=False)
            yield Label("Title")
            yield Input(self.title_value, id="title", placeholder="the version's title")
            yield Label("Format (enter or click)")
            yield OptionList(id="rows")
            yield Label("Copy from this story (enter or click toggles)")
            yield OptionList(id="copy")
            yield Label(self._target_label(), id="target-label")
            yield Input(str(self.target), id="target", type="integer")
            yield Static("", id="note")
            yield Static("", id="error")
            with Horizontal():
                yield Button("Make version", id="save", variant="success")
                yield Button("Cancel", id="cancel")
            yield Static("tab: next box     ctrl+s: make it     esc: cancel", markup=False)

    def refill(self):
        super().refill()
        lst = self.query_one("#copy", OptionList)
        keep = lst.highlighted
        lst.clear_options()
        for key in versions.COPY_OPTIONS:
            on = key in self.copy
            t = Text()
            t.append("[x] " if on else "[ ] ", style="green" if on else "dim")
            t.append(manuscript_label(self.source_fmt, self.fmt) if key == "manuscript" else versions.COPY_LABELS[key])
            lst.add_option(Option(t, id=key))
        lst.highlighted = keep if keep is not None else 0

    def format_warning(self):
        return "A manuscript copy is always a rough start: expect to rewrite it." if "manuscript" in self.copy and \
            formats.is_script(self.source_fmt) != formats.is_script(self.fmt) else ""

    def on_option_list_option_selected(self, event):
        if event.option_list.id == "copy":
            key = event.option.id
            self.copy = [c for c in self.copy if c != key] if key in self.copy else self.copy + [key]
            self.refill()
            return
        super().on_option_list_option_selected(event)

    def values(self):
        return {"title": self.query_one("#title", Input).value.strip(), "format": self.fmt,
                "target": formats.parse_target(self.query_one("#target", Input).value),
                "copy": [c for c in versions.COPY_OPTIONS if c in self.copy]}
