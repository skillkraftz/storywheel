"""The title bar. Textual's own Header grows to a tall version when it is clicked; ours stays one line in every mode."""
from textual.widgets import Header


class QuietHeader(Header):
    def _on_click(self):
        pass

    def watch_tall(self, tall):
        self.remove_class("-tall")
