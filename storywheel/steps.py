"""
The steps you roll through, in order, and the little engine that fills them.

To add a step, add a Step(...) to steps_for(). Each field is a function that takes
the context and returns a string. Reorder that list to change the flow. The beats
of the story body come from a structure (see structures.py), not from this file.

The words themselves live in JSON (storywheel/data); this file only says how
they are put together.
"""
import json
import re
from pathlib import Path

from . import frames, structures
from . import threads as T
from .library import Entry
from .mix import Mix
from .text import fix_articles, fix_particles, implicit, particle_verbs, motif_from, plural, pronouns, title_case

MOTIF_SOMEONE_CHANCE = 0.25    # how often a person or creature motif is offered as a {SOMEONE}


def public(d):
    """Drop internal keys (the ones starting with _)."""
    return {k: v for k, v in (d or {}).items() if not k.startswith("_")}


# Fields about the protagonist, shown on their own card: 'Vesna's sister' reads 'their sister'.
ABOUT_THE_CHARACTER = {"want", "need", "flaw", "secret"}

# Lowercase placeholders that borrow another slot's lists.
ALIASES = {"first": "first_name", "last": "last_name", "adj2": "adj",
           "noun2": "noun", "motif": "noun"}
# {title_nouns} is the plural of one draw from title_noun, and so on.
PLURALS = {"nouns": "noun", "title_nouns": "title_noun"}


# --- the context ------------------------------------------------------------------

