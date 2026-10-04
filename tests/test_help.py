"""Help from one source: the files in storywheel/data/help, key tables made from the real bindings, and every place that shows them."""
import asyncio
import json

import pytest
from textual.widgets import Input, OptionList, Static, TabbedContent

from storywheel import helpdoc, keys, settings, vault, writer
from storywheel.cli import main as cli
from conftest import screen_text

SKIP_NVIM = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


# --- the files ---------------------------------------------------------------------------------------------------------------------

def test_there_is_one_file_per_mode_and_the_topics():
    assert helpdoc.names() == ["wheel", "builder", "writer", "settings", "words", "universes", "structures", "genres-and-flavor", "exports", "backups",
                               "dictionary", "grammar", "keys"]
    for n in helpdoc.names():
        doc = helpdoc.load(n)
        assert doc.title and doc.intro and len(doc.intro) > 60, n
    assert helpdoc.resolve("F3") == "writer" and helpdoc.resolve("export") == "exports" and helpdoc.resolve("gen") == "genres-and-flavor"
    assert helpdoc.resolve("nonsense") is None


def test_every_binding_has_a_one_line_description():
    assert helpdoc.missing_descriptions() == []                      # the failure lists each undescribed binding


def test_the_key_tables_come_from_the_real_bindings():
    from storywheel import tui
    text = helpdoc.text("wheel")
    for b in tui.MainScreen.BINDINGS:
        if b.key.split(",")[0] not in ("f1", "f2", "f3", "f4", "f5"):
            assert helpdoc.key_text(b) in text, b.key
    assert "F1 F2 F3 F4 F5" in text and "Keep this step and move on" in text
    groups = dict(helpdoc.key_groups("builder"))
    assert "Everywhere in the Builder" in groups and "The universes list" in groups and "The stories list" in groups


def test_a_new_binding_without_a_description_is_caught(monkeypatch):
    from textual.binding import Binding
    from storywheel import settings_app
    monkeypatch.setattr(settings_app.SettingsScreen, "BINDINGS", [*settings_app.SettingsScreen.BINDINGS, Binding("z", "zap", "Zap")])
    assert any("zap" in m for m in helpdoc.missing_descriptions())


def test_the_writer_table_uses_the_keys_as_you_set_them(home):
    settings.save_global({"key_italic": "<A-k>"})
    text = helpdoc.text("writer")
    assert "Alt+K" in text and "Italic" in text
    for name in keys.WRITER_KEYS:
        assert name in helpdoc.load("writer").groups[0]["items"], name       # (a new shortcut needs a description)
    for key in keys.RESERVED:
        assert key in helpdoc.load("writer").groups[1]["items"], key


def test_search_finds_sections_across_the_pages():
    hits = helpdoc.search("rhymes")
    assert hits and hits[0][0] in ("dictionary", "words") and any(h[1] == "Rhymes" for h in hits)
    assert helpdoc.search("zzzzqqq") == []
    assert any(n == "writer" for n, _h, _s in helpdoc.search("italic"))
    assert any(n == "exports" and h == "Shunn manuscript format" for n, h, _s in helpdoc.search("shunn"))


def test_text_wraps():
    assert max(len(l) for l in helpdoc.text("builder", 80).splitlines()) <= 80


# --- the command line ---------------------------------------------------------------------------------------------------------------

def test_storywheel_help_lists_prints_and_searches(home, capsys):
    cli(["help"])
    out = capsys.readouterr().out
    assert "wheel" in out and "genres-and-flavor" in out and "storywheel help -s WORDS" in out
    cli(["help", "exports"])
    assert "Shunn manuscript format" in capsys.readouterr().out
    cli(["help", "f2", "--width", "0"])
    assert capsys.readouterr().out.startswith("The Universe Builder\n====")
    cli(["help", "-s", "backups", "restore"])
    assert "backups: Restoring" in capsys.readouterr().out
    cli(["help", "wheel", "--json"])
    doc = json.loads(capsys.readouterr().out)
    assert doc["name"] == "wheel" and [s["heading"] for s in doc["sections"]][:2] == ["About", "Keys"]
    with pytest.raises(SystemExit) as e:
        cli(["help", "nope"])
    assert "No help page called 'nope'" in str(e.value)


# --- the screens ----------------------------------------------------------------------------------------------------------------------

def run_hub(script, start=("builder", {"universe": "thornwood"}), size=(190, 50)):
    from storywheel import hub as hubmod
    from storywheel.engine import Engine
    from storywheel.ratings import Ratings
    async def go():
        app = hubmod.Hub(start, lambda: Engine(seed=3), lambda: Ratings())
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


@pytest.fixture
def world(home):
    u = vault.create_universe("Thornwood", ["western"])
    u.new_story("The Last Clause")
    return u


@pytest.mark.parametrize("key,mode,needle", [("f1", "wheel", "The Wheel rolls a story idea"), ("f2", "builder", "The Builder is where a kept idea grows"),
                                              ("f4", "settings", "Everything about you and the program"), ("f5", "words", "An offline dictionary and thesaurus")])
