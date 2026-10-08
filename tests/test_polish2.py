"""Polish 2 (ISSUES #19-36): what a writer does, and what they see."""
from test_polish1 import ann, builder_run  # noqa: F401  (the fixture and helper of polish 1)


def status(s):
    w = s.query_one("#status")
    for name in ("content", "renderable"):
        if hasattr(w, name):
            return str(getattr(w, name))
    return str(w.render())


# --- 19. messages name the key that works -----------------------------------------------------------------------------------

def test_19_the_structure_row_points_to_m(home, ann):
    async def script(app, pilot):
        s = app.screen_ref
        await pilot.click("#outline", offset=(5, 2))
        await pilot.pause()
        for _ in range(40):
            if s.top_rows()[s.outline.highlighted or 0][0] == "meta:structure":
                break
            await pilot.press("down")
        await pilot.press("e")
        await pilot.pause()
        return status(s)
    msg = builder_run(script)
    assert "with m" in msg and "Wheel" not in msg, msg


def test_19_p_on_a_prose_story_points_to_m(home, ann):
    async def script(app, pilot):
        s = app.screen_ref
        await pilot.press("P")
        await pilot.pause()
        return status(s)
    msg = builder_run(script)
    assert "not a screenplay" in msg and "with m" in msg and "(S, story settings)" not in msg, msg

