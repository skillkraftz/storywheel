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
from textual.widgets import DataTable, Footer, Header, Input, Label, Select, Static, Switch, TabbedContent, TabPane, TextArea

from . import keys, paths, settings, vault, writing_stats

MODE_KEYS = "F1 Wheel   F2 Builder   F3 Writer   F4 Settings   F5 Words"

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
        ("spell_marks", "Spelling marks", "choice", ["all", "subtle", "misspellings only"],
         "Red wavy = not a word (always shown). Blue = a lowercase letter where a capital belongs (SpellCap); pink = a rare word (SpellRare); "
         "cyan = a word from another region's spelling (SpellLocal). 'subtle' shows those three as a faint dotted line; 'misspellings only' hides them."),
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
         "For new stories (a story can choose its own). short-story is complete; novel is partial (chapters start new pages); screenplay is a stub."),
        ("export_format", "Default export type", "choice", ["docx", "odt", "pdf", "md", "txt"], "The file type the one-key export makes; you can pick another each time."),
        ("export_title_bold", "Title in bold", "bool", None, "On the first page of the .docx."),
        ("export_header", "Page header shows", "choice", ["full", "keyword"],
         "full: the whole title.  keyword: Shunn's one-word short title (a story can set its own title_keyword)."),
        ("export_anonymous", "Always export anonymously", "bool", None,
         "No name, contact block, byline or surname; the header is 'Title / page'. (Export also has an anonymous choice for one-offs.) "
         "Without a name in Settings > You, exports are anonymous anyway."),
        ("export_one_space", "One space after periods", "bool", None, "Double spaces after . ! ? are exported as one space."),
        ("export_curly_quotes", "Curly quotes in the export", "bool", None, "The manuscript keeps straight quotes (so spellcheck works); the export turns them into “curly” ones."),
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

HELP = f"""\
[b]Settings[/b]        {MODE_KEYS}

  Everything is saved as you change it, to ~/.storywheel/settings.toml.
  [b]tab[/b] / [b]shift+tab[/b]  next / previous box        [b]left right[/b] on the tabs  switch tab
  [b]q[/b]  back to where you were    [b]Q[/b]  Quit storywheel (asks first)    [b]F1-F5[/b]  the modes (Wheel, Builder, Writer, Settings, Words)
  The Stats tab shows words per day, your streaks, and per-story totals (what the Writer recorded).
"""


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


class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape,question_mark,q", "close", "Close")]
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    HelpScreen > Static { width: 90; height: auto; border: round $accent; background: $surface; padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Static(HELP)

    def action_close(self):
        self.dismiss(None)


class SettingsScreen(KeptScreen, Screen):
    BINDINGS = navigation.footer([
        *navigation.mode_bindings("settings"),
        Binding("question_mark", "help", "Help", key_display="?"),
        navigation.back_binding(),
        navigation.quit_binding(),
    ], keep=())
    DEFAULT_CSS = """
    SettingsScreen VerticalScroll { padding: 1 2; }
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
                yield Static("Words per day (newest first)", classes="title")
                yield DataTable(id="days")
                yield Static("Per story", classes="title")
                yield DataTable(id="stories")
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
        self.b.remember()

    def on_screen_resume(self):
        self.app.title = "storywheel · Settings"
        self.app.sub_title = "saved as you go"
        self.b.remember()

    def enter(self, payload=None):
        """Back in Settings from another mode: other modes may have changed settings, so show what is saved now."""
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

    def on_input_changed(self, event):
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
        if event.pane.id == "t-stats":
            self.refresh_stats()

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
            days.add_row(date, f"{words:,}", "█" * max(1 if words else 0, int(30 * words / top)))
        stories = self.query_one("#stories", DataTable)
        stories.clear(columns=True)
        cells = [(uni, title, f"{words:,}", f"{t:,}" if t else "") for uni, title, words, t in rows]
        for i, head in enumerate(("Universe", "Story", "Words", "Today")):      # (explicit widths: never a clipped name)
            stories.add_column(head, width=max([len(head)] + [len(c[i]) for c in cells]) + 1)
        for c in cells:
            stories.add_row(*c)

    # --- actions ----------------------------------------------------------------------------------------------

    def action_noop(self):
        self.say("You are in Settings.")

    def action_help(self):
        self.app.push_screen(HelpScreen())

    def action_mode(self, which):
        self.b.go(which)


    def action_noop_mode(self):
        self.say("You are in Settings.")

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
