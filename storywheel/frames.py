"""
Frames: making sentences that mean something.

Atoms are assembled into sentences by templates ("frames"), and a frame filled at
random can be grammatical and still nonsense: "the hot springs was built over a
black stallion". This module keeps frames sensible with a small set of FEATURES
and REQUIREMENTS.

Features say what an atom is (the vocabulary is VOCAB below). Requirements say
what a slot, or a verb's subject or object, must be:

    "buryable"        has the feature
    "!living"         does not have it
    "magic|authority" has either (alternatives are separated by |)

A list of requirements means all of them. An atom with no features listed gets the
default for its slot (a thing is portable and buryable; someone is human; a landmark
is outdoors); anything else must be declared.

In a frame, a slot can require features of whatever fills it:

    {THING:buryable}       a thing that can be buried
    {CLOSE:human}          a close person who is human
    {landmark:built}       the story's landmark, which has to be a built structure
                           (a frame that can't be satisfied is skipped for this story)

Verb atoms (act_person, act_thing, ..., habit_*, do_*) declare what their SUBJECT and
OBJECT must be. The frame doesn't say which slots those are; they follow from the
order of the sentence. A verb's subject is the nearest person slot before it that is
not already some earlier verb's object (the opener's {first} counts), and its object
is the next slot after it of the kind the verb takes (a person, a thing, a place, a
message or a disaster). A hiding place ("under the floor") has the thing it hides as
its subject.

The solver fills the nouns first, then picks verbs that fit the nouns it got, and
starts over if a verb has nothing to fit. `lint(library)` checks, for every frame in
the data, that every slot can be satisfied by at least MIN_SATISFIERS atoms, and that
most draws succeed first time, so a restriction can never starve a slot.

Agreement: {is}, {was}, {has} and {does} agree with the nearest noun before them
("the stockyards were"), and {lies|lie} picks the first form for a singular subject
and the second for a plural one.
"""
import re
from collections import Counter

MIN_SATISFIERS = 3        # every slot in every frame must have at least this many atoms
MIN_COVERAGE = 0.5        # and at least this share of draws must succeed without a retry
MAX_ATTEMPTS = 14         # noun/verb redraws before a frame is given up on

VOCAB = {
    # things
    "portable": "one person can carry it (the default for things)",
    "buryable": "can be buried or hidden underground (the default for things)",
    "magic": "magical (a thing), or able to do magic (a person)",
    "valuable": "worth money",
    "living": "an animal: not buried, burned or locked in a box",
    "bulky": "too big for a pocket or a small hiding place",
    "paper": "letters, maps, deeds, books: can be forged, copied, read",
    # people
    "human": "a person (the default for someone)",
    "creature": "not human: a talking fox, a troll, a dragon",
    "friendly": "kindly toward the protagonist",
    "threatening": "dangerous or hostile",
    "authority": "holds office or power: a sheriff, a judge, a queen",
    # places
    "built": "a made structure (a hall, a bridge), as opposed to natural",
    "natural": "not built: a lake, a mesa; or a natural disaster",
    "indoor": "somewhere with a roof and a door",
    "outdoor": "open air (the default for landmarks)",
    "diggable": "has ground something can be buried in",
    # disasters
    "manmade": "caused by people: a robbery, a feud, a strike",
    "strikes": "can hit or strike a place: weather, plague, fire, robbery, war (not 'the death of the king')",
    # messages
    "physical": "a thing you can hold: paper, a note (the default for messages)",
    # prizes
    "material": "something you can own and be given: land, gold, a horse",
    "social": "a standing among people: a seat on the council, a pardon",
    "inner": "a feeling or a lesson (for prizes: not something to be given; for verbs: an inner act)",
    # verbs
    "mundane": "an ordinary, everyday action (what a routine is made of)",
    "gentle": "a kind or reconciling act (forgave, thanked, took in): what an ending is made of",
    "stows": "puts something somewhere and leaves it there (hid, buried, kept): goes with a hiding place",
    "trades": "gives something up for something else (sold, pawned, traded away): goes with 'to pay for'",
    # manners (how something is done)
    "speech": "a spoken manner ('in the old tongue', 'in whispers'): fits speaking, not crawling or paying",
    "carrying": "needs something in hand ('with drawn steel', 'with a clipboard')",
    "feeling": "a state of mind ('in silent dread', 'in a panic'): only where a frame asks for it",
    # when (technology): an atom without either feature fits any time
    "modern": "needs present-day technology (a burner phone, a flash drive): not in the 1920s",
    "period": "belongs to an older time (a telegram, a gramophone): not in the present day",
    # ages (jobs): who can do this work. A job with none of these is "adult" (and an elder may still do it)
    "child": "a job for someone under 13 (a paper round at 12)",
    "teen": "a job or role for someone 13 to 19 (paperboy, class president, freshman)",
    "adult": "a grown-up's work (the default for a job); said only when a job also has teen or elder",
    "elder": "someone 60 or older ('retired ...')",
    # anything
    "plural": "takes 'are' and 'were': 'the stockyards', 'two scarred brothers'",
}

