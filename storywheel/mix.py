"""
The story mix: what actually steers rolling for one story.

The mix starts as the blend of the chosen genres' profiles (equal weight each).
The writer can then exclude a tag, exclude one list, boost a tag, or reset.
Those adjustments live in the story's own JSON (story["mix"]) and never touch
the genre profiles, so the next story starts from the defaults again.

How weights work (the one place this is decided):

* A tag's weight is the blended profile weight, times its boost.
* A list's (or an entry's) weight is the BIGGEST weight among its tags ("max",
  not "sum", so a list isn't favored just for carrying many tags).
* Excluding a tag zeroes every list and entry that carries it. Exclusion is
  absolute: the wildcard floor never brings it back.
* Wildcard floor: lists that are not excluded but whose tags the mix doesn't
  mention (weight 0) share a small slice of each pick (12% by default), so
  off-genre surprises still happen. Slots that repeat all through a story
  (rival, job, place, names) get a lower floor, set per slot in genres.json. If a slot has no mentioned
  lists they get everything; if it has no wildcard lists the mentioned ones do.
* The floor is not spread evenly over every other genre: lists tagged with a neighbor of the story's genres (`_neighbors` in
  genres.json) and untagged lists share it, and genres that are not neighbors get only FAR_SHARE (10%) of it between them. With no neighbor lists in a slot, the floor shrinks to that tenth.
* Inside a list, a plain string has weight 1. An entry with its own tags uses
  those tags' weight instead (so a "western" entry is 3x likelier in a
  western story), or OFF_WEIGHT if the mix doesn't mention them.
"""

FAR_SHARE = 0.1           # of the wildcard floor, the part that may go to genres that are not neighbors of the story's genres
OFF_WEIGHT = 0.1          # an entry tagged with something the mix ignores
UNKNOWN_GENRE_WEIGHT = 3  # a genre with no profile becomes a tag with this weight


def new_mix(base=()):
    return {"base": list(base), "exclude_tags": [], "exclude_lists": [], "boost": {}}


def story_mix(story):
    """The story's mix dict, created (and upgraded from v1 files) if missing."""
    mix = story.setdefault("mix", new_mix())
    mix.setdefault("base", [])
    mix.setdefault("exclude_tags", [])
    mix.setdefault("exclude_lists", [])
    mix.setdefault("boost", {})
    return mix


def genres_of(story):
    """The genres kept in the story, e.g. ['western', 'fairy tale']."""
    text = (story.get("kept", {}).get("genre") or {}).get("genre", "")
    return [g.strip().lower() for g in text.replace(",", "/").split("/") if g.strip()]


def sync_base(story):
    """Make the mix's base match the kept genres. Exclusions and boosts stay."""
    story_mix(story)["base"] = genres_of(story)


