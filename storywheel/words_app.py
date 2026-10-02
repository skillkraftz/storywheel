"""The Words mode (F5): the language tools, as a mode of their own. Offline.

    Lookup       meanings, every similar word, every opposite, wider and narrower words, parts, related forms; Enter or a click on a
                 word looks it up; back and forward remember where you were
    Vocabulary   from a word or topic: types of it, parts of it, terms of its subject, related words; keep the ones you like
    Word bank    the words you kept, per story or universe; save them as a universe atom list for the Wheel and Builder
    Overused     a story's most frequent words and words repeated close together, and where they are

Opened from the Writer (F5), it carries the word under the cursor; "Use in Writer" goes back and replaces that word with the one you
picked, in the same form (running -> sprinting).
"""
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, OptionList, Select, Static, TabbedContent, TabPane
from textual.widgets.option_list import Option

from . import dictionary, inflect, overused, vault, wordbank
from .header import QuietHeader

MODE_KEYS = "F1 Wheel   F2 Builder   F3 Writer   F4 Settings   F5 Words"

HELP = f"""\
[b]Words[/b]        {MODE_KEYS}

[b]Lookup[/b]  type a word and press Enter. Plurals, past tenses and misspellings work.
  [b]Enter[/b] or a click on a word looks it up       [b]b[/b] / [b]n[/b]  back / forward through the words you looked up
  [b]/[/b]  filter the lists                          [b]a[/b]  add the word to the word bank       [b]c[/b]  copy it
  [b]u[/b]  Use in Writer: go back to the Writer and replace the word you were on (only when you came from the Writer)

[b]Vocabulary[/b]  type a word or topic: its types, its parts, the terms of its subject, related words.
  [b]Enter[/b] or [b]space[/b] chooses a word, [b]g[/b] a whole group, [b]a[/b] adds the chosen ones to the word bank, [b]l[/b] looks one up.

[b]Word bank[/b]  per story or per universe. [b]d[/b] removes the word. "Save as atom list" writes it into the universe's lists
  for the slot you pick, so the Wheel and the Builder roll with it.

[b]Overused[/b]  the most frequent words of a story (everyday words left out) and words repeated close together. Enter on a
  place opens the Writer there.

[b]q[/b] goes back to where you were. Meanings: Open English WordNet (CC BY 4.0); similar words also the Moby Thesaurus.
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


def vocab_groups(result):
    """[(title, [words])] for the vocabulary list, in order."""
    out = []
    for s in result["senses"]:
        head = f"{s['word']} ({s['pos']}): {s['definition']}"
        for title, key in (("Kinds of it (wider)", "kinds"), ("Types of it", "types"), ("Parts of it", "parts"), ("Terms from its subject", "domain")):
            if s[key]:
                out.append((f"{head}  —  {title}", s[key]))
    if result["related"]:
        out.append(("Related words (Moby Thesaurus)", result["related"]))
    return out


# --- the screen -------------------------------------------------------------------------------------------------------------------

class WordsScreen(Screen):
    BINDINGS = [
        Binding("f1", "mode('wheel')", "Wheel", key_display="F1"),
        Binding("f2", "mode('builder')", "Builder", key_display="F2"),
        Binding("f3", "mode('writer')", "Writer", key_display="F3"),
        Binding("f4", "mode('settings')", "Settings", key_display="F4"),
        Binding("f5", "noop", "Words", key_display="F5"),
        Binding("question_mark", "help", "Help", key_display="?"),
        Binding("q", "leave", "Back"),
        Binding("b", "back", "Back a word", show=False),
        Binding("n", "forward", "Forward", show=False),
        Binding("slash", "filter", "Filter", show=False),
        Binding("u", "use", "Use in Writer", show=False),
        Binding("a", "add", "Add to bank", show=False),
        Binding("c", "copy", "Copy", show=False),
        Binding("space", "choose", "Choose", show=False),
        Binding("g", "group", "Choose group", show=False),
        Binding("l", "lookup_chosen", "Look up", show=False),
        Binding("d", "remove", "Remove", show=False),
    ]
    DEFAULT_CSS = """
    WordsScreen TabbedContent { height: 1fr; }
    WordsScreen TabPane { height: 1fr; }
    WordsScreen #status { height: 1; padding: 0 1; background: $boost; }
    WordsScreen .bar { height: 3; }
    WordsScreen .bar Input { width: 1fr; }
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
        self.chosen = set()
        self.vocab = None
        self.vocab_rows = []
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
                    yield Button("Add to bank", id="add")
                    yield Button("Copy", id="copy")
            with TabPane("Vocabulary", id="t-vocab"):
                with Horizontal(classes="bar"):
                    yield Input(placeholder="a word or topic: kitchen, saddle, storm…", id="topic")
                    yield Button("Gather", id="gather")
                    yield Button("Add chosen to bank", id="vadd")
                yield Static("Enter or space chooses a word; g chooses a whole group; a adds the chosen words to the word bank.", classes="note")
                yield OptionList(id="vocab")
            with TabPane("Word bank", id="t-bank"):
                with Horizontal(classes="bar"):
                    yield Select([("(no story or universe yet)", "none")], id="scope", allow_blank=False)
                    yield Input(placeholder="add a word of your own", id="addword")
                    yield Button("Add", id="bankadd")
                yield OptionList(id="bank")
                with Horizontal(classes="bar"):
                    yield Select([(s, s) for s in wordbank.slots()], value="thing", id="slot", allow_blank=False)
                    yield Input(placeholder="name of the list", id="listname")
                    yield Button("Save as atom list", id="savelist")
                    yield Button("Remove word", id="remove")
            with TabPane("Overused", id="t-over"):
                with Horizontal(classes="bar"):
                    yield Select([("(no story yet)", "none")], id="overstory", allow_blank=False)
                    yield Button("Analyze", id="analyze")
                yield Static("", id="oversummary", classes="note")
                yield OptionList(id="over")
                yield OptionList(id="occ")
        yield Static("", id="status", markup=False)
        yield Footer()

    def on_mount(self):
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
        self.setup_scopes()
        self.refresh_bank()
        self.setup_stories()
        if not dictionary.installed():
            self.say(dictionary.NOT_INSTALLED)
        if self.handover and self.handover.get("word"):
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
        self.query_one("#back", Button).disabled = self.pos <= 0
        self.query_one("#forward", Button).disabled = self.pos >= len(self.history) - 1

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
        for lst_id in ("results", "vocab", "bank"):
            lst = self.query_one(f"#{lst_id}", OptionList)
            if lst.has_focus and lst.highlighted is not None:
                oid = lst.get_option_at_index(lst.highlighted).id
                if oid and oid[:2] in ("w:", "v:", "b:"):
                    _k, w, pos = parse_id(oid)
                    return w, pos
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
        elif i == "topic":
            self.gather(event.value)
        elif i == "addword":
            self.bank_add_typed(event.value)

    def on_input_changed(self, event):
        if event.input.id == "filter":
            self.filter = event.value
            self.show_results()

    def on_option_list_option_selected(self, event):
        lst, oid = event.option_list.id, event.option.id
        if lst == "results" and oid and oid.startswith("w:"):
            self.lookup(parse_id(oid)[1])
        elif lst == "vocab" and oid and oid.startswith("v:"):
            self.toggle_vocab(event.option_list.highlighted)
        elif lst == "over" and oid:
            self.show_occurrences(oid)
        elif lst == "occ" and oid:
            self.open_in_writer(oid)

    def on_button_pressed(self, event):
        event.stop()
        {"go": lambda: self.lookup(self.query_one("#word", Input).value), "back": self.action_back, "forward": self.action_forward,
         "use": self.action_use, "add": self.action_add, "copy": self.action_copy, "gather": lambda: self.gather(self.query_one("#topic", Input).value),
         "vadd": self.vocab_add, "bankadd": lambda: self.bank_add_typed(self.query_one("#addword", Input).value),
         "savelist": self.save_list, "remove": self.action_remove, "analyze": self.analyze}.get(event.button.id or "", lambda: None)()

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
        self.say(f"Copied “{w}”." if how else f"Couldn't reach a clipboard (install xclip or wl-clipboard). The word is: {w}")

    def action_add(self):
        w, _ = self.current_word()
        tab = self.query_one(TabbedContent).active
        if tab == "t-vocab":
            return self.vocab_add()
        if not w:
            self.say("Move to a word first.")
            return
        self.bank_add([w])

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

    # --- Vocabulary -----------------------------------------------------------------------------------------------------------------

    def gather(self, topic):
        topic = (topic or "").strip()
        if not topic:
            return
        try:
            self.vocab = dictionary.vocabulary(topic)
        except dictionary.DictionaryMissing as e:
            self.say(str(e))
            return
        self.chosen = set()
        self.render_vocab()
        n = sum(len(w) for _t, w in vocab_groups(self.vocab)) if self.vocab["found"] else 0
        self.say(f"{n} words around “{topic}”." if self.vocab["found"] else f"Nothing found for “{topic}”.")
        self.query_one("#vocab", OptionList).focus()

    def render_vocab(self):
        lst = self.query_one("#vocab", OptionList)
        previous = lst.highlighted
        self.vocab_rows = []
        for title, words in vocab_groups(self.vocab) if self.vocab and self.vocab["found"] else []:
            self.vocab_rows.append((title, None))
            for w in words:
                self.vocab_rows.append((w, f"v:{w}\x1f{len(self.vocab_rows)}"))
        lst.clear_options()
        options = []
        for text, oid in self.vocab_rows:
            if oid is None:
                options.append(_opt(text, None, style="bold"))
            else:
                w = parse_id(oid)[1]
                options.append(_opt(f"  [{'x' if w.lower() in self.chosen else ' '}] {w}", oid))
        lst.add_options(options)
        if previous is not None:
            lst.highlighted = min(previous, max(0, len(options) - 1))
        elif options:
            lst.highlighted = next((n for n, r in enumerate(self.vocab_rows) if r[1]), 0)

    def toggle_vocab(self, index):
        if index is None or index >= len(self.vocab_rows) or not self.vocab_rows[index][1]:
            return
        w = parse_id(self.vocab_rows[index][1])[1].lower()
        self.chosen.symmetric_difference_update({w})
        self.render_vocab()

    def action_choose(self):
        """Space on a word in the Vocabulary list chooses it (the same as Enter)."""
        lst = self.query_one("#vocab", OptionList)
        if self.query_one(TabbedContent).active == "t-vocab" and lst.has_focus:
            self.toggle_vocab(lst.highlighted)

    def action_group(self):
        lst = self.query_one("#vocab", OptionList)
        i = lst.highlighted
        if self.query_one(TabbedContent).active != "t-vocab" or i is None:
            return
        start = i
        while start > 0 and self.vocab_rows[start][1]:
            start -= 1
        end = i + 1
        while end < len(self.vocab_rows) and self.vocab_rows[end][1]:
            end += 1
        group = {parse_id(r[1])[1].lower() for r in self.vocab_rows[start + 1:end] if r[1]}
        if group <= self.chosen:
            self.chosen -= group
        else:
            self.chosen |= group
        self.render_vocab()

    def action_lookup_chosen(self):
        if self.query_one(TabbedContent).active == "t-vocab":
            lst = self.query_one("#vocab", OptionList)
            i = lst.highlighted
            if i is not None and self.vocab_rows[i][1]:
                self.query_one(TabbedContent).active = "t-lookup"
                self.lookup(parse_id(self.vocab_rows[i][1])[1])

    def vocab_add(self):
        if not self.chosen:
            self.say("Choose some words first (Enter or space on a word, g for a group).")
            return
        # keep the writer's own spelling/capitalization from the list
        spelled = {parse_id(r[1])[1].lower(): parse_id(r[1])[1] for r in self.vocab_rows if r[1]}
        self.bank_add([spelled.get(w, w) for w in sorted(self.chosen)], note=(self.vocab or {}).get("topic", ""))
        self.chosen = set()
        self.render_vocab()

    # --- Word bank -------------------------------------------------------------------------------------------------------------------

    def setup_scopes(self):
        sel = self.query_one("#scope", Select)
        options = []
        if self.universe is not None:
            if self.story is not None:
                options.append((f"This story: {self.story.title}", "story"))
            options.append((f"This universe: {self.universe.name}", "universe"))
        if not options:
            options = [("(open a universe in the Builder first)", "none")]
        sel.set_options(options)
        sel.value = options[0][1]

    def scope(self):
        v = self.query_one("#scope", Select).value
        return v if v in ("story", "universe") else None

    def bank_data(self):
        s = self.scope()
        if not s or self.universe is None:
            return None
        return wordbank.load(self.universe, self.story if s == "story" else None)

    def refresh_bank(self):
        lst = self.query_one("#bank", OptionList)
        previous = lst.highlighted
        lst.clear_options()
        data = self.bank_data()
        if data is None:
            lst.add_options([_opt("Open a universe in the Builder (F2) to keep a word bank.", None, style="dim")])
            return
        if not data["words"]:
            lst.add_options([_opt("Empty. Add words from Lookup (a) or Vocabulary (Add chosen to bank).", None, style="dim")])
            return
        lst.add_options([_opt(w["word"] + (f"   — {w['note']}" if w.get("note") else ""), f"b:{w['word']}") for w in data["words"]])
        if previous is not None:
            lst.highlighted = min(previous, len(data["words"]) - 1)

    def on_select_changed(self, event):
        if event.select.id == "scope":
            self.refresh_bank()

    def bank_add(self, words, note=""):
        s = self.scope()
        if not s or self.universe is None:
            self.say("There is no story or universe to keep a word bank in: open one in the Builder first.")
            return
        n = wordbank.add(self.universe, words, self.story if s == "story" else None, note)
        self.refresh_bank()
        where = "this story's" if s == "story" else "this universe's"
        self.say(f"Added {n} word{'s' if n != 1 else ''} to {where} word bank." + ("" if n == len(words) else f" ({len(words) - n} already there.)"))

    def bank_add_typed(self, text):
        words = [w.strip() for w in (text or "").replace("\n", ",").split(",") if w.strip()]
        if words:
            self.bank_add(words)
            self.query_one("#addword", Input).value = ""

    def action_remove(self):
        s = self.scope()
        lst = self.query_one("#bank", OptionList)
        if self.query_one(TabbedContent).active != "t-bank" or not s or lst.highlighted is None:
            return
        oid = lst.get_option_at_index(lst.highlighted).id
        if oid and oid.startswith("b:"):
            wordbank.remove(self.universe, oid[2:], self.story if s == "story" else None)
            self.refresh_bank()
            self.say(f"Removed “{oid[2:]}”.")

    def save_list(self):
        data = self.bank_data()
        if data is None or self.universe is None:
            self.say("There is no word bank to save.")
            return
        slot = self.query_one("#slot", Select).value
        name = self.query_one("#listname", Input).value.strip() or data["name"]
        try:
            path, n, skipped = wordbank.save_as_atom_list(self.universe, data, slot, name)
        except ValueError as e:
            self.say(str(e))
            return
        from . import paths
        self.say(f"Saved {n} words as a '{slot}' list: {paths.tilde(path)}. The Wheel and Builder use it for this universe."
                 + (f" Skipped {len(skipped)} longer than five words." if skipped else ""))

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

    def action_leave(self):
        self.b.go(self.b.back, self.context())


class WordsApp(App):
    TITLE = "storywheel · Words"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = []

    def __init__(self, state_store=None, back="builder", payload=None):
        super().__init__()
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