class Ctx(dict):
    """
    Everything a template can see: the story's kept fields plus the fields of
    the candidate being built.

    {UPPERCASE} placeholders are building blocks: a fresh draw from the slot
    of the same name (lowercased) every time. {lowercase} placeholders are
    story fields; if the story doesn't have one yet (say, a skipped step) it is
    invented on the spot and stays the same for the rest of this roll.

    'Seeds' are things an earlier step invented in passing, like a name inside
    a title. A step's first roll reuses them, so a title like "Wade's Lantern"
    tends to produce a protagonist named Wade. Rerolls ignore seeds.
    """
    def __init__(self, engine, story, exclude=None, current=None, fresh=False,
                 threads=None, record=False, atoms=None):
        super().__init__()
        self.engine = engine
        self.mix = engine.mix_for(story)
        self.seeds = story.get("seeds", {})
        self.fresh = fresh
        self.kept = {}
        for key, fields in story["kept"].items():
            if key != exclude:
                self.kept.update(public(fields))
        self.update(self.kept)
        self.update(public(current))
        self.made = {}
        self.made_by = {}                       # which field's work invented each key of `made`
        self.inputs = {}                        # earlier steps' values this roll read (see record_read)
        self._depth = 0
        self.step_key = exclude
        self.hints = {}                         # e.g. the title noun, offered as the motif
        # Threads: what the spine has introduced so far. A spine roll (record=True)
        # starts empty and adds to it; other steps read the story's kept threads.
        self.threads = dict(story.get("threads", {})) if threads is None else threads
        self.record = record
        self.field = None                       # the field being made, for attributing threads
        self.later = set()                      # thread kinds a later beat already introduced
        # Atoms: nothing used elsewhere in this story may be drawn again. `used` comes from
        # the steps already kept; `drawn` is what this roll (and the item being edited) has used.
        self.used = {tuple(a) for key, lst in story.get("atoms", {}).items() if key != exclude
                     for a in lst}
        self.drawn = {tuple(a) for lst in (atoms or {}).values() for a in lst}
        # a universe character who is the protagonist is not also drawn as a passing stranger
        pro = (story.get("kept", {}).get("protagonist") or {}).get("name")
        if pro and exclude != "protagonist":
            self.used |= {(slot, pro) for slot in ("someone", "close", "rival")}
        self.atom_log = []                      # (field, slot, text) in the order drawn
        self._motif_offered = False

    def tech(self):
        """The technology this story assumes: its era's own (a "period" or "modern" feature) once the era is known, else the one its genres assume
        (genres.json `_tech`), else None. Atoms that need the other kind are never drawn."""
        era = dict.get(self, "era")
        if era:
            feats = self.engine.features_of("era", era) or ()
            for kind in ("period", "modern"):
                if kind in feats:
                    return kind
        return self.mix.tech()

    def tech_accept(self, accept=None):
        """`accept` (a function Entry -> bool, or None) narrowed to the story's technology."""
        tech = self.tech()
        if tech is None:
            return accept
        banned = "modern" if tech == "period" else "period"
        return lambda e: banned not in (e.features or ()) and (accept is None or accept(e))

    def draw(self, slot):
        """Text from a slot, chosen through the story mix and remembered (nothing used in
        this story is drawn again). Templates that use a thread we have are favored, and
        ones that need a thread we lack are skipped."""
        wl, entry = self.engine.pick_item(slot, self.mix, self.adjuster(slot), self.used | self.drawn,
                                          accept=self.tech_accept(), commit=False, bias=self.bias(slot, ()))
        return self.finish_atom(slot, wl, entry)

    def adjuster(self, slot):
        """How much likelier or rarer each entry of a slot is, for threads and for ratings."""
        ratings = self.engine.ratings
        if ratings is None or not any(wl.is_template for wl in self.engine.library.by_slot.get(slot, [])):
            return self.thread_weight
        return lambda text: self.thread_weight(text) * ratings.frame_factor(slot, text)

    def bias(self, slot, others):
        """A rating-based factor for an atom, given the atoms already chosen beside it."""
        ratings = self.engine.ratings
        if ratings is None:
            return None
        return lambda e: ratings.atom_bias(slot, e.text, others)

    def pick_atom(self, slot, accept, local=()):
        """(list, entry) for a slot that satisfies `accept`, not yet remembered; None if none does.
        Frames use this while they are still working out which atoms fit together."""
        if slot == "someone" and self.offer_motif():
            motif = dict.get(self, "motif")
            guest = Entry(f"the {motif}", features=("creature",) if self.engine.motif_kind(motif) == "creature"
                          else ("human",))
            if accept is None or accept(guest):
                return None, guest
        return self.engine.pick_item(slot, self.mix, None, self.used | self.drawn | set(local), self.tech_accept(accept), commit=False,
                                     bias=self.bias(slot, local))

    def finish_atom(self, slot, wl, entry):
        """Remember a pick, and return its text. Things and people that a spine beat brings in
        become threads."""
        if wl is not None:
            self.engine.commit(wl, entry)
            self.drawn.add((slot, entry.text))
            self.atom_log.append((self.field, slot, entry.text))
        if slot == "title_noun":
            self.hints["motif"] = entry.text    # a title's last noun is what it is 'about'
        text = entry.text
        if slot in T.THREAD_KINDS:
            text = fill(self, text)             # settle the exact words, so later beats can repeat them
            if self.record and slot not in self.threads and slot not in self.later:
                self.threads[slot] = {"text": text, "beat": self.field,
                                      "features": list(entry.features or ())}
        return text

    def sentence(self, slot, opening="", closing="."):
        """A template from `slot`, with its atoms chosen to fit (see frames.py). A template
        the story can't satisfy is set aside and another drawn."""
        skip = set()
        for _ in range(frames.MAX_ATTEMPTS):
            wl, entry = self.engine.pick_item(slot, self.mix, self.adjuster(slot),
                                              self.used | self.drawn | skip, commit=False)
            body = entry.text
            end = "" if body.rstrip().endswith((".", "!", "?")) else closing
            try:
                text = frames.solve(self, opening + body + end)
            except frames.Starved:
                skip.add((slot, body))
                continue
            self.finish_atom(slot, wl, entry)
            return text
        wl, entry = self.engine.pick_item(slot, self.mix, self.thread_weight, self.used | self.drawn, commit=False)
        body = entry.text
        self.engine.notify(f"Could not fit every restriction in a '{slot}' frame; one was relaxed.")
        text = frames.solve(self, opening + body + ("" if body.rstrip().endswith((".", "!", "?")) else closing),
                            relax=True)
        self.finish_atom(slot, wl, entry)
        return text

    def can_resolve(self, name):
        return frames.is_known(self.engine.library, name)

    def field_features(self, name):
        """What the story's own field is, for frames: the character, a rival, a landmark, a thread."""
        e = self.engine
        if name in ("first", "name", "job"):
            feats = {"human"}
            job = dict.get(self, "job")
            if job and "magic" in (e.features_of("job", job) or ()):
                feats.add("magic")
            return feats
        if name == "rival":
            return e.features_of("rival", self["rival"])
        if name == "landmark":
            return e.features_of("landmark", self["landmark"])
        if name == "place":
            return {"outdoor"}
        value = self[name]                      # a thread or the motif: make sure it exists
        kind = name[4:]
        if kind == "motif":
            if e.motif_kind(self["motif"]) == "object":
                return {"portable", "buryable"}
            kind = "thing"
        thread = self.threads.get(kind)
        return None if thread is None else thread.get("features")

    def thread_weight(self, template):
        return T.weight(template, self.threads)

    def is_kept(self, key):
        """Is this earlier-step value one the writer has kept (as opposed to a stand-in)?"""
        if key in ("first", "last"):
            key = "name"
        return key in self.kept

    def __getitem__(self, key):
        self._depth += 1
        try:
            value = super().__getitem__(key)
        finally:
            self._depth -= 1
        if self._depth == 0:
            self.record_read(key, value)
        return value

    def record_read(self, key, value):
        """Note a value from ANOTHER step that this roll used, and whether it was kept or a stand-in
        (the roll had to invent it because that step isn't kept). Candidates carry this as _inputs."""
        owner = OWNER.get(key)
        if owner is None or owner == self.step_key or key in self.inputs:
            return
        self.inputs[key] = {"value": value, "step": owner, "standin": not self.is_kept(key)}

    def __missing__(self, key):
        if key.isupper():                       # a building block: fresh every time
            return self.block(key)
        if key.startswith("the_"):              # a thread (or the motif) again, definite
            value = self[key] = self.reference(key[4:])
            return value
        if key == "first" and "name" in self:
            return self["name"].split()[0]
        if key == "last" and "name" in self:
            return self["name"].split()[-1]
        value = self.seeded(key)
        self[key] = self.made[key] = value
        self.made_by[key] = self.field
        return value

    def block(self, key):
        if key == "ODDITY":                     # a deliberate wildcard: any adjective + noun
            return fix_articles(f"a {self.engine.word('adjectives')} {self.engine.word('nouns')}")
        if key == "ALLITERATION":
            return self.alliteration()
        slot = key.lower()
        if not self.engine.has_slot(slot):
            return f"[{key}]"
        if key == "SOMEONE" and self.offer_motif():
            return f"the {dict.get(self, 'motif')}"
        return self.draw(slot)

    def verify_threads(self, field, beat_text):
        """Threads this beat introduced must be findable in its finished text. Normally
        they are; if the pronoun pass reworded one ("Amanda's" -> "their") we note that."""
        first = dict.get(self, "first") or (dict.get(self, "name", "").split() or [""])[0]
        for kind, t in list(self.threads.items()):
            if t["beat"] == field:
                ok = T.verify(t, beat_text, first)
                if ok:
                    self.threads[kind] = ok
                else:
                    del self.threads[kind]

    def offer_motif(self):
        """Sometimes the title's person or creature (the preacher, the raven) is the one who shows up."""
        motif = dict.get(self, "motif")
        if (motif and not self._motif_offered
                and self.engine.motif_kind(motif) in ("person", "creature")
                and self.engine.rng.random() < MOTIF_SOMEONE_CHANCE):
            self._motif_offered = True
            return True
        return False

    def reference(self, name):
        """{the_thing}, {the_someone}...: the story's thread of that kind, as 'the ...'.
        With no such thread yet, a fresh one is drawn (and, in a spine, introduced).
        {the_motif}: 'the lantern' if the motif is an object; for a person, creature,
        place or idea it falls back to the story's thing, or a fresh {THING}."""
        if name == "motif":
            motif = self["motif"]
            if self.engine.motif_kind(motif) == "object":
                return f"the {motif}"
            name = "thing"
        if name not in T.THREAD_KINDS:
            return f"[the_{name}]"
        if name in self.threads:
            return T.definite(self.threads[name]["text"])
        return self.block(name.upper())

    def seeded(self, key):
        """A seed from an earlier step if this is a first roll, else a new invention."""
        if not self.fresh and key in self.seeds:
            return self.seeds[key]
        return self.invent(key)

    def invent(self, key):
        e = self.engine
        if key == "name":
            return f"{self['first']} {self['last']}"
        if key == "age":
            return str(e.rng.randint(17, 84))
        if key == "genre":
            return " / ".join(e.rng.sample(e.library.genre_names, 2))
        if key == "structure":
            return e.rng.choice([st.label for st in structures.registry().values()])
        if key in PLURALS:
            return plural(fill(self, self.draw(PLURALS[key])))
        if key == "title":
            return title_case(fill(self, self.sentence("title", "", "")))
        slot = ALIASES.get(key, key)
        if e.has_slot(slot):
            is_template = any(wl.is_template for wl in e.library.by_slot[slot])
            text = fill(self, self.sentence(slot, "", "") if is_template else self.draw(slot))
            if key in ABOUT_THE_CHARACTER:
                name = dict.get(self, "name", "")
                text = implicit(text, dict.get(self, "first") or (name.split() or [""])[0])
            return text
        return f"[{key}]"

    def alliteration(self):
        e = self.engine
        letter = e.rng.choice("bcdfghlmprstw")
        first = e.rng.choice([lambda: e.word("adjectives", letter),
                              lambda: e.word(e.rng.choice(["adjectives", "nouns", "verbs"]), letter)])()
        return f"{first} {plural(e.word('nouns', letter))}"