class Mix:
    def __init__(self, data, library):
        self.data = data                    # the story's mix dict (changed in place)
        self.profiles = library.profiles
        self.default = library.default_profile
        self.floor = library.floor
        self.floors = library.floors
        self.neighbors = getattr(library, "neighbors", {})

    @classmethod
    def for_story(cls, story, library):
        return cls(story_mix(story), library)

    # --- weights -------------------------------------------------------------

    def blended(self):
        """Genre profiles averaged, ignoring exclusions and boosts."""
        profiles = []
        for name in self.data["base"]:
            name = name.lower()
            profiles.append(self.profiles.get(name) or {name: UNKNOWN_GENRE_WEIGHT, "general": 1.0})
        if not profiles:
            profiles = [self.default]
        out = {}
        for profile in profiles:
            for tag, w in profile.items():
                out[tag] = out.get(tag, 0.0) + w / len(profiles)
        return out

    def weights(self):
        """Every tag's current weight, boosts applied, excluded tags at 0."""
        w = self.blended()
        for tag, factor in self.data["boost"].items():
            w[tag] = w.get(tag, 1.0) * factor   # boosting an unmentioned tag starts it at 1
        for tag in self.data["exclude_tags"]:
            w[tag] = 0.0
        return w

    def is_tag_excluded(self, tag):
        return tag in self.data["exclude_tags"]

    def is_list_excluded(self, wl):
        return (wl.id in self.data["exclude_lists"]
                or any(t in self.data["exclude_tags"] for t in wl.tags))

    def tags_weight(self, tags, weights=None):
        weights = self.weights() if weights is None else weights
        return max((weights.get(t, 0.0) for t in tags), default=0.0)

    def list_weight(self, wl, weights=None):
        """0 if excluded or unmentioned; see list_status to tell those apart."""
        if self.is_list_excluded(wl):
            return 0.0
        return self.tags_weight(wl.tags, weights)

    def entry_weight(self, entry, weights=None):
        if not entry.tags:
            return 1.0
        if any(t in self.data["exclude_tags"] for t in entry.tags):
            return 0.0
        return self.tags_weight(entry.tags, weights) or OFF_WEIGHT

    def near_tags(self):
        """Tags of the genres next door to the story's genres (from genres.json `_neighbors`), plus the genres' own tags."""
        near = set()
        for name in self.data["base"]:
            near.add(name.lower())
            near.update(self.neighbors.get(name.lower(), ()))
        return near

    def is_near(self, wl, near):
        """A list the floor may draw from freely: untagged, or tagged with a neighboring genre."""
        return not wl.tags or any(t in near for t in wl.tags)

    def floor_for(self, slot):
        """The wildcard share for a slot: anchor slots that repeat through a story
        (rival, job, place, names...) get a lower one than one-off blocks."""
        return self.floors.get(slot, self.floor)

    # --- picking probabilities -------------------------------------------------------

    def list_probabilities(self, lists):
        """Chance of each list being picked, in the same order. Sums to 1.

        If every list for the slot is excluded there is nothing sensible to
        draw, so the exclusions are ignored for that slot rather than
        returning nothing."""
        weights = self.weights()
        live = [wl for wl in lists if not self.is_list_excluded(wl)]
        if not live:
            return [1.0 / len(lists)] * len(lists) if lists else []
        w = {wl.id: self.list_weight(wl, weights) for wl in live}
        mentioned = [wl for wl in live if w[wl.id] > 0]
        wild = [wl for wl in live if w[wl.id] <= 0]
        floor = self.floor_for(lists[0].slot)
        wild_share = 0.0 if not wild else (1.0 if not mentioned else floor)
        total = sum(w[wl.id] for wl in mentioned)
        near_tags = self.near_tags()
        known = any(name.lower() in self.neighbors for name in self.data["base"])     # genres without neighbors listed keep the even floor
        near = [wl for wl in wild if not known or self.is_near(wl, near_tags)]
        far = [wl for wl in wild if wl not in near]
        if mentioned and known and not near:
            wild_share *= FAR_SHARE        # no neighbors written for this slot: the rest of the floor stays with the story's own and the general lists
        far_part = 1.0 if not near else FAR_SHARE if far else 0.0
        wild_part = {wl.id: (1.0 - far_part) / len(near) for wl in near}
        wild_part.update({wl.id: far_part / len(far) for wl in far})
        probs = []
        for wl in lists:
            if wl not in live:
                probs.append(0.0)
            elif w[wl.id] > 0:
                probs.append((1.0 - wild_share) * w[wl.id] / total)
            else:
                probs.append(wild_share * wild_part[wl.id])
        return probs

    # --- editing this story's mix (used by the mix editor) ----------------------------

    def _toggle(self, key, value, on):
        items = self.data[key]
        if on and value not in items:
            items.append(value)
        elif not on and value in items:
            items.remove(value)

    def exclude_tag(self, tag, on=True):
        self._toggle("exclude_tags", tag.strip().lower(), on)

    def exclude_list(self, list_id, on=True):
        self._toggle("exclude_lists", list_id, on)

    def set_boost(self, tag, factor):
        tag = tag.strip().lower()
        if factor is None or factor == 1:
            self.data["boost"].pop(tag, None)
        else:
            self.data["boost"][tag] = float(factor)

    def reset(self):
        """Back to the genre defaults. Kept pieces are not touched."""
        base = self.data["base"]
        self.data.clear()
        self.data.update(new_mix(base))
