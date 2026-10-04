"""Transparent background: the terminal's default background for (nearly) every cell, in every mode; colors; the Writer's highlight
groups; Neovide's opacity; Settings > Appearance."""
import asyncio
import fcntl
import os
import pty
import select
import struct
import sys
import termios
import time
from pathlib import Path

import pytest

from storywheel import appearance, builder, fill, settings, settings_app, store, tui, vault, writer
from conftest import make_engine, screen_text
from test_notepad import run, story, AT, LINES  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
pyte = pytest.importorskip("pyte", reason="the terminal-screen tests need pyte")


def paint(home, mode, g=None, seconds=5):
    """Run `storywheel <mode>` in a terminal and return {background: cells} of the settled screen."""
    env = dict(os.environ, TERM="xterm-256color", COLORTERM="truecolor", PYTHONPATH=str(ROOT))
    if g is not None:
        settings.save_global(dict(settings.load_global(), **g))
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe(sys.executable, [sys.executable, "-m", "storywheel", mode], env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 140, 0, 0))
    screen = pyte.Screen(140, 40)
    stream = pyte.ByteStream(screen)
    end = time.time() + seconds
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.3)
        if r:
            try:
                stream.feed(os.read(fd, 65536))
            except OSError:
                break
    counts = {}
    for y in range(40):
        for x in range(140):
            counts[screen.buffer[y][x].bg] = counts.get(screen.buffer[y][x].bg, 0) + 1
    try:
        os.kill(pid, 9)
        os.waitpid(pid, 0)
    except OSError:
        pass
    return counts


@pytest.fixture
def world(home):
    u = vault.create_universe("Thornwood", ["western"])
    u.new_entity("character", "Stacie Anderson")
    u.new_story("The Last Clause")
    return u


@pytest.mark.parametrize("mode", ["builder", "wheel", "settings", "words"])
def test_every_mode_uses_the_terminals_default_background(world, mode):
    counts = paint(world.path, mode)
    total = sum(counts.values())
    assert counts.get("default", 0) > 0.97 * total, counts


def test_without_transparency_the_backgrounds_are_colors(world):
    counts = paint(world.path, "builder", {"transparent_background": False})
    assert counts.get("default", 0) < 0.1 * sum(counts.values()), counts


# --- the theme and the colors ------------------------------------------------------------------------------------------------------

def test_colors_are_names_or_hex_or_blank():
    p = appearance.parse_color
    assert p("") == "" and p("  ") == "" and p("White") == "#ffffff" and p("amber") == "#ffbf00"
    assert p("#E8E1D0") == "#e8e1d0" and p("e8e1d0") == "#e8e1d0" and p("#abc") == "#aabbcc"
    assert p("notacolor") is None and p("#12") is None and p("#gggggg") is None


def test_the_theme_follows_the_settings(home):
    t = appearance.make_theme(True, "#e8e1d0", "#ffbf00")
    assert t.ansi and t.background == "ansi_default" and t.foreground == "#e8e1d0" and t.accent == "#ffbf00" and t.primary == "#ffbf00"
    t = appearance.make_theme(True, "", "")
    assert t.foreground == "ansi_default" and t.accent == "ansi_green"
    t = appearance.make_theme(False, "", "#5fafd7")
    assert not t.ansi and t.background != "ansi_default" and t.accent == "#5fafd7"
    settings.save_global(dict(settings.load_global(), transparent_background=False, text_color="cream"))
    assert appearance.values() == (False, "#f3ead3", "")


def test_the_apps_apply_the_theme_and_settings_change_it_live(home):
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            start = app.theme
            s = app.screen
            s.save("transparent_background", False)
            await pilot.pause()
            solid = app.theme
            ok = s.save_color("accent_color", "amber", s.query_one("#f-accent_color"))
            bad = s.save_color("text_color", "nonsense")
            return start, solid, ok, bad, app.current_theme.accent, str(s.query_one("#status").content)
    start, solid, ok, bad, accent, status = asyncio.run(go())
    assert start == "storywheel-clear" and solid == "storywheel-solid" and ok is True and bad is False and accent == "#ffbf00"
    assert "isn't a color I know" in status
    assert settings.load_global()["accent_color"] == "#ffbf00"


