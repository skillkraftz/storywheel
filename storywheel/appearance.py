"""How storywheel looks: a transparent background (the terminal's own background shows through: kitty applies background_opacity only to
cells that use the terminal's DEFAULT background), your text color and your accent color. One set of choices (Settings > Appearance)
for the Textual modes and, through the story settings, for the Writer and Neovide.

    apply(app)   set the app's theme from the settings
"""
import re

from textual.theme import BUILTIN_THEMES, Theme

from . import settings

NAMES = {
    "black": "#000000", "white": "#ffffff", "red": "#e06c75", "green": "#98c379", "yellow": "#e5c07b", "blue": "#61afef",
    "magenta": "#c678dd", "cyan": "#56b6c2", "orange": "#d19a66", "pink": "#f4a6c0", "gray": "#9aa0a6", "grey": "#9aa0a6",
    "amber": "#ffbf00", "cream": "#f3ead3", "gold": "#d4af37", "teal": "#2aa198", "purple": "#a78bfa", "lavender": "#b4a7d6",
}
DEFAULT_ACCENT = "#5fafd7"


def parse_color(text):
    """'#rrggbb' for a hex color ('#abc' too) or a color name; '' for blank; None if it is neither."""
    t = (text or "").strip().lower()
    if not t:
        return ""
    if t in NAMES:
        return NAMES[t]
    m = re.fullmatch(r"#?([0-9a-f]{6}|[0-9a-f]{3})", t)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return "#" + h
    return None


def values(g=None):
    """(transparent, text color or '', accent color) from the global settings."""
    g = g or settings.load_global()
    return (g.get("transparent_background", True) is not False,
            parse_color(g.get("text_color", "")) or "", parse_color(g.get("accent_color", "")) or "")


def make_theme(transparent=True, text="", accent=""):
    """A Textual theme: the ANSI one (every background is the terminal's default) when transparent, else the usual dark one; your colors
    on top of either."""
    if transparent:
        base = BUILTIN_THEMES["ansi-dark"]
        theme = Theme(name="storywheel-clear", primary=accent or base.primary, secondary=base.secondary, warning=base.warning,
                      error=base.error, success=base.success, accent=accent or base.accent, foreground=text or base.foreground,
                      background=base.background, surface=base.surface, panel=base.panel, boost=base.boost, dark=True,
                      luminosity_spread=base.luminosity_spread, text_alpha=base.text_alpha, variables=dict(base.variables), ansi=True)
    else:
        base = BUILTIN_THEMES["textual-dark"]
        theme = Theme(name="storywheel-solid", primary=accent or base.primary, secondary=base.secondary, warning=base.warning,
                      error=base.error, success=base.success, accent=accent or base.accent, foreground=text or base.foreground,
                      background=base.background, surface=base.surface, panel=base.panel, boost=base.boost, dark=True,
                      luminosity_spread=base.luminosity_spread, text_alpha=base.text_alpha, variables=dict(base.variables))
    return theme


def apply(app, g=None):
    """Give the app the theme the settings ask for (call it again after a setting changes)."""
    theme = make_theme(*values(g))
    app.register_theme(theme)
    app.theme = theme.name
    return theme
