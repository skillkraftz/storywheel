"""The offline dictionary and thesaurus: building the index, lookups (inflected, missing), the CLI, no network at run time."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from dictfixture import build_fixture
from storywheel import dictionary, dictionary_build

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def index(tmp_path, monkeypatch):
    out, counts = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    dictionary.forget()
    yield out
    dictionary.forget()


def test_the_index_is_built_with_counts(tmp_path):
    out, counts = build_fixture(tmp_path)
    assert out.exists() and counts["synsets"] == 18 and counts["moby_roots"] == 5 and counts["words"] > 15


def test_ids_pack_and_unpack():
    ids = [5, 900, 3, 70000, 5]
    assert dictionary_build.unpack_ids(dictionary_build.pack_ids(ids)) == [3, 5, 900, 70000]
    assert dictionary_build.unpack_ids(dictionary_build.pack_ids([])) == []


def test_a_common_word_has_meanings_examples_synonyms_and_a_kind_of(index):
    r = dictionary.lookup("dog")
    assert r["found"] and len(r["entries"]) == 1
    e = r["entries"][0]
    noun = next(p for p in e["parts"] if p["pos"] == "noun")
    assert [s["definition"] for s in noun["senses"]] == ["a domesticated canine", "a despicable person"]
    assert noun["senses"][0]["examples"] == ["the dog barked"] and noun["senses"][0]["kind_of"] == ["canine"]
    assert e["close_synonyms"][:2] == ["domestic dog", "wretch"]               # WordNet first
    assert e["synonyms"][2:] == ["cur", "hound", "mutt", "pooch"]               # then the wider (Moby) list, no repeats
    assert "dog" not in [w.lower() for w in e["synonyms"]]


@pytest.mark.parametrize("form,base", [("geese", "goose"), ("wolves", "wolf"), ("running", "run"), ("ran", "run"), ("dogs", "dog"),
                                       ("Happier", "happy"), ("DOGS", "dog"), ("dog's", "dog"), ("  dog. ", "dog"), ("sprinted", "sprint"),
                                       ("dashes", "dash"), ("leaves", "leaf")])
def test_inflected_forms_find_the_base_word(index, form, base):
    r = dictionary.lookup(form)
    assert r["found"] and base in [e["word"] for e in r["entries"]], r["entries"]


def test_a_form_says_what_it_is_a_form_of(index):
    e = dictionary.lookup("geese")["entries"][0]
    assert e["word"] == "goose" and e["form_of"] == "geese"
    e = dictionary.lookup("dog")["entries"][0]
    assert e["form_of"] is None


def test_leaves_gives_both_the_noun_and_the_verb_base(index):
    words = [e["word"] for e in dictionary.lookup("leaves")["entries"]]
    assert "leaf" in words and "leave" in words


def test_opposites_come_from_wordnet_and_from_the_head_of_a_similar_adjective(index):
    assert dictionary.lookup("happy")["entries"][0]["antonyms"] == ["unhappy"]
    assert dictionary.lookup("unhappy")["entries"][0]["antonyms"] == ["happy"]
    assert dictionary.lookup("cheerful")["entries"][0]["antonyms"] == ["unhappy", "sad"]          # via "similar" to the head (happy, glad)


def test_a_word_only_in_the_thesaurus_still_has_synonyms(index):
    r = dictionary.lookup("happy")
    assert r["entries"][0]["synonyms"][0] == "glad" and "joyful" in r["entries"][0]["synonyms"]


def test_a_missing_word_says_so_and_offers_close_spellings(index):
    r = dictionary.lookup("hapyp")
    assert not r["found"] and r["entries"] == [] and "happy" in r["suggestions"]
    assert dictionary.lookup("zzzqx")["suggestions"] == []
    assert dictionary.lookup("")["found"] is False
    text = "\n".join(dictionary.card_lines(dictionary.lookup("hapyp")))
    assert "No entry for 'hapyp'" in text and "Did you mean: happy" in text


def test_the_card_text_groups_by_part_of_speech(index):
    text = "\n".join(dictionary.card_lines(dictionary.lookup("run")))
    assert "verb" in text and "1. move fast by using legs" in text and "“She ran home”" in text
    assert "similar: sprint, dash" in text and "More similar words:" in text and "gallop" in text


def test_every_similar_word_is_returned_never_cut_off(index):
    e = dictionary.lookup("dog")["entries"][0]
    assert e["synonyms"] == ["domestic dog", "wretch", "cur", "hound", "mutt", "pooch"] and "more_synonyms" not in e
    assert e["close_synonyms"] == ["domestic dog", "wretch"] and e["wide_synonyms"] == ["cur", "hound", "mutt", "pooch"]
    assert "more" not in " ".join(dictionary.card_lines(dictionary.lookup("dog"))).replace("More similar words", "")


def test_each_meaning_lists_its_own_similar_words_types_parts_and_related_forms(index):
    e = dictionary.lookup("dog")["entries"][0]
    noun = next(p for p in e["parts"] if p["pos"] == "noun")
    first, second = noun["senses"]
    assert first["synonyms"] == ["domestic dog"] and second["synonyms"] == ["wretch"]
    assert first["types_of"] == ["puppy", "pup"] and first["parts"] == ["tail"] and first["kind_of"] == ["canine"]
    assert e["related_forms"] == {"derivation": ["doggy"]}
    tail = dictionary.lookup("tail")["entries"][0]["parts"][0]["senses"][0]
    assert tail["part_of"] == ["dog", "domestic dog"]


def test_indirect_opposites_are_the_opposites_of_similar_words_and_labelled(index):
    e = dictionary.lookup("happy")["entries"][0]
    assert e["antonyms"] == ["unhappy"]
    assert e["indirect_antonyms"] == [{"word": "sad", "via": "glad"}]               # sad is the opposite of glad, which is similar to happy
    text = "\n".join(dictionary.card_lines(dictionary.lookup("happy")))
    assert "Opposite (indirect, opposites of similar words):" in text and "sad (of glad)" in text


def test_vocabulary_gathers_types_parts_subject_terms_and_related_words(index):
    v = dictionary.vocabulary("dog")
    assert v["found"]
    s = v["senses"][0]
    assert s["types"] == ["puppy", "pup"] and s["parts"] == ["tail"] and s["kinds"] == ["canine"]
    assert s["domain"] == ["kennel", "vaccinate", "veterinary medicine"] or set(s["domain"]) == {"kennel", "vaccinate", "veterinary medicine"}
    assert v["related"] == ["cur", "hound", "mutt", "pooch"]
    assert dictionary.vocabulary("zzzqx")["found"] is False


def test_an_index_from_an_older_version_asks_to_be_rebuilt(tmp_path, monkeypatch):
    import sqlite3
    old = tmp_path / "old.sqlite"
    db = sqlite3.connect(str(old))
    db.execute("create table meta (key text, value text)")
    db.execute("insert into meta values ('schema', '1')")
    db.commit(); db.close()
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(old))
    dictionary.forget()
    with pytest.raises(dictionary.DictionaryMissing, match="older version"):
        dictionary.lookup("dog")


def test_candidates_cover_the_regular_endings():
    c = dictionary.candidates
    assert "run" in c("running") and "make" in c("making") and "city" in c("cities") and "box" in c("boxes") and "stop" in c("stopped")
    assert "happy" in c("happier") and "big" in c("biggest") and "wolf" in c("wolves")


def test_not_installed_is_a_plain_message(tmp_path, monkeypatch):
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(tmp_path / "none.sqlite"))
    dictionary.forget()
    assert dictionary.installed() is False
    with pytest.raises(dictionary.DictionaryMissing, match="storywheel dictionary install"):
        dictionary.lookup("dog")


def cli(*args, env_index=None):
    import os
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    if env_index:
        env["STORYWHEEL_DICTIONARY"] = str(env_index)
    return subprocess.run([sys.executable, "-m", "storywheel", *args], capture_output=True, text=True, env=env, timeout=60)


def test_cli_define_and_thesaurus_json(index):
    d = json.loads(cli("define", "geese", "--json", env_index=index).stdout)
    assert d["found"] and d["entries"][0]["word"] == "goose" and d["entries"][0]["parts"][0]["senses"][0]["definition"].startswith("web-footed")
    assert "synonyms" not in d["entries"][0]
    t = json.loads(cli("thesaurus", "happy", "--json", env_index=index).stdout)
    e = t["entries"][0]
    assert e["close_synonyms"] == ["glad"] and "joyful" in e["synonyms"] and e["antonyms"] == ["unhappy"] and "parts" not in e
    assert e["indirect_antonyms"] == [{"word": "sad", "via": "glad"}] and "wide_synonyms" in e
    v = json.loads(cli("vocabulary", "dog", "--json", env_index=index).stdout)
    assert v["found"] and v["senses"][0]["types"] == ["puppy", "pup"]
    m = json.loads(cli("lookup", "happy", "--json", env_index=index).stdout)
    assert "parts" in m["entries"][0] and "synonyms" in m["entries"][0]


def test_cli_text_output_and_missing_word(index):
    out = cli("thesaurus", "happy", env_index=index).stdout
    assert "similar:  glad" in out and "opposite: unhappy" in out
    out = cli("define", "hapyp", env_index=index).stdout
    assert "No entry for 'hapyp'" in out and "Did you mean: happy" in out
    assert json.loads(cli("define", "zzzqx", "--json", env_index=index).stdout)["found"] is False


def test_cli_without_a_dictionary_exits_with_the_install_message(tmp_path):
    r = cli("define", "dog", "--json", env_index=tmp_path / "none.sqlite")
    assert r.returncode == 1 and json.loads(r.stdout)["installed"] is False and "dictionary install" in json.loads(r.stdout)["error"]


def test_cli_dictionary_build_and_status(tmp_path, monkeypatch):
    out, _ = build_fixture(tmp_path / "src")
    target = tmp_path / "built.sqlite"
    r = cli("dictionary", "build", "--oewn", str(tmp_path / "src" / "oewn.xml"), "--moby", str(tmp_path / "src" / "moby.txt"), env_index=target)
    assert r.returncode == 0 and "Dictionary ready" in r.stdout, r.stdout + r.stderr
    st = json.loads(cli("dictionary", "status", "--json", env_index=target).stdout)
    assert st["installed"] and "CC BY 4.0" in st["wordnet"] and "public domain" in st["moby"]


def test_lookups_never_use_the_network(index, monkeypatch):
    import socket
    def boom(*a, **k):
        raise AssertionError("network used")
    monkeypatch.setattr(socket.socket, "connect", boom)
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    assert dictionary.lookup("running")["found"]


def test_only_install_can_touch_the_network():
    import inspect
    from storywheel import dictionary as d, dictionary_build as b
    assert "urllib" not in inspect.getsource(d) and "socket" not in inspect.getsource(d)
    assert "urlopen" in inspect.getsource(b.download)


def test_a_lookup_takes_milliseconds(index):
    import time
    dictionary.lookup("dog")
    t = time.perf_counter()
    for w in ("dog", "running", "geese", "happy", "hapyp"):
        dictionary.lookup(w)
    assert (time.perf_counter() - t) / 5 < 0.05
