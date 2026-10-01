"""The picking math: blending, weights, the wildcard floor, exclusions, and
per-story overrides that must never leak."""
import copy
from collections import Counter

import pytest

from storywheel.library import Entry
from storywheel.mix import Mix, genres_of, new_mix, story_mix, sync_base
from conftest import PROFILES, make_library, mix_for, wl


def test_single_genre_uses_its_profile(library):
    assert mix_for(library, "western").weights() == {"western": 3, "historical": 2, "general": 1}


def test_two_genres_blend_equally(library):
    w = mix_for(library, "western", "fantasy").weights()
    assert w["western"] == 1.5 and w["fantasy"] == 1.5
    assert w["historical"] == 1.0 and w["mythological"] == 1.0
    assert w["general"] == 1.0                      # shared tag keeps its weight


def test_no_genre_uses_default_profile(library):
    assert mix_for(library).weights() == {"general": 1.0}


def test_unknown_genre_becomes_a_tag(library):
    w = mix_for(library, "steampunk").weights()
    assert w["steampunk"] == 3 and w["general"] == 1


def test_list_weight_is_max_of_its_tags_not_sum(library):
    mix = mix_for(library, "western")
    assert mix.list_weight(wl("job/a", ["western", "historical"])) == 3
    assert mix.list_weight(wl("job/b", ["historical", "general"])) == 2


def test_probabilities_sum_to_one_and_follow_weights(library):
    lists = [wl("job/a", ["western"]), wl("job/b", ["general"])]    # weights 3 and 1, no wildcards
    probs = mix_for(library, "western").list_probabilities(lists)
    assert probs == pytest.approx([0.75, 0.25])


def test_wildcard_floor_takes_its_share(library):
    lists = [wl("job/west", ["western"]), wl("job/space", ["sci-fi"])]
    probs = mix_for(library, "western").list_probabilities(lists)
    assert probs == pytest.approx([0.88, 0.12])


def test_floor_is_split_among_wildcard_lists(library):
    lists = [wl("job/west", ["western"]), wl("job/a", ["sci-fi"]), wl("job/b", ["heist"])]
    probs = mix_for(library, "western").list_probabilities(lists)
    assert probs == pytest.approx([0.88, 0.06, 0.06])


def test_floor_is_configurable():
    lib = make_library([], floor=0.25)
    lists = [wl("job/west", ["western"]), wl("job/space", ["sci-fi"])]
    assert mix_for(lib, "western").list_probabilities(lists) == pytest.approx([0.75, 0.25])


def test_only_wildcards_share_everything(library):
    lists = [wl("job/a", ["sci-fi"]), wl("job/b", ["heist"])]
    assert mix_for(library, "western").list_probabilities(lists) == pytest.approx([0.5, 0.5])


def test_untagged_list_is_a_wildcard(library):
    lists = [wl("job/west", ["western"]), wl("job/none", [])]
    assert mix_for(library, "western").list_probabilities(lists) == pytest.approx([0.88, 0.12])


def test_excluded_tag_has_zero_weight_despite_the_floor(library):
    lists = [wl("job/west", ["western", "historical"]), wl("job/myth", ["mythological"]),
             wl("job/space", ["sci-fi"])]
    mix = mix_for(library, "western", exclude_tags=["historical"])
    probs = mix.list_probabilities(lists)
    assert probs[0] == 0.0
    assert sum(probs) == pytest.approx(1.0)


def test_excluded_list_has_zero_weight(library):
    lists = [wl("job/a", ["western"]), wl("job/b", ["western"]), wl("job/c", ["sci-fi"])]
    mix = mix_for(library, "western", exclude_lists=["job/b"])
    assert mix.list_probabilities(lists)[1] == 0.0


def test_excluded_lists_are_never_drawn(library, engine):
    lists = [wl("job/a", ["western"], ["a"]), wl("job/b", ["mythological"], ["b"]),
             wl("job/c", ["sci-fi"], ["c"])]
    lib = make_library(lists)
    engine.library = lib
    mix = mix_for(lib, "western", exclude_tags=["mythological"], exclude_lists=["job/c"])
    assert {engine.pick("job", mix) for _ in range(300)} == {"a"}


def test_everything_excluded_falls_back_instead_of_returning_nothing(library):
    lists = [wl("job/a", ["western"]), wl("job/b", ["western"])]
    mix = mix_for(library, "western", exclude_tags=["western"])
    assert mix.list_probabilities(lists) == pytest.approx([0.5, 0.5])


def test_boost_multiplies_a_tag(library):
    mix = mix_for(library, "western", boost={"western": 2})
    assert mix.weights()["western"] == 6


