"""The Lookup dialog (F5 in every mode): type a word, see its meanings, similar words and opposites. Offline."""
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from . import dictionary

CREDIT = "Meanings: Open English WordNet (CC BY 4.0). Similar words: also the Moby Thesaurus (public domain)."


class LookupScreen(ModalScreen):
    BINDINGS = [Binding("escape", "close", "Close")]
    DEFAULT_CSS = """
    LookupScreen { align: center middle; }
    LookupScreen #dlg { width: 100; max-width: 95%; height: 85%; border: round $accent; background: $surface; padding: 0 1; }
    LookupScreen Input { margin: 1 0 0 0; }
    LookupScreen #card { height: 1fr; margin-top: 1; }
    LookupScreen #credit { color: $text-muted; height: 1; }
    LookupScreen #hint { color: $text-muted; height: 1; }
    """

    def __init__(self, word=""):
        super().__init__()
        self.word = word

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static("Look up a word   (Enter looks it up, Esc closes; try a plural, past tense or a misspelling)", id="hint", markup=False)
            yield Input(self.word, placeholder="a word", id="word")
            with VerticalScroll(id="card"):
                yield Static("", id="result", markup=False)
            yield Static(CREDIT, id="credit", markup=False)

    def on_mount(self):
        self.query_one("#word", Input).focus()
        if self.word:
            self.show(self.word)
        elif not dictionary.installed():
            self.query_one("#result", Static).update(dictionary.NOT_INSTALLED)

    def on_input_submitted(self, event):
        self.show(event.value)

    def show(self, word):
        out = self.query_one("#result", Static)
        if not word.strip():
            out.update("")
            return
        try:
            result = dictionary.lookup(word)
        except dictionary.DictionaryMissing as e:
            out.update(str(e))
            return
        out.update(self.render_result(result))

    @staticmethod
    def render_result(result):
        lines = dictionary.card_lines(result, width=90)
        text = Text()
        for i, line in enumerate(lines):
            style = "bold" if (i == 0 or line in ("noun", "verb", "adjective", "adverb") or line in ("Similar:", "Opposite:")) else ""
            if line and set(line) == {"="}:
                continue
            text.append(line + "\n", style=style)
        return text

    def action_close(self):
        self.dismiss(None)
