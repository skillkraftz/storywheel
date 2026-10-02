"""English word forms: which form is this word in (running = the -ing form of run), and the same form of another word
(sprint -> sprinting). Used to make a replacement from the thesaurus fit the sentence.

Irregular words come from the tables below (WordNet's own lists of irregular forms are incomplete and untagged: "write" lists
"written" but not "wrote"); everything else follows the usual spelling rules.
"""
import re

VOWELS = "aeiou"

IRREGULAR_VERBS = {  # base: (past, past participle)
    "arise": ("arose", "arisen"), "awake": ("awoke", "awoken"), "be": ("was", "been"), "bear": ("bore", "borne"),
    "beat": ("beat", "beaten"), "become": ("became", "become"), "begin": ("began", "begun"), "bend": ("bent", "bent"),
    "bet": ("bet", "bet"), "bid": ("bid", "bid"), "bind": ("bound", "bound"), "bite": ("bit", "bitten"), "bleed": ("bled", "bled"),
    "blow": ("blew", "blown"), "break": ("broke", "broken"), "breed": ("bred", "bred"), "bring": ("brought", "brought"),
    "build": ("built", "built"), "burn": ("burnt", "burnt"), "burst": ("burst", "burst"), "buy": ("bought", "bought"),
    "cast": ("cast", "cast"), "catch": ("caught", "caught"), "choose": ("chose", "chosen"), "cling": ("clung", "clung"),
    "come": ("came", "come"), "cost": ("cost", "cost"), "creep": ("crept", "crept"), "cut": ("cut", "cut"), "deal": ("dealt", "dealt"),
    "dig": ("dug", "dug"), "do": ("did", "done"), "draw": ("drew", "drawn"), "dream": ("dreamt", "dreamt"), "drink": ("drank", "drunk"),
    "drive": ("drove", "driven"), "eat": ("ate", "eaten"), "fall": ("fell", "fallen"), "feed": ("fed", "fed"), "feel": ("felt", "felt"),
    "fight": ("fought", "fought"), "find": ("found", "found"), "flee": ("fled", "fled"), "fling": ("flung", "flung"), "fly": ("flew", "flown"),
    "forbid": ("forbade", "forbidden"), "forget": ("forgot", "forgotten"), "forgive": ("forgave", "forgiven"), "freeze": ("froze", "frozen"),
    "get": ("got", "gotten"), "give": ("gave", "given"), "go": ("went", "gone"), "grind": ("ground", "ground"), "grow": ("grew", "grown"),
    "hang": ("hung", "hung"), "have": ("had", "had"), "hear": ("heard", "heard"), "hide": ("hid", "hidden"), "hit": ("hit", "hit"),
    "hold": ("held", "held"), "hurt": ("hurt", "hurt"), "keep": ("kept", "kept"), "kneel": ("knelt", "knelt"), "know": ("knew", "known"),
    "lay": ("laid", "laid"), "lead": ("led", "led"), "leap": ("leapt", "leapt"), "learn": ("learnt", "learnt"), "leave": ("left", "left"),
    "lend": ("lent", "lent"), "let": ("let", "let"), "lie": ("lay", "lain"), "light": ("lit", "lit"), "lose": ("lost", "lost"),
    "make": ("made", "made"), "mean": ("meant", "meant"), "meet": ("met", "met"), "mistake": ("mistook", "mistaken"), "overcome": ("overcame", "overcome"),
    "pay": ("paid", "paid"), "put": ("put", "put"), "quit": ("quit", "quit"), "read": ("read", "read"), "ride": ("rode", "ridden"),
    "ring": ("rang", "rung"), "rise": ("rose", "risen"), "run": ("ran", "run"), "say": ("said", "said"), "see": ("saw", "seen"),
    "seek": ("sought", "sought"), "sell": ("sold", "sold"), "send": ("sent", "sent"), "set": ("set", "set"), "sew": ("sewed", "sewn"),
    "shake": ("shook", "shaken"), "shed": ("shed", "shed"), "shine": ("shone", "shone"), "shoot": ("shot", "shot"), "show": ("showed", "shown"),
    "shrink": ("shrank", "shrunk"), "shut": ("shut", "shut"), "sing": ("sang", "sung"), "sink": ("sank", "sunk"), "sit": ("sat", "sat"),
    "sleep": ("slept", "slept"), "slide": ("slid", "slid"), "sling": ("slung", "slung"), "smell": ("smelt", "smelt"), "speak": ("spoke", "spoken"),
    "speed": ("sped", "sped"), "spend": ("spent", "spent"), "spill": ("spilt", "spilt"), "spin": ("spun", "spun"), "spit": ("spat", "spat"),
    "split": ("split", "split"), "spread": ("spread", "spread"), "spring": ("sprang", "sprung"), "stand": ("stood", "stood"),
    "steal": ("stole", "stolen"), "stick": ("stuck", "stuck"), "sting": ("stung", "stung"), "stink": ("stank", "stunk"),
    "stride": ("strode", "stridden"), "strike": ("struck", "struck"), "string": ("strung", "strung"), "strive": ("strove", "striven"),
    "swear": ("swore", "sworn"), "sweep": ("swept", "swept"), "swell": ("swelled", "swollen"), "swim": ("swam", "swum"), "swing": ("swung", "swung"),
    "take": ("took", "taken"), "teach": ("taught", "taught"), "tear": ("tore", "torn"), "tell": ("told", "told"), "think": ("thought", "thought"),
    "throw": ("threw", "thrown"), "thrust": ("thrust", "thrust"), "tread": ("trod", "trodden"), "undergo": ("underwent", "undergone"),
    "understand": ("understood", "understood"), "undo": ("undid", "undone"), "upset": ("upset", "upset"), "wake": ("woke", "woken"),
    "wear": ("wore", "worn"), "weave": ("wove", "woven"), "weep": ("wept", "wept"), "win": ("won", "won"), "wind": ("wound", "wound"),
    "withdraw": ("withdrew", "withdrawn"), "wring": ("wrung", "wrung"), "write": ("wrote", "written"),
}
IRREGULAR_NOUNS = {  # singular: plural
    "child": "children", "man": "men", "woman": "women", "person": "people", "foot": "feet", "tooth": "teeth", "goose": "geese",
    "mouse": "mice", "louse": "lice", "ox": "oxen", "die": "dice", "leaf": "leaves", "wolf": "wolves", "knife": "knives", "wife": "wives",
    "life": "lives", "half": "halves", "calf": "calves", "shelf": "shelves", "loaf": "loaves", "thief": "thieves", "self": "selves",
    "elf": "elves", "scarf": "scarves", "hoof": "hooves", "sheep": "sheep", "deer": "deer", "fish": "fish", "moose": "moose",
    "series": "series", "species": "species", "aircraft": "aircraft", "cactus": "cacti", "fungus": "fungi", "nucleus": "nuclei",
    "radius": "radii", "stimulus": "stimuli", "alumnus": "alumni", "analysis": "analyses", "basis": "bases", "crisis": "crises",
    "diagnosis": "diagnoses", "hypothesis": "hypotheses", "thesis": "theses", "oasis": "oases", "phenomenon": "phenomena",
    "criterion": "criteria", "datum": "data", "medium": "media", "bacterium": "bacteria", "appendix": "appendices", "index": "indices",
    "matrix": "matrices", "vertex": "vertices", "axis": "axes", "genus": "genera", "gallows": "gallows", "trellis": "trellises",
    "hero": "heroes", "potato": "potatoes", "tomato": "tomatoes", "echo": "echoes", "veto": "vetoes", "torpedo": "torpedoes",
    "piano": "pianos", "photo": "photos", "roof": "roofs", "chief": "chiefs", "belief": "beliefs", "cliff": "cliffs", "proof": "proofs",
}
IRREGULAR_ADJECTIVES = {  # base: (comparative, superlative)
    "good": ("better", "best"), "bad": ("worse", "worst"), "ill": ("worse", "worst"), "far": ("farther", "farthest"),
    "little": ("less", "least"), "many": ("more", "most"), "much": ("more", "most"), "old": ("older", "oldest"),
    "well": ("better", "best"),
}
TWO_SYLLABLE_ER = {"narrow", "simple", "gentle", "clever", "quiet", "polite", "common", "handsome", "pleasant", "cruel", "stupid",
                   "able", "humble", "feeble", "noble", "subtle", "sincere", "severe", "remote", "mature"}