# Features that limit where an atom may be used: an atom with one of these is drawn only by a slot that asks for it
# ({MANNER:speech}), never by a plain {MANNER}.
RESTRICTED = {"speech", "carrying", "feeling"}

# Which slots are whose nouns, for binding verbs to subjects and objects.
SLOT_KIND = {"someone": "person", "close": "person", "thing": "thing", "message": "message",
             "disaster": "disaster"}
FIELD_KIND = {"first": "person", "name": "person", "job": "person", "rival": "person", "the_someone": "person",
              "landmark": "place", "place": "place",
              "the_thing": "thing", "the_motif": "thing",
              "the_message": "message", "the_disaster": "disaster"}
# verb slot -> (subject kinds, object kind)
VERBS = {}
for _fam, _obj in (("person", "person"), ("thing", "thing"), ("place", "place"),
                   ("message", "message"), ("event", "disaster")):
    for _pre in ("act", "do", "habit"):
        VERBS[f"{_pre}_{_fam}"] = (("person",), _obj)
VERBS["hiding"] = (("thing", "message"), None)       # a hiding place has the hidden thing as its subject
AGREE = {"is": ("is", "are"), "was": ("was", "were"), "has": ("has", "have"), "does": ("does", "do")}
SPECIAL_BLOCKS = {"ODDITY", "ALLITERATION"}

# {name}  {name:requirements}  {singular|plural}. Requirements may themselves contain "|" ("a|b").
_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z_0-9]*)(?::([^{}]*)|\|([^{}]*))?\}")

# Lowercase names a story can always fill, besides the slots of the library.
KNOWN_FIELDS = {"first", "last", "name", "age", "place", "era", "season", "landmark", "rumor", "rival", "job",
                "trait", "want", "need", "flaw", "secret", "motif", "title", "genre", "mood", "structure",
                "nouns", "title_nouns", "adj2", "noun2", "the_motif", "the_thing", "the_someone",
                "the_message", "the_disaster"}


def is_known(library, name):
    """Can the story fill a placeholder of this name? (Anything else would leak into the text.)"""
    if name in SPECIAL_BLOCKS or name in AGREE:
        return True
    if name.isupper():
        return library.has_slot(name.lower())
    return name in KNOWN_FIELDS or library.has_slot(name)


def unknown_names(library, text):
    """Placeholders in `text` that nothing can fill."""
    return [m.group(1) for m in _PLACEHOLDER.finditer(text)
            if m.group(3) is None and not is_known(library, m.group(1))]


def leaks(library, text):
    """Pieces of a rendered text that look like an unresolved slot: a braced name, an UPPERCASE
    slot name, a name_with_underscores, a [KEY] marker, or a stray | . Should always be []."""
    found = re.findall(r"[{}|]", text)
    found += re.findall(r"\[[A-Za-z_]+\]", text)
    found += re.findall(r"\b[A-Za-z]+_[A-Za-z_]+\b", text)
    slots = {n.upper() for n in library.by_slot} | SPECIAL_BLOCKS
    found += [w for w in re.findall(r"\b[A-Z][A-Z_]{2,}\b", text) if w in slots]
    return found


