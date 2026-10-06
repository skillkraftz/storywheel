"""Help that knows the format (batch 18): the help in tabs. The Writer's float opens on the guide to the story's format (Screenplay, or
Writing prose) beside Writing basics, Keys and Export; every mode's help screen is its guide, Keys and Topics, opening on the mode."""
import asyncio

import pytest
from textual.widgets import Input, Static, Tabs

from storywheel import builder, fill, helpdoc, store, vault, writer
from storywheel.helpscreen import HelpScreen
from conftest import make_engine, run_tui


# --- the tabs ------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("fmt,guide", [("screenplay", "Screenplay"), ("short-film", "Screenplay"), ("feature-film", "Screenplay"),
                                       ("short-story", "Writing prose"), ("novel", "Writing prose"), (None, "Writing prose")])
def test_the_writer_s_tabs_start_with_the_format_s_guide(fmt, guide):
    assert [t for t, _s in helpdoc.tabs("writer", fmt)] == [guide, "Writing basics", "Keys", "Export"]


def test_the_screenplay_tab_covers_what_a_script_writer_needs():
    text = helpdoc.tab_text(helpdoc.tabs("writer", "screenplay")[0][1])[0]
    flat = " ".join(text.split())
    for needle in ("Tab cycles the line you are on", "Enter after a cue", "A new name typed in lowercase", "press Tab on the line to make it a cue",
                   "The sidebar lists the scenes", "The page estimate", "p. 12 of ~15", "The flip test", "Export", "(CONT'D)",
                   "Final Draft and Fade In both do this by default"):
        assert needle in flat, needle


def test_the_writer_s_keys_tab_holds_the_keys_and_the_basics_tab_does_not():
    tabs = dict(helpdoc.tabs("writer", "short-story"))
    assert [h for h, _b in tabs["Keys"]] == ["Keys", "Mouse"]
    assert "Keys" not in [h for h, _b in tabs["Writing basics"]] and "This help" in [h for h, _b in tabs["Writing basics"]]
    assert "Shunn manuscript format" in [h for h, _b in tabs["Export"]] and "Screenplays" in [h for h, _b in tabs["Export"]]


@pytest.mark.parametrize("mode", ["wheel", "builder", "settings", "words"])
def test_every_mode_is_its_guide_keys_and_topics(mode):
    tabs = helpdoc.tabs(mode)
    assert [t for t, _s in tabs][1:] == ["Keys", "Topics"] and tabs[0][0] in helpdoc.load(mode).title
    assert "Keys" in [h for h, _b in tabs[1][1]] and "Keys" not in [h for h, _b in tabs[0][1]]
    assert [h for h, _b in tabs[2][1]] == [helpdoc.load(t).title for t in helpdoc.TOPICS]


def test_the_command_line_prints_the_tabs(home):
    import json, subprocess, sys
    from pathlib import Path
    out = subprocess.run([sys.executable, "-m", "storywheel", "help", "writer", "--tabs", "--json", "--format", "short-film", "--width", "60"],
                         capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent)
    tabs = json.loads(out.stdout)
    assert [t["title"] for t in tabs] == ["Screenplay", "Writing basics", "Keys", "Export"]
    assert all(len(line) <= 60 or line.startswith("  ") for t in tabs for line in t["text"].splitlines())


# --- the help screens in the modes ---------------------------------------------------------------------------------------------

def run_builder(script):
    async def go():
        app = builder.BuilderApp(engine_factory=lambda x: fill.make_engine(x, seed=1))
        async with app.run_test(size=(200, 50)) as pilot:
            await pilot.pause()
            return await script(app, pilot)
    return asyncio.run(go())


def shown(app):
    return str(app.screen.query_one("#help-text", Static).content)


