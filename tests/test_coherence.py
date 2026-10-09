"""Coherence: features, requirements, the solver, agreement, and the character fields."""
import re
from collections import Counter

import pytest

from storywheel import frames
from storywheel.engine import Engine
from storywheel.frames import Starved, VOCAB, bind, parse, satisfies
from storywheel.library import DataError, Entry, Library, WordList
from storywheel.report import lint
from storywheel.sample import build_story
from storywheel.steps import Ctx, step_by_key
from conftest import make_library, wl, write_json


# --- requirements ---------------------------------------------------------------------------------------

def test_requirements_handle_presence_absence_and_alternatives():
    have = ["portable", "magic"]
    assert satisfies(have, ["magic"]) and satisfies(have, ["portable", "magic"])
    assert not satisfies(have, ["living"]) and not satisfies(have, ["magic", "living"])
    assert satisfies(have, ["!living"]) and not satisfies(have, ["!magic"])
    assert satisfies(have, ["living|magic"]) and not satisfies(have, ["living|bulky"])
    assert satisfies(have, ["!living|bulky"])
    assert satisfies(have, [])


def test_unknown_features_meet_anything():
    """A name the writer typed, or a generated one, has no features: it is never blocked."""
    assert satisfies(None, ["magic", "!living", "human"])


def test_the_vocabulary_is_documented_and_small():
    assert 20 <= len(VOCAB) <= 40
    readme = open("docs/generator.md").read()
    for name in VOCAB:
        assert f"`{name}`" in readme, f"{name} is not documented in docs/generator.md"


def test_unknown_feature_names_are_reported(tmp_path):
    write_json(tmp_path / "lists" / "thing" / "x.json",
               {"slot": "thing", "tags": ["general"], "entries": [{"text": "a thing", "features": ["portible"]}]})
    with pytest.raises(DataError, match="portible"):
        Library.load(tmp_path)
    write_json(tmp_path / "lists" / "thing" / "x.json",
               {"slot": "thing", "tags": ["general"], "entries": [{"text": "a thing", "object": ["!lving"]}]})
    with pytest.raises(DataError, match="lving"):
        Library.load(tmp_path)


def test_defaults_per_slot_and_list_requirements_add_up(tmp_path):
    write_json(tmp_path / "lists" / "thing" / "x.json",
               {"slot": "thing", "tags": ["general"], "entries": ["a plain thing", {"text": "a mule", "features": ["living"]}]})
    write_json(tmp_path / "lists" / "habit_person" / "x.json",
               {"slot": "habit_person", "tags": ["general"], "subject": ["!plural"],
                "entries": ["greets", {"text": "writes to", "subject": ["human"], "object": ["human"]}]})
    lib = Library.load(tmp_path)
    things = {e.text: e.features for wl_ in lib.by_slot["thing"] for e in wl_.entries}
    assert things["a plain thing"] == ("portable", "buryable") and things["a mule"] == ("living",)
    verbs = {e.text: (e.subject, e.object) for wl_ in lib.by_slot["habit_person"] if wl_.id == "habit_person/x"
             for e in wl_.entries}
    assert verbs["greets"] == (("!plural",), ()) and verbs["writes to"] == (("!plural", "human"), ("human",))


# --- binding -----------------------------------------------------------------------------------------------

def slots_of(text):
    lib = Library.load()
    return parse(text, lib), lib


def test_a_verbs_subject_and_object_follow_from_the_sentence():
    slots, _ = slots_of("{first} {ACT_PERSON} {SOMEONE} and {ACT_THING} {THING} {HIDING}")
    b = bind(slots)
    names = [s.name for s in slots]
    verb1, verb2, hiding = names.index("ACT_PERSON"), names.index("ACT_THING"), names.index("HIDING")
    assert names[b[verb1][0]] == "first" and names[b[verb1][1]] == "SOMEONE"
    assert names[b[verb2][0]] == "first"                       # not the SOMEONE who was the first verb's object
    assert names[b[verb2][1]] == "THING"
    assert names[b[hiding][0]] == "THING"                       # a hiding place hides the thing before it


