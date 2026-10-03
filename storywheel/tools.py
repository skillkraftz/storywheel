"""One way to say a tool is missing: what is missing, what needs it, and the exact command to fix it."""

TOOLS = {
    "dictionary": ("The dictionary", "Looking up words, the thesaurus and Words mode need it", "storywheel dictionary install"),
    "wordfreq": ("The wordfreq package", "Words > Vocabulary needs it to tell everyday words from rare ones", "pipx inject storywheel wordfreq"),
    "neovim": ("Neovim (0.10 or newer)", "the Writer needs it", "sudo apt install neovim"),
    "libreoffice": ("LibreOffice", "making .odt and .pdf files needs it", "sudo apt install libreoffice-writer"),
    "neovide": ("Neovide", "the Writer's own window (Settings > Writer > Use Neovide) needs it; the terminal is used instead", "cargo install neovide"),
    "clipboard": ("A clipboard tool", "copying to the system clipboard needs one", "sudo apt install xclip"),
    "python-docx": ("The python-docx package", "Word (.docx) export needs it", "pipx inject storywheel python-docx"),
}


def is_arm64():
    """True on a 64-bit ARM machine (a Raspberry Pi). STORYWHEEL_ARCH overrides it, for tests."""
    import os
    import platform
    return (os.environ.get("STORYWHEEL_ARCH") or platform.machine()).lower() in ("aarch64", "arm64")


NEOVIDE_ARM64 = ("Neovide has no ready-made build for arm64 (this machine), so the Writer uses the terminal. "
                 "To build it yourself (optional, slow):  cargo install neovide")


def missing(name, extra=""):
    """'<Thing> isn't installed. <What needs it>. To fix it, run:  <command>'  (plus an optional extra sentence)."""
    thing, why, command = TOOLS[name]
    text = f"{thing} isn't installed. {why[:1].upper()}{why[1:]}. To fix it, run:  {command}"
    return text + (f"   {extra}" if extra else "")

TOOLS.update({
    "kitty": ("kitty", "`storywheel kitty` needs it", "sudo apt install kitty"),
    "pipx": ("pipx", "installing and updating storywheel needs it", "sudo apt install pipx && pipx ensurepath"),
    "git": ("git", "updating storywheel needs it", "sudo apt install git"),
})
