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
import re
from collections import deque
from pathlib import Path

from . import library as lib
from .library import Entry
from .markov import NameMaker


# Stems of dictionary words the random-word wildcard must never use.
BLOCKED_WORDS = re.compile(
    r"^(?:racis\w*|sexis\w*|nazi\w*|nigg\w*|fagg\w*|retard\w*|cunt\w*|whore\w*|rape[sd]?|raping|rapist\w*|slut\w*|"
    r"bitch\w*|fuck\w*|shit\w*|genocid\w*|holocaust|pedo\w*|molest\w*|tranny|dyke|spic|kike|chink|gook|coon|"
    r"wetback|incest\w*|lynch\w*)$", re.IGNORECASE)


# Slots whose weights are the point (a mood leans toward the genre): the recent-picks memory would flatten them.
MEMORYLESS = {"mood"}


class Engine:
    def __init__(self, seed=None, library=None, user_dir=None, rng=None, persist=False, ratings=None):
        """`persist=True` loads and saves the recent-picks memory in user_dir. Leave it
        off for anything that must be repeatable from a seed (sample, tests)."""
        self.rng = rng or random.Random(seed)
        self.library = library or lib.Library.load(user_dir)
        self._recent = {}                  # list id -> deque of recent entry texts
        self.ratings = ratings             # what the writer has rated; down-weights what keeps getting - (ratings.py)
        self._memory_path = Path(user_dir) / "recent.json" if persist and user_dir else None
        self._remembered = self._load_memory()
        self._faker = None
        self._words = None
        self.trace = None                  # set to [] to record every pick (see pick_entry)
        self.frame_log = None              # set to [] to record every frame the solver fills (tests)
        self._makers = {}
        self._kinds = None
        self._dictionary = None
        self._object_words = None
        self._feature_index = None
        self.last_entry = None             # the Entry behind the most recent pick
        self.notices = []                  # things the user should hear about (see take_notices)
        self.universes = []                # universes the generator may draw from (see set_universes)

    def set_universes(self, universes):
        """Let the generator draw from these universes: their entities become atoms (boosted), and their
        genre leanings blend into every story's mix. An empty list removes them again."""
        from . import universe_atoms
        lists = []
        for u in universes:
            lists += universe_atoms.build_lists(u)
        self.library.replace_lists("universe:", lists)
        self.universes = list(universes)
        self._feature_index = None
        self._proper = self._proper_names_pattern(universes)

    @staticmethod
    def _proper_names_pattern(universes):
        """A pattern for the names of the universes' people and places, so 'the Sheriff Lund' can become 'Sheriff Lund'."""
        import re
        from .promote import ARTICLE
        names = set()
        for u in universes:
            for kind in ("character", "place"):
                for e in u.entities(kind):
                    n = e.name.strip()
                    if len(n) >= 3 and not ARTICLE.match(n) and e.proper is not False:
                        names.add(n)
        if not names:
            return None
        alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
        return re.compile(r"\b(?:the|a|an)\s+(?=(?:%s)\b)" % alt, re.IGNORECASE)

    def proper(self, text):
        """Templates say 'the {rival}'; a universe character is a proper name, so the article goes."""
        pattern = getattr(self, "_proper", None)
        return pattern.sub("", text) if pattern else text

    def mix_for(self, story):
        """The mix for rolling this story: its own, plus the selected universes' genres and atom boosts.
        (The story's saved mix is not changed.)"""
        from . import universe_atoms
        from .mix import Mix, story_mix
        data = story_mix(story)
        if not self.universes:
            return Mix(data, self.library)
        merged = {"base": list(data["base"]), "exclude_tags": list(data["exclude_tags"]),
                  "exclude_lists": list(data["exclude_lists"]), "boost": dict(data["boost"])}
        for u in self.universes:
            s = u.settings()
            for g in s["genres"]:
                if g.lower() not in merged["base"]:
                    merged["base"].append(g.lower())
            merged["boost"][universe_atoms.tag(u)] = merged["boost"].get(universe_atoms.tag(u), 1.0) * s["atom_boost"]
        return Mix(merged, self.library)

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
        return self.pick_item(slot, mix, adjust, avoid)[1].text

    def pick_item(self, slot, mix, adjust=None, avoid=None, accept=None, commit=True, bias=None):
        """(list, entry) for a slot, or None if no entry satisfies `accept` (a function
        Entry -> bool, used by frames to demand features). With commit=False nothing is
        remembered until you call commit(): a frame that has to be redrawn leaves no trace."""
        lists = list(self.library.by_slot[slot])
        if all(mix.is_list_excluded(wl) for wl in lists):
            self.notify(f"Everything for '{slot.replace('_', ' ')}' is excluded in this mix, "
                        f"so the exclusions were ignored for it.")
        # First look in every list for something fresh in this story; only if nothing is, reuse.
        for reuse in ((False, True) if avoid else (True,)):
            pool = list(lists)
            while pool:
                wl = pool[0] if len(pool) == 1 else self.rng.choices(pool, weights=self._list_weights(pool, mix, accept))[0]
                entry = self.choose_entry(wl, mix, adjust, avoid, accept, reuse, bias)
                if entry is not None:
                    if commit:
                        self.commit(wl, entry)
                    return wl, entry
                pool = [other for other in pool if other is not wl]      # nothing there fits: try another list
        return None

    def _list_weights(self, pool, mix, accept):
        """How likely each list is to be chosen. When a frame demands features, a list counts only
        for the share of it that fits: otherwise a list with a single acceptable entry would hand
        that one entry the list's whole probability (and 'a fortune teller' would be everywhere)."""
        probs = mix.list_probabilities(pool)
        if not accept:
            return probs
        fits = []
        for wl in pool:
            if wl.generator or not wl.entries:
                fits.append(1.0)
            else:
                fits.append(sum(1 for e in wl.entries if accept(e)) / len(wl.entries))
        weights = [p * f for p, f in zip(probs, fits)]
        return weights if sum(weights) > 0 else probs

    def pick_list(self, slot, mix):
        lists = self.library.by_slot[slot]
        if len(lists) == 1:
            return lists[0]
        return self.rng.choices(lists, weights=mix.list_probabilities(lists))[0]

    def pick_entry(self, wl, mix, adjust=None, avoid=None):
        """Choose from one list and remember the choice."""
        entry = self.choose_entry(wl, mix, adjust, avoid, None)
        self.commit(wl, entry)
        return entry

    def choose_entry(self, wl, mix, adjust=None, avoid=None, accept=None, reuse=True, bias=None):
        """An Entry from this list (None if none satisfies `accept`), with no side effects
        beyond using the random generator. With reuse=False, entries already used in this
        story (`avoid`) are not offered at all."""
        if wl.generator:
            entry = Entry(self.generate(wl.generator), kind=None)
            return entry if not accept or accept(entry) else None
        if wl.markov and self.rng.random() < wl.markov:
            name = self.maker(wl).make(self.rng, reject=self.dictionary)
            if name:
                entry = Entry(name)
                return entry if not accept or accept(entry) else None
        weights = mix.weights()
        options = [(e, mix.entry_weight(e, weights) * (adjust(e.text) if adjust else 1.0) * (bias(e) if bias else 1.0))
                   for e in wl.entries if not accept or accept(e)]
        if not options:
            return None
        live = [(e, w) for e, w in options if w > 0]
        if not live:
            self.notify(f"Every entry in '{wl.id}' is excluded in this mix, "
                        f"so the exclusions were ignored for it.")
        options = live or [(e, 1.0) for e, _ in options]
        if not reuse and avoid:                          # nothing already used in this story
            options = [(e, w) for e, w in options if (wl.slot, e.text) not in avoid]
            if not options:
                return None
        recent = () if wl.slot in MEMORYLESS else self._recent_for(wl)
        used = lambda e: bool(avoid) and (wl.slot, e.text) in avoid
        # fresh in this story and not picked lately; relax memory first, then the story's set
        for keep in (lambda e: not used(e) and e.text not in recent,
                     lambda e: not used(e),
                     lambda e: e.text not in recent,
                     lambda e: True):
            fresh = [(e, w) for e, w in options if keep(e)]
            if fresh:
                break
        return self.rng.choices([e for e, _ in fresh], weights=[w for _, w in fresh])[0]

    def commit(self, wl, entry):
        """Remember a choice: it joins the recent picks and the trace."""
        if any(e is entry for e in wl.entries):
            self._recent_for(wl).append(entry.text)
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

    def features_of(self, slot, text):
        """The features of a known atom, found by its text (None if it isn't one we know,
        for example something the writer typed)."""
        if self._feature_index is None:
            self._feature_index = {}
            for wl in self.library.lists.values():
                if not wl.is_template and not wl.generator:
                    for e in wl.entries:
                        self._feature_index.setdefault((wl.slot, e.text.lower()), e.features)
        return self._feature_index.get((slot, (text or "").lower()))

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
        """A random dictionary word: pos is 'adjectives', 'nouns' or 'verbs'. A few words are never
        offered (slurs, hate and sexual-violence terms): a random title must not be able to say them."""
        if self._words is None:
            from wonderwords import RandomWord
            self._words = RandomWord(rng=self.rng)
        for _ in range(20):
            word = self._words.word(include_parts_of_speech=[pos], starts_with=starts_with)
            if not BLOCKED_WORDS.search(word):
                return word
        return self._words.word(include_parts_of_speech=[pos], starts_with=starts_with) if not starts_with else "quiet"
