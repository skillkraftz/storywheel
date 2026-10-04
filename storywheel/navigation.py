"""Moving between modes and leaving: the same keys and words in every footer and help screen.

    F1-F5   the five modes (one footer entry says so)
    q       back: to the mode you came from (or closes a panel or dialog)
    Q       quit storywheel (asks first)
"""
from textual.binding import Binding

MODES = (("f1", "wheel", "Wheel"), ("f2", "builder", "Builder"), ("f3", "writer", "Writer"), ("f4", "settings", "Settings"),
         ("f5", "words", "Words"))
QUIT_LABEL = "Quit storywheel"
QUIT_QUESTION = "Quit storywheel?  Everything is saved."
NO_BACK = "There is nothing to go back to: you started here. Press Q to quit storywheel."


def mode_bindings(current, writer_action=None):
    """Bindings for F1-F5, each its own footer entry (F1 Wheel, F2 Builder...) that a click sends to that mode. The key of the mode you are in
    opens that mode's help instead of moving."""
    out = []
    for key, mode, name in MODES:
        action = "noop_mode" if mode == current else (writer_action if (mode == "writer" and writer_action) else f"mode('{mode}')")
        out.append(Binding(key, action, name, key_display=key.upper(), show=True))
    return out


def back_binding():
    return Binding("q", "back_mode", "Back")


def quit_binding():
    return Binding("Q", "quit_program", QUIT_LABEL, key_display="Q", show=False)


def footer(bindings, keep=()):
    """A screen's bindings with the footer trimmed to: the five modes, ? Help, q Back and the few keys named in `keep` (actions, in the order
    shown). Every other binding still works; it is listed in the help instead."""
    import dataclasses
    from textual.binding import Binding as B
    modes, helps, backs, kept, rest = [], [], [], {}, []
    for b in bindings:
        if not isinstance(b, B):
            rest.append(b)
            continue
        key = b.key.split(",")[0]
        if key in ("f1", "f2", "f3", "f4", "f5"):
            modes.append(dataclasses.replace(b, show=True))
        elif b.action == "help":
            helps.append(b)
        elif b.action == "back_mode":
            backs.append(b)
        elif b.action in keep and b.action not in kept:
            kept[b.action] = dataclasses.replace(b, show=True)
        else:
            rest.append(dataclasses.replace(b, show=False))
    return [*modes, *helps, *backs, *[kept[a] for a in keep if a in kept], *rest]