def test_settings_has_an_appearance_tab(home):
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            return [p.id for p in app.screen.query("TabPane")], [bool(app.screen.query(f"#f-{k}")) for k in
                    ("transparent_background", "text_color", "accent_color")]
    tabs, fields = asyncio.run(go())
    assert "t-appearance" in tabs and all(fields)


# --- the Writer ------------------------------------------------------------------------------------------------------------------------

BG = """
R.bg = {}
for _, g in ipairs({ "Normal", "NormalNC", "NormalFloat", "FloatBorder", "SignColumn", "EndOfBuffer", "WinSeparator", "StatusLine",
                     "StatusLineNC", "MsgArea", "Pmenu", "SwPad", "FloatTitle", "CursorLine" }) do
  local h = vim.api.nvim_get_hl(0, { name = g, link = false })
  R.bg[g] = h.bg or false
end
R.fg = vim.api.nvim_get_hl(0, { name = "Normal", link = false }).fg or false
"""


def test_the_writer_clears_every_background_group(home, story):
    r = run(story, "", "", BG)
    assert all(v is False for v in r["bg"].values()), r["bg"]


def test_the_writer_keeps_its_colors_when_transparency_is_off(home, story):
    settings.save_story(story.path, {"transparent_background": False})
    r = run(story, "", "", BG)
    assert r["bg"]["Normal"] is not False


def test_the_writers_text_and_accent_colors(home, story):
    settings.save_story(story.path, {"text_color": "#e8e1d0", "accent_color": "#ffbf00"})
    r = run(story, "", "", BG + """
        R.accent = vim.api.nvim_get_hl(0, { name = "SwBreak", link = false }).fg
        R.border = vim.api.nvim_get_hl(0, { name = "FloatBorder", link = false }).fg
    """)
    assert r["fg"] == 0xe8e1d0 and r["accent"] == 0xffbf00 and r["border"] == 0xffbf00
    assert all(v is False for v in r["bg"].values())


def test_floats_and_the_menu_are_transparent_too(home, story):
    r = run(story, "", "<F12>", """
        local m = require('sw.menu').last
        R.winhl = vim.api.nvim_get_option_value("winhighlight", { win = m.win })
        local h = vim.api.nvim_get_hl(0, { name = "NormalFloat", link = false })
        R.bg = h.bg or false
        R.pmenu = vim.api.nvim_get_hl(0, { name = "Pmenu", link = false }).bg or false
        R.sel = vim.api.nvim_get_hl(0, { name = "PmenuSel", link = false }).reverse
    """)
    assert r["bg"] is False and r["pmenu"] is False and r["sel"] is True


def test_the_sidebar_and_pad_windows_use_the_clear_background(home, story):
    r = run(story, "", "<F9>", """
        R.pad = vim.api.nvim_get_hl(0, { name = "SwPad", link = false }).bg or false
        R.left_hl = vim.wo[require('sw.layout').left].winhighlight
    """)
    assert r["pad"] is False and "SwPad" in r["left_hl"]


def test_the_kitty_writer_window_has_its_own_opacity_setting(home, story):
    from storywheel import writer
    settings.save_story(story.path, {"writer_opacity": 0.7})
    kit = lambda: writer.kitty_command("/usr/bin/kitty", settings.load_story(story.path), ["nvim"])
    assert "background_opacity=0.7" in kit()
    settings.save_story(story.path, {"writer_opacity": 0.7, "transparent_background": False})
    assert "background_opacity=1.0" in kit()
    settings.save_story(story.path, {"writer_opacity": 5})
    assert "background_opacity=1.0" in kit()


def test_the_new_settings_reach_the_writer(home):
    u = vault.create_universe("U")
    s = u.new_story("S")
    settings.save_global(dict(settings.load_global(), text_color="#fff", accent_color="amber", writer_opacity=0.6))
    st = settings.load_story(s.path)
    assert st["transparent_background"] is True and st["text_color"] == "#fff" and st["writer_opacity"] == 0.6