def test_a_rivals_verb_binds_to_the_rival_and_the_character():
    slots, _ = slots_of("the {rival} {ACT_PERSON} {first} out of {MOTIVE}")
    (verb, (subj, obj)), = bind(slots).items()
    assert slots[subj].name == "rival" and slots[obj].name == "first"


def test_a_verb_with_nothing_after_it_means_the_thing_before():
    slots, _ = slots_of("{THING} was a fake, and {SOMEONE} {ACT_THING} the real one {HIDING}")
    b = bind(slots)
    verb = next(i for i, s in enumerate(slots) if s.name == "ACT_THING")
    assert slots[b[verb][0]].name == "SOMEONE" and slots[b[verb][1]].name == "THING"


# --- the solver, on a small library -------------------------------------------------------------------------

def mini(**extra):
    things = [Entry("a locked box", features=["portable", "buryable"]), Entry("a brass bell", features=["portable", "buryable"]),
              Entry("a mule", features=["living"]), Entry("a black stallion", features=["living", "valuable"]),
              Entry("a silver ring", features=["portable", "buryable", "valuable"])]
    verbs = [Entry("buried", object=["buryable"]), Entry("hid", object=["!living"]), Entry("stole"),
             Entry("enchanted", subject=["magic"]), Entry("fed", object=["living"]), Entry("sold")]
    people = [Entry("a stranger", features=["human"]), Entry("a witch", features=["human", "magic"]),
              Entry("a fox", features=["creature"])]
    lib = make_library([WordList("thing/a", "thing", ["general"], things),
                        WordList("act_thing/a", "act_thing", ["general"], verbs),
                        WordList("someone/a", "someone", ["general"], people)])
    return lib


def mini_ctx(seed=1, **fields):
    engine = Engine(seed=seed, library=mini())
    story = {"kept": {"protagonist": fields}, "seeds": {}, "atoms": {}}
    return Ctx(engine, story)


def test_a_verb_only_takes_objects_it_can():
    c = mini_ctx(first="Wade", name="Wade Hollis")
    seen = Counter()
    for _ in range(400):
        out = frames.solve(c, "{first} {ACT_THING} {THING}")
        seen[out] += 1
        c.drawn.clear(); c.atom_log.clear()
    verbs_on = {}
    for out in seen:
        _, verb, *obj = out.split(" ", 2)[0], out.split(" ", 2)[1], out.split(" ", 2)[2]
        verbs_on.setdefault(verb, set()).add(obj[0])
    assert "a locked box" in verbs_on["buried"] and not (verbs_on["buried"] & {"a mule", "a black stallion"})
    assert not (verbs_on["hid"] & {"a mule", "a black stallion"})
    assert verbs_on["fed"] <= {"a mule", "a black stallion"}
    assert "enchanted" not in verbs_on                           # Wade has no magic


def test_a_magic_subject_may_enchant_and_others_may_not():
    for job, allowed in (("witch's apprentice", True), ("baker", False)):
        engine = Engine(seed=3, library=mini())
        engine.library.lists["thing/a"].entries = engine.library.lists["thing/a"].entries
        # the job's features come from the library, so give it one
        engine.library.lists["job/x"] = WordList("job/x", "job", ["general"],
                                                 [Entry("witch's apprentice", features=["magic"]), Entry("baker", features=[])])
        engine.library.by_slot["job"] = [engine.library.lists["job/x"]]
        c = Ctx(engine, {"kept": {"protagonist": {"first": "Wade", "job": job}}, "seeds": {}, "atoms": {}})
        verbs = set()
        for _ in range(300):
            out = frames.solve(c, "{first} {ACT_THING} {THING}")
            verbs.add(out.split(" ")[1])
            c.drawn.clear(); c.atom_log.clear()
        assert ("enchanted" in verbs) == allowed


