"""The Words mode (F5): the language tools, as a mode of their own. Offline.

    Lookup       meanings, every similar word, every opposite, wider and narrower words, parts, related forms; Enter or a click on a
                 word looks it up; back and forward remember where you were
    Vocabulary   words worth learning (not everyday, not obscure), a fresh batch at a time; mark them Known or Learning
    My words     the words you are learning, with their meanings; flashcards
    Overused     a story's most frequent words and words repeated close together, and where they are

On any word in Lookup or My words, "Add to this universe's word list" puts it on the universe's own list for a slot (job, thing, place...)
so the Wheel and Builder roll with it. Opened from the Writer (F5), Words carries the word under the cursor; "Use in Writer" goes back
and replaces it with the one you picked, in the same form (running -> sprinting).
"""
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, OptionList, Select, Static, TabbedContent, TabPane
from textual.widgets.option_list import Option

from . import dictionary, inflect, learn, overused, vault, wordbank
from . import appearance, navigation, tools
from .footer import FitFooter
from .header import QuietHeader

MODE_KEYS = "F1 Wheel   F2 Builder   F3 Writer   F4 Settings   F5 Words"

HELP = f"""\
[b]Words[/b]        {MODE_KEYS}

[b]Lookup[/b]  type a word and press Enter. Plurals, past tenses and misspellings work.
  [b]Enter[/b] or a click on a word looks it up       [b]b[/b] / [b]n[/b]  back / forward through the words you looked up
  [b]/[/b]  filter the lists                          [b]c[/b]  copy the word       [b]a[/b]  Learn this word (it goes to My words)
  [b]w[/b]  Use in this universe's stories: pick the slot (job, thing, place...) and the Wheel and Builder will use the word
  [b]u[/b]  Use in Writer: go back to the Writer and replace the word you were on (only when you came from the Writer)

[b]Vocabulary[/b]  words worth learning: not everyday, not obscure, each with a one-line meaning. Pick how rare, the part of
  speech and the subject, then [b]New batch[/b] (it never repeats a word you have seen; [b]Start over[/b] forgets what you have seen).
  [b]Enter[/b] opens the full entry in Lookup; [b]l[/b] marks a word ★ Learning (it goes to My words), [b]k[/b] marks it ✓ Known
  (never offered again). Difficulty: uncommon (like "lantern"), rare (like "serendipity"), very rare (like "gallivant").

[b]My words[/b]  the words you are learning, with meanings. [b]Enter[/b] looks one up, [b]k[/b] marks it Known (removes it),
  [b]d[/b] removes it, [b]w[/b] Use in this universe's stories, [b]f[/b] flashcards (the word first; space shows the meaning). You can type
  a word of your own to learn.

[b]Universe words[/b]  the words you put on this universe's lists with [b]w[/b]: see them by slot and remove any ([b]d[/b]).

[b]Overused[/b]  the most frequent words of a story (everyday words left out) and words repeated close together. Enter on a
  place opens the Writer there.

[b]q[/b] goes back to where you were; [b]Q[/b] Quit storywheel (asks first); F1-F5 are the modes. Meanings: Open English WordNet (CC BY 4.0); similar words also the Moby Thesaurus;
word frequencies: wordfreq (data CC BY-SA 4.0).
"""


