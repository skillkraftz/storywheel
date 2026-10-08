"""
The Settings mode (F4): who you are, goals, the Writer's preferences, export defaults, universe boost, where the
library lives, and your writing statistics. It edits ~/.storywheel/settings.toml; every change is saved as you make it.
"""
import os

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from .grammar_categories import CATEGORIES as GRAMMAR_CATEGORIES
from . import appearance, navigation
from .footer import FitFooter
from .keptscreen import KeptScreen
from .header import QuietHeader
from textual.widgets import DataTable, Footer, Header, Input, Label, OptionList, Select, Static, Switch, TabbedContent, TabPane, Tabs, TextArea
from textual.widgets.option_list import Option

from . import keys, paths, settings, vault, writing_stats


# (tab title, [(key, label, kind, extra, hint)])   kinds: text, multiline, int, float, bool, choice, path
SECTIONS = [
    ("You", [
        ("legal_name", "Legal name", "text", None, "Printed top left of a manuscript's first page."),
        ("author_name", "Byline / pen name", "text", None, "The 'by ...' under the title (blank: your legal name)."),
        ("surname", "Surname for page headers", "text", None, "Blank: the last word of your name."),
        ("address", "Address", "multiline", None, "One line per line; printed on the first page."),
        ("email", "Email", "text", None, ""),
        ("phone", "Phone", "text", None, ""),
    ]),
    ("Goals", [
        ("daily_goal", "Daily word goal", "int", None, "Shown in the Writer's status line and the Builder's stats box. 0 turns it off."),
    ]),
    ("Appearance", [
        ("transparent_background", "Transparent background", "bool", None,
         "Use your terminal's own background, so a translucent terminal (kitty background_opacity...) shows through. Applies to every mode and to the Writer."),
        ("text_color", "Text color", "color", None, "Blank: your terminal's own text color. A name (white, cream, amber...) or a hex color like #e8e1d0."),
        ("accent_color", "Accent color", "color", None, "Titles, borders, scene breaks, the chosen item. Blank: the usual blue. A name or a hex color like #5fafd7."),
    ]),
    ("Writer", [
        ("stats_skip_paste", "Don't count pasted text", "bool", None, "On: words you paste are not added to today's count (they raise the starting total instead). Off: pasted words count as written."),
        ("notepad_mode", "Notepad mode", "bool", None, "On: type like in an ordinary editor (Escape does not change modes). Off: Vim behavior."),
        ("writer_kitty", "Open the Writer in its own kitty window", "bool", None, "When storywheel runs inside kitty, the Writer opens in a window of its own with the font, size, line height, padding and opacity below, and the window closes when you come back. storywheel itself keeps your normal spacing. Outside kitty the Writer runs in this terminal."),
        ("writer_font", "Writer font", "text", None, "Only in the kitty Writer window. Blank: your kitty font."),
        ("writer_font_size", "Writer font size", "int", None, "Points (kitty font_size)."),
        ("writer_line_height", "Writer line height", "int", None, "Percent of the font's own height (kitty modify_font cell_height): 100 is normal, 140 reads like a typewriter, 200 is double spaced."),
        ("writer_padding", "Writer padding", "int", None, "Space around the text in the kitty Writer window (kitty window_padding_width, in points)."),
        ("writer_opacity", "Writer window opacity", "float", None, "Only in the kitty Writer window: 0.85 is a little see-through, 1 is solid. Used when the background is transparent."),
        ("paragraph_spacing", "Space between paragraphs", "int", None, "Extra blank lines shown between paragraphs (shown, not typed). With a kitty line height you may not need any."),
        ("scene_marker", "Scene break in the file", "choice", ["***", "* * *", "#"],
         "What the scene-break key inserts: a line holding only this. (*** or * * * or # lines are all recognized when you type them.)"),
        ("column_width", "Column width", "int", None, "Characters."),
        ("indent_display", "Show a paragraph indent", "bool", None, ""),
        ("typewriter", "Typewriter mode", "bool", None, "Keep the current line in the middle of the screen."),
        ("invisibles", "Show invisibles", "bool", None, ""),
    ]),
    ("Spelling", [
        ("spellcheck", "Spellcheck", "bool", None, "Underlines words the dictionary doesn't know. Names from the universe are known; right-click > Add to Dictionary teaches it more."),
        ("spell_dictionary", "Spellcheck knows the dictionary's words", "bool", None,
         "Besides Neovim's English list, accept every word in the offline dictionary (and its plurals, -ing, -ed, -er, -est forms). Needs the dictionary: run storywheel dictionary install."),
        ("spell_lenient", "Accept words built from known words", "bool", None,
         "A known word plus -ing, -ed, -er, -ers, -ly, -ness, -less, -ful, or un-/re- in front passes (\"gunsmithing\", \"unlatch\"). Needs the dictionary."),
        ("spell_region", "English spelling", "choice", ["US", "UK"],
         "US: realize, color, center. UK: realise, colour, centre. The other region's spellings are marked as misspellings (red). A story can choose its own."),
        ("spell_marks", "Spelling marks", "choice", ["all", "subtle", "misspellings only"],
         "Red wavy = not a word (always shown). Blue = a lowercase letter where a capital belongs (SpellCap); pink = a rare word (SpellRare); "
         "'subtle' shows those two as a faint dotted line; 'misspellings only' hides them. The other region's spelling (SpellLocal; see English spelling) is always red."),
        ("autocorrect", "Autocorrect common slips", "bool", None, "When you finish a word: i → I, im → I'm, dont → don't, teh → the... (a short list; never inside other words)."),
    ]),
    ("Grammar", [
        ("grammar", "Check grammar (LanguageTool)", "bool", None,
         "Off by default. When on, the Writer starts a LanguageTool server on this computer and stops it when you turn this off or leave the Writer. "
         "Install it once with:  storywheel grammar install   (or  --from FILE.zip). Needs Java."),
        *[(key, label, "bool", None, hint) for key, _cid, label, _on, hint in GRAMMAR_CATEGORIES],
        ("grammar_off_rules", "Turned-off rules", "text", None,
         "Rule ids, separated by commas. Right-click a problem in the Writer > Turn off this rule adds one here."),
        ("grammar_pause_ms", "Check after a pause of (ms)", "int", None, "How long you stop typing before changed paragraphs are checked."),
        ("grammar_memory_mb", "Memory limit (MB)", "int", None, "The most memory LanguageTool's Java may use (this computer only). 512 is plenty for a short story; a Raspberry Pi 4 can spare it."),
    ]),
    ("Export", [
        ("font", "Manuscript font", "choice", ["Times New Roman", "Courier New"], "Shunn allows either."),
        ("format", "Default format", "choice", ["short-story", "novel", "screenplay"],
         "For new stories (a story can choose its own). short-story is complete; novel is partial (chapters start new pages); screenplay writes Fountain and exports script pages (PDF, .fdx)."),
        ("export_format", "Default export type", "choice", ["docx", "odt", "pdf", "md", "txt"], "The file type the one-key export makes; you can pick another each time."),
        ("export_title_bold", "Title in bold", "bool", None, "On the first page of the .docx."),
        ("export_header", "Page header shows", "choice", ["full", "keyword"],
         "full: the whole title.  keyword: Shunn's one-word short title (a story can set its own title_keyword)."),
        ("export_anonymous", "Always export anonymously", "bool", None,
         "No name, contact block, byline or surname; the header is 'Title / page'. (Export also has an anonymous choice for one-offs.) "
         "Without a name in Settings > You, exports are anonymous anyway."),
        ("export_one_space", "One space after periods", "bool", None, "Double spaces after . ! ? are exported as one space."),
        ("export_curly_quotes", "Curly quotes in the export", "bool", None, "The manuscript keeps straight quotes (so spellcheck works); the export turns them into “curly” ones."),
        ("script_contd", "Screenplays: automatic (CONT'D)", "bool", None,
         "A character who speaks again after action in the same scene gets (CONT'D) after the name in the PDF (and, dimmed, on screen in the Writer). "
         "Final Draft and Fade In do this by default; turn it off if you prefer the cleaner page. Across a page break (CONT'D) is always added."),
        ("manuscripts_dir", "Manuscripts folder", "path", None,
         "Exports go here, one folder per story: <folder>/<Story Title>/<Story Title> <date>.docx. Default ~/Writing."),
    ]),
    ("Keys", [(k, label, "key", None, f"Default {keys.label(default)}. Type a key such as Alt+I, Ctrl+B or F9 and press Enter.")
              for k, (label, default) in keys.WRITER_KEYS.items()]),
    ("Universes", [
        ("atom_boost", "Preference for your own names", "float", None,
         "How much likelier a universe's own people, places and things are in rolls than ordinary ones. 1.5 is about a strong genre list's share. "
         "Your default for every universe; a universe can set its own."),
    ]),
    ("Library", [
        ("library", "Library folder", "path", None, "Where universes, stories and manuscripts live. Changing it does not move anything."),
    ]),
    ("Updates", [
        ("update_remote", "Git remote to update from", "text", None,
         "Optional. storywheel update uses the folder storywheel was installed from (and that folder's own git remote). This is only for when that folder is gone: a git URL, or user@computer:path."),
    ]),
]

