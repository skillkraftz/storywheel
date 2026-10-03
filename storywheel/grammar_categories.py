"""The LanguageTool categories you can switch on and off (Settings > Grammar). See grammar.py."""

# (setting key, LanguageTool category id, label, on by default, what it finds). Fiction and dialogue trigger the "picky" style categories
# constantly (fragments, contractions, repeated words in speech), so those start off. Spelling is Neovim's job, so TYPOS is off too.
CATEGORIES = [
    ("grammar_cat_grammar", "GRAMMAR", "Grammar", True, "agreement, verb forms, articles, word order"),
    ("grammar_cat_punctuation", "PUNCTUATION", "Punctuation", True, "commas, missing or doubled marks"),
    ("grammar_cat_casing", "CASING", "Capital letters", True, "sentence starts, names"),
    ("grammar_cat_confused", "CONFUSED_WORDS", "Confused words", True, "their/there, its/it's, effect/affect"),
    ("grammar_cat_semantics", "SEMANTICS", "Meaning", True, "words that contradict or don't fit"),
    ("grammar_cat_misc", "MISC", "Other", True, "everything LanguageTool files elsewhere"),
    ("grammar_cat_typos", "TYPOS", "Spelling (LanguageTool's)", False, "Neovim's spellcheck does this already, with your universe's names"),
    ("grammar_cat_typography", "TYPOGRAPHY", "Typography", False, "curly quotes, dashes: the manuscript keeps straight quotes on purpose"),
    ("grammar_cat_style", "STYLE", "Style", False, "picky: sentence length, 'very', passive voice; fiction trips it constantly"),
    ("grammar_cat_redundancy", "REDUNDANCY", "Redundancy", False, "picky: 'free gift', 'past history'"),
    ("grammar_cat_plain", "PLAIN_ENGLISH", "Plain English", False, "picky: wordy phrases"),
    ("grammar_cat_colloquial", "COLLOQUIALISMS", "Colloquialisms", False, "picky: informal wording; dialogue is full of it"),
    ("grammar_cat_repetitions", "REPETITIONS_STYLE", "Repeated words", False, "picky: the same word twice nearby"),
]
CATEGORY_DEFAULTS = {key: on for key, _id, _label, on, _hint in CATEGORIES}
