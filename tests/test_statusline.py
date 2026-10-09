"""The Writer's status line, read off a real terminal emulator (tmux). It looked garbled in an earlier capture made with a
small Python screen emulator (pyte); tmux shows it is clean."""
import shutil
import subprocess
import time

import pytest

from storywheel import settings, vault, writer

pytestmark = [pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed"),
              pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux is not installed")]


def tmux(*args):
    return subprocess.run(["tmux", "-L", "swtest", *args], capture_output=True, text=True)


@pytest.mark.parametrize("notepad", [True, False])
def test_the_status_line_is_clean_on_a_real_terminal(home, notepad):
    u = vault.create_universe("Thornwood")
    s = u.new_story("Tale")
    s.append_scene("Opening", "Stacie ran down the road, past the mill.\n\nIt was dry.")
    settings.save_story(s.path, {"notepad_mode": notepad, "daily_goal": 1000})
    argv, env = writer.command(s, home / "ret.txt")
    exports = " ".join(f"{k}={v!r}" for k, v in env.items() if k.startswith(("NVIM", "XDG", "STORYWHEEL", "PYTHONPATH")))
    tmux("kill-server")
    tmux("new-session", "-d", "-s", "t", "-x", "110", "-y", "30", f"env {exports} TERM=xterm-256color {argv[0]}")
    try:
        end, rows = time.time() + 10, []
        while time.time() < end:
            time.sleep(0.4)
            rows = tmux("capture-pane", "-p", "-t", "t").stdout.split("\n")
            if any("today" in r and "words" in r and "in this scene" in r for r in rows):
                break
        status = [r for r in rows if "in this scene" in r]
        assert len(status) == 1, rows
        assert status[0].strip() == "Tale (short story)  ·  words: in this scene 11 · in the story 11 · today 0 / 1,000 words · 0%"
        assert rows.index(status[0]) == 28                      # the row above the (empty) command line
        assert not any("/tmp" in r or "pytest" in r for r in rows)     # no file path leaks anywhere on the screen
    finally:
        tmux("kill-server")
