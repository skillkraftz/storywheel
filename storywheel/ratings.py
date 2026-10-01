"""
Ratings: + and - on lines and fields, kept in ~/.storywheel/ratings.json.

Every rating remembers the line, where it came from, and what produced it: the
FRAME (the template) and the ATOMS that filled it. From that the tool learns, gently:

* a frame that keeps getting - is drawn less often;
* so is a pair of atoms that keep getting - together ("buried" + "a mule");
* and, more weakly, a single atom that keeps getting -.

"Gently" means: one - is no evidence at all (a line can be bad for many reasons); the
effect starts only when a frame or pair has a net score of -2, shrinks by about a fifth
for each further net -, and never goes below a floor, so nothing is ever ruled out.
Rate a line + and the - on the same frame is outweighed. Pressing the same key again
clears a rating.

`storywheel report` lists the worst-rated lines and the frames that produced them.
Ratings never change a seeded `sample` run, which doesn't read them.
"""
import datetime
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

# (rate per strike, floor, net score where it starts to bite)
FRAME = (0.8, 0.25, -2)
COMBO = (0.7, 0.20, -2)
ATOM = (0.9, 0.50, -3)

VERSION = 1


def _factor(net, rule):
    rate, floor, start = rule
    strikes = start - net + 1 if net <= start else 0
    return max(floor, rate ** strikes) if strikes else 1.0


def frame_key(slot, template):
    return f"{slot}\x1f{template}"


def atom_key(slot, text):
    return f"{slot}\x1f{text}"


def combo_key(a, b):
    return "\x1e".join(sorted((atom_key(*a), atom_key(*b))))


def provenance(library, atoms):
    """Split a field's atoms ([[slot, text], ...]) into (its frame, its other atoms).
    The frame is the template pick (a slot whose lists are templates); None for a plain atom field."""
    frame, rest = None, []
    for slot, text in atoms or []:
        is_template = any(wl.is_template for wl in library.by_slot.get(slot, []))
        if is_template and frame is None:
            frame = {"slot": slot, "template": text}
        elif not is_template:
            rest.append([slot, text])
    return frame, rest