def __getattr__(name):
    if name == "HELP":                                   # (Settings' help page, from storywheel/data/help/settings.md)
        from . import helpdoc
        return helpdoc.text("settings")
    raise AttributeError(name)


def parse(kind, text):
    """(ok, value) for what was typed into a box."""
    text = text.strip()
    if kind == "int":
        return (text.lstrip("-").isdigit() and int(text) >= 0), (int(text) if text.lstrip("-").isdigit() else None)
    if kind == "float":
        try:
            v = float(text)
            return v > 0, v
        except ValueError:
            return False, None
    return True, text


class StatsTable(DataTable):
    """The Stats tab's tables: e edits the highlighted day (the days table), 0 resets it, R forgets a story's history (the stories table)."""
    BINDINGS = [Binding("e", "fix", "Edit"), Binding("0", "zero", "Reset"), Binding("R", "forget", "Forget history")]

    def action_fix(self):
        self.screen.stats_edit(self, False)

    def action_zero(self):
        self.screen.stats_edit(self, True)

    def action_forget(self):
        self.screen.stats_forget(self)


class SettingsScreen(KeptScreen, Screen):
    BINDINGS = navigation.footer([
        *navigation.mode_bindings("settings"),
        Binding("question_mark", "help", "Help", key_display="?"),
        navigation.back_binding(),
        navigation.quit_binding(),
    ], keep=())
    DEFAULT_CSS = """
    SettingsScreen VerticalScroll { padding: 1 2; }
    SettingsScreen #helpresults { height: 10; }
    SettingsScreen #helpscroll { height: 1fr; }
    SettingsScreen #helpsearch { width: 70; }
    SettingsScreen .row { height: auto; margin-bottom: 1; }
    SettingsScreen .label { text-style: bold; }
    SettingsScreen .hint { color: $text-muted; }
    SettingsScreen Input, SettingsScreen Select { width: 70; }
    SettingsScreen TextArea { width: 70; height: 5; }
    SettingsScreen #status { height: 1; padding: 0 1; background: $boost; }
    SettingsScreen DataTable { height: 1fr; min-height: 8; }
    SettingsScreen #summary { padding: 0 1; height: auto; }
    SettingsScreen .title { background: $boost; color: $accent; text-style: bold; padding: 0 1; height: 1; }
    """

    def __init__(self, app_ref):
        super().__init__()
        self.b = app_ref
        self.values = {}

    # --- layout ---------------------------------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield QuietHeader()
        g = settings.load_global()
        g["library"] = str(paths.library_root())
        g["manuscripts_dir"] = str(paths.manuscripts_root())
        self.values = g
        self.help_hits = []
        with TabbedContent(id="tabs"):
            for title, fields in SECTIONS:
                with TabPane(title, id=f"t-{title.lower()}"):
                    with VerticalScroll():
                        for key, label, kind, extra, hint in fields:
                            with Vertical(classes="row"):
                                yield Label(label, classes="label")
                                yield from self.control(key, kind, extra, g.get(key))
                                if hint:
                                    yield Static(hint, classes="hint", markup=False)
                        if title == "Keys":
                            yield Static("These work in the Writer. Always available: Alt+M (menu), Ctrl+B (bold), Ctrl+C/X/V, Ctrl+Z/Y, "
                                         "Ctrl+S, Ctrl+A, Ctrl+F/G, Alt+G, Alt+J (join selected lines), F1-F5 (modes; F5 is Words, carrying the word under the cursor). "
                                         "Changes apply the next time the Writer starts.", markup=False)
                        if title == "Writer":
                            from . import writer as _writer
                            exe = _writer.kitty_exe()
                            where = ("storywheel is running in kitty" if _writer.in_kitty() else
                                     "storywheel is not running in kitty, so the Writer uses this terminal (start storywheel inside kitty)")
                            yield Static(f"kitty: {'installed at ' + exe + '; ' + where if exe else 'not installed (sudo apt install kitty); the Writer uses this terminal'}"
                                         f"      Neovim: {'.'.join(map(str, _writer.nvim_version() or ())) or 'not installed'}",
                                         id="writer-tools", markup=False)
                        if title == "Grammar":
                            from . import grammar as _grammar
                            st = _grammar.status()
                            lines = [_grammar.HELP_NOTE,
                                     f"Java: {st['java_version'] or 'not found'}   LanguageTool: {st['version'] or 'not installed'}   "
                                     f"Memory: wants about {st['memory_needed_mb']} MB" + (f", {st['memory_available_mb']} MB free" if st['memory_available_mb'] else ""),
                                     "Ignored items are kept per story (grammar-ignore.json): list or forget them with  storywheel grammar ignored UNIVERSE/STORY [--clear]"]
                            lines += st["problems"]
                            yield Static("\n".join(lines), id="grammar-tools", markup=False)
                        if title == "Library":
                            yield Static(f"App storage: {paths.home()}\nSettings file: {settings.global_path()}", markup=False)
            with TabPane("Stats", id="t-stats"):
                yield Static("", id="summary", markup=False)
                yield Static("Words per day (newest first)   e edits the day's total, 0 resets it", classes="title")
                yield StatsTable(id="days")
                yield Static("Per story   R forgets the story's recorded history (its manuscript is untouched)", classes="title")
                yield StatsTable(id="stories")
            with TabPane("Help", id="t-help"):
                yield Static("Search every help page: modes, keys, exports, backups, the dictionary, grammar... Pick a result to read it.", classes="hint", markup=False)
                yield Input(placeholder="search the help (empty lists the pages)", id="helpsearch")
                yield OptionList(id="helpresults")
                with VerticalScroll(id="helpscroll"):
                    yield Static("", id="helptext", markup=False)
        yield Static("", id="status", markup=False)
        yield FitFooter()

    def control(self, key, kind, extra, value):
        wid = f"f-{key}"
        if kind == "bool":
            return [Switch(bool(value), id=wid)]
        if kind == "choice":
            options = [(o, o) for o in extra]
            if value and value not in extra:
                options.append((str(value), str(value)))
            return [Select(options, value=value if value else extra[0], allow_blank=False, id=wid)]
        if kind == "multiline":
            return [TextArea(str(value or ""), id=wid)]
        return [Input("" if value is None else str(value), id=wid)]

    def on_mount(self):
        for w in self.query("Input, Select, TextArea"):
            w.compact = True                                        # one line per box, so a whole tab fits on the screen
        self.app.title = "storywheel · Settings"
        self.app.sub_title = "saved as you go"
        self.refresh_stats()
        self.call_after_refresh(self.focus_tab_bar)                 # the first Tab / arrow key must do something: Left and Right change tabs
        self.b.remember()

    def focus_tab_bar(self):
        self.set_focus(self.query_one("#tabs", TabbedContent).query_one(Tabs))

    def on_screen_resume(self):
        self.app.title = "storywheel · Settings"
        self.app.sub_title = "saved as you go"
        self.b.remember()

    def show_tab(self, name):
        """Open a tab by name ('you', 'writer'...) and give the tab bar the focus, so Left and Right move between tabs."""
        tabs = self.query_one("#tabs", TabbedContent)
        if f"t-{name}" in [p.id for p in tabs.query(TabPane)]:
            tabs.active = f"t-{name}"
        self.focus_tab_bar()

    def enter(self, payload=None):
        """Back in Settings from another mode: other modes may have changed settings, so show what is saved now."""
        if payload and payload.get("tab"):
            self.show_tab(payload["tab"])
        g = settings.load_global()
        g["library"] = str(paths.library_root())
        g["manuscripts_dir"] = str(paths.manuscripts_root())
        for key, value in g.items():
            if self.values.get(key) == value:
                continue
            self.values[key] = value                                     # (first, so the widgets' own change events see nothing new)
            for w in self.query(f"#f-{key}"):
                try:
                    if isinstance(w, TextArea):
                        w.text = str(value or "")
                    elif isinstance(w, Switch):
                        w.value = bool(value)
                    elif isinstance(w, Select):
                        w.value = value
                    elif isinstance(w, Input):
                        w.value = "" if value is None else str(value)
                except Exception:
                    pass
        self.refresh_stats()

    def say(self, message):
        self.query_one("#status", Static).update(message)

    # --- saving ----------------------------------------------------------------------------------------------

    def kind_of(self, key):
        for _t, fields in SECTIONS:
            for k, _l, kind, _x, _h in fields:
                if k == key:
                    return kind
        return "text"

    def save(self, key, value):
        if key == "library":
            return self.save_library(value)
        if key == "manuscripts_dir":
            return self.save_manuscripts(value)
        g = settings.load_global()
        g[key] = value
        settings.save_global(g)
        if key in ("transparent_background",):
            appearance.apply(self.app)
        self.say(f"Saved: {key} = {value!r}")

    def save_color(self, key, text, box=None):
        """A color: a name (white, cream, amber...) or a hex color; blank means the terminal's own / the usual. Applies at once."""
        value = appearance.parse_color(text)
        if value is None:
            self.say("That isn't a color I know. Try a name (white, cream, amber, cyan...) or a hex color like #e8e1d0, or leave it blank.")
            return False
        g = settings.load_global()
        g[key] = value
        settings.save_global(g)
        self.values[key] = value
        if box is not None:
            box.value = value
        appearance.apply(self.app)
        self.say(f"Saved: {key.replace('_', ' ')} = {value or '(your terminal\'s own)'}. The Writer picks it up the next time it starts.")
        return True

    def save_key(self, key, text, box=None):
        """Check a shortcut (a form we understand, not used by anything else) and save it in Neovim's notation."""
        ok, value = keys.normalize(text)
        if not ok:
            self.say(value)
            return False
        g = settings.load_global()
        current = {k: g.get(k) or keys.DEFAULTS[k] for k in keys.WRITER_KEYS}
        ok, message = keys.check(key, value, current)
        if not ok:
            self.say(message)
            return False
        g[key] = value
        settings.save_global(g)
        self.values[key] = value
        if box is not None:
            box.value = value
        self.say(f"Saved: {keys.WRITER_KEYS[key][0].lower()} is {keys.label(value)} ({value}). It applies the next time the Writer starts.")
        return True

    def save_manuscripts(self, text):
        new = text.strip()
        if not new:
            return
        from pathlib import Path
        target = Path(new).expanduser()
        lib = paths.library_root()
        if target == lib or lib in target.parents:
            self.say("That is inside your library. Choose a folder outside it (the default is ~/Writing).")
            return
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.say(f"Can't use that folder: {e}")
            return
        g = settings.load_global()
        g["manuscripts_dir"] = str(target)
        settings.save_global(g)
        self.say(f"Exports go to {paths.tilde(target)}.")

    def save_library(self, text):
        new = text.strip()
        if not new:
            return
        from pathlib import Path
        target = Path(new).expanduser()
        old = paths.library_root()
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.say(f"Can't use that folder: {e}")
            return
        g = settings.load_global()
        g["library"] = str(target)
        settings.save_global(g)
        if target != old:
            message = f"The library is now {target}. Nothing was moved: your universes are still in {old}."
        else:
            message = f"The library is {target}."
        if "STORYWHEEL_LIBRARY" in os.environ:
            message += "  (STORYWHEEL_LIBRARY is set in your environment and wins.)"
        self.say(message)

    # --- the Help tab ------------------------------------------------------------------------------------------------------------------

    def help_search(self, query):
        """Fill the results: the pages (no query) or the sections that match every word."""
        from . import helpdoc
        lst = self.query_one("#helpresults", OptionList)
        lst.clear_options()
        self.help_hits = []
        if query.strip():
            self.help_hits = [(n, h) for n, h, _snip in helpdoc.search(query)]
            rows = [Option(Text(f"{helpdoc.load(n).title} › {h}   {snip}"), id=str(i)) for i, (n, h, snip) in enumerate(helpdoc.search(query))]
        else:
            self.help_hits = [(n, None) for n, _t, _k in helpdoc.titles()]
            rows = [Option(Text(f"{t}   ({k})"), id=str(i)) for i, (n, t, k) in enumerate(helpdoc.titles())]
        if not rows:
            rows = [Option(Text("Nothing in the help matches that.", style="dim"), id="none", disabled=True)]
        lst.add_options(rows)
        lst.highlighted = 0 if self.help_hits else None
        if self.help_hits:
            self.show_help(0)
        else:
            self.query_one("#helptext", Static).update("")

    def show_help(self, index):
        from . import helpdoc
        if index is None or index >= len(self.help_hits):
            return
        name, heading = self.help_hits[index]
        if heading is None:
            body = helpdoc.text(name, 90)
        else:
            body = f"{helpdoc.load(name).title} › {heading}\n\n" + dict(helpdoc.sections(name))[heading]
        self.query_one("#helptext", Static).update(Text(body))
        self.query_one("#helpscroll").scroll_home(animate=False)

    def on_option_list_option_highlighted(self, event):
        if event.option_list.id == "helpresults" and event.option_id not in (None, "none"):
            self.show_help(int(event.option_id))

    def on_input_changed(self, event):
        if event.input.id == "helpsearch":
            self.help_search(event.value)
            return
        key = (event.input.id or "")[2:]
        kind = self.kind_of(key)
        if kind in ("path", "key", "color"):
            return                                              # saved on Enter, not on every keystroke
        ok, value = parse(kind, event.value)
        if not ok:
            self.say({"int": "Needs a whole number (0 or more).", "float": "Needs a number above 0."}.get(kind, "?"))
            return
        if self.values.get(key) == value:
            return
        self.values[key] = value
        self.save(key, value)

    def on_input_submitted(self, event):
        if event.input.id == "helpsearch":
            self.query_one("#helpresults").focus()
            return
        key = (event.input.id or "")[2:]
        kind = self.kind_of(key)
        if kind == "path":
            (self.save_manuscripts if key == "manuscripts_dir" else self.save_library)(event.value)
        elif kind == "key":
            self.save_key(key, event.value, event.input)
        elif kind == "color":
            self.save_color(key, event.value, event.input)

    def on_switch_changed(self, event):
        key = (event.switch.id or "")[2:]
        if self.values.get(key) != event.value:
            self.values[key] = event.value
            if self.save(key, bool(event.value)) is False:         # refused: put the switch back
                self.values[key] = not event.value
                event.switch.value = not event.value

    def on_select_changed(self, event):
        key = (event.select.id or "")[2:]
        if event.value is not Select.BLANK and self.values.get(key) != event.value:
            self.values[key] = event.value
            self.save(key, event.value)

    def on_text_area_changed(self, event):
        key = (event.text_area.id or "")[2:]
        if self.values.get(key) != event.text_area.text:
            self.values[key] = event.text_area.text
            self.save(key, event.text_area.text)

    def on_tabbed_content_tab_activated(self, event):
        self.say("")                                                # a message belongs to the tab it was about
        if event.pane.id == "t-stats":
            self.refresh_stats()
        elif event.pane.id == "t-help" and not self.help_hits:
            self.help_search("")

    # --- the Stats tab ----------------------------------------------------------------------------------------

    def refresh_stats(self):
        per_day = writing_stats.days()
        cur, best = writing_stats.streak(per_day)
        today = per_day.get(writing_stats.datetime.date.today().isoformat(), 0)
        goal = int(settings.load_global().get("daily_goal") or 0)
        total = sum(per_day.values())
        rows = writing_stats.per_story()
        lines = [f"Today  {today:,}" + (f" / {goal:,} words   {writing_stats.bar(today, goal)}" if goal else " words"),
                 f"Streak  {cur} day{'s' if cur != 1 else ''}   (best {best})",
                 f"Days written  {sum(1 for w in per_day.values() if w > 0)}     Words recorded  {total:,}"
                 f"     Words in all manuscripts  {sum(r[2] for r in rows):,}"]
        self.query_one("#summary", Static).update("\n".join(lines))
        days = self.query_one("#days", DataTable)
        days.clear(columns=True)
        days.add_column("Date", width=11)
        days.add_column("Words", width=9)
        days.add_column("", width=32)
        top = max(per_day.values(), default=0) or 1
        for date, words in writing_stats.history(90):
            days.add_row(date, f"{words:,}", "█" * max(1 if words else 0, int(30 * words / top)), key=date)
        stories = self.query_one("#stories", DataTable)
        stories.clear(columns=True)
        cells = [(uni, title, f"{words:,}", f"{t:,}" if t else "") for uni, title, words, t in rows]
        for i, head in enumerate(("Universe", "Story", "Words", "Today")):      # (explicit widths: never a clipped name)
            stories.add_column(head, width=max([len(head)] + [len(c[i]) for c in cells]) + 1)
        for c in cells:
            stories.add_row(*c)

    def _row_key(self, table):
        try:
            return table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        except Exception:
            return None

    def stats_edit(self, table, reset):
        """Edit or reset the highlighted day's words (with a confirm)."""
        from .tui import ConfirmScreen, EditScreen
        if table.id != "days":
            return self.say_stats("Choose a day in the Words per day table.")
        date = self._row_key(table)
        if not date:
            return
        now = writing_stats.days().get(date, 0)
        if reset:
            return self.app.push_screen(ConfirmScreen(f"Reset {date} from {now:,} words to 0?"), lambda yes: self._set_day(date, 0) if yes else None)

        def done(out):
            text = str((out or {}).get("words", "")).replace(",", "").strip()
            if not text.isdigit():
                return None if out is None else self.say_stats("Words must be a whole number.")
            self.app.push_screen(ConfirmScreen(f"Change {date} from {now:,} to {int(text):,} words?"),
                                 lambda yes: self._set_day(date, int(text)) if yes else None)
        self.app.push_screen(EditScreen(f"Words written on {date}", {"words": str(now)}), done)

    def _set_day(self, date, words):
        writing_stats.set_day(date, words)
        self.refresh_stats()
        self.say_stats(f"{date} is now {writing_stats.days().get(date, 0):,} words.")

    def stats_forget(self, table):
        from .tui import ConfirmScreen
        if table.id != "stories":
            return self.say_stats("Choose a story in the Per story table.")
        idx = table.cursor_row
        found = [(u, s) for u in vault.list_universes() for s in u.stories()]
        if not 0 <= idx < len(found):
            return
        story = found[idx][1]
        recorded = sum(writing_stats.story_days(story).values())
        self.app.push_screen(ConfirmScreen(f"Forget the recorded writing history of '{story.title}' ({recorded:,} words over its days)?\n"
                                           "Its manuscript is not touched."), lambda yes: self._forget(story) if yes else None)

    def _forget(self, story):
        n = writing_stats.reset_story(story)
        self.refresh_stats()
        self.say_stats(f"Forgot {n:,} recorded words of '{story.title}'.")

    def say_stats(self, text):
        self.notify(text)

    # --- actions ----------------------------------------------------------------------------------------------

    def action_noop(self):
        self.action_help()

    def action_help(self):
        from .helpscreen import HelpScreen as SharedHelp
        self.app.push_screen(SharedHelp("settings"))

    def action_mode(self, which):
        self.b.go(which)


    def action_noop_mode(self):
        self.action_help()

    def action_back_mode(self):
        self.b.go("back", {"fallback": self.b.back})

    action_leave = action_back_mode

    def action_quit_program(self):
        from .tui import ConfirmScreen
        self.app.push_screen(ConfirmScreen(navigation.QUIT_QUESTION), lambda yes: self.b.go("quit") if yes else None)


class SettingsApp(App):
    TITLE = "storywheel · Settings"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = []

    def __init__(self, state_store=None, back="builder"):
        super().__init__()
        appearance.apply(self)
        self.state_store = state_store
        self.back = back
        self.next = None

    def on_mount(self):
        self.push_screen(SettingsScreen(self))

    def remember(self):
        if self.state_store is not None:
            try:
                self.state_store.update(mode="settings", back=self.back)
            except OSError:
                pass

    def go(self, where, payload=None):
        self.next = (where, payload or {})
        self.exit()


def run_settings(state_store=None, back="builder"):
    app = SettingsApp(state_store, back)
    app.run()
    return app.next
