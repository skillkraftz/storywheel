"""Under kitty's keyboard protocol Ctrl+I arrives as CSI 105;5u, which Neovim reads as <C-i>, distinct from Tab. Checked by sending exactly
those bytes to a real terminal-mode Neovim (kitty itself cannot be run here)."""
import fcntl
import os
import pty
import select
import struct
import termios
import time
from pathlib import Path

import pytest

from storywheel import settings, vault, writer

ROOT = Path(__file__).resolve().parent.parent


def type_into_writer(story, keys, env_extra, settle=2.5):
    argv, env = writer.command(story, story.path.parent / "return-k.txt")
    env.update({"PYTHONPATH": str(ROOT), "TERM": "xterm-256color", "STORYWHEEL_INTERNAL_CLIPBOARD": "1"})
    env.pop("KITTY_WINDOW_ID", None)
    env.update(env_extra)
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe(argv[0], argv, env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 36, 120, 0, 0))

    def drain(seconds):
        end = time.time() + seconds
        while time.time() < end:
            if select.select([fd], [], [], 0.1)[0]:
                try:
                    if not os.read(fd, 65536):
                        return
                except OSError:
                    return
    drain(settle)
    for k in keys:
        os.write(fd, k)
        drain(0.4)
    os.write(fd, b"\x1bOQ")                                  # F2: save and leave
    drain(2.0)
    os.waitpid(pid, 0)
    return story.manuscript_path.read_text() if hasattr(story, "manuscript_path") else "".join(p.read_text() for p in story.scenes())


@pytest.fixture
def story(home):
    u = vault.create_universe("U")
    s = u.new_story("S")
    s.add_scene("One", "")
    settings.save_story(s.path, {"spellcheck": False})
    return s


def test_ctrl_i_as_kitty_sends_it_toggles_italic_and_tab_does_not(home, story):
    ctrl_i = b"\x1b[105;5u"
    text = type_into_writer(story, [b"a ", ctrl_i, b"b"], {"KITTY_WINDOW_ID": "1"})
    assert text.strip() == "a *b*", text
    other = vault.create_universe("V").new_story("T")
    other.add_scene("One", "")
    settings.save_story(other.path, {"spellcheck": False})
    text = type_into_writer(other, [b"a ", b"\t", b"b"], {"KITTY_WINDOW_ID": "1"})
    assert "*" not in text, text                                     # (Tab is Tab: it never makes italics)


def test_without_kitty_the_plain_terminal_keeps_ctrl_i_off(home, story):
    text = type_into_writer(story, [b"a ", b"\x1b[105;5u", b"b"], {})
    assert "*b*" not in text.replace("**", "*"), text