class Ratings:
    def __init__(self, path=None, records=None):
        self.path = Path(path) if path else None
        self.records = list(records or [])
        self._tally_cache = None

    # --- storage -----------------------------------------------------------------------------

    @classmethod
    def load(cls, home):
        path = Path(home) / "ratings.json"
        records = []
        if path.exists():
            try:
                records = json.loads(path.read_text(encoding="utf-8")).get("ratings", [])
            except (ValueError, OSError, AttributeError):
                records = []               # a damaged file just means we start again
        return cls(path, records)

    def save(self):
        if not self.path:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({"version": VERSION, "ratings": self.records}, indent=1),
                                 encoding="utf-8")
        except OSError:
            pass                           # never let a full disk stop a story

    # --- recording -----------------------------------------------------------------------------

    @staticmethod
    def _line_key(story_id, step, field, text):
        return (story_id, step, field, text)

    def current(self):
        """The latest rating of each line, dropping cleared ones."""
        latest = {}
        for r in self.records:
            latest[self._line_key(r["story"], r["step"], r["field"], r["text"])] = r
        return [r for r in latest.values() if r["rating"]]

    def rating_of(self, story_id, step, field, text):
        value = 0
        for r in self.records:
            if self._line_key(r["story"], r["step"], r["field"], r["text"]) == self._line_key(story_id, step, field, text):
                value = r["rating"]
        return value

    def rate(self, story_id, step, field, text, value, frame=None, atoms=(), title=""):
        """Record +1 or -1 for a line. Giving the rating a line already has clears it.
        Returns the rating now in force (-1, 0 or 1)."""
        previous = self.rating_of(story_id, step, field, text)
        now = 0 if previous == value else value
        self.records.append({
            "t": datetime.datetime.now().isoformat(timespec="seconds"), "story": story_id, "title": title,
            "step": step, "field": field, "text": text, "rating": now,
            "frame": frame, "atoms": [list(a) for a in atoms]})
        self._tally_cache = None
        self.save()
        return now

    # --- what the ratings add up to ---------------------------------------------------------------

    def _tally(self):
        if self._tally_cache is None:
            frames, atoms, combos = defaultdict(int), defaultdict(int), defaultdict(int)
            for r in self.current():
                if r["frame"]:
                    frames[frame_key(r["frame"]["slot"], r["frame"]["template"])] += r["rating"]
                items = [tuple(a) for a in r["atoms"]]
                for a in items:
                    atoms[atom_key(*a)] += r["rating"]
                for a, b in combinations(sorted(set(items)), 2):
                    combos[combo_key(a, b)] += r["rating"]
            self._tally_cache = (frames, atoms, combos)
        return self._tally_cache

    def frame_factor(self, slot, template):
        return _factor(self._tally()[0].get(frame_key(slot, template), 0), FRAME)

    def atom_factor(self, slot, text):
        return _factor(self._tally()[1].get(atom_key(slot, text), 0), ATOM)

    def combo_factor(self, slot, text, others):
        """Factor for choosing (slot, text) alongside atoms already chosen in the same line."""
        combos = self._tally()[2]
        out = 1.0
        for other in others:
            out *= _factor(combos.get(combo_key((slot, text), tuple(other)), 0), COMBO)
        return out

    def atom_bias(self, slot, text, others):
        """Everything ratings say about picking this atom here: its own record, and its pairings."""
        return self.atom_factor(slot, text) * self.combo_factor(slot, text, others)

    # --- the report ----------------------------------------------------------------------------------

    def worst_lines(self, n=10):
        frames = self._tally()[0]
        bad = [r for r in self.current() if r["rating"] < 0]
        def net(r):
            return frames.get(frame_key(r["frame"]["slot"], r["frame"]["template"]), 0) if r["frame"] else 0
        return sorted(bad, key=lambda r: (net(r), r["t"]))[:n]

    def worst_frames(self, n=10):
        """[(net, minus, plus, slot, template)], most disliked first."""
        stats = defaultdict(lambda: [0, 0])
        for r in self.current():
            if r["frame"]:
                stats[(r["frame"]["slot"], r["frame"]["template"])][r["rating"] > 0] += 1
        rows = [(plus - minus, minus, plus, slot, tpl) for (slot, tpl), (minus, plus) in stats.items() if minus > plus]
        return sorted(rows)[:n]

    def worst_combos(self, n=10):
        stats = defaultdict(lambda: [0, 0])
        for r in self.current():
            items = sorted({tuple(a) for a in r["atoms"]})
            for a, b in combinations(items, 2):
                stats[(a, b)][r["rating"] > 0] += 1
        rows = [(plus - minus, minus, plus, a, b) for (a, b), (minus, plus) in stats.items() if minus > plus]
        return sorted(rows)[:n]


def format_report(ratings, n=10):
    cur = ratings.current()
    if not cur:
        return "  No ratings yet. Press + or - on a line while you roll."
    plus = sum(r["rating"] > 0 for r in cur)
    out = [f"  {len(cur)} rated lines: {plus} liked, {len(cur) - plus} disliked.", ""]
    lines = ratings.worst_lines(n)
    out.append("  Worst-rated lines")
    if not lines:
        out.append("    (none)")
    for r in lines:
        where = f"{r['step']}.{r['field']}" if r["field"] else r["step"]
        out.append(f"    - {r['text']}")
        out.append(f"        {where}" + (f"   in \"{r['title']}\"" if r.get("title") else ""))
        if r["frame"]:
            out.append(f"        frame: [{r['frame']['slot']}] {r['frame']['template']}")
        if r["atoms"]:
            out.append("        atoms: " + ", ".join(t for _s, t in r["atoms"]))
    frames = ratings.worst_frames(n)
    out += ["", "  Frames that keep getting -"]
    if not frames:
        out.append("    (none)")
    for net, minus, plus_, slot, tpl in frames:
        factor = ratings.frame_factor(slot, tpl)
        out.append(f"    {net:+d}  ({minus} - / {plus_} +)  [{slot}] {tpl}"
                   + (f"   now drawn at {factor:.0%}" if factor < 1 else "   (not down-weighted yet)"))
    combos = ratings.worst_combos(n)
    out += ["", "  Atom pairs that keep getting -"]
    if not combos:
        out.append("    (none)")
    for net, minus, plus_, a, b in combos:
        out.append(f"    {net:+d}  ({minus} - / {plus_} +)  \"{a[1]}\" + \"{b[1]}\"")
    return "\n".join(out)