class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape,question_mark,q", "close", "Close")]
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    HelpScreen > Static { width: 100; height: auto; border: round $accent; background: $surface; padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Static(HELP)

    def action_close(self):
        self.dismiss(None)


# --- the rows (pure: used by the screen and the tests) -------------------------------------------------------------------------

def parse_id(oid):
    """(kind, word, pos) of a row id: 'w:word|pos\x1f7', 'v:word\x1f7' or 'b:word'."""
    kind, body = oid[:1], oid[2:].split("\x1f")[0]
    word, _, pos = body.partition("|")
    return kind, word, pos or None


def _opt(text, id_=None, disabled=False, style=""):
    return Option(Text(text, style=style), id=id_, disabled=disabled or id_ is None)


def lookup_rows(result, filter_text=""):
    """[(text, id or None, style)] for a lookup result. A row with an id is a word you can look up (id = 'w:<word>|<pos>')."""
    f = filter_text.strip().lower()
    rows = []

    def heading(text):
        rows.append((text, None, "bold"))

    def info(text):
        rows.append((text, None, "dim"))

    def word(w, pos="", note=""):
        if not f or f in w.lower():
            rows.append((f"    {w}" + (f"   ({note})" if note else ""), f"w:{w}|{pos}\x1f{len(rows)}", ""))      # (the same word can be in several lists: ids must differ)
            return True
        return False

    if not result["found"]:
        heading(f"No entry for '{result['word'] or result['query']}'.")
        if result["suggestions"]:
            info("Did you mean (Enter looks it up):")
            for s in result["suggestions"]:
                word(s)
        return rows
    for e in result["entries"]:
        heading(e["word"] + (f"   (form of “{e['form_of']}”)" if e["form_of"] else ""))
        for part in e["parts"]:
            heading(f"  {part['pos']}")
            for i, s in enumerate(part["senses"], 1):
                info(f"  {i}. {s['definition']}")
                if s["examples"]:
                    info(f"       “{s['examples'][0]}”")
                if s["synonyms"]:
                    info("     similar words:")
                    for w in s["synonyms"]:
                        word(w, part["pos"])
                for label, key in (("a kind of (wider)", "kind_of"), ("types of it (narrower)", "types_of"), ("parts of it", "parts"),
                                   ("it is part of", "part_of")):
                    if s[key]:
                        info(f"     {label}:")
                        for w in s[key]:
                            word(w)
        if e["wide_synonyms"]:
            heading(f"  More similar words ({len(e['wide_synonyms'])})")
            for w in e["wide_synonyms"]:
                word(w)
        if e["antonyms"]:
            heading("  Opposite words")
            for w in e["antonyms"]:
                word(w)
        if e["indirect_antonyms"]:
            heading("  Opposite words, indirect (opposites of similar words)")
            for a in e["indirect_antonyms"]:
                word(a["word"], "", a["via"])
        for kind, words in e["related_forms"].items():
            heading(f"  Related forms ({kind})")
            for w in words:
                word(w)
    return rows


# --- the screen -------------------------------------------------------------------------------------------------------------------

class SlotScreen(ModalScreen):
    """Pick the slot a word goes into on the universe's own list: what kind of thing it is in a story."""
    BINDINGS = [Binding("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    SlotScreen { align: center middle; }
    SlotScreen #dlg { width: 70; height: auto; border: round $accent; background: $surface; padding: 1 2; }
    SlotScreen Button { margin-right: 2; }
    SlotScreen #hint { color: $text-muted; }
    """
    HINTS = {"job": "a job or trade", "thing": "an object", "place": "a town or region", "landmark": "a feature of a place",
             "someone": "a kind of person", "disaster": "a trouble", "title_noun": "a word for titles"}

    def __init__(self, word, universe_name):
        super().__init__()
        self.word, self.universe_name = word, universe_name

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(f"Add “{self.word}” to {self.universe_name}'s word list", markup=False)
            yield Static("Which slot does it fit? The Wheel and Builder will use it when they need that kind of thing in this universe.", id="hint", markup=False)
            yield Select([(f"{s}" + (f"  ({self.HINTS[s]})" if s in self.HINTS else ""), s) for s in wordbank.slots()],
                         value="thing" if "thing" in wordbank.slots() else wordbank.slots()[0], id="slot", allow_blank=False)
            with Horizontal():
                yield Button("Add", id="ok", variant="primary")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event):
        event.stop()
        self.dismiss(self.query_one("#slot", Select).value if event.button.id == "ok" else None)

    def action_cancel(self):
        self.dismiss(None)


class FlashcardScreen(ModalScreen):
    """The word first; Space shows the meaning; then Got it (k: Known, leaves the list) or Again (n: next)."""
    BINDINGS = [Binding("escape,q", "close", "Close"), Binding("space,enter", "reveal", "Show meaning"),
                Binding("k", "known", "Got it: Known"), Binding("n,right", "next", "Again / next")]
    DEFAULT_CSS = """
    FlashcardScreen { align: center middle; }
    FlashcardScreen #card { width: 80; height: 14; border: round $accent; background: $surface; padding: 1 3; content-align: center middle; }
    FlashcardScreen #keys { width: 80; color: $text-muted; text-align: center; }
    """

    def __init__(self, entries):
        super().__init__()
        import random
        self.entries = entries
        random.shuffle(self.entries)
        self.i = 0
        self.shown = False
        self.known = []

    def compose(self) -> ComposeResult:
        yield Static("", id="card", markup=False)
        yield Static("Space: show the meaning    k: I know it (take it off the list)    n: again later / next    Esc: stop", id="keys")

    def on_mount(self):
        self.draw()

    def draw(self):
        e = self.entries[self.i]
        text = f"{e['word']}\n\n" + (f"{e.get('pos') or ''}\n{e.get('definition') or e.get('note') or '(no meaning on file)'}" if self.shown else "")
        self.query_one("#card", Static).update(text + f"\n\n{self.i + 1} / {len(self.entries)}")

    def action_reveal(self):
        self.shown = True
        self.draw()

    def action_next(self):
        self.i += 1
        self.shown = False
        if self.i >= len(self.entries):
            return self.action_close()
        self.draw()

    def action_known(self):
        self.known.append(self.entries[self.i]["word"])
        self.action_next()

    def action_close(self):
        self.dismiss(self.known)


class WordsScreen(Screen):
    BINDINGS = [
        *navigation.mode_bindings("words"),
        Binding("question_mark", "help", "Help", key_display="?"),
        navigation.back_binding(),
        navigation.quit_binding(),
        Binding("b", "back", "Back a word", show=False),
        Binding("n", "forward", "Forward", show=False),
        Binding("slash", "filter", "Filter", show=False),
        Binding("u", "use", "Use in Writer", show=False),
        Binding("a", "add", "Learn this word", show=False),
        Binding("c", "copy", "Copy", show=False),
        Binding("w", "wordlist", "Use in this universe's stories", show=False),
        Binding("k", "known", "Known", show=False),
        Binding("l", "learning", "Learning", show=False),
        Binding("d", "remove", "Remove", show=False),
        Binding("f", "flashcards", "Flashcards", show=False),
    ]
    DEFAULT_CSS = """
    WordsScreen TabbedContent { height: 1fr; }
    WordsScreen TabPane { height: 1fr; }
    WordsScreen #status { height: 1; padding: 0 1; background: $boost; }
    WordsScreen .bar { height: 1; margin-bottom: 1; }
    WordsScreen .bar Input { width: 1fr; }
    WordsScreen Button, WordsScreen Button.-textual-compact:disabled, WordsScreen Button.-style-default:disabled,
    WordsScreen Button:disabled, WordsScreen Button:hover, WordsScreen Button:focus { height: 1 !important; border: none !important; border-top: none !important; border-bottom: none !important; }
    WordsScreen .bar Button { margin-left: 1; min-width: 12; }
    WordsScreen OptionList { height: 1fr; border: none; scrollbar-gutter: stable; }
    WordsScreen OptionList:focus { border: none; }
    WordsScreen TabPane { padding: 0 1; }
    WordsScreen .note { color: $text-muted; height: auto; }
    WordsScreen Select { width: 40; }
    WordsScreen #tools Button { min-width: 14; margin-right: 1; }
    """

    def __init__(self, app_ref, payload):
        super().__init__()
        self.b = app_ref
        self.payload = payload or {}
        self.history, self.pos = [], -1
        self.result = None
        self.rows = []
        self.filter = ""
        self.origin = None
        self.my = learn.MyWords()
        self.batch = []
        self.subject_options = [("Any subject", "any")]
        self.over = None
        self.universe = None
        self.story = None
        self.handover = self.payload.get("handover")          # {"word", "replace": {file, row, start, end, text}} from the Writer

    # --- layout -----------------------------------------------------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield QuietHeader()
        with TabbedContent(id="tabs"):
            with TabPane("Lookup", id="t-lookup"):
                with Horizontal(classes="bar"):
                    yield Input(placeholder="a word  (Enter looks it up)", id="word")
                    yield Button("Look up", id="go")
                    yield Button("◀ Back", id="back")
                    yield Button("Forward ▶", id="forward")
                with Horizontal(classes="bar"):
                    yield Input(placeholder="filter the words below", id="filter")
                yield OptionList(id="results")
                with Horizontal(id="tools", classes="bar"):
                    yield Button("Use in Writer", id="use")
                    yield Button("Learn this word", id="add")
                    yield Button("Use in this universe's stories", id="lookuplist")
                    yield Button("Copy", id="copy")
                yield Static("", id="usenote", classes="note", markup=False)
            with TabPane("Vocabulary", id="t-vocab"):
                with Horizontal(classes="bar"):
                    yield Select([(d, d) for d in learn.DIFFICULTY], value="any", id="difficulty", allow_blank=False)
                    yield Select([("Any part of speech", "any")] + [(p, p) for p in learn.POS], value="any", id="vpos", allow_blank=False)
                    yield Select([("Any subject", "any")], value="any", id="subject", allow_blank=False)
                    yield Button("New batch", id="newbatch")
                    yield Button("Start over", id="startover")
                yield Static("Words worth learning: not everyday, not obscure.   ★ Learning (in My words)   ✓ Known (never offered again)   "
                             "Enter opens the full entry; l = Learning, k = Known.", classes="note", markup=False)
                yield Static("How rare: uncommon (like “lantern”)   rare (like “serendipity”)   very rare (like “gallivant”)", classes="note", markup=False)
                yield OptionList(id="learn")
                with Horizontal(id="learntools", classes="bar"):
                    yield Button("Learning", id="learning")
                    yield Button("Known", id="known")
                    yield Button("Open in Lookup", id="openlookup")
            with TabPane("My words", id="t-mine"):
                yield Static("", id="minenote", classes="note")
                with Horizontal(classes="bar"):
                    yield Input(placeholder="a word you want to learn  (Enter adds it)", id="myword")
                    yield Button("Add", id="myadd")
                yield OptionList(id="mine")
                with Horizontal(id="minetools", classes="bar"):
                    yield Button("Flashcards", id="flash")
                    yield Button("Known", id="mineknown")
                    yield Button("Remove", id="remove")
                    yield Button("Use in this universe's stories", id="minelist")
            with TabPane("Universe words", id="t-uwords"):
                yield Static("", id="uwnote", classes="note")
                yield OptionList(id="uwords")
                with Horizontal(classes="bar"):
                    yield Button("Remove from the list", id="uwremove")
            with TabPane("Overused", id="t-over"):
                with Horizontal(classes="bar"):
                    yield Select([("(no story yet)", "none")], id="overstory", allow_blank=False)
                    yield Button("Analyze", id="analyze")
                yield Static("", id="oversummary", classes="note")
                yield OptionList(id="over")
                yield OptionList(id="occ")
        yield Static("", id="status", markup=False)
        yield FitFooter()

    def on_mount(self):
        for w in self.query("Input, Select, Button"):
            w.compact = True                                        # one-line boxes and buttons: more room for the words
        self.start()

    def on_screen_resume(self):
        self.app.title = "storywheel · Words"
        self.app.sub_title = "offline dictionary and thesaurus"
        self.b.remember()

    def enter(self, payload):
        """Words was kept alive while you were elsewhere. A word handed over from the Writer, or a different universe, starts it afresh
        (the lookup path, tabs and lists stay as they were otherwise)."""
        payload = payload or {}
        handed = payload.get("handover")
        old = self.universe.slug if self.universe else None
        new = payload.get("universe") or old
        if handed or new != old:
            self.payload = payload
            self.handover = handed
            self.start(keep_view=not handed)
        else:
            self.refresh_mine()
            self.refresh_uwords()
            self.refresh_buttons()

    def start(self, keep_view=False):
        self.app.title = "storywheel · Words"
        self.app.sub_title = "offline dictionary and thesaurus"
        self.universe = vault.get_universe(self.payload.get("universe")) if self.payload.get("universe") else None
        if self.universe is None and self.payload.get("story_ref"):
            self.universe = vault.get_universe(self.payload["story_ref"][0])
        if self.universe is not None:
            slug = self.payload.get("story")
            self.story = self.universe.story(slug) if slug else None
            if self.story is None and self.universe.stories():
                self.story = self.universe.stories()[0]
        self.setup_stories()
        self.setup_subjects()
        migrated = wordbank.migrate_banks(self.my)
        self.refresh_mine()
        self.refresh_uwords()
        if not dictionary.installed():
            self.say(dictionary.NOT_INSTALLED)
        elif migrated:
            self.say(f"Your old word banks ({migrated} words) are now in My words.")
        if self.handover and self.handover.get("word"):
            self.query_one(TabbedContent).active = "t-lookup"
            self.query_one("#word", Input).value = self.handover["word"]
            self.lookup(self.handover["word"], origin=True)
            self.query_one("#results", OptionList).focus()
        else:
            self.query_one("#word", Input).focus()
        self.refresh_buttons()
        self.b.remember()

    def say(self, message):
        self.query_one("#status", Static).update(message)

    def refresh_buttons(self):
        use = self.query_one("#use", Button)
        use.disabled = not (self.handover and self.handover.get("replace"))
        self.query_one("#usenote", Static).update(
            "" if not use.disabled else "“Use in Writer” is greyed out because you didn't come from the Writer: press F5 on a word in the Writer, "
            "pick a word here, then Use in Writer brings it back and replaces that word.")
        self.query_one("#back", Button).disabled = self.pos <= 0
        self.query_one("#forward", Button).disabled = self.pos >= len(self.history) - 1
        for b in self.query(Button):                                   # (a greyed-out button must stay one line high too)
            b.styles.border = ("none", "black")

    # --- Lookup ------------------------------------------------------------------------------------------------------------------

    def lookup(self, word, push=True, origin=False):
        word = (word or "").strip()
        if not word:
            return
        try:
            result = dictionary.lookup(word)
        except dictionary.DictionaryMissing as e:
            self.say(str(e))
            return
        self.result = result
        for note in dictionary.take_notes():
            self.say(note)
        if origin and self.handover:
            self.origin = {"text": self.handover["word"], "base": result.get("base"), "kind": result.get("form_kind")}
        if push:
            self.history = self.history[:self.pos + 1] + [word]
            self.pos = len(self.history) - 1
        self.query_one("#word", Input).value = word
        self.filter = ""
        self.query_one("#filter", Input).value = ""
        self.show_results()
        self.refresh_buttons()
        self.say(f"{word}: " + ("found." if result["found"] else "no entry."))

    def show_results(self, keep=False):
        lst = self.query_one("#results", OptionList)
        previous = lst.highlighted
        self.rows = lookup_rows(self.result, self.filter) if self.result else []
        lst.clear_options()
        lst.add_options([_opt(t, i, style=st) for t, i, st in self.rows])
        if keep and previous is not None:
            lst.highlighted = min(previous, max(0, len(self.rows) - 1))
        else:
            first = next((n for n, r in enumerate(self.rows) if r[1]), None)
            lst.highlighted = first

    def current_word(self):
        """(word, pos) of the highlighted word row in whichever list has the focus, or (None, None)."""
        lst = self.query_one("#results", OptionList)
        if lst.highlighted is not None:
            oid = lst.get_option_at_index(lst.highlighted).id
            if oid and oid.startswith("w:"):
                _k, w, pos = parse_id(oid)
                return w, pos
        return None, None

    def on_input_submitted(self, event):
        i = event.input.id
        if i == "word":
            self.lookup(event.value)
            self.query_one("#results", OptionList).focus()
        elif i == "myword":
            self.add_by_hand(event.value)

    def on_input_changed(self, event):
        if event.input.id == "filter":
            self.filter = event.value
            self.show_results()

    def on_option_list_option_selected(self, event):
        lst, oid = event.option_list.id, event.option.id
        if lst == "results" and oid and oid.startswith("w:"):
            self.lookup(parse_id(oid)[1])
        elif lst == "learn" and oid:
            self.open_in_lookup(self.batch[int(oid[2:])]["word"])
        elif lst == "mine" and oid:
            self.open_in_lookup(self.mine[int(oid[2:])]["word"])
        elif lst == "over" and oid:
            self.show_occurrences(oid)
        elif lst == "occ" and oid:
            self.open_in_writer(oid)

    def on_button_pressed(self, event):
        event.stop()
        {"go": lambda: self.lookup(self.query_one("#word", Input).value), "back": self.action_back, "forward": self.action_forward,
         "use": self.action_use, "add": self.action_add, "copy": self.action_copy, "lookuplist": self.action_wordlist,
         "newbatch": self.new_batch, "learning": lambda: self.mark("learning"), "known": lambda: self.mark("known"),
         "openlookup": lambda: self.batch_word() and self.open_in_lookup(self.batch_word()["word"]),
         "flash": self.action_flashcards, "mineknown": lambda: self.mark("known"), "remove": self.action_remove,
         "startover": self.start_over, "myadd": lambda: self.add_by_hand(self.query_one("#myword", Input).value),
         "uwremove": self.action_remove,
         "minelist": self.action_wordlist, "analyze": self.analyze}.get(event.button.id or "", lambda: None)()

    def action_back(self):
        if self.pos > 0:
            self.pos -= 1
            self.lookup(self.history[self.pos], push=False)
        else:
            self.say("That is the first word you looked up.")

    def action_forward(self):
        if self.pos < len(self.history) - 1:
            self.pos += 1
            self.lookup(self.history[self.pos], push=False)
        else:
            self.say("That is the last word you looked up.")

    def action_filter(self):
        self.query_one(TabbedContent).active = "t-lookup"
        self.query_one("#filter", Input).focus()

    def action_noop(self):
        self.say("You are in Words.")

    def action_help(self):
        self.app.push_screen(HelpScreen())

    def action_copy(self):
        w, _ = self.current_word()
        if not w:
            self.say("Move to a word first.")
            return
        from . import clipboard
        how = clipboard.copy(w, self.app)
        self.say(f"Copied “{w}”." if how else tools.missing("clipboard", f"The word is: {w}"))

    def action_add(self):
        """Add the highlighted Lookup word to My words, with its meaning."""
        w, pos = self.current_word()
        if not w:
            self.say("Move to a word first.")
            return
        entry = learn.fill_definition({"word": w, "pos": pos or "", "definition": ""})
        new = self.my.mark_learning(w, entry.get("pos") or "", entry.get("definition") or "")
        self.refresh_mine()
        self.say(f"“{w}” is in My words." if new else f"“{w}” is already in My words.")

    def open_in_lookup(self, word):
        self.query_one(TabbedContent).active = "t-lookup"
        self.lookup(word)
        self.query_one("#results", OptionList).focus()

    # --- Use in Writer -------------------------------------------------------------------------------------------------------------

    def replacement_for(self, word, pos):
        o = self.origin or {}
        text = o.get("text") or (self.handover or {}).get("word") or word
        try:
            db = dictionary.connect()
        except dictionary.DictionaryMissing:
            db = None
        pos_name = {"noun": "noun", "verb": "verb", "adjective": "adjective", "adverb": "adverb"}.get(pos or "")
        form = inflect.reinflect(text, o.get("base") or text, word, pos_name, db=db) if o.get("kind") not in (None, "base") else word
        return inflect.apply_case(text, form)

    def action_use(self):
        if not (self.handover and self.handover.get("replace")):
            self.say("Press F5 in the Writer, on a word, to use a word from here (it comes back and replaces that word).")
            return
        w, pos = self.current_word()
        if not w:
            self.say("Move to the word you want, then press u.")
            return
        replace = dict(self.handover["replace"], new=self.replacement_for(w, pos), picked=w)
        self.b.go("writer", {"universe": self.handover.get("universe"), "story": self.handover.get("story"), "replace": replace})

    # --- Vocabulary (words worth learning) ----------------------------------------------------------------------------------------------

    def setup_subjects(self):
        try:
            options = learn.subjects()
        except dictionary.DictionaryMissing:
            return
        self.subject_options = [(label, key or "any") for label, key in options]
        sel = self.query_one("#subject", Select)
        sel.set_options(self.subject_options)
        sel.value = "any"

    def new_batch(self):
        try:
            self.batch = learn.batch(20, self.query_one("#difficulty", Select).value,
                                     None if self.query_one("#vpos", Select).value == "any" else self.query_one("#vpos", Select).value,
                                     None if self.query_one("#subject", Select).value == "any" else self.query_one("#subject", Select).value,
                                     exclude=self.my.excluded())
        except dictionary.DictionaryMissing as e:
            self.say(str(e))
            return
        except learn.WordfreqMissing as e:
            self.say(str(e))
            return
        self.my.mark_seen([w["word"] for w in self.batch])
        self.render_batch()
        left = "" if len(self.batch) >= 20 else " (that is all this filter has left: widen it, or forget what you have seen)"
        self.say(f"{len(self.batch)} new words{left}." if self.batch else "No new words with these filters: widen them.")
        self.query_one("#learn", OptionList).focus()

    def batch_marker(self, word):
        w = word.lower()
        return "★" if w in self.my.learning_words() else "✓" if w in self.my.known else " "

    def render_batch(self):
        lst = self.query_one("#learn", OptionList)
        previous = lst.highlighted
        lst.clear_options()
        width = max([len(w["word"]) for w in self.batch] + [8])
        lst.add_options([_opt(f" {self.batch_marker(w['word'])} {w['word']:<{width}}  {w['pos']:<9} {w['definition']}", f"l:{i}")
                         for i, w in enumerate(self.batch)])
        if previous is not None and self.batch:
            lst.highlighted = min(previous, len(self.batch) - 1)
        elif self.batch:
            lst.highlighted = 0

    def batch_word(self):
        lst = self.query_one("#learn", OptionList)
        if lst.highlighted is None or not self.batch:
            return None
        return self.batch[lst.highlighted]

    def mark(self, status):
        """Mark the highlighted word in whichever list is showing: 'learning' or 'known'."""
        tab = self.query_one(TabbedContent).active
        if tab == "t-vocab":
            w = self.batch_word()
            if not w:
                return self.say("Move to a word first.")
            if status == "learning":
                self.my.mark_learning(w["word"], w["pos"], w["definition"])
                self.say(f"“{w['word']}” is in My words.")
            else:
                self.my.mark_known(w["word"])
                self.say(f"“{w['word']}” is marked Known: it won't be offered again.")
            self.render_batch()
            self.refresh_mine()
        elif tab == "t-mine" and status == "known":
            e = self.mine_entry()
            if e:
                self.my.mark_known(e["word"])
                self.say(f"“{e['word']}” is marked Known and left your list.")
                self.refresh_mine()
        elif tab == "t-lookup" and status == "learning":
            self.action_add()

    def action_known(self):
        self.mark("known")

    def action_learning(self):
        self.mark("learning")

    # --- My words ----------------------------------------------------------------------------------------------------------------------

    def refresh_mine(self):
        lst = self.query_one("#mine", OptionList)
        previous = lst.highlighted
        lst.clear_options()
        entries = [learn.fill_definition(e) for e in self.my.learning]
        self.mine = entries
        if not entries:
            lst.add_options([_opt("Nothing here yet. Mark words Learning in Vocabulary, or add a word from Lookup (a).", None, style="dim")])
            self.query_one("#minenote", Static).update("")
            return
        width = max(len(e["word"]) for e in entries)
        lst.add_options([_opt(f"  {e['word']:<{width}}  {(e.get('pos') or ''):<9} {e.get('definition') or e.get('note') or ''}", f"m:{i}")
                         for i, e in enumerate(entries)])
        self.query_one("#minenote", Static).update(f"{len(entries)} word{'s' if len(entries) != 1 else ''} you are learning. Enter looks one up; f = flashcards.")
        if previous is not None:
            lst.highlighted = min(previous, len(entries) - 1)

    def mine_entry(self):
        lst = self.query_one("#mine", OptionList)
        if lst.highlighted is None or not getattr(self, "mine", None) or lst.highlighted >= len(self.mine):
            return None
        return self.mine[lst.highlighted]

    def action_remove(self):
        tab = self.query_one(TabbedContent).active
        if tab == "t-uwords":
            lst = self.query_one("#uwords", OptionList)
            if lst.highlighted is not None and getattr(self, "uw", None) and lst.highlighted < len(self.uw):
                slot, word = self.uw[lst.highlighted]
                wordbank.remove_added(self.universe, slot, word)
                self.refresh_uwords()
                self.say(f"Took “{word}” off the '{slot}' list: the Wheel and Builder won't use it any more.")
            return
        if tab != "t-mine":
            return
        e = self.mine_entry()
        if e:
            self.my.remove(e["word"])
            self.refresh_mine()
            self.say(f"Removed “{e['word']}” from My words.")

    def add_by_hand(self, text):
        """A word you want to learn, typed in (several can be separated by commas). Its part of speech and meaning come from the dictionary."""
        words = [w.strip() for w in (text or "").replace("\n", ",").split(",") if w.strip()]
        if not words:
            return
        results = []
        for w in words:
            entry = learn.fill_definition({"word": w, "pos": "", "definition": ""})
            results.append((w, self.my.add_by_hand(w, entry.get("pos") or "", entry.get("definition") or "")))
        self.query_one("#myword", Input).value = ""
        self.refresh_mine()
        new = [w for w, r in results if r != "have"]
        self.say((f"Added {', '.join('“' + w + '”' for w in new)} to My words." if new else "") +
                 (" Already there: " + ", ".join(w for w, r in results if r == "have") + "." if len(new) != len(results) else ""))

    def start_over(self):
        """Forget which words the batches have shown (Known and Learning words stay as they are), so New batch can offer them again."""
        n = len(self.my.seen)
        self.my.forget_seen()
        self.say(f"Forgot the {n} words you had been shown. Words you marked Known or Learning stay that way." if n else "Nothing had been shown yet.")

    def action_flashcards(self):
        if not getattr(self, "mine", None):
            self.say("My words is empty: nothing to practise yet.")
            return
        def done(known):
            for w in known or []:
                self.my.mark_known(w)
            self.refresh_mine()
            if known:
                self.say(f"{len(known)} word{'s' if len(known) != 1 else ''} marked Known and taken off your list.")
        self.app.push_screen(FlashcardScreen(list(self.mine)), done)

    # --- Universe words: what was put on this universe's lists -------------------------------------------------------------------------

    def refresh_uwords(self):
        lst = self.query_one("#uwords", OptionList)
        previous = lst.highlighted
        lst.clear_options()
        if self.universe is None:
            self.uw = []
            lst.add_options([_opt("Open a universe in the Builder (F2) to have word lists.", None, style="dim")])
            self.query_one("#uwnote", Static).update("")
            return
        self.uw = wordbank.added_words(self.universe)
        if not self.uw:
            lst.add_options([_opt("Nothing yet: press w on a word in Lookup or My words (Use in this universe's stories).", None, style="dim")])
            self.query_one("#uwnote", Static).update(f"{self.universe.name}'s own word lists are empty.")
            return
        lst.add_options([_opt(f"  {slot:<16} {word}", f"x:{i}") for i, (slot, word) in enumerate(self.uw)])
        self.query_one("#uwnote", Static).update(f"{len(self.uw)} word{'s' if len(self.uw) != 1 else ''} the Wheel and Builder can use in {self.universe.name}. "
                                                 "The slot is the kind of thing it stands for (job, thing, place...).")
        if previous is not None:
            lst.highlighted = min(previous, len(self.uw) - 1)

    # --- Add to this universe's word list ------------------------------------------------------------------------------------------------

    def action_wordlist(self):
        tab = self.query_one(TabbedContent).active
        if tab == "t-mine":
            e = self.mine_entry()
            word = e["word"] if e else None
        elif tab == "t-vocab":
            b = self.batch_word()
            word = b["word"] if b else None
        else:
            word, _ = self.current_word()
        if not word:
            self.say("Move to a word first.")
            return
        if self.universe is None:
            self.say("There is no universe to add it to: open one in the Builder (F2) first.")
            return
        self.app.push_screen(SlotScreen(word, self.universe.name), lambda slot: self.add_to_list(word, slot))

    def add_to_list(self, word, slot):
        if not slot:
            return
        try:
            path, new = wordbank.add_to_universe_list(self.universe, word, slot)
        except ValueError as e:
            self.say(str(e))
            return
        from . import paths
        self.refresh_uwords()
        self.say((f"Added “{word}” to {self.universe.name}'s '{slot}' list" if new else f"“{word}” was already on the '{slot}' list")
                 + f" ({paths.tilde(path)}). The Wheel and Builder use it for this universe.")

    # --- Overused ---------------------------------------------------------------------------------------------------------------------

    def setup_stories(self):
        sel = self.query_one("#overstory", Select)
        stories = self.universe.stories() if self.universe is not None else []
        options = [(f"{s.title}  ({self.universe.name})", s.slug) for s in stories] or [("(no story yet)", "none")]
        sel.set_options(options)
        sel.value = (self.story.slug if self.story is not None else options[0][1])

    def analyze(self):
        slug = self.query_one("#overstory", Select).value
        story = self.universe.story(slug) if self.universe is not None and slug != "none" else None
        if story is None:
            self.say("There is no story to look at: open one in the Builder first.")
            return
        self.over = overused.report(story)
        self.over_story = story
        lst = self.query_one("#over", OptionList)
        lst.clear_options()
        options = [_opt(f"Most frequent words (everyday words left out)  ·  {self.over['words']:,} words in all", None, style="bold")]
        for i, r in enumerate(self.over["frequent"]):
            forms = f"   ({', '.join(r['forms'])})" if len(r["forms"]) > 1 else ""
            options.append(_opt(f"  {r['word']}  ×{r['count']}{forms}", f"f:{i}"))
        options.append(_opt("Repeated close together (within about 50 words)", None, style="bold"))
        for i, r in enumerate(self.over["repeats"][:60]):
            options.append(_opt(f"  {r['word']}  ×{r['count']}  in {len(r['clusters'])} place{'s' if len(r['clusters']) != 1 else ''}", f"r:{i}"))
        lst.add_options(options)
        self.query_one("#oversummary", Static).update("Pick a word to see where it is; Enter on a place opens the Writer there.")
        self.query_one("#occ", OptionList).clear_options()
        lst.focus()
        lst.highlighted = 1 if len(options) > 1 else None
        self.say(f"Looked at {self.over['words']:,} words.")

    def show_occurrences(self, oid):
        kind, _, i = oid.partition(":")
        r = (self.over["frequent"] if kind == "f" else self.over["repeats"])[int(i)]
        occ = self.query_one("#occ", OptionList)
        occ.clear_options()
        places = r["where"] if kind == "f" else [o for cluster in r["clusters"] for o in cluster]
        options = []
        for n, o in enumerate(places):
            options.append(_opt(f"  {o['scene'] or '-':<14} line {o['line']:<5} {o['text']}", f"o:{n}:{o['file']}|{o['line']}"))
        occ.add_options(options)

    def open_in_writer(self, oid):
        file, _, line = oid.split(":", 2)[2].rpartition("|")
        story = getattr(self, "over_story", None) or self.story
        if story is None or self.universe is None:
            return
        self.b.go("writer", {"universe": self.universe.slug, "story": story.slug, "scene": {"path": file, "line": int(line)}})

    # --- leaving -----------------------------------------------------------------------------------------------------------------------

    def action_mode(self, which):
        self.b.go(which, self.context())

    def context(self):
        return {"universe": self.universe.slug if self.universe else self.payload.get("universe"),
                "story": self.story.slug if self.story else self.payload.get("story")}

    def action_noop_mode(self):
        self.say("You are in Words.")

    def action_back_mode(self):
        self.b.go("back", dict(self.context(), fallback=self.b.back))

    action_leave = action_back_mode

    def action_quit_program(self):
        from .tui import ConfirmScreen
        self.app.push_screen(ConfirmScreen(navigation.QUIT_QUESTION), lambda yes: self.b.go("quit") if yes else None)


class WordsApp(App):
    TITLE = "storywheel · Words"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = []

    def __init__(self, state_store=None, back="builder", payload=None):
        super().__init__()
        appearance.apply(self)
        self.state_store = state_store
        self.back = back
        self.payload = payload or {}
        self.next = None

    def on_mount(self):
        self.push_screen(WordsScreen(self, self.payload))

    def remember(self):
        if self.state_store is not None:
            try:
                self.state_store.update(mode="words", back=self.back)
            except OSError:
                pass

    def go(self, where, payload=None):
        self.next = (where, payload or {})
        self.exit()


def run_words(state_store=None, back="builder", payload=None):
    app = WordsApp(state_store, back, payload)
    app.run()
    return app.next
