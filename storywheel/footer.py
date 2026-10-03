"""A footer that fits: when the terminal is too narrow for every key, the less important ones are left out (they are in the help screen)
instead of being cut off half-way. What always stays: the F1-F5 modes, q Back, Q Quit and ? Help. The order of a screen's BINDINGS is the order of
importance, so the entries at the end go first."""
from textual.widgets import Footer
from textual.widgets._footer import FooterKey

ESSENTIAL_ACTIONS = ("back_mode", "quit_program", "help", "mode", "noop_mode")


def key_width(key):
    """The room a footer entry takes: the key, the description, and the padding around them."""
    compact = key.has_class("-compact") if hasattr(key, "has_class") else False
    return len(key.key_display) + (0 if compact else 2) + (1 if key.description else 0) + len(key.description) + 1


def choose(entries, width):
    """Which entries to show: (action, text width) pairs in order; drop optional ones from the end until the rest fit. Returns indexes kept."""
    keep = list(range(len(entries)))

    def total():
        return sum(entries[i][1] for i in keep)

    for i in reversed(range(len(entries))):
        if total() <= width:
            break
        action = entries[i][0]
        if not any(action.startswith(a) for a in ESSENTIAL_ACTIONS):
            keep.remove(i)
    return keep


class FitFooter(Footer):
    _last_width = 0

    def compose(self):
        widgets = list(super().compose())
        keys = [w for w in widgets if isinstance(w, FooterKey)]
        width = self.size.width or self.screen.size.width or self.app.size.width
        keep = set(choose([(k.action, key_width(k)) for k in keys], width))
        shown = [w for w in widgets if not isinstance(w, FooterKey) or keys.index(w) in keep]
        self.styles.grid_size_columns = max(1, sum(1 for w in shown if isinstance(w, FooterKey)))
        self._last_width = width
        yield from shown

    def on_resize(self, event):
        if event.size.width != self._last_width and self.is_attached:
            self.call_after_refresh(self.recompose)
