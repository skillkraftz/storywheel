"""
The Universe Builder (Textual): grow a kept idea into a world.

    left     universes (create, rename, delete) and the open universe's stories
    middle   the universe overview, or a story's outline, in boxes; below, tabs for Characters, Places,
             Things, Groups, Notes with a list and the selected entity as a card of fields
    right    the selected entity's notes (editable), its links, and the stories it appears in

The card works like the Wheel's: left-click (or f) rolls a field, right-click (or e) writes it, the wheel
steps through that field's history, space rolls every blank field, R rolls the whole entity again (asks).
Mode keys everywhere: F1 Wheel, F2 Builder, F3 Writer (and in the Writer, F2 comes back here).
"""
from rich.style import Style
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from .header import QuietHeader
from textual.widgets import Button, Footer, Header, Input, Label, OptionList, Static, TabbedContent, TabPane, Tabs, Tab, TextArea
from textual.widgets.option_list import Option

from . import fill, outline, paths, promote, rename, schemas, settings, state, vault, writing_stats
from .text import motif_from, plural_n
from .tui import CardList, ChoiceScreen, ConfirmScreen, EditScreen, _quiet

MODE_KEYS = "F1 Wheel   F2 Builder   F3 Writer   F4 Settings   F5 Words"
TYPE_ORDER = ["character", "place", "thing", "group", "note"]

HELP = f"""\
[b]Universe Builder[/b]        {MODE_KEYS}

[b]F5[/b]  Words: look up a word, words to learn, My words, overused words (offline)

[b]Entities[/b] (the tabs: 1-5 switch)
  [b]n[/b]        new entity (starts blank)         [b]d[/b]  delete (asks first)
  [b]space[/b]    roll every blank field            [b]R[/b]  roll the whole entity again (asks)
  [b]f[/b]        roll the highlighted field        [b]e[/b]  write it by hand
  [b]r[/b]        rename (shows every match first)  [b]c[/b]  add your own field (write-only)
  Outline (right column, tab 6): click selects and the wheel scrolls; [b]right-click[/b] or [b]e[/b] edits the selected row.
  [b]6[/b] [b]7[/b] [b]8[/b]  right column: Outline, Scenes (Enter opens the Writer at that scene), Notes
  [b]+[/b] [b]-[/b]      like / dislike the line

[b]Mouse[/b]   click a field: roll it.  right-click: write it.  wheel over a field: its history.
         [b]▲ ▼[/b] rate.  Fields marked ✎ are write-only (the generator can't fill them).

[b]Universe and stories[/b]
  [b]N[/b]  new universe   [b]s[/b]  universe settings (genre leanings, exclusions, boosts, own lists)
  [b]o[/b]  universe overview   [b]S[/b]  story settings   [b]G[/b]  your details (author, address...)
  [b]w[/b] or F3  write the open story in the Writer   [b]x[/b]  export it (docx, odt, pdf, md, txt)
  [b]C[/b]  copy the manuscript as plain text   [b]W[/b]  new Wheel draft
  [b]q[/b]  quit   [b]?[/b]  this help   [b]tab[/b]  next list   [b]esc[/b]  back to the card

Roll results use the universe's genre leanings, the entity's other fields, and existing entities
(a rival, owner, parent place or leader can be a real entity).
"""

SETTINGS_FIELDS = [("format", "format (short-story / novel / screenplay)"), ("font", "font"),
                   ("column_width", "column width (characters)"), ("daily_goal", "daily word goal"),
                   ("title_keyword", "short title for page headers"), ("indent_display", "show paragraph indent (true/false)"),
                   ("typewriter", "typewriter mode (true/false)"), ("invisibles", "show invisibles (true/false)"),
                   ("spellcheck", "spellcheck (true/false)")]
GLOBAL_FIELDS = [("legal_name", "legal name (first page, top left)"), ("author_name", "byline / pen name"),
                 ("address", "address (use \\n for new lines)"), ("email", "email"), ("phone", "phone")]


def _as_bool(text, default=False):
    t = str(text).strip().lower()
    return True if t in ("true", "yes", "1", "on") else False if t in ("false", "no", "0", "off") else default


def _as_int(text, default):
    try:
        return int(str(text).strip())
    except ValueError:
        return default