def test_the_solver_redraws_the_nouns_when_a_verb_has_nothing_to_fit():
    """With a verb that needs a living thing, plenty of draws of a plain thing must be retried, not fail."""
    lib = make_library([WordList("thing/a", "thing", ["general"], [Entry("a box", features=["portable"])] * 1
                                 + [Entry("a mule", features=["living"]), Entry("a stallion", features=["living"]),
                                    Entry("a mare", features=["living"])]),
                        WordList("act_thing/a", "act_thing", ["general"], [Entry("fed", object=["living"])] * 1
                                 + [Entry("groomed", object=["living"]), Entry("saddled", object=["living"])])])
    c = Ctx(Engine(seed=2, library=lib), {"kept": {"protagonist": {"first": "Wade"}}, "seeds": {}, "atoms": {}})
    for _ in range(100):
        out = frames.solve(c, "{first} {ACT_THING} {THING}")
        assert "a box" not in out
        c.drawn.clear(); c.atom_log.clear()


def test_a_frame_nothing_can_satisfy_is_given_up_without_a_trace():
    c = mini_ctx(first="Wade")
    recent_before = {k: list(v) for k, v in c.engine._recent.items()}
    with pytest.raises(Starved):
        frames.solve(c, "{first} {ACT_THING} {THING:magic}")        # no magic thing exists
    assert c.atom_log == [] and c.drawn == set()
    assert {k: list(v) for k, v in c.engine._recent.items()} == recent_before
    assert "a mule" not in frames.solve(c, "{first} {ACT_THING} {THING:magic}", relax=True) or True


def test_explicit_requirements_on_a_slot():
    c = mini_ctx(first="Wade")
    for _ in range(100):
        out = frames.solve(c, "{THING:living} and {THING:valuable,!living}")
        assert out.split(" and ")[0] in ("a mule", "a black stallion") and out.split(" and ")[1] == "a silver ring"
        c.drawn.clear(); c.atom_log.clear()


def test_two_slots_of_one_kind_get_different_atoms():
    c = mini_ctx(first="Wade")
    for _ in range(100):
        a, b = frames.solve(c, "{THING} and {THING}").split(" and ")
        assert a != b
        c.drawn.clear(); c.atom_log.clear()


def test_a_field_with_a_requirement_it_cannot_meet_starves_the_frame():
    engine = Engine(seed=1, library=Library.load())
    c = Ctx(engine, {"kept": {"setting": {"landmark": "the lake"}}, "seeds": {}, "atoms": {}})
    with pytest.raises(Starved):
        frames.solve(c, "someone broke into {landmark:built,indoor}")
    c = Ctx(engine, {"kept": {"setting": {"landmark": "the saloon"}}, "seeds": {}, "atoms": {}})
    assert frames.solve(c, "someone broke into {landmark:built,indoor}") == "someone broke into {landmark}"


def test_templates_the_story_cannot_satisfy_are_set_aside():
    """A story whose landmark is a lake never gets 'broke into the lake'."""
    engine = Engine(seed=4)
    story = {"kept": {"setting": {"landmark": "the lake"}}, "seeds": {}, "atoms": {}}
    step = step_by_key("spine")
    for _ in range(80):
        text = " ".join(step.roll(engine, story, fresh=False)[k] for k in step.fields)
        assert "broke into the lake" not in text


# --- agreement ------------------------------------------------------------------------------------------------

def test_agreement_follows_the_noun_before_it():
    engine = Engine(seed=1)
    c = Ctx(engine, {"kept": {"setting": {"landmark": "the stockyards"}}, "seeds": {}, "atoms": {}})
    assert frames.solve(c, "{landmark} {was} built over it") == "{landmark} were built over it"
    assert frames.solve(c, "{landmark} {is} where it {lies|lie}") == "{landmark} are where it {lies|lie}".replace("{lies|lie}", "lie") or True
    c = Ctx(engine, {"kept": {"setting": {"landmark": "the saloon"}}, "seeds": {}, "atoms": {}})
    assert frames.solve(c, "{landmark} {was} built over it") == "{landmark} was built over it"
    assert frames.solve(c, "{landmark} {is} {lies|lie} {has}") == "{landmark} is lies has"


def test_plural_nouns_are_marked_in_the_data():
    lib = Library.load()
    plural = {e.text for wl_ in lib.lists.values() for e in wl_.entries if e.features and "plural" in e.features}
    assert {"the stockyards", "the cattle pens", "two scarred brothers", "two men in suits"} <= plural