class Starved(Exception):
    """A frame can't be filled with what the story has: try another."""


# --- requirements -------------------------------------------------------------------------------

def parse_reqs(spec):
    return [r.strip() for r in (spec or "").split(",") if r.strip()] if isinstance(spec, str) else list(spec or ())


def satisfies(features, reqs):
    """Do these features meet every requirement? Unknown features (None) meet anything."""
    if features is None:
        return True
    have = set(features)
    for req in reqs:
        if not any(((alt[1:] not in have) if alt.startswith("!") else (alt in have))
                   for alt in (a.strip() for a in req.split("|"))):
            return False
    return True


def allowed(features, reqs):
    """Meets the requirements, and carries no restricted feature the slot did not ask for."""
    if not satisfies(features, reqs):
        return False
    if not features:
        return True
    asked = {a.strip() for r in reqs for a in r.split("|")}
    return not any(f in RESTRICTED and f not in asked for f in features)


def check_vocabulary(entry):
    """Problems with an entry's features or requirements (typos), as strings."""
    out = []
    names = list(entry.features or ())
    for req in list(entry.subject) + list(entry.object):
        names += [a.strip().lstrip("!") for a in req.split("|")]
    for name in names:
        if name not in VOCAB:
            out.append(f"'{name}' is not a known feature (known: {', '.join(VOCAB)})")
    return out


# --- parsing and binding ------------------------------------------------------------------------

class Slot:
    def __init__(self, m, library):
        self.start, self.end = m.start(), m.end()
        self.name, self.spec, self.alt = m.group(1), parse_reqs(m.group(2)), m.group(3)
        self.agree = self.alt is not None or (self.name in AGREE and not self.spec)
        self.atom = None            # the lowercase slot name, for an {ATOM}
        self.field = None           # the field name, for a {field}
        if self.agree:
            pass
        elif self.name.isupper() and self.name not in SPECIAL_BLOCKS and library.has_slot(self.name.lower()):
            self.atom = self.name.lower()
        elif self.name in FIELD_KIND:
            self.field = self.name
        self.kind = SLOT_KIND.get(self.atom) or FIELD_KIND.get(self.field)
        self.relational = self.atom in VERBS


def parse(text, library):
    return [Slot(m, library) for m in _PLACEHOLDER.finditer(text)]


def bind(slots):
    """{verb slot index: (subject index or None, object index or None)}."""
    consumed, out = set(), {}
    for i, sl in enumerate(slots):
        if not sl.relational:
            continue
        subject_kinds, object_kind = VERBS[sl.atom]
        subj = next((j for j in range(i - 1, -1, -1)
                     if slots[j].kind in subject_kinds and (sl.atom == "hiding" or j not in consumed)), None)
        obj = None
        if object_kind:
            obj = next((j for j in range(i + 1, len(slots)) if slots[j].kind == object_kind), None)
            if obj is None:                                  # "hid the real one": it means the thing before
                obj = next((j for j in range(i - 1, -1, -1)
                            if slots[j].kind == object_kind and j not in consumed), None)
            if obj is not None:
                consumed.add(obj)
        out[i] = (subj, obj)
    return out


# --- solving ------------------------------------------------------------------------------------

