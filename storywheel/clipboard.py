"""Copy text to the system clipboard, using whatever the machine has."""
import os
import shutil
import subprocess

# (program, arguments); the first one installed wins
TOOLS = [("wl-copy", []), ("xclip", ["-selection", "clipboard"]), ("xsel", ["--clipboard", "--input"]),
         ("pbcopy", []), ("clip.exe", [])]


def copy(text, app=None):
    """Put text on the clipboard. Returns the name of what did it, or None if nothing could.
    Falls back to the terminal's own clipboard escape (OSC 52) when the app is running."""
    for program, args in TOOLS:
        if shutil.which(program) is None:
            continue
        if program == "wl-copy" and not os.environ.get("WAYLAND_DISPLAY"):
            continue
        if program in ("xclip", "xsel") and not os.environ.get("DISPLAY"):
            continue
        try:
            subprocess.run([program, *args], input=text.encode("utf-8"), check=True, timeout=5,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return program
        except (OSError, subprocess.SubprocessError):
            continue
    if app is not None:
        try:
            app.copy_to_clipboard(text)
            return "the terminal (OSC 52)"
        except Exception:
            pass
    return None
