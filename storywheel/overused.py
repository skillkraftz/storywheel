"""Overused words in a story: the most frequent words (leaving out the everyday ones) and words repeated close together,
with where they are. Reads the manuscript; changes nothing."""
import re

from . import vault

# everyday words that are supposed to repeat (the small words of English, plus the very common verbs)
STOPWORDS = set("""
a about above after again against all almost also although always am among an and another any anyone anything are around as at away
back be because been before behind being below between both but by came can cannot could did do does doing done down during each
either else even ever every everyone everything few for from get gets getting go goes going gone got had has have having he her here
hers herself him himself his how however i if in into is it its itself just know let like made make many may me might more most much
must my myself never no nobody none nor not nothing now of off often on once one only onto or other others our ours ourselves out over
own per perhaps quite rather really said say says see seemed she should since so some someone something still such than that the their
theirs them themselves then there these they thing things think this those though through thus to together too took toward towards
under until up upon us used very was way we well went were what whatever when where whether which while who whom whose why will with
within without would yes yet you your yours yourself yourselves
""".split())

WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*[A-Za-z]|[A-Za-z]")


def tokens(story):
    """[(word lowercased, scene title, file, line number (1-based), column, the line)] for every word of the manuscript, in order."""
    out = []
    for path in story.files():
        text = vault.Story._read(story, path)
        scenes = vault.parse_scenes(text)
        lines = text.split("\n")
        for i, line in enumerate(lines, 1):
            if vault.marker_label(line.strip()) is not None:
                continue
            scene = next((sc for sc in scenes if sc["start"] <= i <= sc["end"]), None)
            title = (scene["label"] if scene and scene["label"] else f"Scene {scenes.index(scene) + 1}") if scene else ""
            for m in WORD.finditer(line):
                out.append((m.group(0).lower().replace("’", "'"), title, str(path), i, m.start(), line))
    return out


def stem(word):
    """A rough stem so that 'walk', 'walks' and 'walked' count together."""
    w = word
    for suffix, repl in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[: -len(suffix)] + repl
    return w


def snippet(line, col, width=70):
    start = max(0, col - width // 2)
    text = line[start:start + width].strip()
    return ("…" if start else "") + text + ("…" if start + width < len(line) else "")


def frequent(story, top=40, min_count=3, toks=None):
    """The most frequent words that are not everyday words: [{word, count, forms, where: [occurrence]}], most frequent first.
    Words are counted by stem ('walk' + 'walked'); `forms` lists what was actually written."""
    toks = toks if toks is not None else tokens(story)
    groups = {}
    for tok in toks:
        w = tok[0]
        if w in STOPWORDS or len(w) < 3:
            continue
        groups.setdefault(stem(w), []).append(tok)
    ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    out = []
    for key, occ in ranked:
        if len(occ) < min_count or len(out) >= top:
            break
        forms = sorted({o[0] for o in occ})
        out.append({"word": min(forms, key=len), "count": len(occ), "forms": forms, "where": [_where(o) for o in occ]})
    return out


def _where(tok):
    word, scene, path, line, col, text = tok
    return {"word": word, "scene": scene, "file": path, "line": line, "col": col, "text": snippet(text, col)}


def close_repeats(story, window=50, toks=None, min_len=4):
    """Words (not everyday ones) used again within `window` words: [{word, count, clusters: [[occurrence...]]}], most repeated first.
    A cluster is a run of uses each within the window of the one before."""
    toks = toks if toks is not None else tokens(story)
    last = {}
    clusters = {}
    for pos, tok in enumerate(toks):
        w = tok[0]
        if w in STOPWORDS or len(w) < min_len:
            continue
        key = stem(w)
        prev = last.get(key)
        if prev is not None and pos - prev <= window:
            groups = clusters.setdefault(key, [])
            if groups and groups[-1][-1][0] == prev:
                groups[-1].append((pos, tok))
            else:
                groups.append([(prev, toks[prev]), (pos, tok)])
        last[key] = pos
    out = []
    for key, groups in clusters.items():
        occ = [[_where(t) for _p, t in g] for g in groups]
        out.append({"word": key, "count": sum(len(g) for g in groups), "clusters": occ})
    out.sort(key=lambda r: (-r["count"], r["word"]))
    return out


def report(story, top=40, window=50):
    toks = tokens(story)
    return {"words": len(toks), "frequent": frequent(story, top, toks=toks), "repeats": close_repeats(story, window, toks=toks)}
