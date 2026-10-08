"""The free text of the in-app help agrees with the program (ISSUES #16; the manual's Appendix B). The key tables are made from the real
bindings; these checks are for the sentences around them."""
import re

from storywheel import helpdoc


def page(name):
    return open(helpdoc.__file__.replace("helpdoc.py", f"data/help/{name}.md"), encoding="utf-8").read()


def test_the_universe_panel_promises_only_keys_it_has():
    text = page("wheel")
    section = text[text.index("## The universe panel"):]
    section = section.split("\n## ")[0] if "\n## " in section[5:] else section
    assert "e to edit" not in section and "d to delete" not in section and "n to add" not in section
    assert "done in the Builder" in section
    from storywheel import tui
    assert {b.key for b in tui.UniverseTree.BINDINGS if hasattr(b, "key")} >= {"u"}          # (the one key the text names)


def test_u_capital_is_described_as_pointing_to_the_builder():
    items = {a: d for g in helpdoc.load("wheel").groups for a, d in g["items"].items()}
    assert "Remove the selected value" not in items["universe_remove"] and "Builder" in items["universe_remove"]


def test_the_wheels_button_row_lists_every_button():
    text = page("wheel")
    line = next(l for l in text.splitlines() if l.startswith("- Buttons under the card"))
    for label in ("Roll", "Keep", "Back", "Skip", "Flavor", "+Beat", "-Beat", "Send to Builder", "New draft"):
        assert label in line


def test_all_the_written_genres_are_called_written():
    text = page("genres-and-flavor")
    assert "until their lists are written" not in text
    for g in ("heist", "adventure", "coming-of-age"):
        assert g in text.split("Written in full:")[1].split("\n")[0], g


def test_colon_q_is_said_to_need_vim_keys():
    line = next(l for l in page("writer").splitlines() if "F2 or the Builder key" in l)
    assert "Vim keys" in line and "notepad" in line


def test_footers_say_a_focused_list_adds_its_keys():
    assert "adds its own" in page("keys")


def test_structures_and_exports_name_the_builder_and_the_prose_fountain_export():
    assert "story form" in page("structures")
    assert "prose story can also be exported as Fountain" in page("exports")


def test_no_page_says_nothing_is_destroyed_without_the_trash_or_old_labels():
    for n in helpdoc.names():
        text = page(n)
        assert "send its protagonist or setting to the current story" not in text
        assert not re.search(r"\bnot written yet\b", text), n
