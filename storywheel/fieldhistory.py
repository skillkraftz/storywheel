"""The Builder's per-field history (every value a field has had, for the scroll wheel and the arrow keys), kept beside the entity so it is
still there tomorrow: `<universe>/.field-history/<entity id>.json`. Acts like the dict the Builder always used, keyed (entity id, field)."""
import json
from pathlib import Path

from . import vault

FOLDER = ".field-history"


def path_for(universe, eid):
    return Path(universe.path) / FOLDER / f"{eid}.json"


def read(universe, eid):
    try:
        data = json.loads(path_for(universe, eid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    fields = data.get("fields") if isinstance(data, dict) else None
    return {k: v for k, v in (fields or {}).items() if isinstance(v, list)}


def read_prov(universe, eid):
    """{field: {value text: {"frame": ..., "atoms": [...]}}}: what produced each rolled value, so a rating can teach the generator."""
    try:
        data = json.loads(path_for(universe, eid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    prov = data.get("prov") if isinstance(data, dict) else None
    return prov if isinstance(prov, dict) else {}


def write(universe, eid, fields, prov=None):
    fields = {k: v for k, v in fields.items() if v}
    p = path_for(universe, eid)
    if not fields:
        if p.exists():
            vault.forget(p)
            p.unlink()
        return
    doc = {"entity": eid, "fields": fields}
    prov = {f: t for f, t in (prov if prov is not None else read_prov(universe, eid)).items() if t and f in fields}
    if prov:
        doc["prov"] = prov
    vault._write(p, json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


def drop(universe, eid):
    write(universe, eid, {})


def move(universe, old, new):
    fields = read(universe, old)
    if fields:
        write(universe, new, {**read(universe, new), **fields})
        drop(universe, old)


class FieldHistory(dict):
    """{(entity id, field): [values]}, loaded from disk the first time an entity is touched; call save(eid) after changing its lists."""

    def __init__(self):
        super().__init__()
        self.universe = None
        self.loaded = set()
        self.prov = {}                      # (entity id, field) -> {value text: {"frame", "atoms"}}

    def use(self, universe):
        if universe is None:
            return
        if self.universe is None or self.universe.path != universe.path:
            self.clear()
            self.prov = {}
            self.loaded = set()
            self.universe = universe

    def ensure(self, eid):
        if self.universe is None or eid in self.loaded:
            return
        self.loaded.add(eid)
        for field, values in read(self.universe, eid).items():
            dict.setdefault(self, (eid, field), list(values))
        for field, table in read_prov(self.universe, eid).items():
            self.prov.setdefault((eid, field), dict(table))

    def get(self, key, default=None):
        self.ensure(key[0])
        return dict.get(self, key, default)

    def setdefault(self, key, default=None):
        self.ensure(key[0])
        return dict.setdefault(self, key, default)

    def __getitem__(self, key):
        self.ensure(key[0])
        return dict.__getitem__(self, key)

    def fields_of(self, eid):
        self.ensure(eid)
        return {k[1]: v for k, v in dict.items(self) if k[0] == eid}

    def set_provenance(self, eid, field, text, frame, atoms):
        self.ensure(eid)
        self.prov.setdefault((eid, field), {})[text] = {"frame": frame, "atoms": atoms}

    def provenance(self, eid, field, text):
        """(frame, atoms) that produced this value, or (None, []) for a value written by hand (or rolled before this was kept)."""
        self.ensure(eid)
        got = self.prov.get((eid, field), {}).get(text)
        return (got["frame"], [tuple(a) for a in got["atoms"]]) if got else (None, [])

    def prov_of(self, eid):
        self.ensure(eid)
        return {k[1]: v for k, v in self.prov.items() if k[0] == eid}

    def save(self, eid):
        if self.universe is not None:
            write(self.universe, eid, self.fields_of(eid), self.prov_of(eid))

    def rename(self, old, new):
        """An entity's id changed (a placeholder got a real name): its history follows."""
        self.ensure(old)
        for (eid, k) in [key for key in dict.keys(self) if key[0] == old]:
            dict.__setitem__(self, (new, k), dict.pop(self, (eid, k)))
            if (eid, k) in self.prov:
                self.prov[(new, k)] = self.prov.pop((eid, k))
        self.loaded.add(new)
        if self.universe is not None:
            drop_old = path_for(self.universe, old)
            if drop_old.exists():
                vault.forget(drop_old)
                drop_old.unlink()
        self.save(new)