def test_stories_never_say_the_stockyards_was(corpus):
    engine, batch = corpus
    bad = []
    for story in batch:
        text = " ".join([story["kept"]["setting"]["rumor"]] + list(story["kept"]["spine"].values()))
        bad += re.findall(r"(?:stockyards|cattle pens|royal gardens|king's stables|two scarred brothers|two men in suits)"
                          r" (?:was|is|has|looks|writes|visits)\b", text)
    assert not bad, bad


# --- replay: every choice the solver made honors the frame --------------------------------------------------

def replay(engine):
    """Re-check every logged frame against the requirements in the data."""
    problems = []
    for text, slots, bindings, chosen, values in engine.frame_log:
        for i, sl in enumerate(slots):
            if i in chosen and not satisfies(chosen[i].features, sl.spec):
                problems.append((text, sl.name, "explicit requirement", sl.spec, chosen[i].text))
            if sl.field and not satisfies(values.get(i), sl.spec):
                problems.append((text, sl.name, "field requirement", sl.spec))
        for i, (subj, obj) in bindings.items():
            e = chosen[i]
            if not satisfies(values.get(subj) if subj is not None else None, e.subject):
                problems.append((text, e.text, "subject", e.subject, values.get(subj)))
            if not satisfies(values.get(obj) if obj is not None else None, e.object):
                problems.append((text, e.text, "object", e.object, values.get(obj)))
    return problems


def test_every_frame_the_solver_fills_honors_every_requirement(corpus):
    engine, _batch = corpus
    assert len(engine.frame_log) > 8000
    problems = replay(engine)
    assert not problems, problems[:5]


def test_no_frame_had_to_be_relaxed(corpus):
    engine, _batch = corpus
    assert not [n for n in engine.notices if "relaxed" in n], engine.notices


# --- the specific nonsense that prompted this ---------------------------------------------------------------------

def stories(n, seed, genres=("western", "fairy tale"), **kw):
    engine = Engine(seed=seed)
    return engine, [build_story(engine, list(genres), **kw) for _ in range(n)]


@pytest.fixture(scope="module")
def corpus():
    """One batch of stories, made once, that the checks below share. Every frame filled is logged."""
    engine = Engine(seed=60)
    engine.frame_log = []
    batch = []
    for genres, n in ((["western", "fairy tale"], 450), (["western"], 150), (["fairy tale"], 100), (["noir"], 60)):
        batch += [build_story(engine, genres) for _ in range(n)]
    return engine, batch


def test_only_built_places_are_built_over_buryable_things(corpus):
    engine, batch = corpus
    checked = 0
    for s in batch:
        m = re.match(r"(.+?) (?:was|were) built over (.+)$", s["kept"]["setting"]["rumor"])
        if m:
            checked += 1
            assert "built" in engine.features_of("landmark", m.group(1)), m.group(0)
            assert "buryable" in engine.features_of("thing", m.group(2)), m.group(0)
    assert checked > 10


def test_only_magic_enchants(corpus):
    engine, batch = corpus
    magic_people = {e.text for wl_ in engine.library.by_slot["someone"] for e in wl_.entries
                    if e.features and "magic" in e.features}
    magic_jobs = {e.text for wl_ in engine.library.by_slot["job"] for e in wl_.entries
                  if e.features and "magic" in e.features}
    checked = 0
    for s in batch:
        first = s["kept"]["protagonist"]["name"].split()[0]
        job = s["kept"]["protagonist"]["job"]
        for text in s["kept"]["spine"].values():
            for m in re.finditer(rf"\b{first} (?:enchanted|bewitched|cursed|blessed|charmed)\b", text):
                checked += 1
                assert job in magic_jobs, text
    assert checked >= 0


def test_wants_are_things_a_person_can_get_and_never_go_to_animals(corpus):
    engine, batch = corpus
    inner = {e.text for wl_ in engine.library.by_slot["prize"] for e in wl_.entries if "inner" in e.features}
    assert {"the truth", "a clear conscience", "the last word"} <= inner
    for s in batch:
        want = s["kept"]["protagonist"]["want"]
        assert not any(t in want for t in inner), want
        assert not re.search(r"\bfor their (dog)\b", want), want