STRESSED_LAST = {"begin", "forget", "regret", "prefer", "refer", "occur", "admit", "commit", "permit", "submit", "control", "patrol",
                 "compel", "expel", "propel", "rebel", "excel", "equip", "omit", "upset", "offset", "unwrap", "repel", "confer", "defer",
                 "transfer", "deter", "incur", "recur", "overrun", "outrun", "forbid", "beget", "inter", "abet"}
ES_AFTER_O = {"go", "do", "echo", "hero", "potato", "tomato", "veto", "torpedo", "volcano", "tornado", "mosquito", "cargo", "domino"}
INVERSE_VERBS = {past: base for base, (past, _pp) in IRREGULAR_VERBS.items()}


def syllables(word):
    w = word.lower()
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
        n -= 1
    return max(1, n)


def _doubles(w):
    """Does a final consonant double before -ing/-ed/-er (run -> running, begin -> beginning, visit -> visiting)?"""
    if w in STRESSED_LAST:
        return True
    return bool(re.search(r"[^aeiou][aeiou][^aeiouwxy]$", w)) and syllables(w) == 1 and not w.endswith(("er", "en"))


def add_s(w):
    if w in IRREGULAR_NOUNS:
        return IRREGULAR_NOUNS[w]
    if w == "have":
        return "has"
    if re.search(r"(s|x|z|ch|sh)$", w):
        return w + "es"
    if re.search(r"[^aeiou]y$", w):
        return w[:-1] + "ies"
    if w in ES_AFTER_O:
        return w + "es"
    return w + "s"


