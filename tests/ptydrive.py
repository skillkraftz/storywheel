"""The Writer in a real terminal (a pty) read back through pyte: keys and mouse go in as the bytes a terminal sends (SGR mouse codes),
and what is on screen comes back as text. This is what the headless driver cannot see (drawing, hit-testing of floats)."""
import fcntl
import os
import pty
import select
import struct
import termios
import time

import pyte

from storywheel import writer
from test_notepad import ROOT


class Term:
    def __init__(self, story, rows=36, cols=120, env_extra=None, settle=2.0):
        argv, env = writer.command(story, story.path.parent / "return-term.txt")
        env.update({"PYTHONPATH": str(ROOT), "TERM": "xterm-256color", "STORYWHEEL_INTERNAL_CLIPBOARD": "1"})
        env.pop("KITTY_WINDOW_ID", None)
        env.update(env_extra or {})
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.ByteStream(self.screen)
        self.rows, self.cols = rows, cols
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            # the size is set before Neovim starts (a real terminal has one from the first byte); setting it afterwards made Neovim 0.11
            # draw its first frame for 24x80 and paint the status line at the wrong place
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
            os.execvpe(argv[0], argv, env)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        self.alive = True
        self.drain(settle)

    def drain(self, seconds=0.4):
        end = time.time() + seconds
        while time.time() < end:
            if select.select([self.fd], [], [], 0.05)[0]:
                try:
                    chunk = os.read(self.fd, 65536)
                except OSError:
                    self.alive = False
                    return
                if not chunk:
                    self.alive = False
                    return
                self.feed(chunk)

    _dcs_open = b""

    def feed(self, chunk):
        """Feed pyte, without the DCS strings (`ESC P ... ESC \\`: Neovim's XTGETTCAP questions). A real terminal swallows them; pyte
        would print their text on the screen, at the cursor, over the writing."""
        data = self._dcs_open + chunk
        self._dcs_open = b""
        out = b""
        while data:
            i = data.find(b"\x1bP")
            if i < 0:
                out += data
                break
            out += data[:i]
            j = data.find(b"\x1b\\", i)
            if j < 0:                           # the string goes on in the next read
                self._dcs_open = data[i:]
                break
            data = data[j + 2:]
        self.stream.feed(out)

    def send(self, data, wait=0.4):
        os.write(self.fd, data.encode() if isinstance(data, str) else data)
        self.drain(wait)

    # keys by name
    KEYS = {"F1": b"\x1bOP", "F2": b"\x1bOQ", "F3": b"\x1bOR", "F4": b"\x1bOS", "F5": b"\x1b[15~", "F6": b"\x1b[17~", "F7": b"\x1b[18~",
            "F8": b"\x1b[19~", "F9": b"\x1b[20~", "F10": b"\x1b[21~", "F12": b"\x1b[24~", "Esc": b"\x1b", "Enter": b"\r", "Down": b"\x1b[B",
            "Up": b"\x1b[A", "Left": b"\x1b[D", "Right": b"\x1b[C", "Ctrl+O": b"\x0f", "Ctrl+R": b"\x12", "Ctrl+Home": b"\x1b[1;5H"}

    def key(self, *names, wait=0.4):
        for n in names:
            self.send(self.KEYS[n], wait)

    def mouse(self, button, action, row, col, wait=0.4):
        """row and col are 0-based screen cells; button: left, right, wheel_up, wheel_down; action: press or release."""
        code = {"left": 0, "middle": 1, "right": 2, "wheel_up": 64, "wheel_down": 65}[button]
        self.send(f"\x1b[<{code};{col + 1};{row + 1}{'M' if action == 'press' else 'm'}", wait)

    def click(self, button, row, col, wait=0.5):
        self.mouse(button, "press", row, col, 0.15)
        self.mouse(button, "release", row, col, wait)

    def lines(self):
        return [l.rstrip() for l in self.screen.display]

    def text(self):
        return "\n".join(self.lines())

    def find(self, needle):
        """(row, col) of the first place `needle` is on the screen, or None."""
        for r, l in enumerate(self.lines()):
            c = l.find(needle)
            if c >= 0:
                return r, c
        return None

    def close(self):
        try:
            os.kill(self.pid, 9)
        except OSError:
            pass
        try:
            os.waitpid(self.pid, 0)
        except OSError:
            pass
