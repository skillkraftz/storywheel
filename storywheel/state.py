"""Where you left off: ~/.storywheel/state.json. Plain `storywheel` reopens exactly there."""
import json

from . import paths


class State:
    def __init__(self, path=None):
        self.path = path or (paths.home() / "state.json")
        self.data = self._read()

    def _read(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def update(self, **changes):
        self.data.update(changes)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def clear(self):
        self.data = {}
        try:
            self.path.unlink()
        except OSError:
            pass
