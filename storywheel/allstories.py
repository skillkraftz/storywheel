"""The list of every story in the library, across all universes (the Builder's L; also `storywheel stories`).

    AllStoriesScreen(status=None, fmt=None)   returns ("open" | "write", universe slug, story slug), or None when closed

Columns: title, universe, format, status, size (words, or pages for a script) and when it was last edited, newest first. s steps through the
status filter and f through the format filter; Enter opens the story in the Builder, w in the Writer. The rows come from shelf.py, which
remembers each story's row until its files change, so reopening the list parses nothing."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Static

from . import formats, shelf, vault

STATUS_STEPS = (None,) + vault.STATUSES
FORMAT_STEPS = (None,) + tuple(f.key for f in formats.FORMATS)


class AllStoriesScreen(ModalScreen):
    BINDINGS = [Binding("escape,q", "close", "Close"), Binding("w", "write", "Write"), Binding("s", "cycle_status", "Status filter"),
                Binding("f", "cycle_format", "Format filter")]
    DEFAULT_CSS = """
    AllStoriesScreen { align: center middle; }
    AllStoriesScreen > Vertical { width: 96%; height: 92%; border: round $accent; background: $surface; padding: 0 1; }
    AllStoriesScreen #all-head { height: 1; color: $accent; text-style: bold; }
    AllStoriesScreen #all-table { height: 1fr; }
    AllStoriesScreen #all-keys { height: 1; color: $text-muted; }
    """

    def __init__(self, status=None, fmt=None):
        super().__init__()
        self.status, self.fmt = status, fmt
        self.found = []

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("", id="all-head", markup=False)
            yield DataTable(id="all-table", cursor_type="row", zebra_stripes=True)
            yield Static("Enter: open in the Builder    w: write    s: status filter    f: format filter    q or esc: close", id="all-keys",
                         markup=False)

    def on_mount(self):
        table = self.query_one("#all-table", DataTable)
        for label, width in (("Title", 34), ("Universe", 20), ("Format", 13), ("Status", 9), ("Size", 13), ("Edited", 16)):
            table.add_column(label, width=width)
        self.refill()
        table.focus()

    def refill(self):
        table = self.query_one("#all-table", DataTable)
        keep = table.cursor_row if table.row_count else 0
        table.clear()
        self.found = shelf.rows(self.status, self.fmt)
        for r in self.found:
            table.add_row(r["title"], r["universe_name"], r["format_label"], r["status"], r["size"], shelf.edited_text(r["edited"]),
                          key=f"{r['universe']}/{r['slug']}")
        if self.found:
            table.move_cursor(row=min(keep, len(self.found) - 1))
        shown = [f"status {self.status}" if self.status else "", f"format {formats.get(self.fmt).short.lower()}" if self.fmt else ""]
        shown = ", ".join(x for x in shown if x)
        n = len(self.found)
        self.query_one("#all-head", Static).update(
            f"All stories: {n} {'story' if n == 1 else 'stories'}" + (f" ({shown})" if shown else "") + ", newest edit first"
            + ("" if self.found else "  (none match)"))

    def current(self):
        table = self.query_one("#all-table", DataTable)
        if not self.found or table.cursor_row is None or table.cursor_row >= len(self.found):
            return None
        return self.found[table.cursor_row]

    def _go(self, what, row=None):
        row = row or self.current()
        if row is not None:
            self.dismiss((what, row["universe"], row["slug"]))

    def action_open(self):
        self._go("open")

    def action_write(self):
        self._go("write")

    def on_data_table_row_selected(self, event):
        event.stop()
        row = next((r for r in self.found if f"{r['universe']}/{r['slug']}" == event.row_key.value), None)
        self._go("open", row)

    def action_cycle_status(self):
        self.status = STATUS_STEPS[(STATUS_STEPS.index(self.status) + 1) % len(STATUS_STEPS)]
        self.refill()

    def action_cycle_format(self):
        self.fmt = FORMAT_STEPS[(FORMAT_STEPS.index(self.fmt) + 1) % len(FORMAT_STEPS)]
        self.refill()

    def action_close(self):
        self.dismiss(None)