def atoms_by_field(c):
    """{field: [[slot, text], ...]}: the atoms each field of this roll drew."""
    out = {}
    for field_name, slot, text in c.atom_log:
        out.setdefault(field_name, []).append([slot, text])
    return out


def fill(c, template):
    """Fill {placeholders} from the context, a few passes deep."""
    text = template
    for _ in range(8):
        if "{" not in text:
            break
        text = text.format_map(c)
    name = dict.get(c, "name", "")
    text = fix_particles(fix_articles(pronouns(text, dict.get(c, "first") or (name.split() or [""])[0],
                                 c.engine.object_words)), particle_verbs(c.engine.library))
    return c.engine.proper(text)


def beat(opening, slot, closing="."):
    def make(c):
        for _ in range(6):                      # a leaked slot name must never reach the writer
            text = fill(c, c.sentence(slot, opening, closing))
            if not frames.leaks(c.engine.library, text):
                break
            c.engine.notify(f"A '{slot}' template left an unfilled slot in the text; it was redrawn.")
        if not opening:
            text = text[:1].upper() + text[1:]                    # whole-sentence steps start with a capital
        return re.sub(r"([.!?] )([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)   # and so does every sentence
    return make

def field(key):
    """A field made the ordinary way: reuse a seed, or invent from the slot."""
    return lambda c: c.seeded(key)


_SEASON_WORDS = None


def season_of(era):
    """The season an era's own words fix ("the week before Christmas" is winter), or None."""
    global _SEASON_WORDS
    if _SEASON_WORDS is None:
        doc = json.loads((Path(__file__).parent / "data" / "seasons.json").read_text(encoding="utf-8"))
        _SEASON_WORDS = {k: v for k, v in doc.items() if not k.startswith("_")}
    text = (era or "").lower()
    for season, words in _SEASON_WORDS.items():
        if any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in words):
            return season
    return None


