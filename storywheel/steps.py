"""
The steps you roll through, in order, and the little engine that fills them.

To add a step, add a Step(...) to STEPS. Each field is a function that takes
the context and returns a string. Reorder STEPS to change the flow.

The words themselves live in JSON (storywheel/data); this file only says how
they are put together.
"""
from .mix import Mix
from .text import fix_articles, motif_from, plural, pronouns, title_case


def public(d):
    """Drop internal keys (the ones starting with _)."""
    return {k: v for k, v in (d or {}).items() if not k.startswith("_")}


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
    def __init__(self, engine, story, exclude=None, current=None, fresh=False):
        super().__init__()
        self.engine = engine
        self.mix = Mix.for_story(story, engine.library)
        self.seeds = story.get("seeds", {})
        self.fresh = fresh
        self.kept = {}
        for key, fields in story["kept"].items():
            if key != exclude:
                self.kept.update(public(fields))
        self.update(self.kept)
        self.update(public(current))
        self.made = {}
        self.hints = {}                         # e.g. the title noun, offered as the motif

    def draw(self, slot):
        """Raw text from a slot, chosen through the story mix."""
        text = self.engine.pick(slot, self.mix)
        if slot == "title_noun":
            self.hints["motif"] = text          # a title's last noun is what it is 'about'
        return text

    def __missing__(self, key):
        if key.isupper():                       # a building block: fresh every time
            return self.block(key)
        if key == "first" and "name" in self:
            return self["name"].split()[0]
        if key == "last" and "name" in self:
            return self["name"].split()[-1]
        value = self.seeded(key)
        self[key] = self.made[key] = value
        return value

    def block(self, key):
        if key == "ODDITY":                     # a deliberate wildcard: any adjective + noun
            return fix_articles(f"a {self.engine.word('adjectives')} {self.engine.word('nouns')}")
        if key == "ALLITERATION":
            return self.alliteration()
        slot = key.lower()
        return self.draw(slot) if self.engine.has_slot(slot) else f"[{key}]"

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
        if key in PLURALS:
            return plural(fill(self, self.draw(PLURALS[key])))
        if key == "title":
            return title_case(fill(self, self.draw("title")))
        slot = ALIASES.get(key, key)
        if e.has_slot(slot):
            return fill(self, self.draw(slot))
        return f"[{key}]"

    def alliteration(self):
        e = self.engine
        letter = e.rng.choice("bcdfghlmprstw")
        first = e.rng.choice([lambda: e.word("adjectives", letter),
                              lambda: e.word(e.rng.choice(["adjectives", "nouns", "verbs"]), letter)])()
        return f"{first} {plural(e.word('nouns', letter))}"


def fill(c, template):
    """Fill {placeholders} from the context, a few passes deep."""
    text = template
    for _ in range(8):
        if "{" not in text:
            break
        text = text.format_map(c)
    name = dict.get(c, "name", "")
    return fix_articles(pronouns(text, dict.get(c, "first") or (name.split() or [""])[0]))


def beat(opening, slot, closing="."):
    def make(c):
        text = fill(c, opening + c.draw(slot) + closing)
        return text if opening else text[:1].upper() + text[1:]   # whole-sentence steps start with a capital
    return make

def field(key):
    """A field made the ordinary way: reuse a seed, or invent from the slot."""
    return lambda c: c.seeded(key)


# --- steps -----------------------------------------------------------------------

class Step:
    def __init__(self, key, label, hint, fields, reroll=None):
        self.key, self.label, self.hint = key, label, hint
        self.fields = fields                 # field name -> generator(ctx)
        self.reroll = reroll or {}           # optional different generator for single-field rerolls

    @property
    def single(self):
        return len(self.fields) == 1

    def roll(self, engine, story, fresh=True):
        c = Ctx(engine, story, exclude=self.key, fresh=fresh)
        out = {}
        for name, gen in self.fields.items():
            out[name] = c[name] = str(gen(c))
        out["_made"] = c.made
        return out

    def roll_field(self, engine, story, current, field_name):
        rest = {k: v for k, v in current.items() if k != field_name}
        c = Ctx(engine, story, exclude=self.key, current=rest, fresh=True)
        gen = self.reroll.get(field_name, self.fields[field_name])
        return dict(current, **{field_name: str(gen(c))})


STEPS = [
    Step("genre", "Genre & mood",
         "Two genres rubbing together is a shortcut to something fresh. "
         "Later steps lean toward ideas that fit what you keep here.",
         {"genre": field("genre"), "mood": field("mood")}),

    Step("title", "Title",
         "A title is a promise about tone. The motif is the thing the title is "
         "about; later steps will keep bringing it back.",
         {"title": field("title"),
          "motif": lambda c: c.hints.get("motif") or motif_from(c["title"], lambda: c.draw("noun"))},
         reroll={"motif": lambda c: c.draw("noun")}),

    Step("protagonist", "Protagonist",
         "Want is what they chase. Need is what they actually have to learn. "
         "The story lives in the gap between the two.",
         {k: field(k) for k in ("name", "age", "job", "trait", "want", "need",
                                "flaw", "secret", "rival")}),

    Step("setting", "Setting",
         "A good setting puts pressure on the character. Ask what this place "
         "makes hard for them.",
         {k: field(k) for k in ("place", "era", "season", "landmark", "rumor")}),

    Step("premise", "Premise",
         "One sentence: who, what they're up against, and what's at stake.",
         {"premise": beat("", "premise", "")}),

    Step("spine", "Story spine",
         "Each 'Because of that' should be caused by the beat before it, not "
         "just come after it. Use [f] to reroll a single beat.",
         {"once":          beat("Once upon a time, ", "once"),
          "every_day":     beat("Every day, {first} ", "routine"),
          "one_day":       beat("One day, ", "inciting"),
          "because_1":     beat("Because of that, {first} ", "reaction"),
          "because_2":     beat("Because of that, ", "escalation"),
          "until_finally": beat("Until finally, ", "climax"),
          "ever_since":    beat("Ever since then, ", "resolution")}),

    Step("twist", "Twist",
         "Optional. Skip it with [x] if the story doesn't need one.",
         {"twist": beat("", "twist", "")}),
]
