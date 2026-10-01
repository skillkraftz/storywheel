"""
A tiny Markov-chain name maker. Train it on a list of names and it invents
new ones that sound like them: Calloway, Hollis, Pruitt -> Callis, Prutt...

Character by character, looking back `order` letters. No dependencies.
"""

END = "$"


class NameMaker:
    def __init__(self, names, order=3):
        self.order = order
        self.known = {n.strip().lower() for n in names}
        self.table = {}
        for name in self.known:
            padded = "^" * order + name + END
            for i in range(len(padded) - order):
                self.table.setdefault(padded[i:i + order], []).append(padded[i + order])

    def _one(self, rng, longest):
        state, out = "^" * self.order, ""
        while len(out) <= longest:
            c = rng.choice(self.table[state])
            if c == END:
                return out
            out += c
            state = (state + c)[-self.order:]
        return out

    def make(self, rng, shortest=4, longest=10, tries=40):
        """A new name that isn't in the training list, or None if it can't find one."""
        for _ in range(tries):
            name = self._one(rng, longest)
            if (shortest <= len(name) <= longest and name not in self.known
                    and not any(len(k) >= 3 and (name.startswith(k) or name.endswith(k))
                                for k in self.known)         # not just a real name plus a tail
                    and not any(name[i] == name[i + 1] == name[i + 2] for i in range(len(name) - 2))
                    and name[-1] not in "-'"):
                return "-".join(p[:1].upper() + p[1:] for p in name.split("-"))
        return None
