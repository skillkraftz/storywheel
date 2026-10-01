"""
One story being rolled: the interaction logic, with no screen in it.

The Textual app and the plain prompt loop both drive a Session, so they behave the
same. A Session knows which step you are on, that step's history of candidates and
which one is showing, and does what each key does: roll, keep, reroll a field, edit,
pick from history, go back, skip, save to your universe, rate a line.

Anything the user should hear about ("Updated 2 mentions in later steps") is queued
with note() and collected with take_notes().
"""
import random

from . import store, structures
from . import ratings as R
from .refs import carry_threads, inherit, reroll_field, substitute, with_field
from .steps import public, steps_for

UNIVERSE_CHANCE = 0.35       # how often "mix" mode pulls from your universe
SOURCE_TAGS = {"edited": " (your edit)", "universe": " (from your universe)", "kept": " (kept)"}


class Session:
    def __init__(self, story, engine, ratings=None, rng=None):
        self.story, self.engine, self.ratings = story, engine, ratings
        self.rng = rng or random
        self.i = 0
        self.hist, self.cur = [], 0
        self.done = False
        self.notes = []

    # --- what is showing ---------------------------------------------------------------------

    @property
    def steps(self):
        return steps_for(self.story)

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
            self.hist.append(dict(public(kept), _src="kept"))
        if not self.hist:
            self.hist.append(self._roll(fresh=False))          # the first roll may reuse seeds
        self.cur = len(self.hist) - 1

    def jump(self, i):
        self.save()
        self.enter(i)

    def back(self):
        if self.i == 0:
            self.note("This is the first step.")
            return False
        self.save()
        self.enter(self.i - 1)
        return True

    def _advance(self):
        if self.i + 1 >= len(self.steps):
            self.done = True
        else:
            self.enter(self.i + 1)

    def skip(self):
        step, story = self.step, self.story
        story["kept"].pop(step.key, None)
        if step.threads:
            story["threads"] = {}
        story["atoms"].pop(step.key, None)
        story["step"] = max(story["step"], self.i + 1)
        self.save()
        self._advance()

    # --- rolling -----------------------------------------------------------------------------------

    def _roll(self, fresh=True):
        step = self.step
        entries = store.load_universe().get(step.key, [])
        mode = self.story.get("universe_mode", "n")
        if entries and (mode == "o" or (mode == "m" and self.rng.random() < UNIVERSE_CHANCE)):
            return dict(self.rng.choice(entries), _src="universe")
        return step.roll(self.engine, self.story, fresh=fresh)

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
        self._add(self._fresh(lambda: reroll_field(step, self.engine, self.story, cand, field)))

    def edit_field(self, field, text):
        text = text.strip()
        if text and text != self.cand.get(field):
            self._add(with_field(self.cand, field, text, src="edited"))
            return True
        return False

    def replace_fields(self, new):
        """The whole item rewritten (in $EDITOR, or by hand): it joins the history."""
        if new != self.fields:
            self._add(inherit(dict(new, _src="edited"), self.cand))
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

    def keep(self):
        """Keep the showing candidate and move on. (Updates later steps that mention what changed.)"""
        story, step, i, cand = self.story, self.step, self.i, self.cand
        old = story["kept"].get(step.key)
        new = public(cand)
        if step.key == "structure" and structures.find(new["structure"]):
            new["structure"] = structures.find(new["structure"]).label     # "kishotenketsu" -> "Kishōtenketsu"
        for k, v in cand.get("_made", {}).items():
            story["seeds"].setdefault(k, v)
        story["kept"][step.key] = new
        if step.key == "structure" and old and structures.get(old["structure"]) is not structures.get(new["structure"]):
            for gone in ("spine",):                 # the old body doesn't fit the new shape
                story["kept"].pop(gone, None)
                story["history"].pop(gone, None)
                story["atoms"].pop(gone, None)
            story["threads"] = {}
            self.note("New structure: the story body will be rolled again when you get to it.")
        if old and old != new:
            n = substitute(story, i, old, new)
            if step.threads:
                n += carry_threads(story, i, story.get("threads"), cand.get("_threads"))
            if n:
                self.note(f"Updated {n} mention(s) in later steps.")
        if step.threads:
            story["threads"] = cand.get("_threads", {})
        story["atoms"][step.key] = [a for lst in cand.get("_atoms", {}).values() for a in lst]
        story["step"] = max(story["step"], i + 1)
        self.save()
        self._advance()

    def save(self):
        """Write the story, its markdown, and the memory of recent picks."""
        path = store.save(self.story)
        self.engine.save_memory()
        return path

    # --- the universe --------------------------------------------------------------------------------

    def universe_total(self):
        return sum(len(v) for v in store.load_universe().values())

    def set_universe_mode(self, answer):
        self.story["universe_mode"] = answer if answer in ("m", "o") else "n"

    def universe_add(self):
        step = self.step
        n, added = store.add_to_universe(step.key, self.cand)
        what = f"{n} {step.label.lower()} entr{'y' if n == 1 else 'ies'}"
        self.note(f"{'Saved to' if added else 'Already in'} your universe ({what}). U removes it.")

    def universe_remove(self):
        removed = store.remove_from_universe(self.step.key, self.cand)
        self.note("Removed from your universe." if removed else "This one isn't in your universe.")

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
