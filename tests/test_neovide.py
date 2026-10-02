"""The optional Neovide front-end, the GUI settings, and paragraph spacing in the terminal."""
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

def test_by_default_the_terminal_is_used(home, story, monkeypatch):
    monkeypatch.setattr(writer, "neovide_exe", lambda: "/usr/bin/neovide")
    argv, env, note = writer.launch(story)
    assert argv[0].endswith("nvim") and "STORYWHEEL_GUI" not in env and note is None


def test_neovide_is_used_when_wanted_and_installed(home, story, monkeypatch):
    settings.save_story(story.path, {"neovide": True})
    monkeypatch.setattr(writer, "neovide_exe", lambda: "/usr/bin/neovide")
    argv, env, note = writer.launch(story)
    assert argv == ["/usr/bin/neovide", "--no-fork"] and env["STORYWHEEL_GUI"] == "neovide" and note is None
    assert env["NVIM_APPNAME"] == "storywheel-writer" and env["STORYWHEEL_STORY_DIR"] == str(story.path)   # the same config


def test_a_missing_neovide_falls_back_to_the_terminal_and_says_so(home, story, monkeypatch):
    settings.save_story(story.path, {"neovide": True})
    monkeypatch.setattr(writer, "neovide_exe", lambda: None)
    argv, env, note = writer.launch(story)
    assert argv[0].endswith("nvim") and "STORYWHEEL_GUI" not in env
    assert "Neovide isn't installed" in note and "terminal" in note and "Settings (F4)" in note
    assert writer.neovide_note(story) == note


def test_the_global_setting_turns_it_on_for_every_story(home, story, monkeypatch):
    settings.save_global({"neovide": True})
    monkeypatch.setattr(writer, "neovide_exe", lambda: "/opt/neovide")
    assert writer.launch(story)[0][0] == "/opt/neovide"
    settings.save_story(story.path, {"neovide": False})                # a story can opt out
    assert writer.launch(story)[0][0].endswith("nvim")


def test_the_neovide_path_can_be_chosen_with_an_environment_variable(home, monkeypatch):
    monkeypatch.setenv("STORYWHEEL_NEOVIDE", "/definitely/not/here")
    assert writer.neovide_exe() is None


def test_running_the_writer_starts_neovide_and_waits(home, story, monkeypatch):
    settings.save_story(story.path, {"neovide": True})
    monkeypatch.setattr(writer, "neovide_exe", lambda: "/usr/bin/neovide")
    monkeypatch.setattr(writer, "check", lambda: None)
    seen = {}
    monkeypatch.setattr(writer.subprocess, "call", lambda argv, env=None: seen.update(argv=argv, env=env) or 0)
    writer.run(story, {"path": "/x/manuscript.md", "line": 4})
    assert seen["argv"] == ["/usr/bin/neovide", "--no-fork"] and seen["env"]["STORYWHEEL_SCENE"] == "/x/manuscript.md:4"


def test_the_builder_tells_you_when_neovide_was_missing(home, story, monkeypatch):
    settings.save_story(story.path, {"neovide": True})
    monkeypatch.setattr(writer, "neovide_exe", lambda: None)
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
    assert "Back from the Writer" in said and "Neovide isn't installed" in said


def test_the_settings_tab_shows_whether_neovide_and_neovim_are_there(home, monkeypatch):
    monkeypatch.setattr(writer, "neovide_exe", lambda: None)
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            return str(app.screen.query_one("#writer-tools").content)
    text = asyncio.run(go())
    assert "Neovide: not installed" in text and "Neovim: 0." in text


# --- inside Neovim -----------------------------------------------------------------------------------------------------

pytestmark_nvim = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


@pytestmark_nvim
def test_the_gui_gets_the_font_and_line_spacing_from_the_settings(home, story):
    settings.save_story(story.path, {"writer_font": "Iosevka Term", "writer_font_size": 17, "line_spacing": 21})
    r = nrun(story, "", "", "R.font = vim.o.guifont; R.ls = vim.o.linespace; R.gui = require('sw.gui').active",
             env_extra={"STORYWHEEL_GUI": "neovide"})
    assert r == {"font": "Iosevka\\ Term:h17", "ls": 21, "gui": True}


@pytestmark_nvim
def test_the_gui_default_font_and_the_terminal_leaves_fonts_alone(home, story):
    r = nrun(story, "", "", "R.font = vim.o.guifont; R.ls = vim.o.linespace", env_extra={"STORYWHEEL_GUI": "neovide"})
    assert r["font"] == "monospace:h15" and r["ls"] == 12
    r2 = nrun(story, "", "", "R.font = vim.o.guifont; R.ls = vim.o.linespace; R.gui = require('sw.gui').active")
    assert r2["font"] == "" and r2["ls"] == 0 and r2["gui"] is False


@pytestmark_nvim
def test_in_the_gui_ctrl_i_is_italic(home, story):
    plain = nrun(story, "", "", "R.ctrl = vim.fn.maparg('<C-i>', 'i') ~= ''", term="xterm-256color")
    gui = nrun(story, "", "", "R.ctrl = vim.fn.maparg('<C-i>', 'i') ~= ''", term="xterm-256color", env_extra={"STORYWHEEL_GUI": "neovide"})
    assert plain["ctrl"] is False and gui["ctrl"] is True


@pytestmark_nvim
def test_the_terminal_can_show_extra_space_between_paragraphs(home, story):
    settings.save_story(story.path, {"paragraph_spacing": 2})
    r = nrun(story, "", "", """
        local marks = vim.api.nvim_buf_get_extmarks(0, require("sw.prose").ns, 0, -1, { details = true })
        R.rows = {}
        for _, m in ipairs(marks) do if m[4].virt_lines then R.rows[#R.rows + 1] = { m[2], #m[4].virt_lines } end end
        R.lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
    """)
    assert r["rows"] == [[1, 2], [3, 2]] and r["lines"] == ["First paragraph here.", "", "Second paragraph here.", "", "Third."]


@pytestmark_nvim
def test_no_paragraph_spacing_by_default_and_none_in_the_gui(home, story):
    r = nrun(story, "", "", "R.n = 0; for _, m in ipairs(vim.api.nvim_buf_get_extmarks(0, require('sw.prose').ns, 0, -1, { details = true })) do if m[4].virt_lines then R.n = R.n + 1 end end")
    assert r == {"n": 0}
    settings.save_story(story.path, {"paragraph_spacing": 1})
    r2 = nrun(story, "", "", "R.n = 0; for _, m in ipairs(vim.api.nvim_buf_get_extmarks(0, require('sw.prose').ns, 0, -1, { details = true })) do if m[4].virt_lines then R.n = R.n + 1 end end",
              env_extra={"STORYWHEEL_GUI": "neovide"})
    assert r2 == {"n": 0}


@pytestmark_nvim
def test_the_spacing_is_display_only(home, story):
    settings.save_story(story.path, {"paragraph_spacing": 3})
    nrun(story, "", "typed", "")
    assert story.scenes()[0].read_text().count("\n\n\n") == 0