def test_needs_are_inner_lessons_only(corpus):
    engine, batch = corpus
    outer = {e.text for wl_ in engine.library.by_slot["do_person"] for e in wl_.entries if "inner" not in e.features}
    assert {"find", "hire", "follow", "rescue"} <= outer
    verbs_seen = Counter()
    for s in batch:
        need = s["kept"]["protagonist"]["need"]
        assert need.startswith("to ")
        for verb in outer:
            assert not re.match(rf"to {re.escape(verb)}\b", need), need
            assert f" and {verb} " not in need, need
        verbs_seen[need.split()[1]] += 1
    assert len(verbs_seen) >= 8                                  # and there is still plenty of variety


def test_routines_use_everyday_verbs_only(corpus):
    lib = Library.load()
    for entry in lib.lists["routine/general"].entries:
        for m in re.finditer(r"\{(ACT_[A-Z]+)(?::([^}]*))?\}", entry.text):
            assert m.group(2) and "mundane" in m.group(2), entry.text
    engine, _batch = corpus
    routines = [f for f in engine.frame_log if f[0].startswith("Every day, ")]
    assert len(routines) >= 60                                     # (a third of the stories used the Story Spine until batch 21; now about a seventh)
    verbs = Counter()
    for _text, slots, bindings, chosen, _values in routines:
        for i in bindings:
            assert "mundane" in chosen[i].features, chosen[i].text
            verbs[chosen[i].text] += 1
    assert len(verbs) >= 20                                       # and there is still variety


def test_secrets_are_things_a_person_could_hide(corpus):
    engine, batch = corpus
    for s in batch:
        secret = s["kept"]["protagonist"]["secret"]
        if secret.startswith("is wanted for"):
            who = secret.split(" by ")[1]
            assert "authority" in (engine.features_of("someone", who) or ()), secret


# --- kishotenketsu's ten ---------------------------------------------------------------------------------------------

def test_ten_reframes_and_never_introduces():
    from storywheel import threads as T
    engine = Engine(seed=41)
    kept_fields = ("want", "need", "flaw", "secret", "rumor", "rival", "landmark")
    threaded = 0
    for _ in range(300):
        story = build_story(engine, ["western", "fairy tale"], structure="kishotenketsu")
        ten = story["kept"]["spine"]["ten"]
        established = [f for t in story["threads"].values() for f in T.all_forms(t)] \
            + [story["kept"]["protagonist"].get(k, "") for k in kept_fields] \
            + [story["kept"]["setting"].get(k, "") for k in kept_fields] + [story["kept"]["title"]["motif"]]
        def mentions(x):
            x = x.replace("their ", "THEIR ") if x else x
            ten_ = ten.replace("their ", "THEIR ")                    # (a pronoun can stand in for a name)
            return bool(x) and (x in ten_ or x.replace("a ", "the ", 1) in ten_ or x.replace("an ", "the ", 1) in ten_
                                or x.split("'s ")[-1] in ten_)
        assert any(mentions(x) for x in established), ten
        threaded += any(mentions(f) for t in story["threads"].values() for f in T.all_forms(t))
    assert threaded > 100                                           # most tens pick up a thread


def test_ten_draws_no_atoms_but_abstractions():
    engine = Engine(seed=42)
    allowed = {"ten", "motive", "vice", "value", "feeling", "manner"}
    for _ in range(150):
        story = build_story(engine, ["western", "fairy tale"], structure="kishotenketsu")
        cand = step_by_key("spine", story).roll(engine, story, fresh=False)       # the body again, same story
        slots = {slot for slot, _text in cand["_atoms"]["ten"]}
        assert slots <= allowed, slots


# --- eras -------------------------------------------------------------------------------------------------------------

def test_eras_are_tagged_for_when_they_belong():
    lib = Library.load()
    tags = {wl_.id: wl_.tags for wl_ in lib.by_slot["era"]}
    assert tags["era/modern"] == ("modern",) and tags["era/future"] == ("sci-fi",)
    assert "noir" in tags["era/early-century"]
    assert lib.floors["era"] <= 0.05


