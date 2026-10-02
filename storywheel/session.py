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

from . import promote, store, structures, universe_atoms, vault
from . import ratings as R
from . import threads as T
from .refs import carry_threads, inherit, reroll_field, substitute, with_field
from .steps import OWNER, public, steps_for
from .text import fix_articles, motif_from

HEADLINE = ("name", "first", "last", "place", "title", "motif", "genre", "structure")     # what a banner names
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
        self.engine.set_universes(self.selected_universes())

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
        before = [st.label for n, st in enumerate(self.steps[:i]) if not self.story["kept"].get(st.key)]
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
        if self.i + 1 >= len(self.steps):
            self.done = True
        else:
            self.enter(self.i + 1)

    def skip(self):
        step, story = self.step, self.story
        story["kept"].pop(step.key, None)
        story.get("inputs", {}).pop(step.key, None)
        if step.threads:
            story["threads"] = {}
        story["atoms"].pop(step.key, None)
        story["step"] = max(story["step"], self.i + 1)
        self.save()
        self._advance()

    # --- rolling -----------------------------------------------------------------------------------

    def _roll(self, fresh=True):
        step = self.step
        entries = self.universe_entries(step.key)
        mode = self.story.get("universe_mode", "n")
        if entries and (mode == "o" or (mode == "m" and self.rng.random() < UNIVERSE_CHANCE)):
            _u, _e, fields = self.rng.choice(entries)
            return self._complete(step, dict(fields, _src="universe"))
        return step.roll(self.engine, self.story, fresh=fresh)

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
        self._add(self._fresh(lambda: reroll_field(step, self.engine, self.story, cand, field)))

    def _follow_title(self, cand, old_title):
        """A hand-written title says what the story is about: the motif follows it (unless you also wrote the motif)."""
        if self.step.key != "title" or "motif" not in cand or cand.get("title", "") == old_title:
            return
        motif = motif_from(cand["title"], lambda: cand["motif"])
        if motif != cand["motif"]:
            cand["motif"] = motif
            self.note(f"The motif now follows your title: '{motif}'. Edit the motif field if that isn't what it is about.")

    def edit_field(self, field, text):
        text = text.strip()
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
        story.setdefault("inputs", {})[step.key] = copy.deepcopy(cand.get("_inputs", {}))
        self._swap_standins(i, new)
        story["step"] = max(story["step"], i + 1)
        self.save()
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
        if not changes:
            return False
        self.cand["_ack"] = dict(self.cand.get("_ack", {}), **{k: now for k, _s, _o, now in changes})
        self.note("Ignoring the change. This candidate stays as it is.")
        return True

    def standins(self, cand=None):
        """{step key: [stand-in values]} for steps this candidate used stand-ins for that are still not kept."""
        out = {}
        for key, inp in (cand if cand is not None else self.cand).get("_inputs", {}).items():
            if inp["standin"] and self.current_value(key) is None:
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

    def step_problems(self, i):
        """[(severity, message)] for a KEPT step: 'changed' when it was built on a stand-in or on a
        value that has since changed, 'broken' when it refers to something that is no longer kept."""
        step = self.steps[i]
        if not self.story["kept"].get(step.key):
            return []
        out = []
        for key, inp in self.story.get("inputs", {}).get(step.key, {}).items():
            now = self.current_value(key)
            owner = next((st.label for st in self.steps if st.key == inp["step"]), inp["step"]).lower()
            if now is None and inp["standin"]:
                out.append(("changed", f"{step.label} was built on a stand-in {owner} ({inp['value']}). "
                                       f"Keep your {owner} to replace it."))
            elif now is None:
                out.append(("broken", f"{step.label} refers to {inp['value']}, but there is no longer a kept {owner}."))
            elif now != inp["value"]:
                out.append(("changed", f"{step.label} was built for {inp['value']}; your {owner} is now {now}."))
        return out

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

    def use_universe_entry(self, step_key, fields):
        """Offer a universe entity as a candidate for its step in this story, jumping there if need be.
        Nothing is kept: the story's kept steps are untouched until you press k."""
        index = next((n for n, st in enumerate(self.steps) if st.key == step_key), None)
        if index is None:
            self.note(f"This story has no '{step_key}' step.")
            return False
        if index != self.i:
            self.jump(index)
        cand = dict(public(fields), _src="universe")
        for name in self.field_names:                      # an entity may leave fields blank
            if not cand.get(name):
                cand[name] = self.cand.get(name, "")
        self._add(cand)
        self.note("Added from your universe as a new candidate. Press k to keep it.")
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
