"""The title bar. Textual's own Header grows to a tall version when it is clicked; ours stays one line in every mode.

Textual runs the click handler of every class in the MRO, so overriding `_on_click` is not enough (Header's still runs and
toggles `-tall`): the handler takes the event and calls `prevent_default()`, which stops the base classes' handlers.
"""
from textual.widgets import Header


class QuietHeader(Header):
    def _on_click(self, event):
        event.prevent_default()

    def watch_tall(self, tall):
        self.remove_class("-tall")
