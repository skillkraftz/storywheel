"""
One story being rolled: the interaction logic, with no screen in it.

The Textual app and the plain prompt loop both drive a Session, so they behave the
same. A Session knows which step you are on, that step's history of candidates and
which one is showing, and does what each key does: roll, keep, reroll a field, edit,
pick from history, go back, skip, save to your universe, rate a line.

Anything the user should hear about ("Updated 2 mentions in later steps") is queued
with note() and collected with take_notes().
"""
import copy
import random
import re

from . import endings, focus, formats, promote, store, structures, universe_atoms, vault
from . import ratings as R
from . import threads as T
from .refs import carry_threads, inherit, reroll_field, substitute, with_field
from .steps import OWNER, public, steps_for
from .text import fix_articles, motif_from

HEADLINE = ("name", "first", "last", "place", "title", "motif", "genre", "structure")     # what a banner names
UNIVERSE_CHANCE = 0.35       # how often "mix" mode pulls from your universe
SOURCE_TAGS = {"edited": " (your edit)", "universe": " (from your universe)", "past": " (from a past story)", "kept": " (kept)"}


class Session:
    def __init__(self, story, engine, ratings=None, rng=None):
        self.story, self.engine, self.ratings = story, engine, ratings
        self.rng = rng or random
        self.i = 0
        self.hist, self.cur = [], 0
        self.done = False
        self.notes = []
        self.engine.set_universes(self.selected_universes())

    # --- what is showing ---------------------------------------------------------------------

    def _repeats_now(self):
        """How many times the repeatable beats occur in the candidate showing (None: as the story has them)."""
        if self.hist and 0 <= self.cur < len(self.hist):
            return self.hist[self.cur].get("_repeats")
        return None

    @property
    def steps(self):
        return steps_for(self.story, self._repeats_now())

    @property
    def step(self):
        return self.steps[self.i]

    @property
    def cand(self):
        return self.hist[self.cur]

    @property
    def fields(self):
        return public(self.cand)

    @property
    def field_names(self):
        return list(self.fields)

    def note(self, message):
        self.notes.append(message)

    def take_notes(self):
        out, self.notes = self.notes + [f"Note: {n}" for n in self.engine.take_notices()], []
        return out

    def marker(self, i):
        """'kept', 'skipped', 'current' or 'pending', for the step list."""
        step = self.steps[i]
        if i == self.i:
            return "current"
        if self.story["kept"].get(step.key):
            return "kept"
        return "skipped" if self.story["step"] > i else "pending"

    # --- moving between steps --------------------------------------------------------------------

    def enter(self, i):
        """Start on step i: its history (with what is kept at the end), or a first roll."""
        self.i, self.done = i, False
        step = self.step
        self.hist = self.story["history"].setdefault(step.key, [])
        kept = self.story["kept"].get(step.key)
        if kept and (not self.hist or public(self.hist[-1]) != public(kept)):
            shown = dict(public(kept), _src="kept")
            if step.key == "spine":
                shown["_repeats"] = self._spine_counts(self.story.get("repeats"))
            self.hist.append(shown)
        if not self.hist:
            self.hist.append(self._roll(fresh=False))          # the first roll may reuse seeds
        self.cur = len(self.hist) - 1

    def jump(self, i):
        self.save()
        self.enter(i)
        before = [st.label for n, st in enumerate(self.steps[:i])
                  if not self.story["kept"].get(st.key) and not self.skipped_on_purpose(st.key)]
        if before:
            self.note(f"Jumped ahead: {', '.join(before)} {'is' if len(before) == 1 else 'are'} not kept yet, "
                      "so this uses stand-ins for what it needs from "
                      f"{'it' if len(before) == 1 else 'them'}.")

    def back(self):
        if self.i == 0:
            self.note("This is the first step.")
            return False
        self.save()
        self.enter(self.i - 1)
        return True

    def _advance(self):
        nxt = self.i + 1
        if nxt >= len(self.steps):
            self.done = True
        elif self._no_protagonist(nxt):
            self.note(f"This story's focus is {focus.get(focus.of_draft(self.story)).label.lower()}: it has no protagonist, so that step was skipped "
                      "(b goes back to it, and F or the focus field changes the focus).")
            self.story["step"] = max(self.story["step"], nxt + 1)
            self.i = nxt
            self._advance()
        else:
            self.enter(nxt)

    def _no_protagonist(self, i):
        """Is step i the Protagonist step of a story whose focus is not a person (and which has nothing kept there)?"""
        return (self.steps[i].key == "protagonist" and not focus.is_person(focus.of_draft(self.story))
                and not self.story["kept"].get("protagonist"))

    def skip(self):
        step, story = self.step, self.story
        story["kept"].pop(step.key, None)
        story.get("inputs", {}).pop(step.key, None)
        if step.threads:
            story["threads"] = {}
        story["atoms"].pop(step.key, None)
        story.setdefault("edited", [])
        if step.key in story["edited"]:
            story["edited"].remove(step.key)
        if step.key not in story.setdefault("skipped", []):
            story["skipped"].append(step.key)                       # (on purpose: R leaves it alone and nothing is flagged for it)
        story["step"] = max(story["step"], self.i + 1)
        self.save()
        self._advance()

    def skipped_on_purpose(self, key):
        """Was this step left out by choice: skipped with x, or the Protagonist step of a story about a place or no one?
        (Nothing kept stands in its place, but nothing is wrong either.)"""
        kept = self.story["kept"]
        if kept.get(key):
            return False
        return key in self.story.get("skipped", ()) or (key == "protagonist" and not focus.is_person(focus.of_draft(self.story)))

    # --- rolling -----------------------------------------------------------------------------------

    def _roll(self, fresh=True):
        step = self.step
        entries = self.universe_entries(step.key)
        mode = self.story.get("universe_mode", "n")
        if entries and (mode == "o" or (mode == "m" and self.rng.random() < UNIVERSE_CHANCE)):
            _u, _e, fields = self.rng.choice(entries)
            return self._complete(step, dict(fields, _src="universe"))
        cand = step.roll(self.engine, self.story, fresh=fresh)
        if step.key == "spine":
            cand["_repeats"] = self._spine_counts(self._repeats_now() or self.story.get("repeats"))
        return cand

    def _complete(self, step, cand):
        """An entry written by hand may leave fields blank: fill them from an ordinary roll."""
        if all(cand.get(name) for name in step.fields):
            return cand
        base = step.roll(self.engine, self.story)
        for name in step.fields:
            if not cand.get(name):
                cand[name] = base[name]
        return cand

    def _fresh(self, make, tries=6):
        """Call make() until it gives something not already in this step's history."""
        seen = [public(c) for c in self.hist]
        for _ in range(tries):
            cand = make()
            if public(cand) not in seen:
                break
        return cand

    def _add(self, cand):
        self.hist.append(cand)
        self.cur = len(self.hist) - 1

    def roll(self):
        self._add(self._fresh(self._roll))

    def reroll_field(self, field):
        step, cand = self.step, self.cand
        if step.key == "genre" and field in ("focus", "ending"):
            self.note(f"The {field} is picked, not rolled: choose it from the list (e, or a click on it).")
            return
        self._add(self._fresh(lambda: reroll_field(step, self.engine, self.story, cand, field)))

    # --- repeatable beats (a Story Spine's "Because of that", the Three-Act's rising action) --------------------------------------------------

    def _structure(self):
        return structures.get(((self.story.get("kept") or {}).get("structure") or {}).get("structure"))

    def _spine_counts(self, repeats=None):
        return self._structure().counts(repeats)

    def beat_group(self, field):
        """(beat, how many times it occurs now) for a field of the story body that can repeat, else None."""
        if self.step.key != "spine" or field is None:
            return None
        b = self._structure().beat(field)
        if b is None or not b.repeat or b.max <= b.min:
            return None
        return b, self._spine_counts(self._repeats_now() or self.story.get("repeats")).get(b.key, b.min)

    def can_add_beat(self, field):
        g = self.beat_group(field)
        return bool(g and g[1] < g[0].max)

    def can_remove_beat(self, field):
        g = self.beat_group(field)
        return bool(g and g[1] > g[0].min)

    def _reshaped(self, counts, mapping):
        """The candidate with the repeatable beats occurring as `counts` says: {new key: the old key its text comes from, or None for a new beat}."""
        cand = self.cand
        new_step = steps_for(self.story, counts)[self.i]
        out = {k: (cand.get(mapping.get(k)) if mapping.get(k) else "") or "" for k in new_step.fields}
        for k, v in cand.items():
            if k.startswith("_") and k not in ("_atoms", "_browse"):
                out[k] = copy.deepcopy(v)
        out["_repeats"] = dict(counts)
        out["_src"] = "edited"
        if "_atoms" in cand:
            old_for = {new: old for new, old in mapping.items() if old}
            out["_atoms"] = {new: copy.deepcopy(cand["_atoms"].get(old, [])) for new, old in old_for.items()}
        if "_made_by" in cand:
            moved = {old: new for new, old in mapping.items() if old}
            out["_made_by"] = {k: moved.get(v, v) for k, v in cand["_made_by"].items() if v not in mapping.values() or v in moved}
        return new_step, out

    def add_beat(self, field):
        """One more of the repeatable beat `field` belongs to, rolled to follow the others (it can use the threads already in play).
        The step's history starts again, because the shape changed."""
        g = self.beat_group(field)
        if g is None:
            self.note("That beat can't be repeated.")
            return False
        b, n = g
        if n >= b.max:
            self.note(f"'{b.label}' can occur at most {b.max} times.")
            return False
        counts = self._spine_counts(self._repeats_now() or self.story.get("repeats"))
        counts[b.key] = n + 1
        mapping = {k: k for k in self.cand if not k.startswith("_")}
        mapping[structures.instance_key(b.key, n + 1)] = None
        step, shaped = self._reshaped(counts, mapping)
        new_key = structures.instance_key(b.key, n + 1)
        shaped["_threads"] = copy.deepcopy(self.cand.get("_threads", {}))
        done = reroll_field(step, self.engine, self.story, shaped, new_key)
        done["_repeats"] = dict(counts)
        self.hist[:] = [done]
        self.cur = 0
        self.note(f"Added a '{b.label}' beat ({n + 1} now). This step's history starts again.")
        return new_key

    def remove_beat(self, field):
        """Take out the beat `field` (one occurrence of a repeatable beat); later ones move up. Threads follow the text: one that no beat
        mentions any more retires, and a thread whose first mention was removed is introduced by the next beat that has it."""
        g = self.beat_group(field)
        if g is None:
            self.note("That beat can't be removed.")
            return False
        b, n = g
        if n <= b.min:
            self.note(f"'{b.label}' needs at least {b.min}.")
            return False
        at = structures.instance_number(field) if structures.base_key(field) == b.key else n
        counts = self._spine_counts(self._repeats_now() or self.story.get("repeats"))
        counts[b.key] = n - 1
        mapping = {k: k for k in self.cand if not k.startswith("_") and not (structures.base_key(k) == b.key and structures.instance_number(k) >= at)}
        for i in range(at, n):                                   # occurrence i+1 moves up into i
            mapping[structures.instance_key(b.key, i)] = structures.instance_key(b.key, i + 1)
        step, shaped = self._reshaped(counts, mapping)
        T.settle(shaped)
        self.hist[:] = [shaped]
        self.cur = 0
        self.note(f"Removed a '{b.label}' beat ({n - 1} now). This step's history starts again.")
        return True

    def _follow_title(self, cand, old_title):
        """A hand-written title says what the story is about: the motif follows it (unless you also wrote the motif)."""
        if self.step.key != "title" or "motif" not in cand or cand.get("title", "") == old_title:
            return
        motif = motif_from(cand["title"], lambda: cand["motif"])
        if motif != cand["motif"]:
            cand["motif"] = motif
            self.note(f"The motif now follows your title: '{motif}'. Edit the motif field if that isn't what it is about.")

    # --- the structure step: a format and a structure that fits it (picked from lists; a typed one must be one of them) -------------

    def structure_fields(self, fields):
        """The structure step's fields made exact ("short film" -> "Screenplay: short film", "kishotenketsu" -> "Kishōtenketsu"), or None
        with a note saying why not: an unknown format or structure, or a structure that doesn't fit the format."""
        out = dict(fields)
        key = formats.find(out.get("format")) if out.get("format") else formats.of_draft(self.story)
        if key is None:
            self.note(f"'{out.get('format')}' is not a format. Choose one: " + ", ".join(f.label for f in formats.FORMATS) + ".")
            return None
        shape = structures.find(out.get("structure", ""))
        fit = [s.label for s in formats.structures_for(key)]
        if shape is None or shape.label not in fit:
            what = f"'{out.get('structure')}' is not one of the structures" if shape is None else f"{shape.label} doesn't fit"
            self.note(f"{what} for a {formats.get(key).label.lower()}. Choose one of: {', '.join(fit)}.")
            return None
        out.update(format=formats.get(key).label, structure=shape.label)
        return out

    def format_label(self):
        """The draft's format as the pickers name it (Short story, Flash fiction...), for the card's header."""
        return formats.get(formats.of_draft(self.story)).label

    def needs_format(self):
        """A brand-new draft that has not been asked its format yet (the Wheel asks first, before anything is rolled or kept)."""
        return "format" not in self.story and not self.story["kept"] and not self.story.get("step")

    def set_focus(self, key):
        """Choose what the story is about (focus.py). A place or no one means no protagonist: the step is skipped and the fallback subject
        stands in; what was kept on the Protagonist step is set aside, not deleted."""
        key = focus.find(key)
        if key is None:
            return False
        self.story["focus"] = key
        label = focus.get(key).label
        if self.step.key == "genre":
            self._add(with_field(self.cand, "focus", label, src="edited"))
        kept = self.story["kept"].get("genre")
        if kept is not None:
            kept["focus"] = label
        pro = self.story["kept"].get("protagonist")
        if not focus.is_person(key):
            self.note(f"Focus: {label.lower()}. There is no protagonist: the Protagonist step is skipped" +
                      (", and what you kept there is set aside (it comes back if the focus does)." if pro else "."))
        elif key in ("two", "ensemble") and pro and not (pro.get("partner") or pro.get("company")):
            self.note(f"Focus: {label.lower()}. Roll the Protagonist step again to make the {'partner' if key == 'two' else 'company'}.")
        return True

    def set_ending(self, key):
        """Choose how the story should end (endings.py). It only steers climax and resolution frames that carry an ending, so a body already
        kept keeps its beats: the note says which to reroll."""
        key = endings.find(key)
        if key is None:
            return False
        self.story["ending"] = key
        label = endings.get(key).label
        if self.step.key == "genre":
            self._add(with_field(self.cand, "ending", label, src="edited"))
        kept = self.story["kept"].get("genre")
        if kept is not None:
            kept["ending"] = label
        if self.story["kept"].get("spine") and key != endings.DEFAULT:
            self.note(f"Ending: {label.lower()}. The story body you kept was written before this; reroll its climax and resolution beats (f) to match.")
        return True

    def set_format(self, key):
        """Choose the draft's format. On the structure step the structure is rolled again among those that fit when the one showing doesn't;
        on any other step the draft's kept structure is swapped for the format's default when it no longer fits (said plainly)."""
        key = formats.find(key)
        if key is None:
            return False
        self.story["format"] = key
        label = formats.get(key).label
        if self.step.key == "structure":
            cand = with_field(self.cand, "format", label, src="edited")
            self._add(cand)
            if not formats.fits(structures.find(cand.get("structure", "")), key):
                self.reroll_field("structure")
                self.note(f"A {label.lower()}: the structure was rolled again among the ones that fit it.")
            return True
        kept = self.story["kept"].get("structure")
        if kept:
            shape = structures.find(kept.get("structure", ""))
            kept["format"] = label
            if not formats.fits(shape, key):
                fit = formats.default_structure(key)
                if fit is not None:
                    kept["structure"] = fit.label
                    self._drop_body()
                    self.note(f"A {label.lower()}: {shape.label if shape else 'the structure'} doesn't fit it, so the structure is now {fit.label} "
                              "and the story body will be rolled again when you get to it.")
                    if self.step.key == "spine":
                        self.enter(self.i)                  # (the body on show was the old structure's: roll it again)
        return True

    def _drop_body(self):
        """Forget the kept story body (its beats belong to the old structure)."""
        story = self.story
        story.pop("repeats", None)
        story["kept"].pop("spine", None)
        story["history"].pop("spine", None)
        story["atoms"].pop("spine", None)
        story["threads"] = {}

    def edit_field(self, field, text):
        text = text.strip()
        if text and self.step.key == "genre" and field == "ending":
            key = endings.find(text)
            if key is None:
                self.note(f"'{text}' is not an ending. Choose one: " + ", ".join(e.label for e in endings.ENDINGS) + ".")
                return False
            return self.set_ending(key)
        if text and self.step.key == "genre" and field == "focus":
            key = focus.find(text)
            if key is None:
                self.note(f"'{text}' is not a focus. Choose one: " + ", ".join(f.label for f in focus.FOCUSES) + ".")
                return False
            return self.set_focus(key)
        if text and self.step.key == "structure":
            fixed = self.structure_fields(dict(self.fields, **{field: text}))
            if fixed is None:
                return False
            if field == "format":
                return self.set_format(fixed["format"])
            text = fixed[field]
        if text and text != self.cand.get(field):
            old_title = self.cand.get("title", "")
            new = with_field(self.cand, field, text, src="edited")
            if field == "title":
                self._follow_title(new, old_title)
            self._add(new)
            return True
        return False

    def replace_fields(self, new):
        """The whole item rewritten (in $EDITOR, or by hand): it joins the history."""
        if self.step.key == "genre" and new.get("ending") is not None:
            key = endings.find(new["ending"])
            if key is None:
                self.note(f"'{new['ending']}' is not an ending. Choose one: " + ", ".join(e.label for e in endings.ENDINGS) + ".")
                return False
            new = dict(new, ending=endings.get(key).label)
            self.story["ending"] = key
        if self.step.key == "genre" and new.get("focus") is not None:
            key = focus.find(new["focus"])
            if key is None:
                self.note(f"'{new['focus']}' is not a focus. Choose one: " + ", ".join(f.label for f in focus.FOCUSES) + ".")
                return False
            new = dict(new, focus=focus.get(key).label)
            self.story["focus"] = key
        if self.step.key == "structure":
            new = self.structure_fields(new)
            if new is None:
                return False
            self.story["format"] = formats.find(new["format"])
        if new != self.fields:
            cand = inherit(dict(new, _src="edited"), self.cand)
            if new.get("motif") == self.fields.get("motif"):            # (you didn't also change the motif by hand)
                self._follow_title(cand, self.fields.get("title", ""))
            self._add(cand)
            return True
        return False

    def pick(self, n):
        """Show candidate n (0-based) again."""
        if 0 <= n < len(self.hist):
            self.cur = n
            return True
        return False

    def field_values(self, field):
        """Every distinct value one field has had, oldest first."""
        values = []
        for c in self.hist:
            if c.get(field) and c[field] not in values:
                values.append(c[field])
        return values

    def pick_value(self, field, value):
        """Bring an old value of one field back, without losing the rest."""
        if value and value != self.cand.get(field):
            self._add(with_field(self.cand, field, value))
            return True
        return False

    def step_value(self, field, direction):
        """Step one field through the values it has had: direction -1 goes to an older one, +1 to a
        newer. Browsing replaces its own last stop instead of piling up a candidate per step."""
        values = self.field_values(field)
        current = self.cand.get(field)
        if current not in values:
            return False
        target = values.index(current) + (1 if direction > 0 else -1)
        if not 0 <= target < len(values):
            return False
        new = with_field(self.cand, field, values[target])
        new["_browse"] = field
        if self.cur == len(self.hist) - 1 and self.cand.get("_browse") == field:
            self.hist[self.cur] = new                      # still browsing this field: replace, don't add
        else:
            self._add(new)
        return True

    def change_summary(self, n, width=70):
        """What candidate n changed from the one before it (all of it, for the first)."""
        c = self.hist[n]
        names = list(public(c))
        if self.step.single or n == 0:
            return self.summary(c, width)
        prev = public(self.hist[n - 1])
        changed = [k for k in names if prev.get(k) != c[k]]
        if not changed:
            return "(same as previous)"
        if len(changed) > 2:
            return self.summary(c, width)
        return "; ".join(f"{k.replace('_', ' ')}: {_short(c[k], max(10, width // len(changed)))}" for k in changed)

    def summary(self, cand, width=70):
        vals = list(public(cand).values())
        text = vals[0] if self.step.single else " · ".join(vals[:3])
        return _short(text, width)

    def source_tag(self, n):
        return SOURCE_TAGS.get(self.hist[n].get("_src"), "")

    # --- keeping ----------------------------------------------------------------------------------

    def keep(self, advance=True):
        """Keep the showing candidate and move on. (Updates later steps that mention what changed.) `advance=False` stays on the step
        (R and the other whole-draft rolls move about themselves)."""
        story, step, i, cand = self.story, self.step, self.i, self.cand
        old = story["kept"].get(step.key)
        new = public(cand)
        if step.key == "genre":                                           # (the focus is the draft's; an older candidate may lack it)
            story["focus"] = focus.find(new.get("focus")) or focus.of_draft(story)
            new["focus"] = focus.get(story["focus"]).label
            story["ending"] = endings.find(new.get("ending")) or endings.of_draft(story)
            new["ending"] = endings.get(story["ending"]).label
        if step.key == "structure":
            fixed = self.structure_fields(new)
            if fixed is None:
                return False                                               # (said why: nothing is kept)
            new = fixed
            story["format"] = formats.find(new["format"])
        for k, v in cand.get("_made", {}).items():
            story["seeds"].setdefault(k, v)
        story["kept"][step.key] = new
        story.setdefault("edited", [])
        story.setdefault("skipped", [])
        if cand.get("_src") == "edited":                                   # (a hand edit: A2 and S ask before they replace it)
            if step.key not in story["edited"]:
                story["edited"].append(step.key)
        elif cand.get("_src") != "kept" and step.key in story["edited"]:
            story["edited"].remove(step.key)
        if step.key in story["skipped"]:
            story["skipped"].remove(step.key)
        story.get("acks", {}).pop(step.key, None)                          # (a fresh keep: the flags dismissed for the old one are over)
        if step.key == "structure" and old and structures.get(old["structure"]) is not structures.get(new["structure"]):
            self._drop_body()                       # (the old body doesn't fit the new shape)
            self.note("New structure: the story body will be rolled again when you get to it.")
        if old and old != new:
            n = substitute(story, i, old, new)
            if step.threads:
                n += carry_threads(story, i, story.get("threads"), cand.get("_threads"))
            if n:
                self.note(f"Updated {n} mention(s) in later steps.")
        if step.threads:
            story["threads"] = cand.get("_threads", {})
        if step.key == "spine":
            story["repeats"] = {k: n for k, n in (cand.get("_repeats") or {}).items() if n > 1}
        story["atoms"][step.key] = [a for lst in cand.get("_atoms", {}).values() for a in lst]
        story.setdefault("inputs", {})[step.key] = copy.deepcopy(cand.get("_inputs", {}))
        self._swap_standins(i, new)
        story["step"] = max(story["step"], i + 1)
        self.save()
        if advance:
            self._advance()

    # --- what a candidate was built from -----------------------------------------------------------------
    #
    # Every candidate records the earlier fields it read (its _inputs), each marked kept or stand-in
    # (a stand-in is a value the roll had to invent because that step wasn't kept). Comparing them to
    # what is kept now says whether a candidate is stale, and what to swap to bring it up to date.

    def current_value(self, key):
        """The kept value of an earlier field now (first and last come from the kept name), or None."""
        owner = OWNER.get(key)
        kept = self.story["kept"].get(owner) or {}
        if key in ("first", "last"):
            name = kept.get("name")
            return (name.split()[0 if key == "first" else -1] if name else None)
        return kept.get(key)

    def input_changes(self, cand=None):
        """[(key, step key, the value it was built with, the value kept now)] for each input that is
        out of date. (An input built from a stand-in is out of date once its step is kept differently.)"""
        out = []
        for key, inp in (cand if cand is not None else self.cand).get("_inputs", {}).items():
            now = self.current_value(key)
            if now is not None and now != inp["value"] and (cand if cand is not None else self.cand).get("_ack", {}).get(key) != now:
                out.append((key, inp["step"], inp["value"], now))
        return out

    def ignore_stale(self):
        """Dismiss the banner for this candidate: it stays as it is, and is not flagged again for
        these values (a different kept value brings the banner back)."""
        changes = self.input_changes()
        if changes:
            self.cand["_ack"] = dict(self.cand.get("_ack", {}), **{k: now for k, _s, _o, now in changes})
            self.note("Ignoring the change. This candidate stays as it is.")
        flagged = self.ignore_step()
        if flagged:
            self.note(f"Ignoring what is flagged on the kept {self.step.label.lower()}. It stays as it is, and is flagged again only if that changes.")
        return bool(changes or flagged)

    def standins(self, cand=None):
        """{step key: [stand-in values]} for steps this candidate used stand-ins for that are still not kept."""
        out = {}
        for key, inp in (cand if cand is not None else self.cand).get("_inputs", {}).items():
            if inp["standin"] and self.current_value(key) is None and not self.skipped_on_purpose(inp["step"]):
                out.setdefault(inp["step"], []).append(inp["value"])
        return out

    def is_stale(self, n=None):
        return bool(self.input_changes(self.hist[self.cur if n is None else n]))

    def stale_banner(self, cand=None):
        """'Built for Mark; your protagonist is now Stacie Anderson', or '' if nothing is out of date."""
        changes = self.input_changes(cand)
        if not changes:
            return ""
        parts = []
        for owner in dict.fromkeys(step for _k, step, _o, _n in changes):
            mine = [c for c in changes if c[1] == owner]
            main = [c for c in mine if c[0] in HEADLINE] or mine[:1]       # name, not every detail that changes too
            old = " ".join(dict.fromkeys(c[2] for c in main))
            new = self.story["kept"][owner].get("name") if owner == "protagonist" else \
                " / ".join(dict.fromkeys(c[3] for c in main))
            label = next((st.label for st in self.steps if st.key == owner), owner).lower()
            parts.append(f"Built for {old}; your {label} is now {new}")
        return "; ".join(parts)

    def standin_line(self, cand=None):
        """A plain statement when the candidate used stand-ins, else ''."""
        used = self.standins(cand)
        if not used:
            return ""
        what = "; ".join(f"{next((st.label for st in self.steps if st.key == k), k).lower()} "
                         f"({', '.join(dict.fromkeys(v))})" for k, v in used.items())
        return f"Uses stand-ins for steps you haven't kept: {what}. They are placeholders, not your choices."

    def update_inputs(self):
        """Swap the old values for the kept ones in a copy of the showing candidate (a new candidate)."""
        changes = self.input_changes()
        if not changes:
            self.note("Nothing to update: this was built from what you have kept.")
            return False
        new = self.update_candidate(self.cand, changes)
        self._add(new)
        self.note(f"Updated this candidate to your kept {', '.join(sorted({self.universe_label(c[1]).lower() for c in changes}))}.")
        return True

    def update_candidate(self, cand, changes):
        pairs = sorted({(old, now) for _k, _s, old, now in changes if old and now and len(old) >= 2},
                       key=lambda p: -len(p[0]))
        new = copy.deepcopy(cand)
        for key in [k for k in new if not k.startswith("_") and isinstance(new[k], str)]:
            for old, now in pairs:
                new[key] = re.sub(r"\b" + re.escape(old) + r"\b", lambda _m, now=now: now, new[key])
            new[key] = fix_articles(new[key])
        for t in (new.get("_threads") or {}).values():
            for old, now in pairs:
                t["text"] = re.sub(r"\b" + re.escape(old) + r"\b", lambda _m, now=now: now, t["text"])
        new["_inputs"] = {k: (dict(v, value=self.current_value(k), standin=False)
                              if self.current_value(k) is not None else v)
                          for k, v in new.get("_inputs", {}).items()}
        new["_made"] = {k: v for k, v in new.get("_made", {}).items() if self.current_value(k) is None}
        return new

    def _swap_standins(self, i, new):
        """Step i was just kept. Later steps that were kept with a stand-in for it (or for what it
        replaced) get the kept value swapped in, so the story doesn't carry a placeholder name."""
        story, count = self.story, 0
        for st in self.steps[i + 1:]:
            kept = story["kept"].get(st.key)
            recorded = story.get("inputs", {}).get(st.key)
            if not kept or not recorded:
                continue
            changes = [(k, v["step"], v["value"], self.current_value(k)) for k, v in recorded.items()
                       if v["step"] == self.steps[i].key and self.current_value(k) not in (None, v["value"])]
            if not changes:
                continue
            fixed = self.update_candidate(dict(kept, _inputs=recorded), changes)
            count += sum(1 for k, v in kept.items() if fixed[k] != v)
            story["kept"][st.key] = public(fixed)
            story["inputs"][st.key] = fixed["_inputs"]
        if count:
            self.note(f"Swapped the kept {self.steps[i].label.lower()} into {count} line(s) built on a stand-in.")

    NO_VALUE = "(none)"          # what an ignored flag remembers when the thing it refers to isn't kept

    def problems(self, i):
        """[{kind, key, step (the owner), value (what it was built with), now, message}] for each flag on KEPT step i, minus the ones
        dismissed with i. kind: 'standin' (built on a stand-in for a step that is still not kept), 'broken' (refers to something no
        longer kept) or 'changed' (built for a value that has since changed). A stand-in for a step skipped on purpose is no flag."""
        step = self.steps[i]
        if not self.story["kept"].get(step.key):
            return []
        acks = self.story.get("acks", {}).get(step.key, {})
        out = []
        for key, inp in self.story.get("inputs", {}).get(step.key, {}).items():
            now = self.current_value(key)
            owner = next((st.label for st in self.steps if st.key == inp["step"]), inp["step"]).lower()
            if now is None and self.skipped_on_purpose(inp["step"]) and (inp["standin"] or not focus.is_person(focus.of_draft(self.story))):
                continue                                    # (a stand-in for a step left out on purpose; "everyone in" a place has no protagonist)
            if now is None and inp["standin"]:
                kind, message = "standin", (f"{step.label} was built on a stand-in {owner} ({inp['value']}). "
                                            f"Keep your {owner} (k) to replace it, or S to roll it now; i dismisses this.")
            elif now is None:
                kind, message = "broken", (f"{step.label} refers to {inp['value']}, but there is no longer a kept {owner}. "
                                           f"Keep the {owner} again, or S to reroll {step.label.lower()}; i dismisses this.")
            elif now != inp["value"]:
                kind, message = "changed", (f"{step.label} was built for {inp['value']}; your {owner} is now {now}. "
                                            "S swaps the new one in; i dismisses this.")
            else:
                continue
            if acks.get(key) == (self.NO_VALUE if now is None else now):
                continue
            out.append({"kind": kind, "key": key, "step": inp["step"], "value": inp["value"], "now": now, "message": message})
        return out

    def step_problems(self, i):
        """[(severity, message)] for a KEPT step: 'changed' (yellow) for a stand-in or a changed value, 'broken' (red) for something
        that is no longer kept."""
        return [("broken" if p["kind"] == "broken" else "changed", p["message"]) for p in self.problems(i)]

    def flag(self, i):
        """None, 'changed' (yellow) or 'broken' (red), for the step list."""
        problems = self.step_problems(i)
        if any(sev == "broken" for sev, _m in problems):
            return "broken"
        return "changed" if problems else None

    def issues(self):
        """Every problem message across the kept steps, broken ones first."""
        found = [(sev, m) for i in range(len(self.steps)) for sev, m in self.step_problems(i)]
        found.sort(key=lambda p: p[0] != "broken")
        return found

    def step_banner(self):
        """The flags on the kept step being shown (the card shows the kept copy), for the banner; '' when there are none."""
        if not self.story["kept"].get(self.step.key) or self.cand.get("_src") != "kept":
            return ""
        return " ".join(m for _sev, m in self.step_problems(self.i))

    def ignore_step(self, i=None):
        """Dismiss the flags on kept step i (this one by default): they stay dismissed for these values, and come back if the thing
        they refer to changes again."""
        i = self.i if i is None else i
        found = self.problems(i)
        if not found:
            return False
        acks = self.story.setdefault("acks", {}).setdefault(self.steps[i].key, {})
        for p in found:
            acks[p["key"]] = self.NO_VALUE if p["now"] is None else p["now"]
        self.save()
        return True

    # --- whole-draft rolls: R, L and S ---------------------------------------------------------------------------------------

    def _roll_step(self, i):
        """Roll step i afresh (a new entry in its history, the first roll when it has none) and keep it. False when it can't be kept."""
        had = bool(self.story["history"].get(self.steps[i].key))
        self.enter(i)
        if had:
            self.roll()
        return self.keep(advance=False) is not False

    def _roll_missing(self, start=0):
        """Roll and keep, in order from `start`, every step not kept and not skipped on purpose. Returns the labels rolled."""
        rolled, i = [], start
        while i < len(self.steps):
            step = self.steps[i]
            if not self.story["kept"].get(step.key) and not self.skipped_on_purpose(step.key):
                label = step.label
                if not self._roll_step(i):
                    break
                rolled.append(label)
            i += 1
        return rolled

    def roll_all(self):
        """R: roll and keep every step that isn't kept yet, in order, so each builds on the ones before it. Kept steps stay, steps
        skipped on purpose stay skipped. Returns how many steps were rolled."""
        here = self.i
        rolled = self._roll_missing()
        self.done = False
        self.enter(len(self.steps) - 1 if rolled else here)
        self.note(f"Rolled and kept {len(rolled)} step(s): {', '.join(rolled)}. Each is in its step's history (h, b)." if rolled else
                  "Every step is already kept or skipped. Nothing to roll.")
        return len(rolled)

    def edited_after(self, i=None):
        """Labels of the kept steps after step i (this one by default) that you wrote or edited by hand."""
        i = self.i if i is None else i
        edited = self.story.get("edited", ())
        return [st.label for st in self.steps[i + 1:] if st.key in edited and self.story["kept"].get(st.key)]

    def reroll_from_here(self):
        """L: reroll and keep every step after this kept one; this step stays. (The screen asks first when edited_after() isn't empty.)
        Returns how many kept steps were replaced, or None when this step isn't kept."""
        story, i = self.story, self.i
        if not story["kept"].get(self.step.key):
            self.note("Keep this step first: L rerolls the steps after a kept one.")
            return None
        replaced = [st.label for st in self.steps[i + 1:] if story["kept"].get(st.key)]
        for st in self.steps[i + 1:]:
            self._unkeep(st)
        self._roll_missing(i + 1)
        self.done = False
        self.enter(i)
        self.note(f"Rerolled the steps after {self.step.label.lower()}: replaced {len(replaced)} kept step(s)"
                  + (f" ({', '.join(replaced)})" if replaced else "") + ". Each old version is in its history (h).")
        return len(replaced)

    def _unkeep(self, step):
        """Forget what step `step` kept (its history stays), without marking it skipped."""
        story = self.story
        if not story["kept"].pop(step.key, None):
            return
        story.get("inputs", {}).pop(step.key, None)
        story["atoms"].pop(step.key, None)
        if step.key in story.get("edited", ()):
            story["edited"].remove(step.key)
        if step.threads:
            story["threads"] = {}
        if step.key == "spine":
            story.pop("repeats", None)

    def fix_changed(self):
        """S: deal with every flagged step at once. A changed value (a new name, title, motif...) is swapped into the step; a step that
        can't be fixed by a swap (the genre or structure changed, or nothing usable to swap) is rerolled; a step built on something
        that was never kept gets that step rolled and kept first. A step you edited by hand is left alone (and said so).
        Returns True when anything was done."""
        story, here = self.story, self.i
        swapped, rerolled, rolled, left = [], [], [], []
        # 1. the steps these flags lean on, if they are still not kept (and not skipped on purpose)
        needed = {p["step"] for i in range(len(self.steps)) for p in self.problems(i) if p["kind"] in ("standin", "broken")}
        for n, st in enumerate(self.steps):
            if st.key in needed and not story["kept"].get(st.key) and not self.skipped_on_purpose(st.key):
                if self._roll_step(n):
                    rolled.append(st.label)
        # 2. each flagged step, in order (a reroll changes what the later ones lean on, so they are looked at after it)
        for n in range(len(self.steps)):
            step = self.steps[n]
            found = self.problems(n)
            if not found:
                continue
            by_hand = step.key in story.get("edited", ())
            changes = [(p["key"], p["step"], p["value"], p["now"]) for p in found if p["kind"] == "changed"]
            swappable = [c for c in changes if c[1] not in ("genre", "structure") and c[2] and c[3] and len(c[2]) >= 2]
            if swappable:
                recorded = story["inputs"][step.key]
                fixed = self.update_candidate(dict(story["kept"][step.key], _inputs=recorded), swappable)
                story["kept"][step.key] = public(fixed)
                story["inputs"][step.key] = {k: (fixed["_inputs"][k] if any(c[0] == k for c in swappable) else v)    # (only what was swapped is up to date)
                                             for k, v in recorded.items()}
                swapped.append(step.label)
            if any(p["kind"] != "standin" for p in self.problems(n)):            # (a stand-in whose step couldn't be rolled stays: a reroll wouldn't help)
                if by_hand:
                    left.append(f"{step.label} (you edited it; i keeps it as it is)")
                elif self._roll_step(n):
                    rerolled.append(step.label)
        self.save()
        self.done = False
        self.enter(here)
        parts = []
        if rolled:
            parts.append("rolled and kept " + ", ".join(rolled))
        if swapped:
            parts.append("swapped the new values into " + ", ".join(swapped))
        if rerolled:
            parts.append("rerolled " + ", ".join(rerolled))
        if left:
            parts.append("left " + ", ".join(left))
        self.note("Fixed what changed: " + "; ".join(parts) + "." if parts else "Nothing to fix: no step is flagged.")
        return bool(rolled or swapped or rerolled)

    def stale_tag(self, n):
        return " (stale)" if self.is_stale(n) else ""

    def save(self):
        """Write the story, its markdown, and the memory of recent picks."""
        path = store.save(self.story)
        self.engine.save_memory()
        return path

    # --- universes the generator may draw from ---------------------------------------------------------

    def available_universes(self):
        return vault.list_universes()

    def selected_universes(self):
        out = []
        for slug in self.story.get("universes", []):
            u = vault.get_universe(slug)
            if u:
                out.append(u)
        return out

    def _sync_engine(self):
        self.engine.set_universes(self.selected_universes())

    def set_universes(self, slugs):
        self.story["universes"] = [s for s in slugs if vault.get_universe(s)]
        self._sync_engine()

    @property
    def home(self):
        """The universe this draft belongs to (its slug), if it was chosen and still exists: promoting puts the story into that universe."""
        slug = self.story.get("home")
        return slug if slug and vault.get_universe(slug) else None

    def set_home(self, slug):
        """Choose the universe this draft belongs to (None: not decided; promotion asks). A home universe is also ticked, so the generator draws from it."""
        if slug and not vault.get_universe(slug):
            return False
        self.story["home"] = slug or None
        if slug and slug not in self.story.get("universes", []):
            self.set_universes(list(self.story.get("universes", [])) + [slug])
        return True

    def toggle_universe(self, slug):
        """Tick or untick a universe for this draft. Returns True if it is selected now."""
        chosen = list(self.story.get("universes", []))
        if slug in chosen:
            chosen.remove(slug)
        elif vault.get_universe(slug):
            chosen.append(slug)
        self.set_universes(chosen)
        return slug in self.story["universes"]

    def universe_entries(self, step_key):
        """[(universe, entity, fields)] that selected universes can offer for a whole step."""
        out = []
        for u in self.selected_universes():
            out += [(u, e, f) for e, f in universe_atoms.step_candidates(u, step_key)]
        return out

    @property
    def universe_mode(self):
        return self.story.get("universe_mode", "n")

    def cycle_universe_mode(self):
        """no -> mix it in -> only from it -> no, for this story. Returns the new mode."""
        order = ["n", "m", "o"]
        self.story["universe_mode"] = order[(order.index(self.universe_mode) + 1) % 3]
        return self.story["universe_mode"]

    def use_universe_entry(self, step_key, fields, src="universe"):
        """Offer a universe entity as a candidate for its step in this story, jumping there if need be.
        Nothing is kept: the story's kept steps are untouched until you press k."""
        index = next((n for n, st in enumerate(self.steps) if st.key == step_key), None)
        if index is None:
            self.note(f"This story has no '{step_key}' step.")
            return False
        if index != self.i:
            self.jump(index)
        cand = dict(public(fields), _src=src)
        for name in self.field_names:                      # an entity may leave fields blank
            if not cand.get(name):
                cand[name] = self.cand.get(name, "")
        self._add(cand)
        self.note("Added from your universe as a new candidate. Press k to keep it." if src == "universe"
                  else "Added from a past story as a new candidate. Press k to keep it.")
        return True

    def universe_label(self, step_key):
        step = next((st for st in self.steps if st.key == step_key), None)
        return step.label if step else step_key.replace("_", " ").title()

    def save_to_universe(self, universe):
        """Save the showing candidate into a universe (see universe_atoms.save_piece)."""
        e, message = universe_atoms.save_piece(universe, self.step.key, self.step.label, self.fields)
        self.note(message)
        return e

    # --- ratings ------------------------------------------------------------------------------------------

    def line_of(self, field=None):
        """(step, field, text) for what a + or - would apply to: a field, or a single-field item."""
        if field is None:
            if not self.step.single:
                return None
            field = self.field_names[0]
        return self.step.key, field, self.cand.get(field, "")

    def rating(self, field=None):
        if self.ratings is None:
            return 0
        line = self.line_of(field)
        return 0 if line is None else self.ratings.rating_of(self.story["id"], *line)

    def rate(self, value, field=None):
        """+1 or -1 on a field (or the whole item when the step has one field). Returns the rating now."""
        if self.ratings is None:
            self.note("Ratings are off for this session.")
            return 0
        line = self.line_of(field)
        if line is None:
            self.note("Select a field first, then press + or -.")
            return 0
        step, field, text = line
        frame, atoms = R.provenance(self.engine.library, self.cand.get("_atoms", {}).get(field))
        now = self.ratings.rate(self.story["id"], step, field, text, value, frame, atoms,
                                title=store.title_of(self.story))
        self.note({1: "Liked.", -1: "Marked down: that line's frame and atoms will come up a little less.",
                   0: "Rating cleared."}[now])
        return now

    # --- the mix (this story only) ----------------------------------------------------------------------------

    def mix(self):
        from .mix import Mix
        return Mix.for_story(self.story, self.engine.library)


def _short(text, n):
    return text if len(text) <= n else text[:n - 3] + "..."
