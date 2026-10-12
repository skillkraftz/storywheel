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


def make_shelf(stories=200, universes=5, seed=2, words=120):
    """A library of short story ideas, the size the all-stories list must stay quick at: `stories` ideas over `universes` collections, a few
    with a manuscript of `words` words, with every status and format in use."""
    from storywheel import formats, ideas
    rng = random.Random(seed)
    unis = [vault.create_universe(f"Shelf {k}", kind="collection") for k in range(universes)]
    keys = [f.key for f in formats.FORMATS]
    made = []
    for n in range(stories):
        u = unis[n % universes]
        s = ideas.new_idea(u, f"Idea Number {n}", f"A logline for idea {n}.\nMore lines.", "flash" if n % 3 else "short-story",
                           status=vault.STATUSES[n % 4] if n % 5 == 0 else None)
        if n % 4 == 0:
            s.manuscript_dir.mkdir(parents=True, exist_ok=True)
            (s.manuscript_dir / "manuscript.md").write_text(paragraph(rng, words) + "\n", encoding="utf-8")
        if n % 40 == 0:
            formats.apply(s, rng.choice(keys))
        made.append(s)
    return unis, made