def solve(ctx, text, relax=False):
    """Fill the atoms in `text` (at its top level) so that every restriction holds.
    Returns the text with atoms replaced by their entries' text, ready for the usual
    formatting. Raises Starved if the story can't satisfy the frame. With relax=True
    restrictions are ignored (a last resort)."""
    lib = ctx.engine.library
    slots = parse(text, lib)
    if not slots:
        return text
    for sl in slots:                                       # a name nothing can fill would leak into the text
        if not sl.agree and not (sl.atom or sl.field) and not ctx.can_resolve(sl.name):
            raise Starved(f"nothing fills {{{sl.name}}}")
    bindings = bind(slots)

    values = {}                                            # slot index -> (features, plural)
    for i, sl in enumerate(slots):                         # fields: known already
        if sl.field:
            feats = ctx.field_features(sl.field)
            if not relax and not satisfies(feats, sl.spec):
                raise Starved(f"{sl.field} does not meet {sl.spec}")
            values[i] = feats

    atoms = [i for i, sl in enumerate(slots) if sl.atom]
    plain = [i for i in atoms if not slots[i].relational]
    relational = [i for i in atoms if slots[i].relational]
    chosen = None
    for _ in range(MAX_ATTEMPTS):
        picks, local = {}, set()
        ok = True
        for i in plain:                                    # nouns and plain atoms first
            got = ctx.pick_atom(slots[i].atom, (lambda e, sp=slots[i].spec: relax or allowed(e.features, sp)), local)
            if got is None:
                if relax:
                    raise Starved(f"nothing for {slots[i].atom}")
                raise Starved(f"nothing satisfies {{{slots[i].name}:{','.join(slots[i].spec)}}}")
            picks[i] = got
            local.add((slots[i].atom, got[1].text))
            values[i] = got[1].features
        for i in relational:                               # then verbs, fitted to the nouns
            sl = slots[i]
            subj, obj = bindings[i]
            sf = values.get(subj) if subj is not None else None
            of = values.get(obj) if obj is not None else None
            accept = (lambda e, sl=sl, sf=sf, of=of:
                      relax or (allowed(e.features, sl.spec) and satisfies(sf, e.subject) and satisfies(of, e.object)))
            got = ctx.pick_atom(sl.atom, accept, local)
            if got is None:
                ok = False
                break
            picks[i] = got
            local.add((sl.atom, got[1].text))
            values[i] = got[1].features
        if ok:
            chosen = picks
            break
    if chosen is None:
        raise Starved("a verb found nothing to fit its subject and object")

    log = getattr(ctx.engine, "frame_log", None)
    if log is not None and not relax:                      # tests replay this to re-check every choice
        log.append((text, slots, bindings, {i: chosen[i][1] for i in atoms}, dict(values)))
    replacements = {}
    for i in atoms:                                        # commit in text order
        wl, entry = chosen[i]
        replacements[i] = ctx.finish_atom(slots[i].atom, wl, entry)
    for i, sl in enumerate(slots):
        if sl.agree:
            before = next((j for j in range(i - 1, -1, -1) if slots[j].kind or slots[j].atom), None)
            plural = before is not None and values.get(before) is not None and "plural" in values[before]
            forms = (sl.name, sl.alt) if sl.alt is not None else AGREE[sl.name]
            replacements[i] = forms[1] if plural else forms[0]
    out, last = [], 0
    for i, sl in enumerate(slots):
        out.append(text[last:sl.start])
        if i in replacements:
            out.append(replacements[i])
        elif sl.spec and sl.field:
            out.append("{" + sl.name + "}")                 # a field with a requirement: spec is dropped
        else:
            out.append(text[sl.start:sl.end] if not sl.spec else "{" + sl.name + "}")
        last = sl.end
    out.append(text[last:])
    return "".join(out)


# --- lint: can every frame be filled? -----------------------------------------------------------

def _signatures(entries):
    """{frozenset of features (or None): how many atoms have exactly them}."""
    return Counter(None if e.features is None else frozenset(e.features) for e in entries)


def _atom_entries(library, slot):
    return [e for wl in library.by_slot.get(slot, []) if not wl.generator for e in wl.entries]


def field_signatures(library, field):
    """Feature sets a field can have, with counts. Mirrors Ctx.field_features."""
    if field in ("first", "name", "job"):
        return Counter({frozenset(["human"]): 8, frozenset(["human", "magic"]): 1})
    if field == "place":
        return Counter({frozenset(["outdoor"]): 1})
    slot = {"rival": "rival", "landmark": "landmark", "the_someone": "someone", "the_thing": "thing",
            "the_motif": "thing", "the_message": "message", "the_disaster": "disaster"}.get(field)
    return _signatures(_atom_entries(library, slot)) if slot else Counter({None: 1})


