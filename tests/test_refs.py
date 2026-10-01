"""Reference substitution and text polish."""
from storywheel.refs import apply_pairs, change_pairs, substitute, with_field
from storywheel.text import fix_articles, motif_from, plural, pronouns, singular, title_case


def test_changing_a_field_updates_mentions_in_the_same_item():
    cand = {"landmark": "the old mill", "rumor": "something is buried under the old mill"}
    new = with_field(cand, "landmark", "the lighthouse")
    assert new["rumor"] == "something is buried under the lighthouse"


def test_edited_field_is_marked_and_other_fields_untouched():
    cand = {"place": "Dry Fork", "era": "the 1880s"}
    new = with_field(cand, "place", "Salt Fork", src="edited")
    assert new == {"place": "Salt Fork", "era": "the 1880s", "_src": "edited"}


def test_renaming_the_protagonist_updates_later_steps():
    story = {"kept": {
        "protagonist": {"name": "Wade Hollis", "job": "baker"},
        "spine": {"once": "Wade was a baker.", "one_day": "One day, Wade Hollis left."},
        "twist": {"twist": "Wade did it."},
    }}
    old = {"name": "Wade Hollis", "job": "baker"}
    new = {"name": "Mara Quill", "job": "baker"}
    story["kept"]["protagonist"] = new
    n = substitute(story, 2, old, new)
    assert n == 3
    assert story["kept"]["spine"] == {"once": "Mara was a baker.", "one_day": "One day, Mara Quill left."}
    assert story["kept"]["twist"] == {"twist": "Mara did it."}


def test_steps_before_the_change_are_left_alone():
    story = {"kept": {"title": {"title": "Wade's Lantern", "motif": "lantern"},
                      "setting": {"place": "Dry Fork"}}}
    substitute(story, 3, {"place": "Dry Fork"}, {"place": "Salt Fork"})   # setting is step 4 (index 3)
    assert story["kept"]["title"]["title"] == "Wade's Lantern"


def test_swaps_match_whole_words_and_survive_odd_replacements():
    fields = {"a": "the cat sat on the category", "b": "x"}
    apply_pairs(fields, [("cat", r"d\og")])
    assert fields["a"] == r"the d\og sat on the category"


def test_short_values_are_not_swapped():
    assert change_pairs({"age": "9"}, {"age": "10"}) == []


def test_pronouns_after_first_mention():
    assert pronouns("Christina let Christina's mother go with Christina", "Christina") == \
        "Christina let their mother go with them"
    assert pronouns("Christina waited", "Christina") == "Christina waited"


def test_articles():
    assert fix_articles("a owl and A apple, a pear") == "an owl and An apple, a pear"


def test_articles_know_consonant_and_vowel_sounds():
    assert fix_articles("a one-armed blacksmith, an one-armed cook") == "a one-armed blacksmith, a one-armed cook"
    assert fix_articles("a unicorn, an unicorn, a used cart") == "a unicorn, a unicorn, a used cart"
    assert fix_articles("a hour, a honest man, a umbrella") == "an hour, an honest man, an umbrella"


def test_plurals_and_singulars():
    assert plural("story") == "stories" and plural("fox") == "foxes" and plural("cat") == "cats"
    assert singular("stags") == "stag" and singular("stories") == "story" and singular("glass") == "glass"


def test_motif_from_title():
    assert motif_from("The Wonderful Wizard of Oz", lambda: "x") == "wizard"
    assert motif_from("Grapes From Space", lambda: "x") == "grape"
    assert motif_from("Of The", lambda: "fallback") == "fallback"


def test_title_case_keeps_small_words_down():
    assert title_case("the keeper of the lighthouse") == "The Keeper of the Lighthouse"