def add_ed(w):
    if w.endswith("e"):
        return w + "d"
    if re.search(r"[^aeiou]y$", w):
        return w[:-1] + "ied"
    if _doubles(w):
        return w + w[-1] + "ed"
    if w.endswith("c") and syllables(w) > 1 and w.endswith("ic"):
        return w + "ked"
    return w + "ed"


def add_ing(w):
    if w.endswith("ie"):
        return w[:-2] + "ying"
    if w.endswith("e") and not w.endswith(("ee", "ye", "oe")) and len(w) > 2:
        return w[:-1] + "ing"
    if _doubles(w):
        return w + w[-1] + "ing"
    if w.endswith("ic") and syllables(w) > 1:
        return w + "king"
    return w + "ing"


def past(w):
    return IRREGULAR_VERBS[w][0] if w in IRREGULAR_VERBS else add_ed(w)


def participle(w):
    return IRREGULAR_VERBS[w][1] if w in IRREGULAR_VERBS else add_ed(w)


def verb_s(w):
    return "is" if w == "be" else "has" if w == "have" else add_s(w) if w not in IRREGULAR_NOUNS else w + "s"


def _short_adjective(w):
    return syllables(w) == 1 or (syllables(w) == 2 and w.endswith("y")) or w in TWO_SYLLABLE_ER


def _er_est(w, suffix):
    if w.endswith("e"):
        return w + suffix[1:]
    if re.search(r"[^aeiou]y$", w):
        return w[:-1] + "i" + suffix
    if re.search(r"[^aeiou][aeiou][^aeiouwxy]$", w) and syllables(w) == 1:
        return w + w[-1] + suffix
    return w + suffix