class RenamePreviewScreen(ModalScreen):
    """Every place the old name appears. Enter / click toggles one; a accepts all, n none; p replaces the accepted."""
    BINDINGS = [Binding("a", "all", "All"), Binding("n", "none", "None"), Binding("p", "go", "Replace"),
                Binding("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    RenamePreviewScreen { align: center middle; }
    RenamePreviewScreen > Vertical { width: 92%; max-width: 130; height: auto; max-height: 92%; border: round $accent;
                                     background: $surface; padding: 1 2; }
    RenamePreviewScreen OptionList { height: auto; max-height: 28; }
    RenamePreviewScreen Horizontal { height: 1; margin-top: 1; }
    RenamePreviewScreen #dlg Button { height: 1; border: none; min-width: 8; margin-right: 2; }
    """

    def __init__(self, old, new, matches):
        super().__init__()
        self.old, self.new, self.matches = old, new, matches

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(f"Rename '{self.old}' to '{self.new}'. These places mention the old name. "
                         "Enter toggles one; a = all, n = none, p = replace the checked ones, esc = rename only the entity.",
                         markup=False)
            yield OptionList(id="matches")
            with Horizontal():
                yield _quiet(Button("Replace all (a, then p)", id="all", variant="success"))
                yield _quiet(Button("Replace checked (p)", id="go", variant="primary"))
                yield _quiet(Button("Only rename (esc)", id="cancel"))

    def on_mount(self):
        self.refill()
        self.query_one("#matches", OptionList).focus()

    def refill(self):
        lst = self.query_one("#matches", OptionList)
        keep = lst.highlighted
        lst.clear_options()
        rows = []
        for n, m in enumerate(self.matches):
            t = Text()
            t.append("[x] " if m.accepted else "[ ] ", style="green" if m.accepted else "dim")
            t.append(f"{m.label}", style="bold")
            t.append(f"  line {m.line_no}: ", style="dim")
            t.append(m.context)
            rows.append(Option(t, id=str(n)))
        lst.add_options(rows)
        lst.highlighted = min(keep, len(rows) - 1) if keep is not None else 0

    def on_option_list_option_selected(self, event):
        m = self.matches[int(event.option.id)]
        m.accepted = not m.accepted
        self.refill()

    def action_all(self):
        for m in self.matches:
            m.accepted = True
        self.refill()

    def action_none(self):
        for m in self.matches:
            m.accepted = False
        self.refill()

    def action_go(self):
        self.dismiss(True)

    def on_button_pressed(self, event):
        if event.button.id == "all":
            self.action_all()
            self.dismiss(True)
        else:
            self.dismiss(event.button.id == "go")

    def action_cancel(self):
        self.dismiss(False)


class BuilderHelp(ModalScreen):
    BINDINGS = [Binding("escape,question_mark,q", "close", "Close")]
    DEFAULT_CSS = """
    BuilderHelp { align: center middle; }
    BuilderHelp > VerticalScroll { width: 100; max-width: 100%; height: auto; max-height: 100%;
                                   border: round $accent; background: $surface; padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(HELP)

    def action_close(self):
        self.dismiss(None)


class UniverseList(OptionList):
    BINDINGS = [Binding("n", "act('new')", "New"), Binding("r", "act('rename')", "Rename"),
                Binding("d", "act('delete')", "Delete")]

    def action_act(self, what):
        self.screen.universe_act(what)


class EntityList(OptionList):
    pass


class StoryOptions(OptionList):
    BINDINGS = [Binding("w", "act('write')", "Write"), Binding("d", "act('delete')", "Delete"),
                Binding("x", "act('export')", "Export")]

    def action_act(self, what):
        self.screen.story_act(what)


class BuilderScreen(Screen):
    BINDINGS = [
        Binding("f1", "mode('wheel')", "Wheel", key_display="F1"),
        Binding("f2", "noop_builder", "Builder", key_display="F2"),
        Binding("f3", "writer", "Writer", key_display="F3"),
        Binding("f4", "mode('settings')", "Settings", key_display="F4"),
        Binding("f5", "mode('words')", "Words", key_display="F5"),
        Binding("space", "roll_blank", "Roll blanks"),
        Binding("f", "roll_field", "Roll"),
        Binding("e", "write_field", "Write"),
        Binding("n", "new_entity", "New"),
        Binding("d", "delete_entity", "Delete"),
        Binding("r", "rename", "Rename"),
        Binding("R", "reroll_all", "Reroll all", show=False),
        Binding("c", "custom_field", "Custom field", show=False),
        Binding("plus,equals_sign", "rate(1)", "Rate", key_display="+/-"),
        Binding("minus", "rate(-1)", "Dislike", show=False),
        Binding("1", "tab(0)", "Characters", show=False), Binding("2", "tab(1)", "Places", show=False),
        Binding("3", "tab(2)", "Things", show=False), Binding("4", "tab(3)", "Groups", show=False),
        Binding("5", "tab(4)", "Notes", show=False),
        Binding("6", "rtab('outline')", "Outline", show=False), Binding("7", "rtab('scenes')", "Scenes", show=False),
        Binding("8", "rtab('notes')", "Notes (right)", show=False),
        Binding("N", "new_universe", "New universe", show=False),
        Binding("s", "universe_settings", "Universe settings", show=False),
        Binding("S", "story_settings", "Story settings", show=False),
        Binding("G", "global_settings", "Your details", show=False),
        Binding("o", "overview", "Overview", show=False),
        Binding("w", "writer", "Write story", show=False),
        Binding("x", "export", "Export", show=False),
        Binding("C", "copy_manuscript", "Copy manuscript", show=False),
        Binding("W", "new_draft", "New Wheel draft", show=False),
        Binding("q", "quit_app", "Quit"),
        Binding("question_mark", "help", "Help", key_display="?"),
        Binding("escape", "focus_card", "", show=False),
    ]
    DEFAULT_CSS = """
    BuilderScreen #body { height: 1fr; }
    BuilderScreen #left { width: 21%; min-width: 38; max-width: 46; border: round $primary-darken-2; }
    BuilderScreen #mid { width: 1fr; }
    BuilderScreen #right { width: 24%; min-width: 40; max-width: 52; border: round $primary-darken-2; }
    BuilderScreen .title { background: $primary-darken-2; color: $text; padding: 0 1; height: 1; }
    BuilderScreen #universes { height: auto; max-height: 12; }
    BuilderScreen #stories { height: 1fr; }
    BuilderScreen .btns { height: 1; }
    BuilderScreen .btns Button { height: 1; border: none; min-width: 4; padding: 0; margin-right: 1; }
    BuilderScreen #mid { overflow: hidden; }
    BuilderScreen #left, BuilderScreen #right { overflow: hidden; }
    BuilderScreen #top-box { height: 8; border: round $primary-darken-2; }
    BuilderScreen #stats { padding: 0 1; height: 1fr; }
    BuilderScreen #rtabs { height: 1fr; }
    BuilderScreen #outline, BuilderScreen #scenes { height: 1fr; }
    BuilderScreen #outline-title { padding: 0 1; color: $text-muted; height: auto; }
    BuilderScreen #notes-pane { height: 1fr; }
    BuilderScreen #tabs { height: 3; }
    BuilderScreen #work { height: 1fr; }
    BuilderScreen #entities { width: 32%; min-width: 32; max-width: 40; height: 100%; border: round $primary-darken-2; }
    BuilderScreen #card-box { width: 1fr; height: 100%; overflow: hidden; border: round $primary; }
    /* every list has the same (no) border focused or not, so focusing one never moves or resizes its contents;
       focus is shown by colour */
    BuilderScreen OptionList, BuilderScreen TextArea { border: none; scrollbar-gutter: stable; }
    BuilderScreen OptionList:focus, BuilderScreen TextArea:focus { border: none; background: $boost; }
    BuilderScreen #card { height: 1fr; border: none; }
    BuilderScreen #notes { height: 1fr; min-height: 8; }
    BuilderScreen #links, BuilderScreen #appears { padding: 0 1; height: auto; max-height: 6; }
    BuilderScreen #card-box .title { margin-top: 0; }
    BuilderScreen .title { height: auto; min-height: 1; }
    BuilderScreen #status { height: 1; padding: 0 1; background: $boost; }
    """

    def __init__(self, app_ref, universe_slug=None, story_slug=None):
        super().__init__()
        self.b = app_ref
        self.universe = None
        self.story = None                  # the story whose outline fills the top boxes (None = universe overview)
        self.type = "character"
        self.entity = None
        self.hist = {}                     # (entity id, field key) -> every value that field has had
        self.start = (universe_slug, story_slug)
        self.start_entity = None
        self.filler = None
        self.scene_entries = []
        self.start_rtab = "r-outline"
        self._busy = False

    # --- layout ---------------------------------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield QuietHeader()
        with Horizontal(id="body"):
            with Vertical(id="left"):
                yield Static("Universes", classes="title")
                yield UniverseList(id="universes")
                with Horizontal(classes="btns"):
                    yield _quiet(Button("+New", id="u-new"))
                    yield _quiet(Button("Rename", id="u-rename"))
                    yield _quiet(Button("Del", id="u-delete"))
                yield Static("Stories", id="stories-title", classes="title", markup=False)
                with Horizontal(classes="btns"):
                    yield _quiet(Button("Outline", id="s-open"))
                    yield _quiet(Button("Write", id="s-write"))
                    yield _quiet(Button("Export", id="s-export"))
                    yield _quiet(Button("+Draft", id="s-draft"))
                yield StoryOptions(id="stories")
            with Vertical(id="mid"):
                with Vertical(id="top-box"):
                    yield Static("Writing", id="top-title", classes="title", markup=False)
                    yield Static("", id="stats", markup=False)
                yield Tabs(*[Tab(schemas.get(t)["plural"], id=f"tab-{t}") for t in TYPE_ORDER], id="tabs",
                           active=f"tab-{self.type}")
                with Horizontal(id="work"):
                    with Vertical(id="entities"):
                        yield Static("", id="entities-title", classes="title", markup=False)
                        yield EntityList(id="entity-list")
                        with Horizontal(classes="btns"):
                            yield _quiet(Button("+New", id="e-new"))
                            yield _quiet(Button("Roll blanks", id="e-blank"))
                            yield _quiet(Button("Del", id="e-delete"))
                    with Vertical(id="card-box"):
                        yield Static("", id="card-title", classes="title", markup=False)
                        yield CardList(id="card")
                        yield Static("Links", classes="title", markup=False)
                        yield Static("", id="links", markup=False)
                        yield Static("Appears in", classes="title", markup=False)
                        yield Static("", id="appears", markup=False)
            with Vertical(id="right"):
                with TabbedContent(id="rtabs", initial=self.start_rtab):
                    with TabPane("Outline", id="r-outline"):
                        yield Static("", id="outline-title", markup=False)
                        yield CardList(id="outline")
                    with TabPane("Scenes", id="r-scenes"):
                        yield OptionList(id="scenes")
                        with Horizontal(classes="btns"):
                            yield _quiet(Button("Write here", id="sc-write"))
                            yield _quiet(Button("+Scene", id="sc-add"))
                    with TabPane("Notes", id="r-notes"):
                        yield Static("Free-form notes about the selected entity (saved as you type)", classes="title", markup=False)
                        yield TextArea("", id="notes")
        yield Static("", id="status", markup=False)
        yield Footer()

    def on_mount(self):
        slug, story = self.start
        unis = vault.list_universes()
        self.universe = vault.get_universe(slug) if slug else (unis[0] if unis else None)
        if self.universe and story:
            self.story = self.universe.story(story)
        if self.universe and self.start_entity:
            self.entity = self.universe.entity(self.start_entity)
        self.refresh_all()
        self.outline.history_wheel = False
        self.query_one("#card", CardList).focus()

    # --- small accessors ---------------------------------------------------------------------------------------

    @property
    def card(self):
        return self.query_one("#card", CardList)

    @property
    def outline(self):
        return self.query_one("#outline", CardList)

    top = outline                       # (the outline used to be the box at the top)

    @property
    def elist(self):
        return self.query_one("#entity-list", OptionList)

    def say(self, message):
        self.query_one("#status", Static).update(message)

    def get_filler(self):
        if self.filler is None or self.filler.universe.slug != self.universe.slug:
            self.filler = fill.Filler(self.universe, self.b.make_engine(self.universe))
        return self.filler

    def field_key(self):
        """The key of the highlighted card row ('custom:eye' for your own fields)."""
        if not self.entity:
            return None
        rows = self.rows()
        i = self.card.highlighted
        return rows[min(i or 0, len(rows) - 1)][0] if rows else None

    # --- showing things ------------------------------------------------------------------------------------------

    def rows(self):
        """[(key, label, value text, spec or None, rating)] for the selected entity's card."""
        e = self.entity
        if not e:
            return []
        out = []
        for spec in schemas.get(e.type)["fields"]:
            if spec.get("body"):
                continue
            out.append((spec["key"], spec["label"], self.display(e, spec), spec))
        for k, v in e.custom.items():
            out.append((f"custom:{k}", k, str(v), None))
        return out

    def display(self, e, spec):
        value = e.fields.get(spec["key"])
        if spec.get("kind") == "link":
            t = self.universe.resolve(value)
            return f"→ {t.name}" if t else (value or "")
        if spec.get("kind") == "links":
            return ", ".join((self.universe.resolve(v).name if self.universe.resolve(v) else v) for v in (value or []))
        return value or ""

    def refresh_all(self, lists=True, light=False):
        """Show everything again. With lists=False the entity list and the left column are left exactly as they are
        (only the card, the top box and the right column change): rolling a field must not move the list.
        With light=True (one field of the selected entity changed) only the card and its links are redrawn: the stats
        box, the outline and the notes cannot have changed."""
        self._busy = True
        try:
            if light:
                self.refresh_card()
                self.refresh_right(notes=False, appears=False)
            else:
                if lists:
                    self.refresh_universes()
                    self.refresh_stories()
                self.refresh_top()
                if lists:
                    self.refresh_entities()
                self.refresh_card()
                self.refresh_right()
        finally:
            self._busy = False
        self.app.title = "storywheel · Universe Builder"
        self.app.sub_title = (self.universe.name if self.universe else "no universe yet") + \
            (f" / {self.story.title}" if self.story else "")
        self.b.remember(self)

    def refresh_universes(self):
        lst = self.query_one("#universes", OptionList)
        lst.clear_options()
        rows = []
        for u in vault.list_universes():
            here = self.universe and u.slug == self.universe.slug
            t = Text()
            t.append("▶ " if here else "  ", style="bold cyan")
            n = len(u.entities())
            t.append(u.name, style="bold" if here else "")
            t.append(f"  {n} entit{'y' if n == 1 else 'ies'}", style="dim")
            rows.append(Option(t, id=u.slug))
        if not rows:
            rows.append(Option(Text("(none yet: press N)", style="dim"), id="", disabled=True))
        lst.add_options(rows)
        if self.universe:
            slugs = [u.slug for u in vault.list_universes()]
            if self.universe.slug in slugs:
                lst.highlighted = slugs.index(self.universe.slug)

    def refresh_stories(self):
        lst = self.query_one("#stories", OptionList)
        lst.clear_options()
        rows = []
        if self.universe:
            for s in self.universe.stories():
                t = Text()
                t.append("▶ " if self.story and s.slug == self.story.slug else "  ", style="bold cyan")
                t.append(s.title)
                t.append(f"  {s.word_count()}w", style="dim")
                rows.append(Option(t, id=s.slug))
        if not rows:
            rows.append(Option(Text("(no stories in this universe)", style="dim"), id="", disabled=True))
        lst.add_options(rows)
        self.query_one("#stories-title", Static).update(
            f"Stories in {self.universe.name}" if self.universe else "Stories")

    def top_rows(self):
        """The boxes at the top: the universe overview, or the open story's outline."""
        rows = []
        if self.story:
            rows.extend(outline.rows(self.story))              # plain text, one beat per row (see outline.py)
            st = settings.load_story(self.story.path)
            rows.append(("settings", "Settings", f"{st['format']} · {st['font']} · goal {st['daily_goal']}/day · "
                                                 f"column {st['column_width']}"))
            rows.append(("words", "Manuscript", f"{self.story.word_count()} words in {plural_n(len(self.story.scene_list()), 'scene')}"))
        elif self.universe:
            s = self.universe.settings()
            rows.append(("u:name", "Name", s["name"]))
            rows.append(("u:genres", "Genre leanings", ", ".join(s["genres"]) or "(none: the generator uses everything)"))
            rows.append(("u:mix", "Mix changes", "; ".join(
                x for x in (("exclude " + ", ".join(s["exclude_tags"])) if s["exclude_tags"] else "",
                            ("lists off: " + ", ".join(s["exclude_lists"])) if s["exclude_lists"] else "",
                            ("boost " + ", ".join(f"{k} {v}" for k, v in s["boost"].items())) if s["boost"] else "") if x)
                or "(none)"))
            rows.append(("u:notes", "Notes", s["notes"].replace("\n", "  ") or "(write the world's overview here)"))
            counts = "  ".join(f"{len(self.universe.entities(t))} {schemas.get(t)['plural'].lower()}" for t in TYPE_ORDER)
            rows.append(("u:counts", "Contents", counts))
        return rows

    def refresh_top(self):
        self.refresh_stats()
        self._keep_view(self.outline, self._build_top)
        self.refresh_scenes()

    def refresh_stats(self):
        """The box at the top: today against the goal, streaks, totals for the story and the universe."""
        if not self.universe:
            self.query_one("#stats", Static).update("Nothing here yet: promote a Wheel story or press N for a universe.")
            return
        sm = writing_stats.summary(self.universe, self.story)
        goal = f" / {sm['goal']:,}" if sm["goal"] else ""
        lines = [f"Today    {sm['today']:,}{goal} words" + (f"   {sm['bar']} {sm['percent']}%" if sm["goal"] else ""),
                 f"Streak   {sm['streak']} day{'s' if sm['streak'] != 1 else ''} (best {sm['best_streak']})"
                 f"      This week  {sm['week']:,} words"]
        if self.story:
            lines.append(f"Story    {sm['story_words']:,} words in {plural_n(sm['story_scenes'], 'scene')}: {sm['story_title']}")
        lines.append(f"Universe {sm['universe_words']:,} words across {sm['universe_stories']} stor"
                     f"{'y' if sm['universe_stories'] == 1 else 'ies'}: {sm['universe_name']}")
        self.query_one("#stats", Static).update("\n".join(lines))
        self.query_one("#top-title", Static).update("Writing")

    def refresh_scenes(self):
        """The Scenes tab: the open story's scenes with their first lines; Enter opens the Writer there."""
        lst = self.query_one("#scenes", OptionList)
        keep = lst.highlighted
        lst.clear_options()
        self.scene_entries = self.story.scene_list() if self.story else []
        if not self.story:
            lst.add_options([Option(Text("Open a story (left column) to see its scenes.", style="dim"), id="none", disabled=True)])
            return
        if not self.scene_entries:
            lst.add_options([Option(Text("No scenes yet. +Scene adds one; the Writer makes the first.", style="dim"),
                                    id="none", disabled=True)])
            return
        rows = []
        for e in self.scene_entries:
            t = Text()
            t.append(f"{e['n']:>2} ", style="dim")
            t.append(e["title"], style="bold")
            t.append(f"  {e['words']}w", style="dim")
            t.append("\n   " + (e["first_line"][:46] + ("…" if len(e["first_line"]) > 46 else "")), style="")
            rows.append(Option(t, id=str(e["n"] - 1)))
        lst.add_options(rows)
        lst.highlighted = min(keep, len(rows) - 1) if keep is not None else 0

    def _build_top(self):
        rows = self.top_rows()
        self.query_one("#outline-title", Static).update(
            f"Story outline: {self.story.title}   (o: universe overview)" if self.story
            else (f"Universe: {self.universe.name}" if self.universe else "No universe"))
        lst = self.outline
        keep = lst.highlighted
        lst.clear_options()
        if not rows:
            lst.add_options([Option(Text("Promote a Wheel story, or press N to make a universe.", style="dim"), id="none")])
            return
        width = max(len(r[1]) for r in rows)
        lst.add_options([Option(_text_row(label.ljust(width), value, rated=None), id=key) for key, label, value in rows])
        if keep is not None:
            lst.highlighted = min(keep, len(rows) - 1)

    def refresh_entities(self):
        self._keep_view(self.elist, self._build_entities)

    def _build_entities(self):
        lst = self.elist
        keep_id = self.entity.id if self.entity else None
        lst.clear_options()
        items = self.universe.entities(self.type) if self.universe else []
        self.items = items
        rows = []
        for e in items:
            t = Text()
            t.append(e.name or f"(blank {e.type})", style="" if e.name else "dim italic")
            rows.append(Option(t, id=e.id))
        if not rows:
            rows.append(Option(Text("(none yet: n)", style="dim"), id="", disabled=True))
        lst.add_options(rows)
        ids = [e.id for e in items]
        if keep_id in ids:
            lst.highlighted = ids.index(keep_id)
            self.entity = items[ids.index(keep_id)]
        elif items:
            lst.highlighted = 0
            self.entity = items[0]
        else:
            self.entity = None
        label = schemas.get(self.type)["plural"]
        self.query_one("#entities-title", Static).update(f"{label} ({len(items)})")
        tabs = self.query_one("#tabs", Tabs)
        if tabs.active != f"tab-{self.type}":
            tabs.active = f"tab-{self.type}"

    def refresh_card(self):
        self._keep_view(self.card, self._build_card)

    def _build_card(self):
        e = self.entity
        lst = self.card
        keep = lst.highlighted
        lst.clear_options()
        title = self.query_one("#card-title", Static)
        if not e:
            title.update("")
            lst.add_options([Option(Text("No entity selected. Press n for a new one.", style="dim"), id="none")])
            return
        title.update(f"{schemas.get(e.type)['label']}: {e.name or '(blank)'}   "
                     "click/f: roll   right-click/e: write   wheel: history   space: roll blanks")
        rows = self.rows()
        width = max(len(r[1]) + (2 if (r[3] is None or not schemas.can_roll(r[3])) else 0) for r in rows) + 2      # (room for the ✎ too)
        options = []
        for key, label, value, spec in rows:
            write_only = spec is not None and not schemas.can_roll(spec)
            rating = self.b.rating(self.universe, e, key)
            options.append(Option(_text_row((label + (" ✎" if write_only or spec is None else "")).ljust(width), value,
                                            rated=rating), id=key))
        lst.add_options(options)
        if keep is not None:
            lst.highlighted = min(keep, len(options) - 1)

    def refresh_right(self, notes=True, appears=True):
        e = self.entity
        notes_box = self.query_one("#notes", TextArea)
        links, appears_box = self.query_one("#links", Static), self.query_one("#appears", Static)
        if not e:
            notes_box.load_text("")
            links.update("")
            appears_box.update("")
            return
        body = e.fields.get("body", "") if e.type == "note" else e.body
        if notes and notes_box.text != body:
            self._busy = True
            try:
                notes_box.load_text(body)
            finally:
                self._busy = False
        lines = []
        for label, target in self.universe.links_from(e):
            lines.append(f"{label} → {target.name if hasattr(target, 'name') else target}")
        for label, other in self.universe.links_to(e):
            lines.append(f"← {other.name or other.id} ({label.lower()})")
        links.update("\n".join(lines) or "(no links yet)")
        if appears:
            found = self.universe.appearances(e)
            appears_box.update("\n".join(s.title for s in found) or "(no story mentions it yet)")

    # --- events -----------------------------------------------------------------------------------------------------

    def on_text_area_changed(self, event):
        """Notes are saved as you type."""
        e = self.entity
        if self._busy or e is None or event.text_area.id != "notes":
            return
        text = event.text_area.text
        current = e.fields.get("body", "") if e.type == "note" else e.body
        if text != current:
            if e.type == "note":
                e.fields["body"] = text
            else:
                e.body = text
            self.universe.save_entity(e)

    def on_tabs_tab_activated(self, event):
        if self._busy or not event.tab:
            return
        t = event.tab.id.replace("tab-", "")
        if t != self.type:
            self.type, self.entity = t, None
            self.refresh_entities()
            self.refresh_card()
            self.refresh_right()
            self.b.remember(self)

    def on_option_list_option_highlighted(self, event):
        if self._busy:
            return
        lst = event.option_list.id
        if lst == "entity-list" and event.option.id and (not self.entity or event.option.id != self.entity.id):
            self.entity = self.universe.entity(event.option.id)
            self.refresh_card()
            self.refresh_right()
            self.b.remember(self)

    def on_option_list_option_selected(self, event):
        lst, oid = event.option_list.id, event.option.id
        if lst == "universes" and oid:
            self.open_universe(oid)
        elif lst == "stories" and oid:
            self.story = self.universe.story(oid)
            self.refresh_all()
        elif lst == "entity-list":
            self.card.focus()
        elif lst == "scenes" and oid not in (None, "none"):
            self.write_scene(int(oid))

    def open_universe(self, slug):
        self.universe, self.story, self.entity = vault.get_universe(slug), None, None
        self.filler = None
        self.refresh_all()

    def on_card_list_field(self, event):
        if event.source.id == "outline":
            if event.button == 3:                       # a left-click only selects; right-click (or e) edits
                self.edit_top(event.index)
            return
        key = self._key_at(event.index)
        if event.button == 3:
            self.write_field(key)
        else:
            self.roll_field(key)

    def on_card_list_rate(self, event):
        if event.source.id == "outline":
            return
        self.b.rate(self.universe, self.entity, self._key_at(event.index), event.value)
        self.refresh_card()

    def on_card_list_scrolled(self, event):
        if event.source.id == "outline":
            return
        self.step_history(self._key_at(event.index), event.direction)

    def _key_at(self, index):
        rows = self.rows()
        return rows[min(index, len(rows) - 1)][0] if rows else None

    def on_button_pressed(self, event):
        event.stop()
        name = event.button.id or ""
        {"u-new": self.action_new_universe, "u-rename": lambda: self.universe_act("rename"),
         "u-delete": lambda: self.universe_act("delete"), "s-open": lambda: self.story_act("open"),
         "s-write": self.action_writer, "s-export": self.action_export, "s-draft": self.action_new_draft,
         "sc-write": lambda: self.write_scene(self.query_one("#scenes", OptionList).highlighted),
         "sc-add": self.add_scene, "e-new": self.action_new_entity, "e-blank": self.action_roll_blank,
         "e-delete": self.action_delete_entity}.get(name, lambda: None)()

    # --- field operations --------------------------------------------------------------------------------------------

    def _set(self, key, value, via):
        """Set a field value on the selected entity, recording history. Renaming goes through a preview."""
        e = self.entity
        if key.startswith("custom:"):
            e.custom[key[7:]] = value
            self.universe.save_entity(e)
        else:
            old = e.fields.get(key)
            if key == "name" and old and old != value and isinstance(old, str):
                return self._rename(e, value)
            e.fields[key] = value
            self.universe.save_entity(e)
        self._remember(e, key)
        self.entity = self.universe.entity(e.id) or self.universe.entity(e.type + "-x") or e
        self.refresh_all(light=(key != "name"))
        if via:
            self.say(via)

    def _remember(self, e, key):
        seq = self.hist.setdefault((e.id, key), [])
        v = e.custom.get(key[7:]) if key.startswith("custom:") else e.fields.get(key)
        if v not in ("", None, []) and v not in seq:
            seq.append(v)

    def roll_field(self, key):
        e = self.entity
        if not e or not key:
            return
        if key.startswith("custom:"):
            self.say("Your own fields are write-only: right-click or press e to write it.")
            return
        spec = schemas.field_spec(e.type, key)
        if not schemas.can_roll(spec):
            self.say(f"'{spec['label']}' is write-only: the generator can't fill it. Right-click or press e to write it.")
            return
        old_id = e.id
        self._remember(e, key)                                    # keep what is there, so it can be brought back
        try:
            value = self.get_filler().roll(e, key)
        except fill.NothingToLink as err:
            self.say(str(err))
            return
        self.hist.setdefault((e.id, key), [])
        self._apply_roll(e, key, value, old_id)

    def _apply_roll(self, e, key, value, old_id):
        if key == "name" and e.fields.get("name") and e.fields["name"] != value:
            self._rename(e, value)
            return
        e.fields[key] = value
        self.universe.save_entity(e)
        self._after_save(e, key, old_id)

    def _keep_view(self, lst, build):
        """Rebuild an option list without moving it: the scroll position is put back unless the highlighted row
        would then be out of sight."""
        y = lst.scroll_y
        build()
        def restore():
            h = lst.highlighted
            height = lst.size.height
            if h is None or y <= h < y + height:
                lst.scroll_to(y=y, animate=False)
        lst.call_after_refresh(restore)

    def _after_save(self, e, key, old_id):
        seq = self.hist.setdefault((e.id, key), [])
        v = e.fields.get(key)
        if v not in ("", None, []) and v not in seq:
            seq.append(v)
        for (eid, k) in list(self.hist):
            if eid == old_id and old_id != e.id:                  # a placeholder id became a real one: history follows
                self.hist[(e.id, k)] = self.hist.pop((eid, k))
        self.entity = self.universe.entity(e.id)
        renamed = key == "name" or e.id != old_id
        self.refresh_all(lists=renamed, light=not renamed)

    def write_field(self, key):
        e = self.entity
        if not e or not key:
            return
        if key.startswith("custom:"):
            return self.app.push_screen(EditScreen(f"Write {key[7:]}", {key[7:]: e.custom.get(key[7:], "")}),
                                        lambda out: self._written_custom(key, out))
        spec = schemas.field_spec(e.type, key)
        kind = spec.get("kind")
        if kind == "link":
            options = [("(clear)", "")] + [(f"{o.name or o.id} ({o.type})", o.id) for o in
                                           self.universe.entities(spec.get("target")) if o.id != e.id] + \
                      [("(write plain text instead)", "\x00text")]
            return self.app.push_screen(ChoiceScreen(f"{spec['label']}: link to…", options),
                                        lambda v: self._written_link(key, spec, v))
        if kind == "links":
            options = [(f"{o.name or o.id}", o.id) for o in self.universe.entities(spec.get("target")) if o.id != e.id]
            if not options:
                self.say(f"There is no {schemas.get(spec['target'])['label'].lower()} here to link to yet.")
                return
            return self.app.push_screen(ChoiceScreen(f"{spec['label']}: choose any", options, True,
                                                     e.fields.get(key) or []),
                                        lambda v: self._written_value(key, v) if v is not None else None)
        if kind == "choice":
            options = [(c, c) for c in spec["choices"]] + [("(clear)", "")]
            return self.app.push_screen(ChoiceScreen(f"{spec['label']}:", options),
                                        lambda v: self._written_value(key, v) if v is not None else None)
        current = e.fields.get(key, "")
        self.app.push_screen(EditScreen(f"Write {spec['label'].lower()}", {key: current}),
                             lambda out: self._written_text(key, out))

    def _written_text(self, key, out):
        if out is not None and out[key] != self.entity.fields.get(key, ""):
            self._written_value(key, out[key].strip())

    def _written_custom(self, key, out):
        if out is not None:
            self._set(key, out[key[7:]].strip(), "Written.")

    def _written_link(self, key, spec, value):
        if value is None:
            return
        if value == "\x00text":
            self.app.push_screen(EditScreen(f"{spec['label']} (plain text)", {key: ""}),
                                 lambda out: self._written_text(key, out))
            return
        self._written_value(key, value)

    def _written_value(self, key, value):
        e = self.entity
        old_id = e.id
        if key == "name" and e.fields.get("name") and e.fields["name"] != value:
            return self._rename(e, value)
        e.fields[key] = value
        self.universe.save_entity(e)
        self._after_save(e, key, old_id)
        self.say("Written.")

    def step_history(self, key, direction):
        e = self.entity
        if not e or not key:
            return
        seq = self.hist.get((e.id, key), [])
        current = e.custom.get(key[7:]) if key.startswith("custom:") else e.fields.get(key)
        if current not in seq:
            if current not in ("", None, []):
                seq = seq + [current]
                self.hist[(e.id, key)] = seq
        if current not in seq or len(seq) < 2:
            self.say("This field has no earlier values yet.")
            return
        target = seq.index(current) + (1 if direction > 0 else -1)
        if not 0 <= target < len(seq):
            self.say("That is the " + ("oldest" if direction < 0 else "newest") + " value this field has had.")
            return
        value = seq[target]
        if key.startswith("custom:"):
            e.custom[key[7:]] = value
            self.universe.save_entity(e)
            self.refresh_card()
        elif key == "name" and e.fields.get("name") and e.fields["name"] != value:
            self._rename(e, value)
        else:
            e.fields[key] = value
            self.universe.save_entity(e)
            self.refresh_card()
            self.refresh_right()

    def _rename(self, e, new_name):
        """A name changed on an entity that had one: show every match of the old name, then apply."""
        old = e.name
        matches = rename.find_matches(self.universe, e, old)
        if not matches:
            n = rename.rename_entity(self.universe, e, new_name, [])
            self._renamed(e, old, new_name, n)
            return
        self.app.push_screen(RenamePreviewScreen(old, new_name, matches),
                             lambda go: self._rename_done(e, old, new_name, matches, go))

    def _rename_done(self, e, old, new, matches, go):
        for m in matches:
            m.accepted = m.accepted and bool(go)
        n = rename.rename_entity(self.universe, e, new, matches)
        self._renamed(e, old, new, n)

    def _renamed(self, e, old, new, n):
        self._remember(e, "name")
        self.entity = self.universe.entity(e.id)
        self.refresh_all()
        self.say(f"Renamed '{old}' to '{new}'." + (f" Rewrote {n} mention(s); reload any open Writer buffers." if n else ""))
        self.b.changed = True

    # --- actions ------------------------------------------------------------------------------------------------------------

    def action_roll_field(self):
        self.roll_field(self.field_key())

    def action_write_field(self):
        if self.focused is self.top:
            if self.top.highlighted is not None:
                self.edit_top(self.top.highlighted)
            return
        self.write_field(self.field_key())

    def action_roll_blank(self):
        e = self.entity
        if not e:
            self.say("No entity selected. Press n for a new one.")
            return
        old_id = e.id
        done = self.get_filler().roll_blank(e)
        if not done:
            self.say("Nothing to roll: every field the generator can fill already has a value.")
            return
        self.universe.save_entity(e)
        for k in done:
            self._after_save(e, k, old_id)
            old_id = e.id
        self.say(f"Rolled {len(done)} blank field(s): {', '.join(done)}.")

    def action_reroll_all(self):
        e = self.entity
        if not e:
            return
        self.app.push_screen(ConfirmScreen(f"Roll every field of '{e.name or 'this entity'}' again?\n\n"
                                           "Write-only fields are kept. Names are not searched for in other files."),
                             self._rerolled_all)

    def _rerolled_all(self, yes):
        if not yes:
            return
        e = self.entity
        for spec in schemas.get(e.type)["fields"]:
            if schemas.can_roll(spec):
                self._remember(e, spec["key"])
        old_id = e.id
        done = self.get_filler().reroll_all(e)
        self.universe.save_entity(e)
        for k in done:
            self._after_save(e, k, old_id)
            old_id = e.id
        self.say(f"Rolled {len(done)} field(s) again.")

    def add_scene(self):
        if not self.story:
            self.say("Open a story first (left column).")
            return
        self.app.push_screen(EditScreen("New scene title", {"title": ""}), self._scene_added)

    def _scene_added(self, out):
        if out is not None:
            self.story.append_scene(out["title"].strip() or "")
            self.refresh_top()
            self.say("Scene added. Press Enter on it to write.")

    def action_new_entity(self):
        if not self.universe:
            self.say("Make a universe first (N).")
            return
        e = self.universe.new_entity(self.type)
        self.entity = e
        self.refresh_all()
        self.say(f"A blank {self.type}. space rolls every blank field; f rolls one; e writes one.")
        self.card.focus()

    def action_delete_entity(self):
        e = self.entity
        if e:
            self.app.push_screen(ConfirmScreen(f"Delete '{e.name or e.id}'?\n\nIt moves to the library's .trash folder, "
                                               "and links to it are cleared."), lambda yes: self._deleted(e, yes))

    def _deleted(self, e, yes):
        if yes:
            self.universe.delete_entity(e)
            self.entity = None
            self.refresh_all()
            self.say(f"Deleted '{e.name or e.id}' (it is in .trash).")

    def action_rename(self):
        e = self.entity
        if e:
            self.app.push_screen(EditScreen(f"Rename {e.name or e.id}", {"name": e.name}),
                                 lambda out: self._written_value("name", out["name"].strip())
                                 if out and out["name"].strip() and out["name"].strip() != e.name else None)

    def action_custom_field(self):
        e = self.entity
        if e:
            self.app.push_screen(EditScreen("Add your own field to this entity", {"field name": "", "value": ""}),
                                 self._custom_added)

    def _custom_added(self, out):
        if out and out["field name"].strip():
            self.entity.custom[out["field name"].strip()] = out["value"].strip()
            self.universe.save_entity(self.entity)
            self.refresh_card()
            self.say("Added. Your own fields are write-only.")

    def action_rate(self, value):
        key = self.field_key()
        if self.entity and key:
            self.b.rate(self.universe, self.entity, key, int(value))
            self.refresh_card()

    def action_tab(self, i):
        self.query_one("#tabs", Tabs).active = f"tab-{TYPE_ORDER[int(i)]}"

    def action_overview(self):
        self.story = None
        self.refresh_all()

    def action_focus_card(self):
        self.card.focus()

    def action_help(self):
        self.app.push_screen(BuilderHelp())


    def action_mode(self, which):
        self.b.go(which)

    def action_quit_app(self):
        self.b.go("quit")

    # --- universes and stories ----------------------------------------------------------------------------------------------

    def action_new_universe(self):
        self.app.push_screen(EditScreen("New universe", {"name": "", "genres (comma separated, optional)": ""}),
                             self._universe_made)

    def _universe_made(self, out):
        if out and out["name"].strip():
            genres = [g.strip() for g in out["genres (comma separated, optional)"].split(",") if g.strip()]
            u = vault.create_universe(out["name"].strip(), genres)
            self.open_universe(u.slug)
            self.say(f"Created '{u.name}'. Press n to add an entity.")

    def universe_act(self, what):
        lst = self.query_one("#universes", OptionList)
        i = lst.highlighted
        opt = lst.get_option_at_index(i) if i is not None else None
        if what == "new":
            return self.action_new_universe()
        u = vault.get_universe(opt.id) if opt and opt.id else self.universe
        if not u:
            return
        if what == "rename":
            self.app.push_screen(EditScreen(f"Rename universe {u.name}", {"name": u.name}),
                                 lambda out: self._universe_renamed(u, out))
        elif what == "delete":
            self.app.push_screen(ConfirmScreen(f"Delete the universe '{u.name}' with all its entities, stories and "
                                               "manuscripts?\n\nIt moves to the library's .trash folder."),
                                 lambda yes: self._universe_deleted(u, yes))

    def _universe_renamed(self, u, out):
        if out and out["name"].strip():
            vault.rename_universe(u, out["name"].strip())
            self.refresh_all()
            self.say(f"Renamed to '{out['name'].strip()}'.")

    def _universe_deleted(self, u, yes):
        if yes:
            u.delete()
            if self.universe and self.universe.slug == u.slug:
                rest = vault.list_universes()
                self.universe, self.story, self.entity = (rest[0] if rest else None), None, None
            self.refresh_all()
            self.say(f"Deleted '{u.name}' (moved to .trash).")

    def story_act(self, what):
        lst = self.query_one("#stories", OptionList)
        i = lst.highlighted
        opt = lst.get_option_at_index(i) if i is not None else None
        s = self.universe.story(opt.id) if opt and opt.id and self.universe else self.story
        if not s:
            self.say("This universe has no story yet. Promote one from the Wheel.")
            return
        if what == "open":
            self.story = s
            self.refresh_all()
        elif what == "write":
            self.story = s
            self.action_writer()
        elif what == "export":
            self.story = s
            self.action_export()
        elif what == "delete":
            self.app.push_screen(ConfirmScreen(f"Delete the story '{s.title}' and its manuscript?\n\n"
                                               "It moves to the library's .trash folder."),
                                 lambda yes: self._story_deleted(s, yes))

    def _story_deleted(self, s, yes):
        if yes:
            s.delete()
            if self.story and self.story.slug == s.slug:
                self.story = None
            self.refresh_all()
            self.say(f"Deleted '{s.title}' (moved to .trash).")

    def edit_top(self, index):
        rows = self.top_rows()
        if not rows:
            return
        key, label, value = rows[min(index, len(rows) - 1)]
        if key == "settings":
            return self.action_story_settings()
        if key in ("words", "meta:structure", "u:counts"):
            self.say({"words": "Words are counted from the manuscript files.", "meta:structure": "The structure was set in the Wheel.",
                      "u:counts": "Counts come from the tabs below."}[key])
            return
        if key == "u:genres" or key == "u:mix":
            return self.action_universe_settings()
        if key.split(":")[0] in ("meta", "section", "setting", "beat"):
            return self.app.push_screen(EditScreen(f"Edit {label.lower().rstrip('.')}", {label: outline.raw(self.story, key)}),
                                        lambda out: self._top_written(key, label, out))
        if key.startswith("u:"):
            sett = self.universe.settings()
            raw = sett["name"] if key == "u:name" else sett["notes"]
            self.app.push_screen(EditScreen(f"Edit {label.lower()}", {label: raw}),
                                 lambda out: self._top_written(key, label, out))

    def _top_written(self, key, label, out):
        if out is None:
            return
        text = out[label].strip()
        if key.split(":")[0] in ("meta", "section", "setting", "beat"):
            outline.save(self.story, key, text)
            if key == "meta:title" and text:                 # a new title: what it is 'about' (the motif) follows it
                motif = motif_from(text, lambda: self.story.meta.get("motif", ""))
                self.story.set_meta(motif=motif)
                self.say(f"Title changed; the motif is now '{motif}' (change it in the Wheel's title step if that is wrong).")
        elif key == "u:name":
            vault.rename_universe(self.universe, text or self.universe.name)
        elif key == "u:notes":
            self.universe.save_settings(notes=text)
        self.refresh_all()

    def action_universe_settings(self):
        if not self.universe:
            return
        s = self.universe.settings()
        fields = {"genre leanings (comma separated)": ", ".join(s["genres"]),
                  "exclude tags (comma separated)": ", ".join(s["exclude_tags"]),
                  "exclude lists (comma separated, e.g. job/western)": ", ".join(s["exclude_lists"]),
                  "boosts (tag=1.5, tag=2)": ", ".join(f"{k}={v}" for k, v in s["boost"].items()),
                  "universe atoms boost (blank = your default, " + f"{s['atom_boost'] if not s['atom_boost_own'] else 'now ' + str(s['atom_boost'])})":
                      str(s["atom_boost"]) if s["atom_boost_own"] else ""}
        self.app.push_screen(EditScreen(f"Universe settings: {self.universe.name}   (own lists: {self.universe.lists_dir}"
                                        "  - put atom files there)", fields), self._universe_settings_done)

    def _universe_settings_done(self, out):
        if out is None:
            return
        vals = list(out.values())
        split = lambda t: [x.strip() for x in t.split(",") if x.strip()]
        boost = {}
        for part in split(vals[3]):
            if "=" in part:
                k, _, v = part.partition("=")
                try:
                    boost[k.strip().lower()] = float(v)
                except ValueError:
                    self.say(f"Ignored boost '{part}' (use tag=1.5).")
        try:
            atom_boost = float(vals[4]) if vals[4].strip() else None
        except ValueError:
            atom_boost = None
            self.say("Boost must be a number; your default is used.")
        self.universe.save_settings(genres=[g.lower() for g in split(vals[0])], exclude_tags=[t.lower() for t in split(vals[1])],
                                    exclude_lists=split(vals[2]), boost=boost, atom_boost=atom_boost)
        self.universe.lists_dir.mkdir(exist_ok=True)
        self.filler = None
        self.refresh_all()
        self.say("Universe settings saved. They apply to the next roll.")

    def action_story_settings(self):
        if not self.story:
            self.say("Open a story's outline first.")
            return
        st = settings.load_story(self.story.path)
        fields = {label: str(st.get(key, "")) for key, label in SETTINGS_FIELDS}
        self.app.push_screen(EditScreen(f"Story settings: {self.story.title}   (the Writer reads them on its next start)", fields),
                             self._story_settings_done)

    def _story_settings_done(self, out):
        if out is None:
            return
        st = settings.load_story(self.story.path)
        vals = dict(zip([k for k, _ in SETTINGS_FIELDS], out.values()))
        st["format"] = vals["format"].strip() or st["format"]
        st["font"] = vals["font"].strip() or st["font"]
        st["column_width"] = _as_int(vals["column_width"], st["column_width"])
        st["daily_goal"] = _as_int(vals["daily_goal"], st["daily_goal"])
        st["title_keyword"] = vals["title_keyword"].strip()
        for k in ("indent_display", "typewriter", "invisibles", "spellcheck"):
            st[k] = _as_bool(vals[k], st[k])
        before = settings.load_story(self.story.path)
        settings.save_story(self.story.path, {k: v for k, v in st.items() if before.get(k) != v or k not in before})
        self.refresh_top()
        self.say("Story settings saved.")

    def action_global_settings(self):
        g = settings.load_global()
        fields = {label: str(g.get(key, "")).replace("\n", "\\n") for key, label in GLOBAL_FIELDS}
        self.app.push_screen(EditScreen(f"Your details (settings.toml): used on the manuscript's first page", fields),
                             self._global_done)

    def _global_done(self, out):
        if out is None:
            return
        g = settings.load_global()
        for (key, _label), value in zip(GLOBAL_FIELDS, out.values()):
            g[key] = value.replace("\\n", "\n").strip()
        settings.save_global(g)
        self.say("Saved to settings.toml.")

    def action_noop_builder(self):
        self.say("You are in the Universe Builder.")

    def write_scene(self, index=None):
        """Open the Writer on the open story, at one of its scenes."""
        entry = self.scene_entries[index] if index is not None and index < len(self.scene_entries) else None
        self.b.open_writer(self, scene=entry)

    def action_rtab(self, name):
        self.query_one("#rtabs", TabbedContent).active = f"r-{name}"
        self.b.remember(self)

    def on_tabbed_content_tab_activated(self, event):
        if event.control.id == "rtabs":
            self.b.remember(self)

    def action_writer(self):
        self.b.open_writer(self)

    def action_export(self):
        self.b.export(self)

    def action_copy_manuscript(self):
        self.b.copy_manuscript(self)

    def action_new_draft(self):
        self.b.go("wheel", {"universe": self.universe.slug if self.universe else None, "new": True})


def _text_row(label, value, rated):
    """One line of a card: label, value, and (for entity fields) the clickable ▲ ▼."""
    t = Text()
    t.append(label, style="bold cyan")
    t.append("  ")
    if value:
        t.append(value)
    else:
        t.append("(blank)", style="dim italic")
    if rated is not None:
        t.append(" ")
        t.append(" ▲ ", style=Style(color="green" if rated > 0 else "grey50", bold=rated > 0, meta={"rate": 1}))
        t.append(" ▼ ", style=Style(color="red" if rated < 0 else "grey50", bold=rated < 0, meta={"rate": -1}))
    return t


class BuilderApp(App):
    TITLE = "storywheel · Universe Builder"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = []

    def __init__(self, engine_factory=None, ratings=None, universe=None, story=None, state_store=None, tab=None,
                 entity=None, rtab=None):
        super().__init__()
        self.start_tab, self.start_entity, self.start_rtab = tab, entity, rtab
        self.engine_factory = engine_factory
        self.ratings = ratings
        self.start = (universe, story)
        self.next = None                   # ("wheel", {...}) / ("quit", {}) after the app closes
        self.changed = False
        self.screen_ref = None
        self.state_store = state_store

    def make_engine(self, universe):
        return self.engine_factory(universe) if self.engine_factory else fill.make_engine(universe, ratings=self.ratings)

    def on_mount(self):
        self.screen_ref = BuilderScreen(self, *self.start)
        if self.start_tab in TYPE_ORDER:
            self.screen_ref.type = self.start_tab
        if self.start_rtab in ("r-outline", "r-scenes", "r-notes"):
            self.screen_ref.start_rtab = self.start_rtab
        self.screen_ref.start_entity = self.start_entity
        self.push_screen(self.screen_ref)

    # --- hooks the screen calls ---------------------------------------------------------------------------------------

    def go(self, where, payload=None):
        self.next = (where, payload or {})
        self.exit()

    def remember(self, screen):
        """Record where we are (state.json), so plain `storywheel` comes back here."""
        if self.state_store is not None:
            try:
                self.state_store.update(mode="builder", universe=screen.universe.slug if screen.universe else None,
                                        story=screen.story.slug if screen.story else None, tab=screen.type,
                                        entity=screen.entity.id if screen.entity else None,
                                        rtab=screen.query_one("#rtabs", TabbedContent).active)
            except OSError:
                pass

    def rating(self, universe, entity, key):
        if self.ratings is None:
            return 0
        text = entity.custom.get(key[7:], "") if key.startswith("custom:") else entity.fields.get(key, "")
        if isinstance(text, list):
            text = ", ".join(text)
        return self.ratings.rating_of(f"universe:{universe.slug}", entity.type, key, str(text))

    def rate(self, universe, entity, key, value):
        if self.ratings is None:
            return 0
        text = entity.custom.get(key[7:], "") if key.startswith("custom:") else entity.fields.get(key, "")
        if isinstance(text, list):
            text = ", ".join(text)
        if not text:
            return 0
        return self.ratings.rate(f"universe:{universe.slug}", entity.type, key, str(text), value, None, (),
                                 title=universe.name)

    def open_writer(self, screen, scene=None):
        """Suspend this app, run Neovim on the story (at a scene, if one is given), and come back to exactly where we were."""
        from . import writer
        story = screen.story
        if story is None and screen.universe is not None and screen.universe.stories():
            story = screen.universe.stories()[0]
        if story is None:
            screen.say("This universe has no story to write yet. Promote one from the Wheel (leave it with q).")
            return
        problem = writer.check()
        if problem:
            screen.say(problem)
            return
        screen.story = story
        story.manuscript_dir.mkdir(parents=True, exist_ok=True)
        note = writer.neovide_note(story)
        if self.state_store is not None:
            self.state_store.update(mode="writer", universe=screen.universe.slug, story=story.slug)
        with self.suspend():
            where = writer.run(story, scene)
        if self.state_store is not None:
            self.state_store.update(mode="builder")
        screen.refresh_all()
        screen.say(f"Back from the Writer ({story.word_count()} words in {story.title})." + (f"  {note}" if note else ""))
        if where == "wheel":
            self.go("wheel", {})

    def export(self, screen, fmt=None):
        """Export the open story's manuscript (a format chosen from a list, unless given)."""
        from . import export as exporter
        story = screen.story
        if story is None and screen.universe is not None and screen.universe.stories():
            story = screen.universe.stories()[0]
        if story is None:
            screen.say("This universe has no story to export yet.")
            return
        screen.story = story
        if fmt is None:
            options = [("Word (.docx), Shunn manuscript format", "docx"), ("Word (.docx), anonymous: no name or contact block", "docx-anon"), ("OpenDocument (.odt), needs LibreOffice", "odt"),
                       ("PDF, needs LibreOffice", "pdf"), ("Markdown (.md)", "md"), ("Plain text (.txt)", "txt"),
                       ("Fountain screenplay (.fountain), a stub", "fountain")]
            self.push_screen(ChoiceScreen(f"Export '{story.title}' as…", options),
                             lambda f: self.export(screen, f) if f else None)
            return
        anonymous = None
        if fmt == "docx-anon":
            fmt, anonymous = "docx", True
        screen.say(f"Exporting {story.title} as .{fmt} …")
        self.refresh()
        try:
            result = exporter.export(story, fmt, anonymous=anonymous)
        except exporter.ExportError as e:
            screen.say(str(e))
            return
        screen.say(f"Exported {result['words']:,} words to {result['shown']}" + "".join(f"   Note: {w}" for w in result["warnings"]))
        screen.last_export = result

    def copy_manuscript(self, screen):
        from . import clipboard, export as exporter
        story = screen.story
        if story is None and screen.universe is not None and screen.universe.stories():
            story = screen.universe.stories()[0]
        if story is None:
            screen.say("This universe has no story to copy.")
            return
        text = exporter.plain_text(story)
        if not text.strip():
            screen.say("The manuscript is empty, so there is nothing to copy.")
            return
        how = clipboard.copy(text, self)
        screen.say(f"Copied the manuscript of '{story.title}' ({len(text.split())} words) as plain text via {how}." if how
                   else "Couldn't reach a clipboard (install wl-clipboard or xclip). Export a .txt instead (x).")


def run_builder(universe=None, story=None, ratings=None, state_store=None, tab=None, entity=None, rtab=None):
    app = BuilderApp(ratings=ratings, universe=universe, story=story, state_store=state_store, tab=tab, entity=entity,
                     rtab=rtab)
    app.run()
    return app
