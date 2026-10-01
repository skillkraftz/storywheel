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


class Engine:
    def __init__(self, seed=None, library=None, user_dir=None, rng=None):
        self.rng = rng or random.Random(seed)
        self.library = library or lib.Library.load(user_dir)
        self._recent = {}                  # list id -> deque of recent entry texts
        self._faker = None
        self._words = None

    # --- picking ---------------------------------------------------------------------

    def has_slot(self, slot):
        return self.library.has_slot(slot)

    def pick(self, slot, mix):
        """Raw text for a slot (placeholders still unexpanded)."""
        return self.pick_entry(self.pick_list(slot, mix), mix)

    def pick_list(self, slot, mix):
        lists = self.library.by_slot[slot]
        if len(lists) == 1:
            return lists[0]
        return self.rng.choices(lists, weights=mix.list_probabilities(lists))[0]

    def pick_entry(self, wl, mix):
        if wl.generator:
            return self.generate(wl.generator)
        weights = mix.weights()
        options = [(e.text, mix.entry_weight(e, weights)) for e in wl.entries]
        options = [(t, w) for t, w in options if w > 0] or [(e.text, 1.0) for e in wl.entries]
        recent = self._recent.setdefault(wl.id, deque(maxlen=max(1, len(wl.entries) // 2)))
        fresh = [(t, w) for t, w in options if t not in recent] or options
        text = self.rng.choices([t for t, _ in fresh], weights=[w for _, w in fresh])[0]
        recent.append(text)
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