def era_field(c):
    """An era. If the setting already has a season, an era that names a different one is passed over."""
    have = dict.get(c, "season")
    era = c.seeded("era")
    for _ in range(12):
        implied = season_of(era)
        if not have or not implied or implied == have:
            break
        era = c.invent("era")
    return era


def mood_field(c):
    """A mood that leans toward the genres just rolled (the story keeps its genre only after this step)."""
    genres = [g.strip().lower() for g in str(dict.get(c, "genre", "")).replace(",", "/").split("/") if g.strip()]
    old = c.mix
    if genres:
        data = dict(old.data)
        data["base"] = genres
        c.mix = Mix(data, c.engine.library)
    try:
        return c.seeded("mood")
    finally:
        c.mix = old


def roll_mood(engine, story, genres):
    """A mood for genres the writer has already chosen (samples, and the Wheel's own pick of a genre)."""
    c = Ctx(engine, story, exclude="genre", fresh=False)
    c["genre"] = " / ".join(genres)
    c.field = "mood"
    return str(mood_field(c))


def season_field(c):
    """A season: the one the era names, if it names one."""
    return season_of(dict.get(c, "era")) or c.seeded("season")


# --- steps -----------------------------------------------------------------------

class Step:
    def __init__(self, key, label, hint, fields, reroll=None, threads=False):
        self.key, self.label, self.hint = key, label, hint
        self.fields = fields                 # field name -> generator(ctx)
        self.reroll = reroll or {}           # optional different generator for single-field rerolls
        self.threads = threads               # do this step's beats introduce threads?

    @property
    def single(self):
        return len(self.fields) == 1

    def roll(self, engine, story, fresh=True):
        c = Ctx(engine, story, exclude=self.key, fresh=fresh,
                threads={} if self.threads else None, record=self.threads)
        out = {}
        for name, gen in self.fields.items():
            c.field = name
            out[name] = c[name] = str(gen(c))
            c.verify_threads(name, out[name])
        out["_made"] = c.made
        out["_made_by"] = c.made_by
        out["_inputs"] = c.inputs
        out["_atoms"] = atoms_by_field(c)
        if self.threads:
            out["_threads"] = c.threads
        return out

    def reroll_value(self, engine, story, current, field_name, threads=None, atoms=None, made=None,
                     made_by=None, report=None):
        """A new value for one field. For a threaded step, `threads` are the ones the
        other beats still depend on; `atoms` are what the item's other fields already use.
        `made` / `made_by` are what the item invented earlier and which field did.
        Returns (value, threads this beat introduced, atoms this field drew). If `report` is a dict
        it is filled with what this reroll invented and read: report["made"], ["made_by"], ["inputs"]."""
        rest = {k: v for k, v in current.items() if k != field_name and not k.startswith("_")}
        threads = threads or {}
        order = list(self.fields)
        mine = order.index(field_name)
        # a beat may only pick up threads introduced before it
        earlier = {k: t for k, t in threads.items() if t["beat"] in order and order.index(t["beat"]) < mine}
        others = {k: v for k, v in (atoms or {}).items() if k != field_name}
        c = Ctx(engine, story, exclude=self.key, current=rest, fresh=True,
                threads=dict(earlier) if self.threads else None, record=self.threads, atoms=others)
        c.update(reusable_made(c, made, made_by, field_name, rest))
        c.later = set(threads) - set(earlier)       # already introduced further on: not ours to record
        c.field = field_name
        gen = self.reroll.get(field_name, self.fields[field_name])
        value = str(gen(c))
        mine = atoms_by_field(c).get(field_name, [])
        if report is not None:
            report.update(made=dict(c.made), made_by=dict(c.made_by), inputs=dict(c.inputs))
        if not self.threads:
            return value, {}, mine
        c.verify_threads(field_name, value)
        return value, {k: t for k, t in c.threads.items() if k not in earlier}, mine

    def roll_field(self, engine, story, current, field_name):
        value, _, _ = self.reroll_value(engine, story, current, field_name)
        return dict(current, **{field_name: value})


