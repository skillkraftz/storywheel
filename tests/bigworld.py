"""A generated universe of the size that felt slow in real use: 160 entities and four ~20k-word stories."""
import random

from storywheel import vault

WORDS = ("the old road ran past a dry creek and the horse would not cross it so we waited until dusk when the wind changed "
         "and somebody said the bell had rung twice though nobody had touched the rope").split()


def paragraph(rng, n=90):
    return " ".join(rng.choice(WORDS) for _ in range(n)).capitalize() + "."


def make_big_universe(seed=1, entities=160, stories=4, words=20000):
    rng = random.Random(seed)
    u = vault.create_universe("Big Country", ["western", "fairy tale"])
    kinds = ["character"] * 60 + ["place"] * 50 + ["thing"] * 40 + ["group"] * 5 + ["note"] * 5
    made = []
    for i in range(entities):
        t = kinds[i % len(kinds)]
        e = u.new_entity(t, f"{t.title()} Name{i}")
        for f in vault.schemas.get(t)["fields"]:
            if f["key"] != "name" and f.get("kind") in ("short", "long", None):
                e.fields[f["key"]] = f"some value {i} for {f['key']}"
        e.body = paragraph(rng, 60)
        u.save_entity(e)
        made.append(e)
    chars = [e for e in made if e.type == "character"]
    for e in made[:40]:                                    # some links, so Links / Appears in have something to find
        if e.type == "thing":
            e.fields["owner"] = rng.choice(chars).id
            u.save_entity(e)
    out = []
    for k in range(stories):
        s = u.new_story(f"Story Number {k}", {"cast": [rng.choice(chars).id for _ in range(3)]},
                        {"Premise": paragraph(rng, 30), "Twist": paragraph(rng, 20)})
        text = []
        total = 0
        scene = 0
        while total < words:
            if scene:
                text.append(f"* * * Scene {scene}")
            for _ in range(8):
                text.append(paragraph(rng))
                total += 90
            scene += 1
        s.manuscript_dir.mkdir(parents=True, exist_ok=True)
        (s.manuscript_dir / "manuscript.md").write_text("\n\n".join(text) + "\n", encoding="utf-8")
        out.append(s)
    return u, out, made
