"""The Writer's shortcuts: names, defaults, and checking what you typed in Settings (F4) > Keys.

A key is stored the way Neovim writes it: <A-i> (Alt+I), <C-b> (Ctrl+B), <F9>. You may type "Alt+I" or "ctrl+b" too.
"""
import re

# setting name -> (label, default)
WRITER_KEYS = {
    "key_italic": ("Italic", "<A-i>"),
    "key_bold": ("Bold", "<A-b>"),
    "key_scene_break": ("Scene break", "<A-s>"),
    "key_menu": ("Writer menu", "<F12>"),
    "key_sidebar": ("Scenes sidebar", "<F9>"),
    "key_peek": ("Peek at a name", "<F8>"),
    "key_overview": ("Story outline overlay", "<C-o>"),
    "key_builder": ("Back to the Builder", "<C-q>"),
    "key_replace": ("Find and replace", "<C-r>"),
    "key_quit": ("Quit storywheel", "<A-q>"),
    "key_lookup": ("Dictionary and thesaurus card", "<F7>"),
    "key_lookup_word": ("Look up a typed word", "<F6>"),
    "key_grammar_next": ("Next grammar problem", "<F10>"),
    "key_grammar_list": ("List of grammar problems", "<S-F10>"),
}
DEFAULTS = {k: v[1] for k, v in WRITER_KEYS.items()}

# keys the Writer needs for itself (or that other modes use); a shortcut can't take them
RESERVED = {
    "<C-c>": "copy", "<C-x>": "cut", "<C-v>": "paste", "<C-z>": "undo", "<C-y>": "redo", "<C-s>": "save",
    "<C-a>": "select all", "<C-f>": "find", "<C-g>": "find next", "<A-g>": "find previous", "<A-j>": "join lines",
    "<C-i>": "Tab (some terminals can't tell it from Ctrl+I)", "<C-m>": "Enter", "<C-j>": "Enter",
    "<C-[>": "Escape", "<F1>": "the Wheel", "<F2>": "the Builder", "<F3>": "the Writer", "<F4>": "Settings", "<F5>": "Words",
    "<A-m>": "the Writer menu (always works)", "<C-b>": "bold (always works)",
    "<C-h>": "delete the previous word (Ctrl+Backspace)", "<C-BS>": "delete the previous word", "<C-Del>": "delete the next word",
}

_MODS = {"alt": "A", "meta": "A", "a": "A", "ctrl": "C", "control": "C", "c": "C", "shift": "S", "s": "S"}


def normalize(text):
    """(ok, key or message). Accepts <A-i>, Alt+I, ctrl+b, F9. Needs Alt or Ctrl, or an F key (a bare letter would type)."""
    t = (text or "").strip()
    if not t:
        return False, "Type a key such as Alt+I, Ctrl+B or F9."
    m = re.fullmatch(r"<([A-Za-z])-(.+)>", t)
    if m:
        mods, key = [m.group(1)], m.group(2)
        # <A-C-x> style chains
        while re.fullmatch(r"[A-Za-z]-.+", key):
            mods.append(key[0]); key = key[2:]
    else:
        parts = [p for p in re.split(r"\s*\+\s*", t) if p]
        key, mods = parts[-1], parts[:-1]
        if re.fullmatch(r"<.+>", key):
            key = key[1:-1]
    mod_set = []
    for mod in mods:
        v = _MODS.get(mod.lower())
        if not v:
            return False, f"'{mod}' is not Alt, Ctrl or Shift."
        if v not in mod_set:
            mod_set.append(v)
    if re.fullmatch(r"[Ff]\d{1,2}", key):
        n = int(key[1:])
        if not 1 <= n <= 12:
            return False, "F keys go from F1 to F12."
        key = f"F{n}"
    elif len(key) == 1 and key.isprintable() and not key.isspace():
        key = key.lower() if key.isalpha() else key
        if not any(m in mod_set for m in ("A", "C")):
            return False, "A letter on its own would just type. Use Alt or Ctrl with it (Alt+I), or an F key."
    else:
        return False, "Type one key, with Alt or Ctrl (Alt+I), or an F key (F9)."
    order = [m for m in ("C", "A", "S") if m in mod_set]
    return True, "<" + "-".join(order + [key]) + ">"


def label(key):
    """<A-i> -> Alt+I (for screens and help)."""
    m = re.fullmatch(r"<(?:(.+)-)?([^-]+|-)>", key or "")
    if not m:
        return key
    names = {"A": "Alt", "C": "Ctrl", "S": "Shift"}
    mods = [names.get(x, x) for x in (m.group(1) or "").split("-") if x]
    k = m.group(2)
    return "+".join(mods + [k.upper() if len(k) == 1 else k])


def check(name, key, current):
    """(ok, message): can `name` take `key`, given the other shortcuts in `current` ({setting: key})?"""
    if key in RESERVED:
        return False, f"{label(key)} is already used for {RESERVED[key]}."
    for other, value in current.items():
        if other != name and value == key:
            return False, f"{label(key)} is already the shortcut for {WRITER_KEYS[other][0].lower()}."
    return True, ""