PRODUCER_GUESS = {"first": "name", "last": "name"}      # for items saved before we recorded who made what


def reusable_made(c, made, made_by, field_name, rest):
    """Which of an item's earlier inventions (its _made) a single-field reroll may reuse.

    Never what the rerolled field invented itself (a reroll of `name` must not rebuild the name from
    the first/last it made), never what another field's current text already settles, and never a
    stand-in for a step that has since been kept: the kept value is used instead. What remains is
    stand-ins for steps that are still unkept, which the other fields use too, so the item stays consistent."""
    out = {}
    for key, value in (made or {}).items():
        producer = (made_by or {}).get(key) or PRODUCER_GUESS.get(key)
        owner = OWNER.get(key)
        if key in rest or (key in ("first", "last") and "name" in rest):
            continue
        if owner and owner != c.step_key and c.is_kept(key):
            continue                                # a stand-in for a step that is kept now: use the kept one
        if producer == field_name:
            # What this field invented is its own to redo (rerolling `name` makes a new first and last).
            # The exception is a stand-in the other fields also use: they say "Perdition", so does this.
            shared = owner != c.step_key and any(re.search(r"\b" + re.escape(value) + r"\b", v) for v in rest.values() if isinstance(v, str))
            if not shared:
                continue
        out[key] = value
    return out


