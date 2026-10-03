"""Screens that are built once and kept (the hub): when one comes back, Textual would re-apply every style rule to every widget on it, which
is most of the time a switch takes. That is only needed if the look changed while it was away (a new theme), so it is skipped otherwise."""


class KeptScreen:
    _styled_version = None

    def _on_screen_resume(self, event):
        version = getattr(self.app, "style_version", None)
        if version is not None and self._styled_version == version:
            event.refresh_styles = False
        else:
            self._styled_version = version
