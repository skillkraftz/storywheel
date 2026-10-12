"""Batch 24 B4 and B6: scene numbers (off by default; both margins of the PDF; in the .fdx) and the optional title page lines
(Notes, Copyright, WGA registration), read back from the PDF, the .fdx, the .fountain file and the Builder's story settings."""
import asyncio
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import Input, Select

from storywheel import export, fountain, screenplay, screenplay_pdf as sp, settings, vault
from storywheel.storysettings import StorySettingsScreen
from test_screenplay_pdf import TOL, pdf_pages

SCRIPT = """Title: Rooms
Credit: Written by

INT. ATTIC - NIGHT

Dust.

INT. CELLAR - DAY

Damp.

INT. LANE - DAY #5#

Rain.

EXT. YARD - NIGHT

Wind.

INT. HALL - DAY #7A#

Quiet.

INT. KITCHEN - DAY

Steam.
"""


@pytest.fixture
def story(home):
    settings.save_global({"author_name": "Andy Example", "address": "12 Example Road\nExampletown", "email": "andy@example.com", "phone": "555 0100"})
    u = vault.create_universe("Lamp", ["ghost story"])
    s = u.new_story("Rooms", {"structure": "Short Film"})
    s.script_path.parent.mkdir(parents=True, exist_ok=True)
    s.script_path.write_text(SCRIPT, encoding="utf-8")
    return s


def heading_numbers(path):
    """[(heading start word, left number text or None, right number text or None, heading x0)] for every scene heading of the script pages."""
    import pdfplumber
    out = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[1:]:                                                      # (page 0 is the title page)
            words = page.extract_words()
            for w in words:
                if w["text"] in ("INT.", "EXT.") and abs(w["x0"] / 72 - 1.5) <= 0.05:
                    row = [x for x in words if abs(x["top"] - w["top"]) < 2 and x is not w]
                    left = next((x["text"] for x in row if x["x1"] / 72 < 1.45), None)
                    right = next((x["text"] for x in row if x["x0"] / 72 > 7.5), None)
                    out.append((w["text"], left, right, w["x0"] / 72, next((x for x in row if x["x1"] / 72 < 1.45), None),
                                next((x for x in row if x["x0"] / 72 > 7.5), None)))
    return out


# --- scene numbers ----------------------------------------------------------------------------------------------------------------

def test_scenes_are_numbered_in_order_carrying_on_from_the_numbers_written_in_the_script():
    els = fountain.parse(SCRIPT).elements
    nums = sp.scene_numbers(els)
    assert [nums[id(e)] for e in els if e.type == "heading"] == ["1", "2", "5", "6", "7A", "7"]       # (7A is written, so the count stays at 6)


def test_the_page_count_does_not_change_with_numbers():
    assert sp.page_count(SCRIPT, True) == sp.page_count(SCRIPT, True) and len(sp.paginate(SCRIPT, True, True)) == len(sp.paginate(SCRIPT, True, False))
    assert [ln.number for pg in sp.paginate(SCRIPT, False, True) for ln in pg.lines if ln is not None and ln.kind == "heading" and ln.number][:2] == ["1", "2"]
    assert not any(ln.number for pg in sp.paginate(SCRIPT) for ln in pg.lines if ln is not None)


def test_scene_numbers_are_off_by_default_and_the_pdf_has_none(story):
    assert settings.load_story(story.path)["script_scene_numbers"] is False and settings.load_global()["script_scene_numbers"] is False
    r = export.export(story, "pdf")
    assert len(heading_numbers(r["path"])) == 6
    for _h, left, right, *_rest in heading_numbers(r["path"]):
        assert left is None and right is None


def test_with_numbers_on_each_heading_has_its_number_in_both_margins(story):
    settings.save_story(story.path, {"script_scene_numbers": True})
    r = export.export(story, "pdf")
    found = heading_numbers(r["path"])
    assert len(found) == 6
    assert [l for _h, l, _r, *_x in found] == [r_ for _h, _l, r_, *_x in found] == ["1", "2", "5", "6", "7A", "7"]
    for _h, _l, _r, x0, lw, rw in found:
        assert abs(lw["x1"] / 72 - 1.4) <= TOL and abs(rw["x0"] / 72 - 7.6) <= TOL and abs(x0 - 1.5) <= TOL     # (the heading itself has not moved)


def test_the_global_default_applies_and_a_story_can_choose_for_itself(story):
    settings.save_global({"script_scene_numbers": True})
    assert settings.load_story(story.path)["script_scene_numbers"] is True
    assert all(l is not None for _h, l, *_r in heading_numbers(export.export(story, "pdf")["path"]))
    settings.save_story(story.path, {"script_scene_numbers": False})
    assert all(l is None for _h, l, *_r in heading_numbers(export.export(story, "pdf")["path"]))


def test_the_final_draft_file_carries_the_numbers_only_when_on(story):
    root = ET.parse(export.export(story, "fdx")["path"]).getroot()
    assert all(p.get("Number") is None for p in root.find("Content").iter("Paragraph"))
    settings.save_story(story.path, {"script_scene_numbers": True})
    root = ET.parse(export.export(story, "fdx")["path"]).getroot()
    got = [p.get("Number") for p in root.find("Content").iter("Paragraph") if p.get("Type") == "Scene Heading"]
    assert got == ["1", "2", "5", "6", "7A", "7"]


# --- the title page ---------------------------------------------------------------------------------------------------------------