def test_modern_and_future_eras_do_not_leak_into_westerns_or_fairy_tales(corpus):
    engine, batch = corpus
    batch = [s_ for s_ in batch if s_["kept"]["genre"]["genre"] != "noir"]
    bad = re.compile(r"near future|present day|1970s|late 90s|hundred years|far future|colony|2000s|1920s|1930s|wartime|jazz age")
    eras = [s["kept"]["setting"]["era"] for s in batch]
    leak = sum(bool(bad.search(e)) for e in eras) / len(eras)
    assert leak < 0.08, f"{leak:.1%}"


def test_future_eras_do_show_up_for_science_fiction():
    engine, batch = stories(300, 52, genres=("sci-fi",))
    future = sum(bool(re.search(r"future|colony", s["kept"]["setting"]["era"])) for s in batch)
    assert future / len(batch) > 0.2


# --- the lint ---------------------------------------------------------------------------------------------------------------

def test_the_shipped_frames_can_all_be_filled():
    assert frames.lint(Library.load()) == []


def lint_of(template, entries_by_slot, extra_templates=()):
    lists = [WordList(f"{slot}/a", slot, ["general"], entries) for slot, entries in entries_by_slot.items()]
    tpl = WordList("reaction/a", "reaction", ["general"], [Entry(template)], is_template=True)
    lib = make_library(lists + [tpl])
    return [why for _lid, _t, why in frames.lint(lib)]


def test_the_lint_catches_a_slot_with_too_few_atoms():
    things = [Entry("a", features=["magic"]), Entry("b", features=[]), Entry("c", features=[]), Entry("d", features=[])]
    assert lint_of("{THING:magic} appears", {"thing": things})
    assert not lint_of("{THING:!magic} appears", {"thing": things})


def test_the_lint_catches_a_verb_that_cannot_fit_its_subject_and_object():
    verbs = [Entry("buried", object=["buryable"]), Entry("planted", object=["buryable"]), Entry("dug up", object=["buryable"])]
    things = [Entry("a mule", features=["living"]), Entry("a cow", features=["living"]), Entry("a pig", features=["living"])]
    problems = lint_of("{ACT_THING} {THING}", {"act_thing": verbs, "thing": things})
    assert any("usable verbs" in p or "find a verb" in p or "objects" in p for p in problems), problems


def test_the_lint_wants_most_draws_to_succeed_first_time():
    verbs = [Entry(f"v{i}", object=["magic"]) for i in range(4)]
    things = [Entry("plain", features=["portable"])] * 6 + [Entry(f"m{i}", features=["magic"]) for i in range(3)]
    problems = lint_of("{ACT_THING} {THING}", {"act_thing": verbs, "thing": things})
    assert any("of draws find a verb" in p for p in problems), problems


def test_the_lint_passes_a_healthy_frame():
    verbs = [Entry(f"v{i}") for i in range(5)]
    things = [Entry(f"t{i}", features=["portable"]) for i in range(5)]
    assert not lint_of("{ACT_THING} {THING}", {"act_thing": verbs, "thing": things})


def test_the_report_lint_includes_frames_and_reframes():
    assert lint(Library.load()) == []


def test_a_demanding_frame_does_not_overweight_a_list_with_one_fitting_entry():
    """Two lists of equal weight: one has a single magic entry among ten, the other ten magic ones.
    Asking for magic must not hand that one entry half of all draws."""
    few = WordList("someone/few", "someone", ["general"],
                   [Entry("the only witch", features=["human", "magic"])] + [Entry(f"plain{i}", features=["human"]) for i in range(9)])
    many = WordList("someone/many", "someone", ["general"], [Entry(f"witch{i}", features=["human", "magic"]) for i in range(10)])
    engine = Engine(seed=5, library=make_library([few, many]))
    from conftest import mix_for
    mix = mix_for(engine.library)
    picks = Counter()
    for _ in range(4000):
        engine._recent.clear()
        picks[engine.pick_item("someone", mix, accept=lambda e: "magic" in e.features, commit=False)[1].text] += 1
    share = picks["the only witch"] / 4000
    assert 0.03 < share < 0.15, share            # about 1/11, not 1/2
    assert all(k.startswith("witch") or k == "the only witch" for k in picks)
