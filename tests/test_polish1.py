"""Polish 1: each fix is tested the way it is used, with real keys (and clicks) sent to Neovim's input, never by calling the Lua directly."""
import pytest

from storywheel import vault, writer
from test_notepad import run, LINES, ROOT  # noqa: F401

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


@pytest.fixture
def two(home):
    u = vault.create_universe("Thornwood", ["western"])
    s = u.new_story("The Last Clause")
    s.add_scene("Opening", "The gate was shut.")
    s.add_scene("The Hall", "The guild hall was dark. Priya went in anyway.")
    return s


# --- 1. the scene sidebar ------------------------------------------------------------------------------------------

def test_1_f9_down_enter_then_typing_types_in_scene_two(home, two):
    r = run(two, "", "<F9><Down><CR>dd", LINES + "; R.mode = vim.fn.mode(); R.name = vim.api.nvim_buf_get_name(0)")
    assert r["mode"] == "i"
    text = "\n".join(r["lines"])
    assert "dd" in text and "The guild hall was dark. Priya went in anyway." in text and "* * * The hall" in text


def test_1_f9_then_q_then_typing_types_text(home, two):
    r = run(two, "", "<F9>q" + "hello", LINES + "; R.mode = vim.fn.mode()")
    assert r["mode"] == "i" and any("hello" in l for l in r["lines"])
    assert any(l.startswith("* * * The hall") for l in r["lines"])         # the next scene's marker line is untouched


def test_1_f9_twice_returns_to_typing(home, two):
    r = run(two, "", "<F9><F9>xyz", LINES + "; R.mode = vim.fn.mode()")
    assert r["mode"] == "i" and any("xyz" in l for l in r["lines"])
    assert any(l.startswith("* * * The hall") for l in r["lines"])


def test_1_sidebar_keys_work_straight_after_f9(home, two):
    # no E21 and Down moves the sidebar cursor
    r = run(two, "", "<F9><Down>", "R.row = vim.api.nvim_win_get_cursor(0)[1]; R.win_left = vim.api.nvim_get_current_win() == require('sw.layout').left; R.msg = vim.fn.execute('messages')")
    assert r["win_left"] is True and r["row"] == 2 and "E21" not in r["msg"]
