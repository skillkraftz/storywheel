"""A list that can hold hundreds of thousands of rows without building them: only the rows on screen (plus a page either side) are
ever fetched and rendered.

    lst = VirtualList(id="words")
    lst.set_source(count, fetch, render)
      count            how many rows there are
      fetch(start, n)  the rows start..start+n-1 (a list; fewer at the end)
      render(row, selected, width) -> rich Text for one line

Keys: up, down, page up, page down, home, end, enter; click selects, double-click (or Enter) activates; the wheel scrolls.
Posts `VirtualList.Highlighted(index)` when the cursor moves and `VirtualList.Selected(index)` on Enter or a double click."""
from collections import OrderedDict

from rich.segment import Segment
from rich.text import Text
from textual import events
from textual.binding import Binding
from textual.geometry import Size
from textual.message import Message
from textual.scroll_view import ScrollView
from textual.strip import Strip

PAGE = 64                 # rows fetched at a time
KEEP_PAGES = 12           # pages kept in memory


class VirtualList(ScrollView, can_focus=True):
    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False), Binding("down", "cursor_down", "Down", show=False),
        Binding("pageup", "page_up", "Page up", show=False), Binding("pagedown", "page_down", "Page down", show=False),
        Binding("home", "first", "First", show=False), Binding("end", "last", "Last", show=False),
        Binding("enter", "select", "Open", show=False),
    ]
    COMPONENT_CLASSES = {"vlist--cursor", "vlist--row"}
    DEFAULT_CSS = """
    VirtualList { height: 1fr; border: none; scrollbar-gutter: stable; }
    VirtualList > .vlist--cursor { background: $accent 40%; }
    VirtualList:focus > .vlist--cursor { background: $accent 60%; }
    """

    class Highlighted(Message):
        def __init__(self, sender, index):
            super().__init__()
            self.list, self.index = sender, index

    class Selected(Message):
        def __init__(self, sender, index):
            super().__init__()
            self.list, self.index = sender, index

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.count = 0
        self.cursor = None
        self._fetch = lambda start, n: []
        self._render = lambda row, selected, width: Text(str(row))
        self._pages = OrderedDict()
        self.fetches = 0                                 # (for tests) how many times rows were fetched

    # --- data --------------------------------------------------------------------------------------------------------------------------

    def set_source(self, count, fetch, render, keep_cursor=False):
        self.count, self._fetch, self._render = count, fetch, render
        self._pages.clear()
        old = self.cursor
        self.cursor = (min(old, count - 1) if (keep_cursor and old is not None and count) else (0 if count else None))
        self._resize()
        self.scroll_to(y=0, animate=False) if not keep_cursor else self._show_cursor()
        self.refresh()
        self._announce()

    def _resize(self):
        self.virtual_size = Size(max(1, self.size.width), self.count)

    def on_resize(self, event):
        self._resize()

    def row(self, index):
        """The data row at `index` (fetched with its page)."""
        if index < 0 or index >= self.count:
            return None
        page = index // PAGE
        if page not in self._pages:
            self.fetches += 1
            rows = self._fetch(page * PAGE, PAGE)
            self._pages[page] = rows
            while len(self._pages) > KEEP_PAGES:
                self._pages.popitem(last=False)
        else:
            self._pages.move_to_end(page)
        rows = self._pages[page]
        i = index - page * PAGE
        return rows[i] if i < len(rows) else None

    def current(self):
        return None if self.cursor is None else self.row(self.cursor)

    # --- drawing -----------------------------------------------------------------------------------------------------------------------

    def render_line(self, y):
        scroll_x, scroll_y = self.scroll_offset
        index = scroll_y + y
        width = self.size.width
        if index >= self.count:
            return Strip.blank(width, self.rich_style)
        row = self.row(index)
        selected = index == self.cursor
        style = self.get_component_rich_style("vlist--cursor") if selected else self.rich_style
        text = self._render(row, selected, width) if row is not None else Text("")
        text = text.copy()
        text.truncate(width, overflow="ellipsis", pad=True)
        segments = [Segment(seg.text, style + seg.style if seg.style else style) for seg in text.render(self.app.console)
                    if seg.text != "\n"]
        return Strip(segments).adjust_cell_length(width, style)

    # --- moving ------------------------------------------------------------------------------------------------------------------------

    def _announce(self):
        if self.cursor is not None:
            self.post_message(self.Highlighted(self, self.cursor))

    def move_to(self, index):
        if not self.count:
            return
        self.cursor = max(0, min(self.count - 1, index))
        self._show_cursor()
        self.refresh()
        self._announce()

    def _show_cursor(self):
        if self.cursor is None:
            return
        top, height = self.scroll_offset.y, max(1, self.size.height)
        if self.cursor < top:
            self.scroll_to(y=self.cursor, animate=False)
        elif self.cursor >= top + height:
            self.scroll_to(y=self.cursor - height + 1, animate=False)

    def action_cursor_up(self):
        self.move_to((self.cursor or 0) - 1)

    def action_cursor_down(self):
        self.move_to((self.cursor or 0) + 1)

    def action_page_up(self):
        self.move_to((self.cursor or 0) - max(1, self.size.height - 1))

    def action_page_down(self):
        self.move_to((self.cursor or 0) + max(1, self.size.height - 1))

    def action_first(self):
        self.move_to(0)

    def action_last(self):
        self.move_to(self.count - 1)

    def action_select(self):
        if self.cursor is not None:
            self.post_message(self.Selected(self, self.cursor))

    def on_click(self, event: events.Click):
        index = self.scroll_offset.y + event.y
        if 0 <= index < self.count:
            self.move_to(index)
            if event.chain >= 2:
                self.post_message(self.Selected(self, index))
        self.focus()
