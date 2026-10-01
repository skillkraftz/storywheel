"""
The engine: picks an entry for a slot, in two stages.

1. Pick a list for the slot, weighted by the story mix (see mix.py).
2. Pick an entry from that list, avoiding recent repeats: an entry isn't
   handed out again until about half the list has been used.

All randomness comes from one random.Random, so a seed makes a run repeatable.
Nothing here touches the network; Faker and wonderwords are used offline.
"""
import random
from collections import deque

from . import library as lib
from .markov import NameMaker


class Engine:
    def __init__(self, seed=None, library=None, user_dir=None, rng=None):
        self.rng = rng or random.Random(seed)
        self.library = library or lib.Library.load(user_dir)
        self._recent = {}                  # list id -> deque of recent entry texts
        self._faker = None
        self._words = None
        self.trace = None                  # set to [] to record every pick (see pick_entry)
        self._makers = {}
        self.notices = []                  # things the user should hear about (see take_notices)

    def notify(self, message):
        if message not in self.notices:
            self.notices.append(message)

    def take_notices(self):
        """Messages queued since the last call, for the UI to show once."""
        out, self.notices = self.notices, []
        return out

    # --- picking ---------------------------------------------------------------------

    def has_slot(self, slot):
        return self.library.has_slot(slot)

    def pick(self, slot, mix):
        """Raw text for a slot (placeholders still unexpanded)."""
        return self.pick_entry(self.pick_list(slot, mix), mix)

    def pick_list(self, slot, mix):
        lists = self.library.by_slot[slot]
        if all(mix.is_list_excluded(wl) for wl in lists):
            self.notify(f"Everything for '{slot.replace('_', ' ')}' is excluded in this mix, "
                        f"so the exclusions were ignored for it.")
        elif len(lists) == 1:
            return lists[0]
        return self.rng.choices(lists, weights=mix.list_probabilities(lists))[0]

    def pick_entry(self, wl, mix):
        if wl.generator:
            return self._record(wl, (), self.generate(wl.generator))
        if wl.markov and self.rng.random() < wl.markov:
            name = self.maker(wl).make(self.rng)
            if name:
                return self._record(wl, (), name)
        weights = mix.weights()
        options = [(e, mix.entry_weight(e, weights)) for e in wl.entries]
        live = [(e, w) for e, w in options if w > 0]
        if not live:
            self.notify(f"Every entry in '{wl.id}' is excluded in this mix, "
                        f"so the exclusions were ignored for it.")
        options = live or [(e, 1.0) for e in wl.entries]
        recent = self._recent.setdefault(wl.id, deque(maxlen=max(1, len(wl.entries) // 2)))
        fresh = [(e, w) for e, w in options if e.text not in recent] or options
        entry = self.rng.choices([e for e, _ in fresh], weights=[w for _, w in fresh])[0]
        recent.append(entry.text)
        return self._record(wl, entry.tags, entry.text)

    def maker(self, wl):
        if wl.id not in self._makers:
            self._makers[wl.id] = NameMaker([e.text for e in wl.entries])
        return self._makers[wl.id]

    def _record(self, wl, entry_tags, text):
        if self.trace is not None:
            self.trace.append((wl.slot, wl.id, set(wl.tags) | set(entry_tags), text))
        return text

    # --- generated lists ------------------------------------------------------------------

    def generate(self, name):
        kind, _, what = name.partition(".")
        if kind == "faker":
            fake = self.faker
            if what == "job":
                return fake.job().split(",")[0].split("/")[0].strip().lower()
            return getattr(fake, what)()
        if kind == "wonderwords":
            return self.word({"adjective": "adjectives", "noun": "nouns", "verb": "verbs"}[what])
        raise lib.DataError(f"unknown generator '{name}'")

    @property
    def faker(self):
        if self._faker is None:
            from faker import Faker
            self._faker = Faker()
            self._faker.seed_instance(self.rng.randrange(2 ** 32))
        return self._faker

    def word(self, pos, starts_with=""):
        """A random dictionary word: pos is 'adjectives', 'nouns' or 'verbs'."""
        if self._words is None:
            from wonderwords import RandomWord
            self._words = RandomWord(rng=self.rng)
        return self._words.word(include_parts_of_speech=[pos], starts_with=starts_with)