def openers():
    """{template slot: the fixed opener that precedes it} -- "Because of that, {first} " -- so
    the lint can see who a verb's subject is. Character fields are about {first}."""
    from . import structures
    out = {slot: "{first} " for slot in ("want", "need", "flaw", "secret")}
    for shape in structures.registry().values():
        for b in shape.beats:
            out[b.slot] = b.opening
    return out


def lint(library):
    """[(list id, entry text, problem)] for frames that restrictions would starve."""
    problems = []
    cache = {}
    lead = openers()
    for wl in library.lists.values():
        if not wl.is_template:
            continue
        for entry in wl.entries:
            slots = parse(lead.get(wl.slot, "") + entry.text, library)
            if not slots:
                continue
            bindings = bind(slots)

            def pool(i):
                sl = slots[i]
                if sl.field:
                    sig = field_signatures(library, sl.field)
                else:
                    sig = _signatures(_atom_entries(library, sl.atom))
                return Counter({s: n for s, n in sig.items() if satisfies(s, sl.spec)}) if sl.spec and not sl.relational else sig

            for i, sl in enumerate(slots):
                if sl.atom and not sl.relational and sl.spec:
                    n = sum(pool(i).values())
                    if n < MIN_SATISFIERS:
                        problems.append((wl.id, entry.text, f"{{{sl.name}:{','.join(sl.spec)}}} fits only {n} atoms"))
                if sl.field and sl.spec:
                    n = sum(pool(i).values())
                    if n < MIN_SATISFIERS:
                        problems.append((wl.id, entry.text, f"{{{sl.name}:{','.join(sl.spec)}}} fits only {n} possible values"))
            for i, (subj, obj) in bindings.items():
                sl = slots[i]
                verbs = [e for e in _atom_entries(library, sl.atom) if satisfies(e.features, sl.spec)]
                if len(verbs) < MIN_SATISFIERS:
                    problems.append((wl.id, entry.text, f"{{{sl.name}}} has only {len(verbs)} verbs"))
                    continue
                key = (sl.atom, tuple(sl.spec), None if subj is None else tuple(sorted(map(str, pool(subj).items()))),
                       None if obj is None else tuple(sorted(map(str, pool(obj).items()))))
                if key not in cache:
                    cache[key] = _verb_coverage(verbs, pool(subj) if subj is not None else None,
                                                pool(obj) if obj is not None else None)
                coverage, usable_verbs, usable_subject, usable_object = cache[key]
                what = None
                if len(usable_verbs) < MIN_SATISFIERS:
                    what = f"only {len(usable_verbs)} usable verbs"
                elif subj is not None and usable_subject < MIN_SATISFIERS:
                    what = f"only {usable_subject} subjects can use any verb"
                elif obj is not None and usable_object < MIN_SATISFIERS:
                    what = f"only {usable_object} objects can use any verb"
                elif coverage < MIN_COVERAGE:
                    what = f"only {coverage:.0%} of draws find a verb"
                if what:
                    problems.append((wl.id, entry.text, f"{{{sl.name}}}: {what}"))
    return problems


def _verb_coverage(verbs, subjects, objects):
    """(share of subject x object draws with a verb, verbs that fit some draw, atoms usable as
    subject, atoms usable as object)."""
    subjects = subjects or Counter({None: 1})
    objects = objects or Counter({None: 1})
    good = total = 0
    used_verbs, used_s, used_o = set(), Counter(), Counter()
    for sf, sn in subjects.items():
        for of, on in objects.items():
            fits = [k for k, v in enumerate(verbs) if satisfies(sf, v.subject) and satisfies(of, v.object)]
            total += sn * on
            if fits:
                good += sn * on
                used_verbs.update(fits)
                used_s[sf] += sn
                used_o[of] += on
    return (good / total if total else 0.0, used_verbs, sum(used_s.values()), sum(used_o.values()))
