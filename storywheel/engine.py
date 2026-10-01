"""
The engine: picks an entry for a slot, in two stages.

1. Pick a list for the slot, weighted by the story mix (see mix.py).
2. Pick an entry from that list, avoiding repeats two ways:
   * the story's own `avoid` set: nothing already used in this story comes back;
   * a memory of recent picks, saved in ~/.storywheel/recent.json so it carries
     across sessions: an entry isn't handed out again until about half its
     list has been used.
   If a list runs out of fresh entries the rules relax (memory first, then the
   story's set) instead of failing.

All randomness comes from one random.Random, so a seed makes a run repeatable.
Nothing here touches the network; Faker and wonderwords are used offline.
"""
import json
import random
from collections import deque
from pathlib import Path

from . import library as lib
from .library import Entry
from .markov import NameMaker


class Engine:
    def __init__(self, seed=None, library=None, user_dir=None, rng=None, persist=False):
        """`persist=True` loads and saves the recent-picks memory in user_dir. Leave it
        off for anything that must be repeatable from a seed (sample, tests)."""
        self.rng = rng or random.Random(seed)
        self.library = library or lib.Library.load(user_dir)
        self._recent = {}                  # list id -> deque of recent entry texts
        self._memory_path = Path(user_dir) / "recent.json" if persist and user_dir else None
        self._remembered = self._load_memory()
        self._faker = None
        self._words = None
        self.trace = None                  # set to [] to record every pick (see pick_entry)
        self._makers = {}
        self._kinds = None
        self._dictionary = None
        self._object_words = None
        self.last_entry = None             # the Entry behind the most recent pick
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

    def pick(self, slot, mix, adjust=None, avoid=None):
        """Raw text for a slot (placeholders still unexpanded). `adjust`, if given,
        is a function text -> factor that scales an entry's weight (0 rules it out);
        the story uses it to prefer templates that pick up its threads. `avoid` is
        a set of (slot, text) already used in this story."""
        return self.pick_entry(self.pick_list(slot, mix), mix, adjust, avoid).text

    def pick_list(self, slot, mix):
        lists = self.library.by_slot[slot]
        if all(mix.is_list_excluded(wl) for wl in lists):
            self.notify(f"Everything for '{slot.replace('_', ' ')}' is excluded in this mix, "
                        f"so the exclusions were ignored for it.")
        elif len(lists) == 1:
            return lists[0]
        return self.rng.choices(lists, weights=mix.list_probabilities(lists))[0]

    def pick_entry(self, wl, mix, adjust=None, avoid=None):
        """The chosen Entry (generated names and words come back as a plain Entry)."""
        if wl.generator:
            return self._record(wl, Entry(self.generate(wl.generator), kind=None))
        if wl.markov and self.rng.random() < wl.markov:
            name = self.maker(wl).make(self.rng, reject=self.dictionary)
            if name:
                return self._record(wl, Entry(name))
        weights = mix.weights()
        options = [(e, mix.entry_weight(e, weights) * (adjust(e.text) if adjust else 1.0))
                   for e in wl.entries]
        live = [(e, w) for e, w in options if w > 0]
        if not live:
            self.notify(f"Every entry in '{wl.id}' is excluded in this mix, "
                        f"so the exclusions were ignored for it.")
        options = live or [(e, 1.0) for e in wl.entries]
        recent = self._recent_for(wl)
        used = lambda e: bool(avoid) and (wl.slot, e.text) in avoid
        # fresh in this story and not picked lately; relax memory first, then the story's set
        for keep in (lambda e: not used(e) and e.text not in recent,
                     lambda e: not used(e),
                     lambda e: e.text not in recent,
                     lambda e: True):
            fresh = [(e, w) for e, w in options if keep(e)]
            if fresh:
                break
        entry = self.rng.choices([e for e, _ in fresh], weights=[w for _, w in fresh])[0]
        recent.append(entry.text)
        return self._record(wl, entry)

    # --- the recent-picks memory ----------------------------------------------------------

    def _recent_for(self, wl):
        if wl.id not in self._recent:
            size = max(1, len(wl.entries) // 2)
            self._recent[wl.id] = deque(self._remembered.get(wl.id, [])[-size:], maxlen=size)
        return self._recent[wl.id]

    def _load_memory(self):
        if not self._memory_path or not self._memory_path.exists():
            return {}
        try:
            data = json.loads(self._memory_path.read_text(encoding="utf-8"))
            return {k: [str(t) for t in v] for k, v in data.get("recent", {}).items()}
        except (ValueError, OSError, AttributeError):
            return {}                      # a damaged memory file just means a fresh start

    def save_memory(self):
        """Write the recent picks to ~/.storywheel/recent.json (only if persist=True)."""
        if not self._memory_path:
            return
        merged = dict(self._remembered)
        merged.update({lid: list(d) for lid, d in self._recent.items()})
        try:
            self._memory_path.parent.mkdir(parents=True, exist_ok=True)
            self._memory_path.write_text(json.dumps({"version": 1, "recent": merged}), encoding="utf-8")
        except OSError:
            pass                           # never let a full disk stop a story

    def maker(self, wl):
        if wl.id not in self._makers:
            self._makers[wl.id] = NameMaker([e.text for e in wl.entries])
        return self._makers[wl.id]

    def _record(self, wl, entry):
        if self.trace is not None:
            self.trace.append((wl.slot, wl.id, set(wl.tags) | set(entry.tags), entry.text))
        self.last_entry = entry
        return entry

    # --- what kind of thing is a title noun? --------------------------------------------

    def motif_kind(self, motif):
        """object, person, place, creature or idea, for a motif that came from a title
        noun. Anything else (a word the writer typed, a dictionary word) counts as an
        object, which is what templates assume by default."""
        if self._kinds is None:
            self._kinds = {}
            for wl in self.library.by_slot.get("title_noun", []):
                for e in wl.entries:
                    self._kinds.setdefault(e.text.lower(), e.kind or "object")
        return self._kinds.get((motif or "").lower(), "object")

    @property
    def object_words(self):
        """Verbs that take a person as their object ('betrayed', 'teamed up with'), for the
        their/them pass: the last word of every act_person / habit_person / do_person entry."""
        if self._object_words is None:
            words = set()
            for slot in ("act_person", "habit_person", "do_person"):
                for wl in self.library.by_slot.get(slot, []):
                    words.update(e.text.split()[-1].lower() for e in wl.entries if e.text.split())
            self._object_words = words
        return self._object_words

    @property
    def dictionary(self):
        """Ordinary English words, so invented names aren't just 'Thistle' or 'Bell'."""
        if self._dictionary is None:
            from wonderwords import RandomWord
            self._dictionary = {w.lower() for w in RandomWord().filter(
                include_parts_of_speech=["nouns", "adjectives", "verbs"])}
        return self._dictionary

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
