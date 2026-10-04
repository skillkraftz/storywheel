"""The Writer in its own kitty window (font, size, line height, padding, opacity), and paragraph spacing."""
import asyncio
import contextlib
import subprocess

import pytest

from storywheel import builder, settings, settings_app, vault, writer
from test_notepad import run as nrun
from conftest import screen_text


@pytest.fixture
def story(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    s.add_scene("Opening", "First paragraph here.\n\nSecond paragraph here.\n\nThird.")
    return s


# --- launching ------------------------------------------------------------------------------------------------------

KITTY_ENV = {"KITTY_WINDOW_ID": "1", "TERM": "xterm-kitty"}


def inside_kitty(monkeypatch, exe="/usr/bin/kitty"):
    for k, v in KITTY_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(writer, "kitty_exe", lambda: exe)


def outside_kitty(monkeypatch):
    monkeypatch.delenv("KITTY_WINDOW_ID", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")


def test_outside_kitty_the_writer_runs_in_this_terminal(home, story, monkeypatch):
    outside_kitty(monkeypatch)
    monkeypatch.setattr(writer, "kitty_exe", lambda: "/usr/bin/kitty")
    argv, env, note = writer.launch(story)
    assert argv[0].endswith("nvim") and "STORYWHEEL_GUI" not in env and note is None


def test_inside_kitty_the_writer_opens_its_own_window_with_the_writing_settings(home, story, monkeypatch):
    inside_kitty(monkeypatch)
    settings.save_story(story.path, {"writer_font": "Courier Prime", "writer_font_size": 17, "writer_line_height": 160, "writer_padding": 30, "writer_opacity": 0.9})
    argv, env, note = writer.launch(story)
    assert argv[0] == "/usr/bin/kitty" and argv[-1].endswith("nvim") or argv[-1] == writer.nvim_exe()
    for o in ("font_size=17", "modify_font=cell_height 160%", "window_padding_width=30", "background_opacity=0.9", "font_family=Courier Prime",
              "remember_window_size=no", "confirm_os_window_close=0"):
        assert o in argv, o
    assert "--class" in argv and "storywheel-writer" in argv and "--start-as=maximized" in argv
    assert env["STORYWHEEL_GUI"] == "kitty" and env["NVIM_APPNAME"] == "storywheel-writer" and env["STORYWHEEL_STORY_DIR"] == str(story.path)
    assert note is None


def test_a_solid_background_means_a_solid_window(home, story, monkeypatch):
    inside_kitty(monkeypatch)
    settings.save_global({"transparent_background": False})
    assert "background_opacity=1.0" in writer.launch(story)[0]


def test_the_defaults_are_a_typewriter_like_line_height(home, story, monkeypatch):
    inside_kitty(monkeypatch)
    argv = writer.launch(story)[0]
    assert "modify_font=cell_height 140%" in argv and "background_opacity=0.85" in argv and not any(a.startswith("font_family=") for a in argv)


def test_the_setting_turns_it_off_and_a_story_can_opt_out(home, story, monkeypatch):
    inside_kitty(monkeypatch)
    settings.save_global({"writer_kitty": False})
    assert writer.launch(story)[0][0].endswith("nvim")
    settings.save_global({"writer_kitty": True})
    assert writer.launch(story)[0][0] == "/usr/bin/kitty"
    settings.save_story(story.path, {"writer_kitty": False})
    assert writer.launch(story)[0][0].endswith("nvim")


def test_a_missing_kitty_falls_back_to_this_terminal_and_says_so(home, story, monkeypatch):
    inside_kitty(monkeypatch, exe=None)
    argv, env, note = writer.launch(story)
    assert argv[0].endswith("nvim") and "STORYWHEEL_GUI" not in env
    assert "kitty isn't installed" in note and "sudo apt install kitty" in note and writer.kitty_note(story) == note


def test_the_kitty_path_can_be_chosen_with_an_environment_variable(home, monkeypatch):
    monkeypatch.setenv("STORYWHEEL_KITTY", "/definitely/not/here")
    assert writer.kitty_exe() is None


def test_running_the_writer_starts_kitty_and_waits(home, story, monkeypatch):
    inside_kitty(monkeypatch)
    monkeypatch.setattr(writer, "check", lambda: None)
    seen = {}
    monkeypatch.setattr(writer.subprocess, "call", lambda argv, env=None: seen.update(argv=argv, env=env) or 0)
    writer.run(story, {"path": "/x/manuscript.md", "line": 4})
    assert seen["argv"][0] == "/usr/bin/kitty" and seen["env"]["STORYWHEEL_SCENE"] == "/x/manuscript.md:4"


def test_the_start_note_appears_only_outside_kitty_and_says_how_to_install_it(home, monkeypatch):
    outside_kitty(monkeypatch)
    note = writer.kitty_start_note()
    assert note and "kitty gives the Writer a better window" in note and "sudo apt install kitty" in note and "\n" not in note
    inside_kitty(monkeypatch)
    assert writer.kitty_start_note() is None
    outside_kitty(monkeypatch)
    settings.save_global({"writer_kitty": False})
    assert writer.kitty_start_note() is None                                      # (switched off: no nagging)


def test_the_start_note_is_shown_in_the_app_at_start(home, monkeypatch):
    from storywheel import hub
    outside_kitty(monkeypatch)
    app = hub.Hub(None, None, None)
    assert writer.KITTY_NOTE == app.start_note() == app.start_message


def test_the_builder_tells_you_when_kitty_was_missing(home, story, monkeypatch):
    inside_kitty(monkeypatch, exe=None)
    monkeypatch.setattr(writer, "check", lambda: None)
    monkeypatch.setattr(writer, "run", lambda s, scene=None: None)
    async def go():
        app = builder.BuilderApp(universe="thornwood", story="the-last-clause")
        monkeypatch.setattr(app, "suspend", lambda: contextlib.nullcontext())
        async with app.run_test(size=(220, 55)) as pilot:
            await pilot.pause()
            await pilot.press("w")
            await pilot.pause()
            return str(app.screen_ref.query_one("#status").content)
    said = asyncio.run(go())
    assert "Back from the Writer" in said and "kitty isn't installed" in said


def test_the_settings_tab_shows_whether_kitty_and_neovim_are_there(home, monkeypatch):
    monkeypatch.setattr(writer, "kitty_exe", lambda: None)
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            return str(app.screen.query_one("#writer-tools").content)
    text = asyncio.run(go())
    assert "kitty: not installed" in text and "Neovim: 0." in text


def test_the_old_neovide_settings_are_gone_from_settings(home):
    names = [k for _t, fields in settings_app.CATEGORIES for k, *_ in fields] if hasattr(settings_app, "CATEGORIES") else []
    text = open(settings_app.__file__).read()
    assert "Neovide" not in text and "neovide" not in text.lower()
    assert "neovide" not in settings.GLOBAL_DEFAULTS and "line_spacing" not in settings.GLOBAL_DEFAULTS
    assert settings.GLOBAL_DEFAULTS["writer_kitty"] is True and settings.GLOBAL_DEFAULTS["writer_line_height"] == 140
    assert "Neovide" not in open(writer.__file__).read()


# --- inside Neovim -----------------------------------------------------------------------------------------------------

pytestmark_nvim = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


@pytestmark_nvim
def test_in_the_gui_ctrl_i_is_italic(home, story):
    plain = nrun(story, "", "", "R.ctrl = vim.fn.maparg('<C-i>', 'i') ~= ''", term="xterm-256color")
    gui = nrun(story, "", "", "R.ctrl = vim.fn.maparg('<C-i>', 'i') ~= ''", term="xterm-256color", env_extra={"STORYWHEEL_GUI": "kitty"})
    assert plain["ctrl"] is False and gui["ctrl"] is True


@pytestmark_nvim
def test_the_terminal_can_show_extra_space_between_paragraphs(home, story):
    settings.save_story(story.path, {"paragraph_spacing": 2})
    r = nrun(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'First paragraph here.', 'Second paragraph here.', 'Third.' })", "", """
        require("sw.prose").decorate(0)
        local marks = vim.api.nvim_buf_get_extmarks(0, require("sw.prose").ns, 0, -1, { details = true })
        R.rows = {}
        for _, m in ipairs(marks) do if m[4].virt_lines then R.rows[#R.rows + 1] = { m[2], #m[4].virt_lines } end end
        R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
    """)
    assert r["rows"] == [[0, 2], [1, 2]] and r["lines"] == ["First paragraph here.", "Second paragraph here.", "Third."]     # (one line is one paragraph: a gap after each but the last)


@pytestmark_nvim
def test_no_paragraph_spacing_by_default_and_the_kitty_window_shows_it_when_asked(home, story):
    lines = "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'First paragraph here.', 'Second paragraph here.', 'Third.' })"
    count = "require('sw.prose').decorate(0); R.n = 0; for _, m in ipairs(vim.api.nvim_buf_get_extmarks(0, require('sw.prose').ns, 0, -1, { details = true })) do if m[4].virt_lines then R.n = R.n + 1 end end"
    assert nrun(story, lines, "", count) == {"n": 0}
    settings.save_story(story.path, {"paragraph_spacing": 1})
    r2 = nrun(story, lines, "", count, env_extra={"STORYWHEEL_GUI": "kitty"})
    assert r2 == {"n": 2}                                                       # (in the kitty window too: the setting is the writer's, line height or not)


@pytestmark_nvim
def test_the_spacing_is_display_only(home, story):
    settings.save_story(story.path, {"paragraph_spacing": 3})
    nrun(story, "", "typed", "")
    assert story.scenes()[0].read_text().count("\n\n\n") == 0
