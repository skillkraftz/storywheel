"""The Words mode (F5): the language tools, as a mode of their own. Offline.

    Lookup       meanings, every similar word, every opposite, wider and narrower words, parts, related forms; Enter or a click on a
                 word looks it up; back and forward remember where you were
    Suggestions  words that fit the story's genres and are not used yet; words the dictionary relates to your characters and places; fresh
                 alternatives for the most overused words
    Vocabulary   words worth learning (not everyday, not obscure), a fresh batch at a time; mark them Known or Learning (★); the ★ words
                 are a filter of the same tab, with flashcards; type a word of your own to learn
    Genre words  every noun, verb, adjective and adverb of the dictionary, ranked by fit to a genre (nothing hidden), filtered by commonness
                 and search; look up, copy, use in the Writer, mark to learn; below them the Wheel's own short lists (names, jobs, places, things)
    Story words  the names and odd words your story really uses, with counts and where; look-alikes flagged; add to the spelling list,
                 make an entity, rename everywhere; its often-used words and close repeats; below it, the words you put on this universe's
                 generator lists

Opened from the Writer (F5), Words carries the word under the cursor; "Use in Writer" goes back and replaces it with the one you picked,
in the same form (running -> sprinting).
"""
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, OptionList, Select, Static, TabbedContent, TabPane, Tabs, Tab
from textual.widgets.option_list import Option

from . import rhymes, dictionary, genrefit, genrewords, inflect, learn, overused, storywords, suggest, vault, wordbank, wordlists, wordsused
from . import appearance, navigation, tools
from .footer import FitFooter
from .keptscreen import KeptScreen
from .header import QuietHeader
from .virtuallist import VirtualList


TAB_HELP = {
    "lookup": "Look any word up: meanings, similar and opposite words, rhymes and related words, each in its own box, and use one in the Writer.",
    "vocab": "Words worth learning, a fresh batch at a time: mark them ★ Learning or ✓ Known, practise the ★ ones with flashcards, or type a word of your own.",
    "genre": "Long lists of nouns, verbs, adjectives and adverbs, ranked by how well they fit a genre, to find the word you want (and a few of the Wheel's own lists, to borrow from).",
    "story": "The names and odd words your story really uses, with counts and where, look-alikes flagged, and its most often used words, so you can fix a spelling, teach the spellchecker, make a name an entity, or vary a word.",
    "suggest": "Words to try in your story: ones that fit its genres and are not used yet, ones the dictionary relates to your characters and places, and fresh alternatives for what you overuse.",
}

def __getattr__(name):
    if name == "HELP":                                   # (Words' help page, from storywheel/data/help/words.md)
        from . import helpdoc
        return helpdoc.text("words")
    raise AttributeError(name)


# --- the rows (pure: used by the screen and the tests) -------------------------------------------------------------------------

def parse_id(oid):
    """(kind, word, pos) of a row id: 'w:word|pos\x1f7', 'v:word\x1f7' or 'b:word'."""
    kind, body = oid[:1], oid[2:].split("\x1f")[0]
    word, _, pos = body.partition("|")
    return kind, word, pos or None


def _opt(text, id_=None, disabled=False, style=""):
    return Option(Text(text, style=style), id=id_, disabled=disabled or id_ is None)


PANES = (("meanings", "Meanings"), ("similar", "Similar"), ("opposites", "Opposites"), ("rhymes", "Rhymes"), ("related", "Related"))


class _Rows:
    """Builds the rows of the Lookup boxes. A row with an id is a word you can look up (id = 'w:<word>|<pos>' plus a counter, because the
    same word can be in several lists and ids must differ)."""

    def __init__(self, filter_text="", counter=None):
        self.f = filter_text.strip().lower()
        self.rows = []
        self.count = counter if counter is not None else [0]

    def heading(self, text):
        self.rows.append((text, None, "bold"))

    def info(self, text):
        self.rows.append((text, None, "dim"))

    def word(self, w, pos="", note=""):
        if self.f and self.f not in w.lower():
            return False
        self.count[0] += 1
        self.rows.append((f"    {w}" + (f"   ({note})" if note else ""), f"w:{w}|{pos}\x1f{self.count[0]}", ""))
        return True


def lookup_panes(result, filter_text="", rhyme=None):
    """{pane: [(text, id or None, style)]} for a lookup result: meanings, similar, opposites, rhymes and related words, each its own box.
    `rhyme` is rhymes.find()'s answer, or {"missing": message}, or None."""
    f = filter_text.strip().lower()
    shared = [0]
    boxes = {name: _Rows(f, shared) for name, _t in PANES}
    if not result["found"]:
        m = boxes["meanings"]
        m.heading(f"No entry for '{result['word'] or result['query']}'.")
        if result["suggestions"]:
            m.info("Did you mean (Enter looks it up):")
            for s in result["suggestions"]:
                m.word(s)
    else:
        many = len(result["entries"]) > 1
        for e in result["entries"]:
            title = e["word"] + (f"   (form of “{e['form_of']}”)" if e["form_of"] else "")
            m = boxes["meanings"]
            m.heading(title)
            for part in e["parts"]:
                m.heading(f"  {part['pos']}")
                for n, sense in enumerate(part["senses"], 1):
                    m.info(f"  {n}. {sense['definition']}")
                    if sense["examples"]:
                        m.info(f"       “{sense['examples'][0]}”")
            sim, opp, rel = boxes["similar"], boxes["opposites"], boxes["related"]
            if many:
                for box in (sim, opp, rel):
                    box.heading(title)
            for part in e["parts"]:
                for n, sense in enumerate(part["senses"], 1):
                    short = sense["definition"] if len(sense["definition"]) <= 48 else sense["definition"][:47] + "…"
                    if sense["synonyms"]:
                        sim.info(f"  {part['pos']} {n}. {short}")
                        for w in sense["synonyms"]:
                            sim.word(w, part["pos"])
                    for label, key in (("a kind of (wider)", "kind_of"), ("types of it (narrower)", "types_of"), ("parts of it", "parts"),
                                       ("it is part of", "part_of")):
                        if sense[key]:
                            rel.info(f"  {part['pos']} {n}. {short}: {label}")
                            for w in sense[key]:
                                rel.word(w)
            if e["wide_synonyms"]:
                sim.heading(f"  More similar words ({len(e['wide_synonyms'])})")
                for w in e["wide_synonyms"]:
                    sim.word(w)
            if e["antonyms"]:
                opp.heading("  Opposite words")
                for w in e["antonyms"]:
                    opp.word(w)
            if e["indirect_antonyms"]:
                opp.heading("  Opposite words, indirect (opposites of similar words)")
                for a in e["indirect_antonyms"]:
                    opp.word(a["word"], "", a["via"])
            for kind, words in e["related_forms"].items():
                rel.heading(f"  Related forms ({kind})")
                for w in words:
                    rel.word(w)
    rh = boxes["rhymes"]
    if rhyme is None:
        pass
    elif rhyme.get("missing"):
        rh.info(rhyme["missing"])
    elif not rhyme["found"]:
        rh.info(f"No pronunciation for “{rhyme['word']}” in the CMU Pronouncing Dictionary.")
    else:
        n = rhyme["syllables"]
        rh.info(f"{rhyme['word']}: {rhyme['pronunciation']}  ({n} syllable{'s' if n != 1 else ''})")
        for title, groups in (("Perfect rhymes", rhyme["perfect"]), ("Near rhymes", rhyme["near"])):
            total = sum(len(ws) for _s, ws in groups)
            rh.heading(f"{title} ({total})")
            if not total:
                rh.info("    none found" + (" with that many syllables" if rhyme.get("limit") else ""))
            for syl, words in groups:
                rh.info(f"  {syl} syllable{'s' if syl != 1 else ''}")
                for w in words:
                    rh.word(w, "", f"{syl}")
        if rhyme["near_more"]:
            rh.info(f"    ({rhyme['near_more']:,} less common near rhymes are not shown; the syllable box narrows the list)")
        if rhyme.get("hidden"):
            rh.info(f"{rhyme['hidden']:,} names and rare words are left out (the second box shows them).")
        elif rhyme.get("filtered") is False and not rhyme.get("rare"):
            rh.info("The main dictionary isn't installed, so names and rare words could not be left out.")
        if rhyme.get("order"):
            rh.info(rhyme["order"])
    for name, _t in PANES:
        if not boxes[name].rows:
            boxes[name].info({"meanings": "No meanings.", "similar": "No similar words.", "opposites": "No opposites in the dictionary.",
                              "rhymes": "Type a word to see what rhymes with it.", "related": "No wider, narrower or related words."}[name])
    return {name: boxes[name].rows for name, _t in PANES}