def title_lines(path):
    return pdf_pages(path)[0][2]


def test_blank_optional_lines_are_left_off_the_title_page(story):
    texts = [l["text"] for l in title_lines(export.export(story, "pdf")["path"])]
    assert not any("Copyright" in t or "WGA" in t or "©" in t for t in texts)
    tp, _w = screenplay.title_page(story)
    assert tp["notes"] == [] and tp["copyright"] == [] and tp["wga"] == []


def test_notes_copyright_and_wga_sit_where_the_standard_puts_them(story):
    settings.save_story(story.path, {"script_wga": "1234567", "script_copyright": "© 2026 Andy Example", "script_notes": "Second draft. Based on a true story."})
    lines = title_lines(export.export(story, "pdf")["path"])
    by = {l["text"]: l for l in lines}
    wga, copy_, phone, email = by["WGA Registration # 1234567"], by["© 2026 Andy Example"], by["555 0100"], by["andy@example.com"]
    for l in (wga, copy_, phone, email):
        assert abs(l["x0"] - 1.5) <= TOL                                                           # bottom left, with the contact block
    assert wga["top"] < copy_["top"] < email["top"] < phone["top"] and phone["top"] > 9.5
    assert copy_["top"] < by["12 Example Road"]["top"] - 0.15                                      # (a blank line between them and the contact)
    notes = [l for l in lines if l["text"] in ("Second draft. Based on a", "Second draft.", "true story.", "a true story.") or "draft" in l["text"] or "story." in l["text"]]
    assert notes and all(abs(l["x1"] - 7.5) <= TOL and l["x0"] > 4.4 for l in notes)               # bottom right, right-aligned, in a column


def test_the_wga_number_is_labelled_unless_it_already_says_so(story):
    settings.save_story(story.path, {"script_wga": "WGAw Registered #99"})
    assert screenplay.title_page(story)[0]["wga"] == ["WGAw Registered #99"]
    settings.save_story(story.path, {"script_wga": "#42"})
    assert screenplay.title_page(story)[0]["wga"] == ["WGA Registration # 42"]


def test_the_scripts_own_title_page_keys_win_over_the_settings(story):
    settings.save_story(story.path, {"script_copyright": "© from settings", "script_notes": "from settings"})
    story.script_path.write_text("Title: Rooms\nCopyright: © from the script\nNotes: first line\n    second line\nWGA registration: 555\n\n" + SCRIPT.split("\n\n", 1)[1], encoding="utf-8")
    tp, _w = screenplay.title_page(story)
    assert tp["copyright"] == ["© from the script"] and tp["notes"] == ["first line", "second line"] and tp["wga"] == ["WGA Registration # 555"]


def test_an_anonymous_script_leaves_out_the_copyright_and_wga_but_keeps_the_notes(story):
    settings.save_story(story.path, {"script_wga": "1234567", "script_copyright": "© 2026 Andy Example", "script_notes": "Second draft"})
    texts = [l["text"] for p in pdf_pages(export.export(story, "pdf", anonymous=True)["path"]) for l in p[2]]
    assert "Second draft" in texts and not any("1234567" in t or "© 2026" in t or "Andy" in t for t in texts)


def test_the_fountain_and_final_draft_files_get_the_lines_too(story):
    settings.save_story(story.path, {"script_wga": "1234567", "script_copyright": "© 2026 Andy Example", "script_notes": "Second draft"})
    s = fountain.parse(Path(export.export(story, "fountain")["path"]).read_text(encoding="utf-8"))
    assert s.title["copyright"] == ["© 2026 Andy Example"] and s.title["wga registration"] == ["WGA Registration # 1234567"] and s.title["notes"] == ["Second draft"]
    root = ET.parse(export.export(story, "fdx")["path"]).getroot()
    assert {"© 2026 Andy Example", "Second draft", "WGA Registration # 1234567"} <= {t.text for t in root.find("TitlePage").iter("Text")}


# --- the Builder's story settings ---------------------------------------------------------------------------------------------------

def run_settings_box(story):
    box = {}

    class Host(App):
        def on_mount(self):
            self.push_screen(StorySettingsScreen(story), lambda out: box.update(out=out))

    async def go():
        app = Host()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            dlg = app.screen
            box["ids"] = [w.id for w in dlg.query("Select, Input")]
            if "f-script_wga" in box["ids"]:
                dlg.query_one("#f-script_scene_numbers", Select).value = "on"
                dlg.query_one("#f-script_wga", Input).value = "777"
                dlg.query_one("#f-script_notes", Input).value = "Draft two"
                await pilot.pause()
                box["note"] = str(dlg.query_one("#note-script_notes").content)
                dlg.action_save()
            else:
                dlg.action_cancel()
            await pilot.pause()
    asyncio.run(go())
    return box


def test_the_story_settings_box_offers_the_screenplay_options_to_a_screenplay_only(story):
    box = run_settings_box(story)
    assert {"f-script_scene_numbers", "f-script_wga", "f-script_copyright", "f-script_notes"} <= set(box["ids"])
    assert "this story's own" in box["note"]
    out, clear = box["out"]
    assert out["script_scene_numbers"] is True and out["script_wga"] == "777" and out["script_notes"] == "Draft two" and "script_copyright" not in out
    prose = vault.get_universe("lamp").new_story("A Prose Tale")
    assert not any(i.startswith("f-script_") for i in run_settings_box(prose)["ids"])