def test_the_builder_s_help_opens_on_its_guide_and_switches_tabs_by_key_and_click(home):
    vault.create_universe("Tabs", ["noir"])
    async def script(app, pilot):
        await pilot.press("question_mark")
        await pilot.pause()
        scr = app.screen
        seen = [(scr.title_now, "Rename the entity" in shown(app))]
        for keys in (("tab",), ("tab",), ("tab",), ("shift+tab",), ("1",)):
            await pilot.press(*keys)
            await pilot.pause()
            seen.append((scr.title_now, "Rename the entity" in shown(app)))
        await pilot.click("#help-tab-1")
        await pilot.pause()
        seen.append((scr.title_now, None))
        return seen
    seen = run_builder(script)
    assert seen[:6] == [("Universe Builder", False), ("Keys", True), ("Topics", False), ("Universe Builder", False), ("Topics", False),
                        ("Universe Builder", False)]
    assert seen[6][0] == "Keys"                                                          # (a click on the tab)


def test_the_wheel_s_help_opens_on_the_wheel_and_topics_has_the_topic_pages(home):
    async def script(app, pilot):
        await pilot.press("question_mark")
        await pilot.pause()
        first = (app.screen.title_now, shown(app))
        await pilot.press("3")
        await pilot.pause()
        return first, shown(app)
    (title, guide), topics = run_tui(store.new_story(), make_engine(home), script)
    assert title == "Wheel" and "Format and structure" in guide
    for page in ("Universes", "Structures", "Screenplays", "Writing prose", "Exports"):
        assert page in topics, page


def test_a_number_typed_in_the_search_box_is_text_not_a_tab(home):
    vault.create_universe("Tabs", ["noir"])
    async def script(app, pilot):
        await pilot.press("question_mark", "slash", "1", "2")
        await pilot.pause()
        return app.screen.query_one("#help-search", Input).value, app.screen.title_now
    assert run_builder(script) == ("12", "Universe Builder")


def test_help_can_open_on_the_tab_that_holds_a_section(home):
    vault.create_universe("Tabs", ["noir"])
    async def script(app, pilot):
        app.push_screen(HelpScreen("builder", section="Keys"))
        await pilot.pause()
        return app.screen.title_now
    assert run_builder(script) == "Keys"


# --- the Writer's float ------------------------------------------------------------------------------------------------------

pytestmark_writer = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


@pytest.fixture
def script_story(home):
    u = vault.create_universe("Thornwood", ["horror"])
    s = u.new_story("The Lamp", {"format": "short-film"})
    s.script_path.parent.mkdir(parents=True, exist_ok=True)
    s.script_path.write_text("Title: The Lamp\n\nINT. ATTIC - NIGHT\n\nDust.\n", encoding="utf-8")
    return s


READ = """
    R.bar = vim.wo.winbar
    R.text = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), '\\n')
    R.float = vim.api.nvim_win_get_config(0).relative
"""


@pytestmark_writer
def test_the_writer_s_help_opens_on_the_screenplay_guide_for_a_script(script_story):
    from test_notepad import run
    r = run(script_story, "", "<F3>", READ)
    assert r["float"] == "editor" and "%#TabLineSel#%1@v:lua.SwHelpTab@ 1 Screenplay" in r["bar"] and "A new name typed in lowercase" in r["text"]


@pytestmark_writer
@pytest.mark.parametrize("keys,title,needle", [("<Tab>", "Writing basics", "This help"), ("<Tab><Tab>", "Keys", "Fixed keys"),
                                               ("<S-Tab>", "Export", "Shunn manuscript format"), ("4", "Export", "Where files go"),
                                               ("2<Tab><Tab><Tab>", "Screenplay", "The flip test")])
def test_tab_shift_tab_and_numbers_switch_the_writer_s_help(script_story, keys, title, needle):
    from test_notepad import run
    r = run(script_story, "", "<F3>" + keys, READ)
    assert f"%#TabLineSel#%" in r["bar"] and r["bar"].split("%#TabLineSel#")[1].split("%X")[0].endswith(f" {title} ")
    assert needle in r["text"]


@pytestmark_writer
def test_a_click_on_a_tab_and_f3_again(script_story):
    from test_notepad import run
    r = run(script_story, "", "<F3>", "SwHelpTab(3)\n" + READ)            # (what a click on the bar's third tab calls)
    assert "Fixed keys" in r["text"]
    r = run(script_story, "", "<F3><F3>", "R.float = vim.api.nvim_win_get_config(0).relative")
    assert r["float"] == ""                                                # (F3 toggles it)