def test_the_key_of_the_mode_you_are_in_opens_its_help(world, key, mode, needle):
    async def script(app, pilot):
        await pilot.press(key)
        await pilot.pause()
        await pilot.pause()
        if type(app.screen).__name__ != "HelpScreen":
            await pilot.press(key)                                       # (first press moves there; the second, in that mode, opens the help)
            await pilot.pause()
            await pilot.pause()
        first = type(app.screen).__name__
        text = " ".join(screen_text(app).split())
        await pilot.press("escape")
        await pilot.pause()
        return first, text, type(app.screen).__name__
    first, text, after = run_hub(script)
    assert first == "HelpScreen" and needle in text and "Keys" in text and after != "HelpScreen"


def test_question_mark_opens_the_same_help_and_q_closes_it(world):
    async def script(app, pilot):
        await pilot.press("question_mark")
        await pilot.pause()
        opened = type(app.screen).__name__
        await pilot.press("q")
        await pilot.pause()
        return opened, type(app.screen).__name__, app.mode_name
    assert run_hub(script) == ("HelpScreen", "BuilderScreen", "builder")


def test_the_help_screen_searches_scrolls_and_shows_a_message_when_nothing_matches(world):
    async def script(app, pilot):
        await pilot.press("question_mark")
        await pilot.pause()
        full = app.screen.query_one("#help-text", Static).content
        await pilot.press("slash")
        await pilot.pause()
        focused = app.screen.query_one("#help-search", Input).has_focus
        app.screen.query_one("#help-search", Input).value = "rename"
        await pilot.pause()
        narrowed = str(app.screen.query_one("#help-text", Static).content)
        head = str(app.screen.query_one("#help-head", Static).content)
        app.screen.query_one("#help-search", Input).value = "zzzzqq"
        await pilot.pause()
        none = str(app.screen.query_one("#help-text", Static).content)
        await pilot.press("escape")                                      # clears the search first
        await pilot.pause()
        still = type(app.screen).__name__
        return len(str(full)), focused, narrowed, head, none, still
    n, focused, narrowed, head, none, still = run_hub(script)
    assert focused and "Rename the entity" in narrowed and len(narrowed) < n and "match" in head
    assert "Nothing on this page matches" in none and still == "HelpScreen"


def test_the_help_screen_is_scrollable(world):
    async def script(app, pilot):
        await pilot.press("question_mark")
        await pilot.pause()
        scroll = app.screen.query_one("#help-scroll")
        await pilot.press("pagedown")
        await pilot.pause()
        return scroll.max_scroll_y > 0, scroll.scroll_y
    can, y = run_hub(script, size=(150, 30))
    assert can and y > 0


def test_settings_has_a_help_tab_that_searches_everything(world):
    async def script(app, pilot):
        await pilot.press("f4")
        await pilot.pause()
        await pilot.pause()
        app.screen.query_one("#tabs", TabbedContent).active = "t-help"
        await pilot.pause()
        await pilot.pause()
        pages = app.screen.query_one("#helpresults", OptionList).option_count
        app.screen.query_one("#helpsearch", Input).value = "rhymes"
        await pilot.pause()
        results = [str(app.screen.query_one("#helpresults", OptionList).get_option_at_index(i).prompt)
                   for i in range(app.screen.query_one("#helpresults", OptionList).option_count)]
        shown = str(app.screen.query_one("#helptext", Static).content)
        app.screen.query_one("#helpresults", OptionList).highlighted = 1
        await pilot.pause()
        other = str(app.screen.query_one("#helptext", Static).content)
        return pages, results, shown, other
    pages, results, shown, other = run_hub(script)
    assert pages == 13 and results and any("Rhymes" in r for r in results) and "Rhymes" in shown + other and shown != other
    assert "rhymes" in (shown + other).lower()


# --- the Writer ---------------------------------------------------------------------------------------------------------------------

@SKIP_NVIM
def test_f3_in_the_writer_opens_the_same_help_in_a_float_that_escape_closes(home):
    from test_notepad import run as nrun
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    s.add_scene("Opening", "Hello brave world")
    r = nrun(s, "", "<F3>", """
        R.float = vim.api.nvim_win_get_config(0).relative
        R.text = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), '\\n')
        R.mod = vim.bo.modifiable
    """)
    assert r["float"] == "editor" and "The Writer" in r["text"] and "Italic" in r["text"] and "Fixed keys" in r["text"] and r["mod"] is False
    r = nrun(s, "", "<F3><Esc>", "R.float = vim.api.nvim_win_get_config(0).relative; R.mode = vim.fn.mode()")
    assert r["float"] == "" and r["mode"] == "i"                                # (closed; back to typing)
    r = nrun(s, "", "<F3>/Alt<CR>", "R.line = vim.fn.line('.'); R.hl = vim.v.hlsearch")
    assert r["line"] > 1 and r["hl"] == 1                                       # (/ searches inside the float)


@SKIP_NVIM
def test_the_writer_menus_help_item_opens_it_too(home):
    from test_notepad import run as nrun
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    s.add_scene("Opening", "Hello")
    r = nrun(s, "", "", """
        R.labels = {}; for i, it in ipairs(require('sw.menu').items()) do R.labels[i] = it[1] end
    """)
    idx = next(i for i, l in enumerate(r["labels"]) if l == "Help")
    r = nrun(s, "", "<F12>" + "<Down>" * idx + "<CR>", "R.float = vim.api.nvim_win_get_config(0).relative; R.t = vim.api.nvim_buf_get_lines(0, 0, 3, false)[1]")
    assert r["float"] == "editor" and r["t"] == "The Writer"