def lookup_rows(result, filter_text=""):
    """All the rows of a lookup (without rhymes) in one list, for plain use and tests."""
    panes = lookup_panes(result, filter_text)
    return [row for name, _t in PANES if name != "rhymes" for row in panes[name]]


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




class WordsScreen(KeptScreen, Screen):
    BINDINGS = navigation.footer([
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
        Binding("e", "entity", "Add to universe / make an entity", show=False),
        Binding("s", "spell", "Add to the spelling list", show=False),
        Binding("r", "rename", "Rename everywhere", show=False),
        Binding("m", "more", "More like these", show=False),
    ], keep=('filter', 'use'))
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
    WordsScreen Select { width: 34; }
    WordsScreen #vview { width: 18; }
    WordsScreen #gwcat { width: 40; }
    WordsScreen #gwband, WordsScreen #gwsort { width: 22; }
    WordsScreen #gwvlist, WordsScreen #sgvlist { height: 1fr; }
    WordsScreen #sgkind { width: 36; }
    WordsScreen #sgpos { width: 18; }
    WordsScreen #swview { width: 24; }
    WordsScreen #swoften { height: 1fr; }
    WordsScreen #knownlist { height: 1fr; border: none; scrollbar-gutter: stable; }
    WordsScreen #gwlist { height: 1fr; }
    WordsScreen #gwgenrelist { width: 1fr; padding: 0 1; }
    WordsScreen #swlist, WordsScreen #swwhere { height: 1fr; }
    WordsScreen #uwords { height: 6; }
    WordsScreen #panes { height: 1fr; }
    WordsScreen .pane { width: 1fr; height: 1fr; border: round $primary-darken-2; }
    WordsScreen .pane OptionList { height: 1fr; border: none; scrollbar-gutter: stable; }
    WordsScreen Select > SelectOverlay, WordsScreen Select > SelectOverlay:focus { height: auto; max-height: 24; border: tall $border-blurred; }
    WordsScreen #rhsyl, WordsScreen #rhrare { width: 100%; }
    WordsScreen #pane-tabs { display: none; height: 2; }
    WordsScreen.-narrow #pane-tabs { display: block; }
    WordsScreen.-narrow .pane { display: none; }
    WordsScreen.-narrow .pane.-shown { display: block; }
    WordsScreen #tools Button { min-width: 14; margin-right: 1; }
    """

    def __init__(self, app_ref, payload):
        super().__init__()
        self.b = app_ref
        self.payload = payload or {}
        self.history, self.pos = [], -1
        self.result = None
        self.rows = []
        self.rhyme = None
        self.filter = ""
        self.origin = None
        self.my = learn.MyWords()
        self.batch = []
        self.subject_options = [("Any subject", "any")]
        self.often = None                                        # overused.report of the story read in Story words
        self.sg_rows, self.sg_token, self.sg_started = [], 0, False
        self.known_rows = []
        self.vview = "new"                                       # Vocabulary shows new words or the ★ Learning ones
        self.mine = []
        self.gw_genres = None                                    # genres Genre words ranks by (None: not set yet; [] means any genre)
        self.gw_rows, self.gw_new = [], []
        self.gw_view, self.gw_building, self._gw_timer, self.gw_started = None, False, None, False
        self.sw_report, self.sw_scope = None, None
        self.sw_items = []
        self.uw = []
        self.universe = None
        self.story = None
        self.handover = self.payload.get("handover")          # {"word", "replace": {file, row, start, end, text}} from the Writer

    # --- layout -----------------------------------------------------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield QuietHeader()
        with TabbedContent(id="tabs"):
            with TabPane("Lookup", id="t-lookup"):
                yield Static(TAB_HELP["lookup"], classes="note", markup=False)
                with Horizontal(classes="bar"):
                    yield Input(placeholder="a word  (Enter looks it up)", id="word")
                    yield Button("Look up", id="go")
                    yield Button("◀ Back", id="back")
                    yield Button("Forward ▶", id="forward")
                with Horizontal(classes="bar"):
                    yield Input(placeholder="filter the words below", id="filter")
                yield Tabs(*[Tab(t, id=f"pt-{n}") for n, t in PANES], id="pane-tabs")
                with Horizontal(id="panes"):
                    for name, title in PANES:
                        with Vertical(id=f"pane-{name}", classes="pane") as box:
                            box.border_title = title
                            if name == "rhymes":
                                yield Select([("Any number of syllables", 0), ("1 syllable", 1), ("2 syllables", 2), ("3 syllables", 3),
                                              ("4 or more", 4)], value=0, id="rhsyl", allow_blank=False)
                                yield Select([("Common words only", 0), ("Names and rare words too", 1)], value=0, id="rhrare", allow_blank=False)
                            yield OptionList(id=f"res-{name}", classes="results")
                with Horizontal(id="tools", classes="bar"):
                    yield Button("Use in Writer", id="use")
                    yield Button("Learn this word", id="add")
                    yield Button("Use in this universe's stories", id="lookuplist")
                    yield Button("Copy", id="copy")
                yield Static("", id="usenote", classes="note", markup=False)
            with TabPane("Suggestions", id="t-suggest"):
                yield Static(TAB_HELP["suggest"], classes="note", markup=False)
                with Horizontal(classes="bar"):
                    yield Select([("For this story", "story"), ("For your characters and places", "entities"), ("Fresh alternatives", "fresh")],
                                 value="story", id="sgkind", allow_blank=False)
                    yield Select([(l, v) for l, v in wordlists.POS_LABELS], value="a", id="sgpos", allow_blank=False)
                    yield Button("Refresh", id="sgrefresh")
                yield Static("", id="sgnote", classes="note", markup=False)
                yield VirtualList(id="sgvlist")
                with Horizontal(id="sgtools", classes="bar"):
                    yield Button("Look up", id="sglookup")
                    yield Button("★ Learn", id="sglearn")
                    yield Button("Copy", id="sgcopy")
                    yield Button("Use in Writer", id="sguse")
                    yield Button("Add to generator list", id="sglist-add")
            with TabPane("Vocabulary", id="t-vocab"):
                yield Static(TAB_HELP["vocab"], classes="note", markup=False)
                with Horizontal(classes="bar"):
                    yield Select([("New words", "new"), ("★ Learning", "learning"), ("✓ Known", "known")], value="new", id="vview", allow_blank=False)
                    yield Select([(d, d) for d in learn.DIFFICULTY], value="any", id="difficulty", allow_blank=False)
                    yield Select([("Any part of speech", "any")] + [(p, p) for p in learn.POS], value="any", id="vpos", allow_blank=False)
                    yield Select([("Any subject", "any")], value="any", id="subject", allow_blank=False)
                    yield Button("New batch", id="newbatch")
                    yield Button("Start over", id="startover")
                with Horizontal(classes="bar"):
                    yield Input(placeholder="a word you want to learn  (Enter adds it to ★ Learning)", id="myword")
                    yield Button("Add", id="myadd")
                yield Static("How rare: uncommon (like “lantern”)   rare (like “serendipity”)   very rare (like “gallivant”)", id="minenote", classes="note", markup=False)
                yield OptionList(id="learn")
                yield OptionList(id="mine")
                yield OptionList(id="knownlist")
                with Horizontal(id="learntools", classes="bar"):
                    yield Button("★ Learning", id="learning")
                    yield Button("✓ Known", id="known")
                    yield Button("Open in Lookup", id="openlookup")
                    yield Button("Flashcards", id="flash")
                    yield Button("Remove", id="remove")
                    yield Button("Use in this universe's stories", id="minelist")
            with TabPane("Story words", id="t-story"):
                yield Static(TAB_HELP["story"], classes="note", markup=False)
                with Horizontal(classes="bar"):
                    yield Select([("(no story yet)", "none")], id="swscope", allow_blank=False)
                    yield Select([("Names and odd words", "words"), ("Often used", "often")], value="words", id="swview", allow_blank=False)
                    yield Button("Read again", id="swread")
                yield Static("", id="swnote", classes="note", markup=False)
                yield OptionList(id="swlist")
                yield OptionList(id="swoften")
                yield OptionList(id="swwhere")
                with Horizontal(id="swtools", classes="bar"):
                    yield Button("Add to spelling list", id="swspell")
                    yield Button("Make an entity", id="swentity")
                    yield Button("Rename everywhere", id="swrename")
                    yield Button("Copy", id="swcopy")
                yield Static("", id="uwnote", classes="note")
                yield OptionList(id="uwords")
                with Horizontal(classes="bar"):
                    yield Button("Remove from the generator list", id="uwremove")
            with TabPane("Genre words", id="t-genre"):
                yield Static(TAB_HELP["genre"], classes="note", markup=False)
                with Horizontal(classes="bar"):
                    yield Select([("Nouns", "n")], value="n", id="gwcat", allow_blank=False)
                    yield Button("Genres…", id="gwgenres")
                    yield Static("", id="gwgenrelist", markup=False)
                with Horizontal(classes="bar"):
                    yield Select([(l, v) for l, v in wordlists.BANDS], value="any", id="gwband", allow_blank=False)
                    yield Select([(l, v) for l, v in wordlists.SORTS], value="fit", id="gwsort", allow_blank=False)
                    yield Input(placeholder="search these words (filters as you type)", id="gwsearch")
                yield Static("", id="gwnote", classes="note", markup=False)
                yield VirtualList(id="gwvlist")
                yield OptionList(id="gwlist")
                with Horizontal(id="gwtools", classes="bar"):
                    yield Button("Look up", id="gwlookup")
                    yield Button("★ Learn", id="gwlearn")
                    yield Button("Copy", id="gwcopy")
                    yield Button("Use in Writer", id="gwuse")
                    yield Button("Add to universe", id="gwentity")
                    yield Button("Add to generator list", id="gwlist-add")
                    yield Button("More like these", id="gwmore")
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
            self.auto_known_check()
            self.refresh_mine()
            self.refresh_uwords()
            self.refresh_buttons()
            self.sw_report = None                     # (the manuscript may have changed in the Writer)

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
        self.setup_subjects()
        migrated = wordbank.migrate_banks(self.my)
        self.auto_known_check()
        self.refresh_mine()
        self.set_view(self.vview)
        self.refresh_uwords()
        self.gw_started = False                      # Genre words opens (and works out the genre fit) the first time it is shown
        self.gw_genres = None
        self.setup_story_scope()
        if not dictionary.installed():
            self.say(dictionary.NOT_INSTALLED)
        elif migrated:
            self.say(f"Your old word banks ({migrated} words) are now in your ★ Learning list (Vocabulary).")
        if self.handover and self.handover.get("word"):
            self.query_one(TabbedContent).active = "t-lookup"
            self.query_one("#word", Input).value = self.handover["word"]
            self.lookup(self.handover["word"], origin=True)
            self.first_word_list().focus()
        else:
            self.query_one("#word", Input).focus()
        self.show_pane("meanings")
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
        self.load_rhymes()
        self.show_results()
        self.refresh_buttons()
        self.say(f"{word}: " + ("found." if result["found"] else "no entry."))

    def result_lists(self):
        return [self.query_one(f"#res-{name}", OptionList) for name, _t in PANES]

    def show_results(self, keep=False):
        """Fill the five boxes (Meanings, Similar, Opposites, Rhymes, Related) from the last lookup; each keeps its own place."""
        panes = lookup_panes(self.result, self.filter, self.rhyme) if self.result else {name: [] for name, _t in PANES}
        self.rows = [row for name, _t in PANES for row in panes[name]]
        for (name, _t), lst in zip(PANES, self.result_lists()):
            previous = lst.highlighted
            lst.clear_options()
            lst.add_options([_opt(t, i, style=st) for t, i, st in panes[name]])
            if keep and previous is not None:
                lst.highlighted = min(previous, max(0, len(panes[name]) - 1))
            else:
                lst.highlighted = next((n for n, r in enumerate(panes[name]) if r[1]), None)

    def load_rhymes(self):
        """The rhymes of the word just looked up (the word as typed if it has a pronunciation, else its base word)."""
        self.rhyme = None
        if not self.result:
            return
        syl = self.query_one("#rhsyl", Select).value or 0
        rare = bool(self.query_one("#rhrare", Select).value)
        try:
            for w in (self.result.get("query"), self.result.get("word")):
                if w:
                    found = rhymes.find(w, syl or None, rare)
                    if found["found"]:
                        found["limit"] = syl
                        found["rare"] = rare
                        self.rhyme = found
                        return
            self.rhyme = found if w else None
        except rhymes.RhymesMissing as e:
            self.rhyme = {"missing": str(e)}

    def first_word_list(self):
        for lst in self.result_lists():
            if any(lst.get_option_at_index(i).id for i in range(lst.option_count)):
                return lst
        return self.result_lists()[0]

    def current_word(self):
        """(word, pos) of the highlighted word row in whichever Lookup box has the focus (else the first box with a word), or (None, None)."""
        lists = self.result_lists()
        focused = [l for l in lists if l.has_focus]
        for lst in focused + [l for l in lists if l not in focused]:
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
            self.first_word_list().focus()
        elif i == "myword":
            self.add_by_hand(event.value)

    def on_input_changed(self, event):
        if event.input.id == "filter":
            self.filter = event.value
            self.show_results()
        elif event.input.id == "gwsearch" and self.gw_started:
            self.gw_search_changed()

    def on_option_list_option_selected(self, event):
        lst, oid = event.option_list.id, event.option.id
        if lst.startswith("res-") and oid and oid.startswith("w:"):
            self.lookup(parse_id(oid)[1])
        elif lst == "learn" and oid:
            self.open_in_lookup(self.batch[int(oid[2:])]["word"])
        elif lst == "mine" and oid:
            self.open_in_lookup(self.mine[int(oid[2:])]["word"])
        elif lst == "knownlist" and oid:
            self.open_in_lookup(self.known_rows[int(oid[2:])]["word"])
        elif lst == "gwlist" and oid:
            self.gw_lookup()
        elif lst == "swlist" and oid:
            self.sw_show_where()
        elif lst == "swwhere" and oid:
            self.sw_open_in_writer(oid)
        elif lst == "swoften" and oid:
            self.sw_show_often_where()

    def on_button_pressed(self, event):
        event.stop()
        {"go": lambda: self.lookup(self.query_one("#word", Input).value), "back": self.action_back, "forward": self.action_forward,
         "use": self.action_use, "add": self.action_add, "copy": self.action_copy, "lookuplist": self.action_wordlist,
         "newbatch": self.new_batch, "learning": lambda: self.mark("learning"), "known": lambda: self.mark("known"),
         "openlookup": self.open_vocab_word,
         "flash": self.action_flashcards, "remove": self.action_remove,
         "startover": self.start_over, "myadd": lambda: self.add_by_hand(self.query_one("#myword", Input).value),
         "uwremove": self.remove_added_word,
         "minelist": self.action_wordlist,
         "sgrefresh": self.sg_refresh, "sglookup": self.gw_lookup, "sglearn": self.gw_learn, "sgcopy": self.action_copy, "sguse": self.action_use,
         "sglist-add": self.gw_generator_list,
         "gwgenres": self.pick_genres, "gwlookup": self.gw_lookup, "gwlearn": self.gw_learn, "gwcopy": self.action_copy, "gwuse": self.action_use,
         "gwentity": self.action_entity, "gwlist-add": self.gw_generator_list, "gwmore": self.action_more,
         "swread": lambda: self.sw_read(force=True), "swspell": self.action_spell, "swentity": self.action_entity,
         "swrename": self.action_rename, "swcopy": self.action_copy}.get(event.button.id or "", lambda: None)()

    def on_tabs_tab_activated(self, event):
        if event.tabs.id == "pane-tabs" and event.tab is not None:
            self.show_pane((event.tab.id or "pt-meanings")[3:])

    def show_pane(self, name):
        """On a narrow terminal the five boxes take turns (the tab bar over them); wide, all are shown."""
        for n, _t in PANES:
            self.query_one(f"#pane-{n}").set_class(n == name, "-shown")

    def on_resize(self, event):
        self.set_class(event.size.width < 150, "-narrow")

    def on_tabbed_content_tab_activated(self, event):
        if event.pane.id == "t-story":
            self.sw_read()
        elif event.pane.id == "t-genre" and not self.gw_started:
            self.gw_started = True
            self.setup_genre()
        elif event.pane.id == "t-suggest" and not self.sg_started:
            self.sg_started = True
            self.sg_refresh()

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
        self.action_help()

    def action_help(self):
        from .helpscreen import HelpScreen as SharedHelp
        self.app.push_screen(SharedHelp("words"))

    def active_tab(self):
        return self.query_one(TabbedContent).active

    def action_copy(self):
        tab = self.active_tab()
        if tab in ("t-genre", "t-suggest"):
            w = self.gw_word()
        elif tab == "t-story":
            if self.query_one("#swview", Select).value == "often":
                w = self.sw_often_word()
            else:
                item = self.sw_item()
                w = item.text if item else None
        elif tab == "t-vocab":
            e = self.vocab_entry()
            w = e["word"] if e else None
        else:
            w, _ = self.current_word()
        if not w:
            self.say("Move to a word first.")
            return
        from . import clipboard
        how = clipboard.copy(w, self.app)
        self.say(f"Copied “{w}”." if how else tools.missing("clipboard", f"The word is: {w}"))

    def action_add(self):
        """a: the same as l, on whichever tab you are in (the word you are on)."""
        self.mark("learning")

    def lookup_learn(self):
        """Add the highlighted Lookup word to the ★ Learning list, with its meaning."""
        w, pos = self.current_word()
        if not w:
            self.say("Move to a word first.")
            return
        entry = learn.fill_definition({"word": w, "pos": pos or "", "definition": ""})
        new = self.my.mark_learning(w, entry.get("pos") or "", entry.get("definition") or "")
        self.refresh_mine()
        self.say(f"“{w}” is ★ Learning." if new else f"“{w}” is already ★ Learning.")

    def open_in_lookup(self, word):
        self.query_one(TabbedContent).active = "t-lookup"
        self.lookup(word)
        self.first_word_list().focus()

    # --- Use in Writer -------------------------------------------------------------------------------------------------------------

    def origin_text(self):
        return (self.origin or {}).get("text") or (self.handover or {}).get("word") or ""

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
        if self.active_tab() in ("t-genre", "t-suggest"):
            word = self.gw_word()
            if not word:
                self.say("Move to a word first.")
                return
            replace = dict(self.handover["replace"], new=inflect.apply_case(self.origin_text(), word), picked=word)
            self.b.go("writer", {"universe": self.handover.get("universe"), "story": self.handover.get("story"), "replace": replace})
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
        batch, auto = [], []
        try:
            for _ in range(6):                                                # words a manuscript uses are skipped (and marked Known): fetch more
                got = learn.batch(20 - len(batch), self.query_one("#difficulty", Select).value,
                                  None if self.query_one("#vpos", Select).value == "any" else self.query_one("#vpos", Select).value,
                                  None if self.query_one("#subject", Select).value == "any" else self.query_one("#subject", Select).value,
                                  exclude=self.my.excluded() | {w["word"].lower() for w in batch})
                if not got:
                    break
                used = wordsused.find([w["word"].lower() for w in got])
                dropped = 0
                for w in got:
                    where = used.get(w["word"].lower())
                    if where:
                        self.my.mark_known(w["word"], where)
                        auto.append((w["word"], where))
                        dropped += 1
                    else:
                        batch.append(w)
                if len(batch) >= 20 or not dropped:                         # (only when some were dropped is there a reason to look for more)
                    break
        except dictionary.DictionaryMissing as e:
            self.say(str(e))
            return
        except learn.WordfreqMissing as e:
            self.say(str(e))
            return
        self.batch = batch
        self.my.mark_seen([w["word"] for w in self.batch])
        self.render_batch()
        left = "" if len(self.batch) >= 20 else " (that is all this filter has left: widen it, or forget what you have seen)"
        known = (f" {len(auto)} more {'was' if len(auto) == 1 else 'were'} already in your stories and marked ✓ Known: "
                 + "; ".join(f"{w} ({wordsused.describe(wh)})" for w, wh in auto[:3]) + ("…" if len(auto) > 3 else "")) if auto else ""
        self.say((f"{len(self.batch)} new words{left}." if self.batch else "No new words with these filters: widen them.") + known)
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
        if tab == "t-vocab" and self.vview == "learning":
            e = self.mine_entry()
            if not e:
                return self.say("Move to a word first.")
            if status == "known":
                self.my.mark_known(e["word"])
                self.say(f"“{e['word']}” is marked Known and left your ★ list.")
                self.refresh_mine()
            else:
                self.say(f"“{e['word']}” is already ★ Learning.")
        elif tab == "t-vocab":
            w = self.batch_word()
            if not w:
                return self.say("Move to a word first.")
            if status == "learning":
                self.my.mark_learning(w["word"], w["pos"], w["definition"])
                self.say(f"“{w['word']}” is ★ Learning.")
            else:
                self.my.mark_known(w["word"])
                self.say(f"“{w['word']}” is marked Known: it won't be offered again.")
            self.render_batch()
            self.refresh_mine()
        elif tab in ("t-genre", "t-suggest"):
            if status == "learning":
                self.gw_learn()
            else:
                self.gw_known()
        elif tab == "t-lookup":
            if status == "learning":
                self.lookup_learn()
            else:
                self.lookup_known()
        else:
            self.say("l and k mark the word you are on: they work in Lookup, Suggestions, Vocabulary and Genre words.")

    def lookup_known(self):
        w, _pos = self.current_word()
        if not w:
            return self.say("Move to a word first.")
        self.my.mark_known(w)
        self.refresh_mine()
        self.say(f"“{w}” is marked Known: it won't be offered again.")

    def gw_known(self):
        row = self.gw_row()
        if not isinstance(row, dict) or row.get("head"):
            return self.say("Only dictionary words can be marked Known (pick Nouns, Verbs, Adjectives or Adverbs).")
        self.my.mark_known(row["word"])
        self.refresh_mine()
        self.query_one("#gwvlist", VirtualList).refresh()
        self.query_one("#sgvlist", VirtualList).refresh()
        self.say(f"“{row['word']}” is marked Known: it won't be offered again.")

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
            lst.add_options([_opt("Nothing here yet. Mark words ★ Learning in New words, add a word from Lookup (a), or type one above.", None, style="dim")])
            self.note_for_view()
            return
        width = max(len(e["word"]) for e in entries)
        lst.add_options([_opt(f"  {e['word']:<{width}}  {(e.get('pos') or ''):<9} {e.get('definition') or e.get('note') or ''}", f"m:{i}")
                         for i, e in enumerate(entries)])
        self.note_for_view()
        if previous is not None:
            lst.highlighted = min(previous, len(entries) - 1)

    def mine_entry(self):
        lst = self.query_one("#mine", OptionList)
        if lst.highlighted is None or not getattr(self, "mine", None) or lst.highlighted >= len(self.mine):
            return None
        return self.mine[lst.highlighted]

    def remove_added_word(self):
        """Take the highlighted word off the universe's generator lists (the section at the bottom of Story words)."""
        lst = self.query_one("#uwords", OptionList)
        if lst.highlighted is not None and self.uw and lst.highlighted < len(self.uw):
            slot, word = self.uw[lst.highlighted]
            wordbank.remove_added(self.universe, slot, word)
            self.refresh_uwords()
            self.say(f"Took “{word}” off the '{slot}' list: the Wheel and Builder won't use it any more.")
        else:
            self.say("Move to a word in the generator-list section first.")

    def action_remove(self):
        tab = self.active_tab()
        if tab == "t-story" and self.focused is self.query_one("#uwords", OptionList):
            return self.remove_added_word()
        if tab != "t-vocab" or self.vview != "learning":
            return self.say("Remove works on the ★ Learning list (switch the first box in Vocabulary).")
        e = self.mine_entry()
        if e:
            self.my.remove(e["word"])
            self.refresh_mine()
            self.say(f"Removed “{e['word']}” from your ★ list.")

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
        self.say((f"Added {', '.join('“' + w + '”' for w in new)} to ★ Learning." if new else "") +
                 (" Already there: " + ", ".join(w for w, r in results if r == "have") + "." if len(new) != len(results) else ""))

    def start_over(self):
        """Forget which words the batches have shown (Known and Learning words stay as they are), so New batch can offer them again."""
        n = len(self.my.seen)
        self.my.forget_seen()
        self.say(f"Forgot the {n} words you had been shown. Words you marked Known or Learning stay that way." if n else "Nothing had been shown yet.")

    def action_flashcards(self):
        if not getattr(self, "mine", None):
            self.say("Nothing is ★ Learning yet: nothing to practise.")
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
            lst.add_options([_opt("Nothing yet: press w on a word in Lookup, Vocabulary or Genre words (Use in this universe's stories).", None, style="dim")])
            self.query_one("#uwnote", Static).update(f"{self.universe.name}'s own word lists are empty.")
            return
        lst.add_options([_opt(f"  {slot:<16} {word}", f"x:{i}") for i, (slot, word) in enumerate(self.uw)])
        self.query_one("#uwnote", Static).update(f"{len(self.uw)} word{'s' if len(self.uw) != 1 else ''} the Wheel and Builder can use in {self.universe.name}. "
                                                 "The slot is the kind of thing it stands for (job, thing, place...).")
        if previous is not None:
            lst.highlighted = min(previous, len(self.uw) - 1)

    # --- Add to this universe's word list ------------------------------------------------------------------------------------------------

    def action_wordlist(self):
        tab = self.active_tab()
        if tab in ("t-genre", "t-suggest"):
            return self.gw_generator_list()
        if tab == "t-vocab":
            e = self.vocab_entry()
            word = e["word"] if e else None
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

    # --- Vocabulary: new words or the ★ Learning ones -----------------------------------------------------------------------------------

    def set_view(self, view):
        self.vview = view if view in ("new", "learning", "known") else "new"
        self.query_one("#learn", OptionList).display = self.vview == "new"
        self.query_one("#mine", OptionList).display = self.vview == "learning"
        self.query_one("#knownlist", OptionList).display = self.vview == "known"
        for bid in ("difficulty", "vpos", "subject", "newbatch", "startover"):
            self.query_one("#" + bid).display = self.vview == "new"
        self.query_one("#remove", Button).display = self.vview == "learning"
        for bid in ("learning", "known", "flash", "minelist"):
            self.query_one("#" + bid).display = self.vview != "known"
        if self.vview == "known":
            self.refresh_known()
        self.note_for_view()

    def note_for_view(self):
        note = self.query_one("#minenote", Static)
        if self.vview == "learning":
            n = len(getattr(self, "mine", []) or [])
            note.update(f"{n} word{'s' if n != 1 else ''} you are learning. Enter looks one up; f = flashcards; k = Known; d = remove." if n else "")
        elif self.vview == "known":
            n = len(self.my.known_entries())
            used = sum(1 for e in self.my.known_entries() if e["where"])
            note.update(f"{n} word{'s' if n != 1 else ''} you know; {used} marked automatically because a manuscript uses them (first place shown). Enter looks one up.")
        else:
            note.update("How rare: uncommon (like “lantern”)   rare (like “serendipity”)   very rare (like “gallivant”)   ★ Learning   ✓ Known   "
                        "Enter opens the full entry; l = Learning, k = Known.")

    def refresh_known(self):
        lst = self.query_one("#knownlist", OptionList)
        previous = lst.highlighted
        lst.clear_options()
        self.known_rows = self.my.known_entries()
        if not self.known_rows:
            lst.add_options([_opt("No known words yet: mark a word ✓ Known, or write it in a story.", None, style="dim")])
            return
        width = max(len(e["word"]) for e in self.known_rows)
        lst.add_options([_opt(f"  ✓ {e['word']:<{width}}  " + (f"used in {wordsused.describe(e['where'])}" if e["where"] else "marked Known by you"), f"k:{i}")
                         for i, e in enumerate(self.known_rows)])
        if previous is not None:
            lst.highlighted = min(previous, len(self.known_rows) - 1)

    def auto_known_check(self):
        """Learning words that a manuscript already uses are words you know: mark them Known (noting where) and say so."""
        try:
            found = wordsused.auto_known(self.my, [e["word"] for e in self.my.learning])
        except Exception:                                                    # never let a bad manuscript stop the tab
            return
        if found:
            self.refresh_mine()
            self.say("Already in your stories, so marked ✓ Known: " + "; ".join(f"{w} ({wordsused.describe(wh)})" for w, wh in sorted(found.items())[:4])
                     + ("…" if len(found) > 4 else ""))

    def on_select_changed(self, event):
        if event.select.id in ("rhsyl", "rhrare"):
            if self.result:
                self.load_rhymes()
                self.show_results(keep=True)
        elif event.select.id == "vview":
            self.set_view(event.value)
        elif event.select.id in ("gwcat", "gwband", "gwsort"):
            if self.gw_started:
                self.gw_new = []
                self.gw_refresh()
        elif event.select.id == "swscope":
            self.sw_scope_changed(event.value)
        elif event.select.id == "swview":
            self.sw_set_view()
        elif event.select.id in ("sgkind", "sgpos"):
            if self.sg_started:
                self.sg_refresh()

    def vocab_entry(self):
        """{"word", ...} for the highlighted row of whichever Vocabulary list is showing."""
        if self.vview == "learning":
            return self.mine_entry()
        if self.vview == "known":
            lst = self.query_one("#knownlist", OptionList)
            rows = getattr(self, "known_rows", [])
            return rows[lst.highlighted] if lst.highlighted is not None and lst.highlighted < len(rows) else None
        return self.batch_word()

    def open_vocab_word(self):
        e = self.vocab_entry()
        if e:
            self.open_in_lookup(e["word"])
        else:
            self.say("Move to a word first.")

    # --- Suggestions ------------------------------------------------------------------------------------------------------------------------

    def sg_refresh(self):
        """Work out the chosen suggestion list in the background (the genre fit comes first, once, if it is not there yet)."""
        lst = self.query_one("#sgvlist", VirtualList)
        note = self.query_one("#sgnote", Static)
        kind = self.query_one("#sgkind", Select).value
        self.query_one("#sgpos").display = kind == "story"
        if not dictionary.installed():
            lst.set_source(0, lambda a, b: [], lambda r, sel, w: Text(""))
            return note.update(dictionary.NOT_INSTALLED)
        if self.gw_building:
            return note.update("Working out which words fit each genre (done once)…")
        if not wordlists.ready():
            self.gw_check_fit()
            return note.update("Working out which words fit each genre (done once)…")
        if self.universe is None:
            lst.set_source(0, lambda a, b: [], lambda r, sel, w: Text(""))
            return note.update("Open a universe in the Builder (F2) to get suggestions for its stories.")
        if kind in ("story", "fresh") and self.story is None:
            lst.set_source(0, lambda a, b: [], lambda r, sel, w: Text(""))
            return note.update("There is no story to suggest for yet: write something in the Writer first.")
        self.sg_token += 1
        token = self.sg_token
        pos = self.query_one("#sgpos", Select).value
        universe, story = self.universe, self.story
        note.update("Looking for words…")
        self.run_worker(lambda: self._sg_work(kind, pos, token, universe, story), thread=True, name="suggest")

    def _sg_work(self, kind, pos, token, universe, story):
        import sqlite3
        db = sqlite3.connect(f"file:{dictionary.index_path()}?mode=ro", uri=True)
        try:
            if kind == "story":
                genres = suggest.story_genres(universe, story)
                rows = suggest.for_story(universe, story, pos, db=db, genres=genres)
                label = {v: l.lower() for l, v in wordlists.POS_LABELS}[pos]
                text = (f"{len(rows)} {label} that fit {', '.join(genres)} and are not in “{story.title}” yet." if genres
                        else "The story has no genre yet: pick one in the Wheel or give the universe genre leanings in the Builder.")
            elif kind == "entities":
                rows = suggest.for_entities(universe, story, db=db)
                text = f"{len(rows)} words the dictionary relates to the jobs, things, places and groups of {universe.name}, not used in the story yet."
            else:
                rows = suggest.fresh_alternatives(universe, story, db=db)
                text = (f"Alternatives for the {sum(1 for r in rows if r['head'])} most overused words of “{story.title}”, the ones that fit the genres first."
                        if rows else "No word is used often enough yet to need an alternative.")
        except Exception as e:                                                  # a bad manuscript must not break the tab
            rows, text = [], f"Could not work out suggestions: {e}"
        finally:
            db.close()
        self.app.call_from_thread(self._sg_done, token, rows, text)

    def _sg_done(self, token, rows, text):
        if token != self.sg_token:
            return                                                              # an older request that finished late
        self.sg_rows = rows
        self.query_one("#sgvlist", VirtualList).set_source(len(rows), lambda start, n: self.sg_rows[start:start + n], self.sg_render_row)
        self.query_one("#sgnote", Static).update(text + ("  ●●● strong fit  ●●○  ●○○." if any(r["mark"] for r in rows) else ""))

    def sg_render_row(self, row, selected, width):
        text = Text()
        if row.get("head"):
            text.append(f" {row['word']}", style="bold underline")
            text.append(f"   {row['definition']}", style="dim")
            return text
        learning = row["word"] in self.my.learning_words()
        text.append(f" {row['mark'] or '   '} " if row["mark"] else "     ", style="bold" if row["fit"] >= 35 else "dim")
        text.append(("★ " if learning else "  ") + f"{row['word'][:22]:<22}", style="bold")
        text.append(f"  {row['definition'][:60]:<60}", style="" if selected else "dim")
        if row.get("note"):
            text.append(f"  {row['note']}", style="italic dim")
        return text

    # --- Genre words: the dictionary's words by part of speech, ranked by genre; the generator's own short lists below ---------------------

    WHEEL = "wheel:"

    def setup_genre(self):
        """Genres to rank by start as the story's own (its outline's genre, else the universe's leanings); none means any genre."""
        if self.gw_genres is None:
            chosen = []
            if self.story is not None:
                try:
                    meta, _sections = self.story.load_outline()
                    chosen = [g.strip().lower() for g in str(meta.get("genre", "")).replace(",", "/").split("/") if g.strip()]
                except Exception:
                    chosen = []
            if not chosen and self.universe is not None:
                chosen = [g.lower() for g in self.universe.settings().get("genres", [])]
            known = set(genrewords.genres(self.library()))
            self.gw_genres = [g for g in chosen if g in known and g != "general"]
        self.gw_options()
        self.gw_check_fit()

    def library(self):
        if not hasattr(self, "_library"):
            from .library import Library
            from . import paths
            self._library = Library.load(paths.home())
        return self._library

    def gw_options(self):
        """The main picker: Nouns / Verbs / Adjectives / Adverbs when the dictionary is there, then the small From the Wheel group."""
        sel = self.query_one("#gwcat", Select)
        options = []
        if dictionary.installed():
            options += wordlists.POS_LABELS
        options += [(f"From the Wheel: {label}", self.WHEEL + key) for label, key in genrewords.labels()]
        current = sel.value if sel.value is not Select.BLANK else None
        sel.set_options(options)
        sel.value = current if any(v == current for _, v in options) else options[0][1]
        have = dictionary.installed()
        for bid in ("gwband", "gwsort"):
            self.query_one("#" + bid).display = have
        if not have:
            self.say(dictionary.NOT_INSTALLED)

    def gw_check_fit(self):
        """Work out the genre fit in the background when it is missing or the genre lists changed, then show the list."""
        if not dictionary.installed():
            return self.gw_refresh()
        if self.gw_building:
            return
        self.gw_building = True
        self.query_one("#gwnote", Static).update("Working out which words fit each genre (done once, and again when the genre lists change)…")
        self.run_worker(self._fit_worker, thread=True, exclusive=False, name="genrefit")

    def _fit_worker(self):
        note = None
        try:
            note = genrefit.ensure(lambda m: self.app.call_from_thread(self.query_one("#gwnote", Static).update, m + " (one time)"), self.library())
        except Exception as e:                                           # never leave the tab stuck on "working"
            note = f"The genre fit could not be built: {e}"
        self.app.call_from_thread(self._fit_done, note)

    def _fit_done(self, note):
        self.gw_building = False
        if note:
            self.say(note)
        if self.gw_started:
            self.gw_refresh()
        if self.sg_started:
            self.sg_refresh()

    def gw_is_wheel(self):
        value = self.gw_value()
        return not dictionary.installed() or str(value).startswith(self.WHEEL)

    def gw_value(self):
        return self.query_one("#gwcat", Select).value

    def gw_category(self):
        """The Wheel list key (first_name, job...) when a From the Wheel list is showing."""
        value = str(self.gw_value())
        return value[len(self.WHEEL):] if value.startswith(self.WHEEL) else None

    def pick_genres(self):
        from .tui import ChoiceScreen
        names = genrewords.genres(self.library()) if self.gw_is_wheel() else wordlists.genres_with_fit()
        options = [("Any genre", "*")] + [(g, g) for g in names if g != "general" or self.gw_is_wheel()]
        self.app.push_screen(ChoiceScreen("Genres to rank by (none or Any genre: the whole list)", options, multi=True,
                                          selected=list(self.gw_genres or []) or ["*"]), self.genres_picked)

    def genres_picked(self, chosen):
        if chosen is None:
            return
        self.gw_genres = [g for g in chosen if g != "*"]
        self.gw_new = []
        self.gw_refresh()

    def gw_refresh(self):
        self.query_one("#gwgenrelist", Static).update("Genres: " + (", ".join(self.gw_genres) if self.gw_genres else "any genre"))
        wheel = self.gw_is_wheel()
        self.query_one("#gwvlist").display = not wheel
        self.query_one("#gwlist").display = wheel
        self.query_one("#gwmore").display = wheel
        self.query_one("#gwentity").display = wheel
        self.query_one("#gwlearn").display = not wheel
        if wheel:
            return self.gw_refresh_wheel()
        self.gw_show_dictionary()

    def gw_show_dictionary(self):
        if self.gw_building or not wordlists.ready():
            self.query_one("#gwvlist", VirtualList).set_source(0, lambda s, n: [], lambda r, sel, w: Text(""))
            return
        pos = self.gw_value()
        band = self.query_one("#gwband", Select).value
        sort = self.query_one("#gwsort", Select).value
        query = self.query_one("#gwsearch", Input).value
        view = wordlists.View(pos, self.gw_genres or (), band, sort, query)
        self.gw_view = view
        lst = self.query_one("#gwvlist", VirtualList)
        lst.set_source(len(view), view.page, self.gw_render_row)
        label = next(l for l, v in wordlists.POS_LABELS if v == pos).lower()
        ranked = f", ranked by fit to {', '.join(self.gw_genres)} (nothing is hidden)" if self.gw_genres and view.sort == "fit" else ""
        freq = "" if wordlists.has_frequencies() else "  (wordfreq is not installed: commonness is unknown, so that filter is off)"
        self.query_one("#gwnote", Static).update(f"{len(view):,} {label}{ranked}.  ●●● strong fit  ●●○  ●○○  ··· none.{freq}")

    def gw_render_row(self, row, selected, width):
        text = Text()
        learning = row["word"] in self.my.learning_words()
        text.append(f" {row['mark'] or '   '} " if self.gw_genres else " ", style="bold" if row["fit"] >= 35 else "dim")
        text.append(("★ " if learning else "  ") + f"{row['word'][:26]:<26}", style="bold")
        text.append(f"  {row['definition']}", style="dim" if not selected else "")
        return text

    def gw_refresh_wheel(self):
        key = self.gw_category()
        query = self.query_one("#gwsearch", Input).value
        library = self.library()
        self.gw_rows = genrewords.rows(library, self.gw_genres or [], key, query)
        lst = self.query_one("#gwlist", OptionList)
        previous = lst.highlighted
        lst.clear_options()
        options = []
        width = min(44, max([len(r.text) for r in self.gw_rows + self.gw_new] + [10]))
        for i, r in enumerate(self.gw_new):
            options.append(_opt(f"  {r.text:<{width}}  new, invented in this style", f"n:{i}", style="italic"))
        for i, r in enumerate(self.gw_rows):
            text = r.text if len(r.text) <= width else r.text[:width - 1] + "…"
            options.append(_opt(f"  {text:<{width}}  {genrewords.tag_label(r.tags, self.gw_genres or [])}", f"g:{i}"))
        if not options:
            options.append(_opt("Nothing in these genres for this list: choose more genres, or Any genre.", None, style="dim"))
        lst.add_options(options)
        if previous is not None and options:
            lst.highlighted = min(previous, len(options) - 1)
        label = next(l for l, k in genrewords.labels() if k == key)
        self.query_one("#gwnote", Static).update(
            f"{len(self.gw_rows)} {label.lower()} from the Wheel's own lists" + (f" in {', '.join(self.gw_genres)}" if self.gw_genres else "") + ".")
        self.query_one("#gwmore", Button).disabled = key not in genrewords.NAME_CATEGORIES

    def on_virtual_list_selected(self, event):
        if event.list.id in ("gwvlist", "sgvlist"):
            self.gw_lookup()

    def gw_search_changed(self):
        if self._gw_timer is not None:
            self._gw_timer.stop()
        self._gw_timer = self.set_timer(0.15, self.gw_refresh)          # filter as you type, without rebuilding on every key

    def gw_row(self):
        """The Wheel row, or the dictionary row (a dict), under the cursor."""
        if self.active_tab() == "t-suggest":
            return self.query_one("#sgvlist", VirtualList).current()
        if self.gw_is_wheel():
            lst = self.query_one("#gwlist", OptionList)
            if lst.highlighted is None:
                return None
            oid = lst.get_option_at_index(lst.highlighted).id
            if not oid:
                return None
            kind, _, i = oid.partition(":")
            rows = self.gw_new if kind == "n" else self.gw_rows
            return rows[int(i)] if int(i) < len(rows) else None
        return self.query_one("#gwvlist", VirtualList).current()

    def gw_word(self):
        row = self.gw_row()
        if row is None:
            return None
        return row["word"] if isinstance(row, dict) else row.text

    def gw_lookup(self):
        row = self.gw_row()
        if row is None:
            return self.say("Move to a word first.")
        if not isinstance(row, dict) and row.frame:
            return self.say("That is a whole phrase for the generator to fill in: pick a single word or name to look up.")
        self.open_in_lookup(self.gw_word())

    def gw_learn(self):
        row = self.gw_row()
        if not isinstance(row, dict) or row.get("head"):
            return self.say("Only dictionary words can be marked to learn (pick Nouns, Verbs, Adjectives or Adverbs).")
        new = self.my.mark_learning(row["word"], row["pos"], row["definition"])
        self.refresh_mine()
        self.query_one("#gwvlist", VirtualList).refresh()
        self.query_one("#sgvlist", VirtualList).refresh()
        self.say(f"“{row['word']}” is ★ Learning (Vocabulary > ★ Learning)." if new else f"“{row['word']}” is already ★ Learning.")

    def gw_generator_list(self):
        word = self.gw_word()
        if not word:
            return self.say("Move to a word first.")
        if self.universe is None:
            return self.say("There is no universe to add it to: open one in the Builder (F2) first.")
        row = self.gw_row()
        if not isinstance(row, dict) and row.frame:
            return self.say("That is a whole phrase with slots in it; the generator lists take words (five at most).")
        if isinstance(row, dict):
            self.app.push_screen(SlotScreen(word, self.universe.name), lambda slot: self.add_to_list(word, slot))
        else:
            self.add_to_list(word, row.slot)

    def gw_add_to_universe(self):
        row = self.gw_row()
        if row is None:
            return self.say("Move to a word first.")
        if isinstance(row, dict):
            return self.say("Dictionary words go on a generator list: press w and pick the slot.")
        if self.universe is None:
            return self.say("There is no universe to add it to: open one in the Builder (F2) first.")
        if row.frame:
            return self.say("That is a whole phrase with slots in it: pick a word, name or thing.")
        try:
            msg, _e = genrewords.add_to_universe(self.universe, self.gw_category(), row.text, row.slot)
        except ValueError as e:
            return self.say(str(e))
        self.refresh_uwords()
        self.say(msg)

    def gw_more_names(self):
        key = self.gw_category()
        names = genrewords.more_names(self.library(), self.gw_genres or [], key, 12, reject=set())
        if not names:
            return self.say("There are too few names in these genres to learn a style from: choose more genres, or Any genre.")
        slot = genrewords.category(key)[2][0]
        self.gw_new = [genrewords.Row(n, tuple(self.gw_genres or []), "", slot, False) for n in names] + self.gw_new[:12]
        self.gw_refresh()
        self.say(f"{len(names)} new names in the style of {', '.join(self.gw_genres) or 'all the genres'}. They are not on any list until you add one (e).")
        self.query_one("#gwlist", OptionList).highlighted = 0

    # --- Story words: what the manuscript really uses ---------------------------------------------------------------------------------------

    def setup_story_scope(self):
        sel = self.query_one("#swscope", Select)
        stories = self.universe.stories() if self.universe is not None else []
        options = [(f"{s.title}", s.slug) for s in stories]
        if len(stories) > 1:
            options.append(("The whole universe", "*"))
        options = options or [("(no story yet)", "none")]
        sel.set_options(options)
        sel.value = self.story.slug if (self.story is not None and any(v == self.story.slug for _, v in options)) else options[0][1]
        self.sw_report = None
        self.sw_set_view()

    def sw_scope_changed(self, value):
        self.sw_report = None
        if self.active_tab() == "t-story":
            self.sw_read()

    def sw_story(self):
        value = self.query_one("#swscope", Select).value
        if self.universe is None or value in ("none", "*", None):
            return None
        return self.universe.story(value)

    def sw_read(self, force=False):
        if self.universe is None:
            self.query_one("#swnote", Static).update("Open a universe in the Builder (F2) to read a story's words.")
            return
        value = self.query_one("#swscope", Select).value
        if value == "none":
            self.query_one("#swnote", Static).update("There is no story to read yet: write something in the Writer first.")
            return
        if self.sw_report is not None and not force:
            return
        try:
            self.sw_report = storywords.analyze(self.universe, self.sw_story())
        except OSError as e:
            return self.say(f"Could not read the manuscript: {e}")
        story = self.sw_story()
        try:
            self.often = overused.report(story) if story is not None else None
        except OSError:
            self.often = None
        self.sw_fill_often()
        items = self.sw_report["items"]
        self.sw_items = items
        lst = self.query_one("#swlist", OptionList)
        lst.clear_options()
        marks = {"name": "◆", "unknown": "?", "variant": "≈"}
        width = min(34, max([len(i.text) for i in items] + [8]))
        lst.add_options([_opt(f" {marks[i.kind]} {i.text:<{width}} ×{i.count:<5} {'not in the dictionary' if i.kind == 'unknown' else i.note}", f"s:{n}")
                         for n, i in enumerate(items)] or [_opt("Nothing to report: every word is one the dictionary knows.", None, style="dim")])
        self.query_one("#swwhere", OptionList).clear_options()
        counts = {k: sum(1 for i in items if i.kind == k) for k in marks}
        why = "" if self.sw_report["dictionary"] else "  (The dictionary is not installed, so only names and look-alikes are shown: storywheel dictionary install.)"
        self.query_one("#swnote", Static).update(
            f"{self.sw_report['words']:,} words read: {counts['variant']} look-alikes ≈, {counts['name']} names ◆, {counts['unknown']} words not in the dictionary ?.{why}")
        if items:
            lst.highlighted = 0
            self.sw_show_where()

    def sw_set_view(self):
        often = self.query_one("#swview", Select).value == "often"
        self.query_one("#swlist").display = not often
        self.query_one("#swoften").display = often
        for bid in ("swspell", "swentity", "swrename"):
            self.query_one("#" + bid).display = not often
        self.query_one("#swwhere", OptionList).clear_options()
        if often and self.often is None and self.sw_story() is None:
            self.query_one("#swnote", Static).update("Often used words are counted for one story: pick a story in the first box.")

    def sw_fill_often(self):
        """The 'Often used' list: the story's most frequent words (everyday words left out), then words repeated close together."""
        lst = self.query_one("#swoften", OptionList)
        lst.clear_options()
        if not self.often:
            lst.add_options([_opt("Pick a story (not the whole universe) to see its often used words.", None, style="dim")])
            return
        options = [_opt(f"Most frequent words (everyday words left out)  ·  {self.often['words']:,} words in all", None, style="bold")]
        for i, r in enumerate(self.often["frequent"]):
            forms = f"   ({', '.join(r['forms'])})" if len(r["forms"]) > 1 else ""
            options.append(_opt(f"  {r['word']}  ×{r['count']}{forms}", f"f:{i}"))
        options.append(_opt("Repeated close together (within about 50 words)", None, style="bold"))
        for i, r in enumerate(self.often["repeats"][:60]):
            options.append(_opt(f"  {r['word']}  ×{r['count']}  in {len(r['clusters'])} place{'s' if len(r['clusters']) != 1 else ''}", f"r:{i}"))
        lst.add_options(options)

    def sw_show_often_where(self):
        lst = self.query_one("#swoften", OptionList)
        if lst.highlighted is None or not self.often:
            return
        oid = lst.get_option_at_index(lst.highlighted).id
        if not oid:
            return
        kind, _, i = oid.partition(":")
        r = (self.often["frequent"] if kind == "f" else self.often["repeats"])[int(i)]
        places = r["where"] if kind == "f" else [o for cluster in r["clusters"] for o in cluster]
        occ = self.query_one("#swwhere", OptionList)
        occ.clear_options()
        occ.add_options([_opt(f"  {o['scene'] or '-':<14} line {o['line']:<5} {o['text']}", f"o:{n}:{o['file']}|{o['line']}") for n, o in enumerate(places)])

    def sw_often_word(self):
        lst = self.query_one("#swoften", OptionList)
        if lst.highlighted is None or not self.often:
            return None
        oid = lst.get_option_at_index(lst.highlighted).id
        if not oid:
            return None
        kind, _, i = oid.partition(":")
        return (self.often["frequent"] if kind == "f" else self.often["repeats"])[int(i)]["word"]

    def sw_item(self):
        lst = self.query_one("#swlist", OptionList)
        if lst.highlighted is None or lst.highlighted >= len(self.sw_items):
            return None
        return self.sw_items[lst.highlighted]

    def sw_show_where(self):
        item = self.sw_item()
        occ = self.query_one("#swwhere", OptionList)
        occ.clear_options()
        if not item:
            return
        occ.add_options([_opt(f"  {o['scene'] or '-':<14} line {o['line']:<5} {o['text']}", f"o:{n}:{o['file']}|{o['line']}") for n, o in enumerate(item.where)]
                        or [_opt("Not written in the manuscript.", None, style="dim")])

    def sw_open_in_writer(self, oid):
        file, _, line = oid.split(":", 2)[2].rpartition("|")
        story = self.sw_story() or self.story
        if story is None or self.universe is None:
            return
        self.b.go("writer", {"universe": self.universe.slug, "story": story.slug, "scene": {"path": file, "line": int(line)}})

    def action_spell(self):
        if self.active_tab() != "t-story":
            return self.say("Add to the spelling list works in Story words.")
        item = self.sw_item()
        if not item or self.universe is None:
            return self.say("Move to a word first.")
        path, new = storywords.add_to_spelling(self.universe, item.text)
        from . import paths
        self.say(f"Added “{item.text}” to the spelling list ({paths.tilde(path)}): the Writer will not mark it." if new
                 else f"“{item.text}” was already on the spelling list.")
        self.sw_read(force=True)

    def action_entity(self):
        tab = self.active_tab()
        if tab == "t-genre":
            return self.gw_add_to_universe()
        if tab != "t-story":
            return self.say("Make an entity works in Story words; Add to universe in Genre words.")
        item = self.sw_item()
        if not item or self.universe is None:
            return self.say("Move to a word first.")
        if item.kind == "name":
            return self.say(f"“{item.text}” is already a {item.note} in {self.universe.name}.")
        from .tui import ChoiceScreen
        def made(kind):
            if not kind:
                return
            e = self.universe.new_entity(kind, item.text, {"role": "supporting"} if kind == "character" else None)
            self.say(f"Made a {kind}, {e.name}, in {self.universe.name}. Open the Builder (F2) to fill it in.")
            self.sw_read(force=True)
        self.app.push_screen(ChoiceScreen(f"Make “{item.text}” a…", [("Character", "character"), ("Place", "place"), ("Thing", "thing")]), made)

    def action_rename(self):
        if self.active_tab() != "t-story":
            return self.say("Rename everywhere works in Story words.")
        item = self.sw_item()
        if not item or self.universe is None:
            return self.say("Move to a word first.")
        from .tui import EditScreen
        suggestion = item.related or item.text
        self.app.push_screen(EditScreen(f"Rename “{item.text}” everywhere in {self.universe.name}", {"new name": suggestion}),
                             lambda got: self.rename_chosen(item, (got or {}).get("new name", "").strip()))

    def rename_chosen(self, item, new):
        if not new or new == item.text:
            return
        from . import rename
        from .builder import RenamePreviewScreen
        entity = item.entity or type("Word", (), {"name": item.text, "path": None, "type": "word", "id": ""})()
        matches = rename.find_matches(self.universe, entity, item.text)
        if not matches and item.entity is None:
            return self.say(f"“{item.text}” is not written anywhere I can change.")
        def done(go):
            for m in matches:
                m.accepted = m.accepted and bool(go)
            if item.entity is not None:
                n = rename.rename_entity(self.universe, item.entity, new, matches)
            else:
                n = rename.apply_matches(self.universe, entity, item.text, new, matches)
            self.say(f"Renamed “{item.text}” to “{new}”: {n} mention{'s' if n != 1 else ''} rewritten. Reload any open Writer buffers.")
            self.sw_read(force=True)
        if not matches:
            return done(False)
        self.app.push_screen(RenamePreviewScreen(item.text, new, matches), done)

    def action_more(self):
        if self.active_tab() != "t-genre":
            return self.say("More like these works in Genre words, for first and last names.")
        if self.gw_category() not in genrewords.NAME_CATEGORIES:
            return self.say("Only names can be invented: pick First names or Last names.")
        self.gw_more_names()

    # --- leaving -----------------------------------------------------------------------------------------------------------------------

    def action_mode(self, which):
        self.b.go(which, self.context())

    def context(self):
        return {"universe": self.universe.slug if self.universe else self.payload.get("universe"),
                "story": self.story.slug if self.story else self.payload.get("story")}

    def action_noop_mode(self):
        self.action_help()

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
