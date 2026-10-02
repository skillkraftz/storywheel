"""Moving between modes and leaving: the same keys and words in every footer and help screen.

    F1-F5   the five modes (one footer entry says so)
    q       back: to the mode you came from (or closes a panel or dialog)
    Q       quit storywheel (asks first)
"""
from textual.binding import Binding

MODES = (("f1", "wheel", "Wheel"), ("f2", "builder", "Builder"), ("f3", "writer", "Writer"), ("f4", "settings", "Settings"),
         ("f5", "words", "Words"))
MODE_LABEL = "Modes: Wheel · Builder · Writer · Settings · Words"
QUIT_LABEL = "Quit storywheel"
QUIT_QUESTION = "Quit storywheel?  Everything is saved."
NO_BACK = "There is nothing to go back to: you started here. Press Q to quit storywheel."


def mode_bindings(current, writer_action=None):
    """Bindings for F1-F5. Only F1 is listed in the footer (as 'F1-F5 Modes: ...'); the key of the mode you are in says so."""
    out = []
    for key, mode, name in MODES:
        action = "noop_mode" if mode == current else (writer_action if (mode == "writer" and writer_action) else f"mode('{mode}')")
        out.append(Binding(key, action, MODE_LABEL if key == "f1" else name, key_display="F1-F5" if key == "f1" else key.upper(),
                           show=(key == "f1")))
    return out


def back_binding():
    return Binding("q", "back_mode", "Back")


def quit_binding():
    return Binding("Q", "quit_program", QUIT_LABEL, key_display="Q")