def test_boost_brings_in_an_unmentioned_tag(library):
    lists = [wl("job/west", ["western"]), wl("job/frontier", ["frontier"])]
    mix = mix_for(library, "western", boost={"frontier": 1.5})
    assert mix.weights()["frontier"] == 1.5
    probs = mix.list_probabilities(lists)
    assert probs == pytest.approx([3 / 4.5, 1.5 / 4.5])     # both mentioned, no floor needed


def test_exclusion_beats_boost(library):
    mix = mix_for(library, "western", boost={"western": 5}, exclude_tags=["western"])
    assert mix.weights()["western"] == 0


def test_entry_weights(library):
    mix = mix_for(library, "western", exclude_tags=["horror"])
    assert mix.entry_weight(Entry("plain")) == 1
    assert mix.entry_weight(Entry("saloon", ["western"])) == 3
    assert mix.entry_weight(Entry("ship", ["sci-fi"])) == 0.1      # off-mix: rare, not impossible
    assert mix.entry_weight(Entry("ghost", ["horror"])) == 0       # excluded: never


def test_tagged_entries_follow_the_genre(engine):
    lists = [wl("landmark/g", ["general"], ["plain", "plain2", "plain3", Entry("saloon", ["western"])])]
    lib = make_library(lists)
    engine.library = lib
    west = Counter(engine.pick("landmark", mix_for(lib, "western")) for _ in range(3000))
    space = Counter(engine.pick("landmark", mix_for(lib, "horror")) for _ in range(3000))
    assert west["saloon"] > 3 * space["saloon"]


# --- per-story overrides --------------------------------------------------------------

def test_editing_one_stories_mix_leaves_profiles_and_other_stories_alone(library):
    before = copy.deepcopy(library.profiles)
    story_a = {"kept": {"genre": {"genre": "fantasy", "mood": "cozy"}}}
    story_b = {"kept": {"genre": {"genre": "fantasy", "mood": "eerie"}}}
    for s in (story_a, story_b):
        sync_base(s)
    a = Mix.for_story(story_a, library)
    a.exclude_tag("mythological")
    a.exclude_list("job/some-list")
    a.set_boost("fantasy", 2)

    assert library.profiles == before
    b = Mix.for_story(story_b, library)
    assert b.weights()["mythological"] == 2                    # the next fantasy story starts from defaults
    assert story_mix(story_b) == {"base": ["fantasy"], "exclude_tags": [], "exclude_lists": [], "boost": {}}
    assert a.weights()["mythological"] == 0 and a.weights()["fantasy"] == 6


def test_new_mixes_do_not_share_state():
    a, b = new_mix(["western"]), new_mix(["western"])
    a["exclude_tags"].append("rural")
    assert b["exclude_tags"] == []


def test_reset_restores_genre_defaults_and_keeps_the_base(library):
    mix = mix_for(library, "western", "fantasy")
    mix.exclude_tag("historical")
    mix.set_boost("western", 3)
    mix.reset()
    assert mix.data == new_mix(["western", "fantasy"])
    assert mix.weights() == mix_for(library, "western", "fantasy").weights()


def test_toggles_are_idempotent(library):
    mix = mix_for(library, "western")
    mix.exclude_tag("Historical")
    mix.exclude_tag("historical")
    assert mix.data["exclude_tags"] == ["historical"]
    mix.exclude_tag("historical", on=False)
    assert mix.data["exclude_tags"] == []
    mix.set_boost("western", 2)
    mix.set_boost("western", 1)
    assert mix.data["boost"] == {}


def test_base_follows_the_kept_genre_but_exclusions_stay():
    story = {"kept": {"genre": {"genre": "Western / fairy tale", "mood": "cozy"}}}
    assert genres_of(story) == ["western", "fairy tale"]
    sync_base(story)
    story["mix"]["exclude_tags"].append("rural")
    story["kept"]["genre"]["genre"] = "noir"
    sync_base(story)
    assert story["mix"]["base"] == ["noir"] and story["mix"]["exclude_tags"] == ["rural"]


def test_story_without_genre_has_empty_base():
    story = {"kept": {}}
    sync_base(story)
    assert story["mix"]["base"] == []


def test_profiles_ship_for_all_14_v1_genres():
    from storywheel.library import Library
    names = set(Library.load().genre_names)
    assert {"mystery", "romance", "horror", "western", "sci-fi", "comedy", "fairy tale",
            "heist", "ghost story", "coming-of-age", "noir", "thriller", "fantasy",
            "adventure"} <= names