def comparative(w):
    if w in IRREGULAR_ADJECTIVES:
        return IRREGULAR_ADJECTIVES[w][0]
    return _er_est(w, "er") if _short_adjective(w) else "more " + w


def superlative(w):
    if w in IRREGULAR_ADJECTIVES:
        return IRREGULAR_ADJECTIVES[w][1]
    return _er_est(w, "est") if _short_adjective(w) else "most " + w


# the forms a word can be in, relative to its base
KINDS = ("base", "s", "past", "pp", "ing", "er", "est")


def forms_of(base):
    """{kind: form} for every kind that makes sense for some part of speech (verb and noun share 's')."""
    w = base.lower()
    return {"base": w, "s": verb_s(w) if w in IRREGULAR_VERBS or w not in IRREGULAR_NOUNS else IRREGULAR_NOUNS[w],
            "past": past(w), "pp": participle(w), "ing": add_ing(w), "er": comparative(w), "est": superlative(w)}


def classify(original, base):
    """Which form of `base` is `original`? One of KINDS, or None when it is not a form of that word."""
    o, b = original.lower(), base.lower()
    if o == b:
        return "base"
    candidates = [("s", [add_s(b), verb_s(b)]), ("ing", [add_ing(b)]), ("past", [past(b)]), ("pp", [participle(b)]),
                  ("er", [comparative(b)]), ("est", [superlative(b)])]
    for kind, forms in candidates:
        if o in forms:
            return kind
    if b in IRREGULAR_NOUNS and o == IRREGULAR_NOUNS[b]:
        return "s"
    return None


def inflect(base, kind, pos=None):
    """The `kind` form of `base`; `pos` ('noun', 'verb', 'adjective', 'adverb') chooses between readings when given.
    Several-word phrases change the word that carries the form (the first word of a verb phrase, the last of a noun phrase).
    A form that makes no sense for the word (-ing of a noun) leaves it as it is."""
    if kind in (None, "base"):
        return base
    words = base.split(" ")
    idx = 0 if pos == "verb" or kind in ("past", "pp", "ing") else len(words) - 1
    if kind in ("er", "est"):
        if pos in ("noun", "verb"):
            return base
        if len(words) > 1:
            return ("more " if kind == "er" else "most ") + base
        return comparative(base.lower()) if kind == "er" else superlative(base.lower())
    if kind in ("past", "pp", "ing") and pos in ("noun", "adjective", "adverb"):
        return base
    if kind == "s" and pos in ("adjective", "adverb"):
        return base
    w = words[idx].lower()
    if kind == "s":
        words[idx] = verb_s(w) if pos == "verb" else add_s(w)
    else:
        words[idx] = {"past": past, "pp": participle, "ing": add_ing}[kind](w)
    return " ".join(words)


def reinflect(original, base, to, pos=None, db=None):
    """The word `to` in the same form as `original` is of `base` ("running", "run", "sprint" -> "sprinting").
    Capital letters are the caller's business (the Writer keeps the original's)."""
    kind = classify(original, base)
    if kind in (None, "base"):
        return to
    if pos is None and db is not None:
        pos = _best_pos(db, to, kind)
    return inflect(to, kind, pos)


def _best_pos(db, word, kind):
    rows = db.execute("select distinct s.pos from senses s join words w on w.id = s.word_id where w.w = ?", (word.lower(),)).fetchall()
    have = {"noun" if p == "n" else "verb" if p == "v" else "adjective" if p in ("a", "s") else "adverb" for (p,) in rows}
    order = {"s": ("noun", "verb"), "past": ("verb",), "pp": ("verb",), "ing": ("verb",), "er": ("adjective", "adverb"),
             "est": ("adjective", "adverb")}.get(kind, ())
    for p in order:
        if p in have:
            return p
    return "verb" if kind in ("past", "pp", "ing") else "adjective" if kind in ("er", "est") else None