STORY_SPINE_HINT = ("Each 'Because of that' should be caused by the beat before it, not "
                    "just come after it. Use [f] to reroll a single beat.")


def spine_step(structure, repeats=None):
    """The story body, with its beats taken from a structure (a repeatable beat as many times as `repeats` says)."""
    fields = {b.key: beat(b.opening, b.slot, b.closing) for b in structure.expand(repeats)}
    hint = STORY_SPINE_HINT if structure.name == structures.DEFAULT else structure.blurb + " Use [f] to reroll a single beat."
    return Step("spine", structure.label, hint, fields, threads=True)


def structure_hint():
    return ("The shape of the story's body. " +
            " ".join(f"{st.label}: {st.blurb}" for st in structures.registry().values()))


def steps_for(story, repeats=None):
    """The steps for one story: the same seven, with the body shaped by its structure and, for the beats that can repeat, by how many
    times the story has them (`repeats`, else the story's own `repeats`)."""
    chosen = structures.get(((story.get("kept") or {}).get("structure") or {}).get("structure"))
    repeats = repeats if repeats is not None else story.get("repeats")
    return [
        Step("genre", "Genre & mood",
             "Two genres rubbing together is a shortcut to something fresh. "
             "Later steps lean toward ideas that fit what you keep here.",
             {"genre": field("genre"), "mood": mood_field}),

        Step("structure", "Structure", structure_hint(), {"structure": field("structure")}),

        Step("title", "Title",
             "A title is a promise about tone. The motif is the thing the title is "
             "about; later steps will keep bringing it back.",
             {"title": field("title"),
              "motif": lambda c: c.hints.get("motif") or motif_from(c["title"], lambda: c.draw("title_noun"))},
             reroll={"motif": lambda c: c.draw("title_noun")}),

        Step("protagonist", "Protagonist",
             "Want is what they chase. Need is what they actually have to learn. "
             "The story lives in the gap between the two.",
             {k: field(k) for k in ("name", "age", "job", "trait", "want", "need",
                                    "flaw", "secret", "rival")}),

        Step("setting", "Setting",
             "A good setting puts pressure on the character. Ask what this place "
             "makes hard for them.",
             {"place": field("place"), "era": era_field, "season": season_field, "landmark": field("landmark"), "rumor": field("rumor")}),

        Step("premise", "Premise",
             "One sentence: who, what they're up against, and what's at stake.",
             {"premise": beat("", "premise", "")}),

        spine_step(chosen, repeats),

        Step("twist", "Twist",
             "Optional. Skip it with [x] if the story doesn't need one.",
             {"twist": beat("", "twist", "")}),
    ]


def step_by_key(key, story=None):
    return next(st for st in steps_for(story or {}) if st.key == key)


STEPS = steps_for({})        # the default shape, for code that doesn't have a story in hand

# Which step supplies each field (first and last come from the protagonist's name, a spine beat
# from the body). A value a roll reads from a different step is one of its inputs.
OWNER = {name: st.key for st in STEPS for name in st.fields}
OWNER.update(first="protagonist", last="protagonist")
for _st in structures.registry().values():
    OWNER.update({b.key: "spine" for b in _st.beats})
