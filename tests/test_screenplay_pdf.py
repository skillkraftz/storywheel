"""The screenplay export (batch 17), read back: the PDF's page, font, positions and pagination rules (pdfplumber), the title page, the
Final Draft file, the .fountain file, and the export record."""
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import pytest

from storywheel import export, fountain, screenplay_pdf as sp, settings, vault

pdfplumber = pytest.importorskip("pdfplumber")

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "screenplay" / "the-lamp.fountain"
TOL = 0.05                                       # inches


def lines_of(page):
    """[{x0, x1, top, text, font}] for each run of text on a line (dual dialogue gives two runs on one line)."""
    rows = defaultdict(list)
    for w in page.extract_words(keep_blank_chars=True, extra_attrs=["fontname", "size"]):
        rows[round(w["top"], 1)].append(w)
    out = []
    for top in sorted(rows):
        ws = sorted(rows[top], key=lambda w: w["x0"])
        runs, cur = [], [ws[0]]
        for w in ws[1:]:
            (runs.append(cur), cur := [w]) if w["x0"] - cur[-1]["x1"] > 20 else cur.append(w)
        runs.append(cur)
        for r in runs:
            out.append({"x0": r[0]["x0"] / 72, "x1": r[-1]["x1"] / 72, "top": top / 72, "text": " ".join(w["text"] for w in r).strip(),
                        "font": r[0]["fontname"], "size": r[0]["size"]})
    return out


def pdf_pages(path):
    with pdfplumber.open(path) as pdf:
        return [(p.width, p.height, lines_of(p)) for p in pdf.pages]


def render(text, tmp_path, name="s.pdf", title=None):
    path = tmp_path / name
    sp.render(text, path, title)
    return pdf_pages(path)


def body(page):
    return [l for l in page[2] if not re.fullmatch(r"\d+\.", l["text"])]


def find(pages, text):
    return [(i, l) for i, p in enumerate(pages) for l in p[2] if l["text"] == text]


# --- the page and the positions ---------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def lamp_pages(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("lamp")
    return render(FIXTURE.read_text(encoding="utf-8"), tmp)


def test_us_letter_and_12_point_courier_prime(lamp_pages):
    for w, h, lines in lamp_pages:
        assert (round(w), round(h)) == (612, 792)
        assert all(l["size"] == pytest.approx(12, abs=0.01) and "CourierPrime" in l["font"] for l in lines)


def test_margins_and_element_positions(lamp_pages):
    xs = defaultdict(set)
    for page in lamp_pages:
        for l in body(page):
            t = l["text"]
            if t.startswith(("INT.", "EXT.")):
                xs["heading"].add(round(l["x0"], 2))
            elif t in ("BRAM", "MARA", "ESTATE AGENT", "MARA (V.O.)", "VOICE (O.S.)", "MARA (CONT'D)") and 3 < l["x0"] < 4.5:
                xs["cue"].add(round(l["x0"], 2))
            elif t.startswith("(") and t.endswith(")") and l["x0"] > 2.9:
                xs["paren"].add(round(l["x0"], 2))
            elif t in ("CUT TO:", "DISSOLVE TO:", "FADE OUT."):
                xs["transition_end"].add(round(l["x1"], 2))
            elif t == "Hello?" or t == "Mum?" or t.startswith("Of course"):
                xs["dialogue"].add(round(l["x0"], 2))
    assert xs["heading"] == {1.5}
    assert all(abs(x - 3.7) <= TOL for x in xs["cue"]) and xs["cue"]
    assert all(abs(x - 3.1) <= TOL for x in xs["paren"]) and xs["paren"]
    assert all(abs(x - 2.5) <= TOL for x in xs["dialogue"]) and xs["dialogue"]
    assert all(abs(x - 7.5) <= TOL for x in xs["transition_end"]) and len(xs["transition_end"]) == 1


def test_action_and_dialogue_stay_inside_their_columns(lamp_pages):
    for page in lamp_pages:
        for l in body(page):
            assert l["x0"] >= 1.5 - TOL and l["x1"] <= 7.5 + TOL, l
            if abs(l["x0"] - 2.5) <= TOL:
                assert l["x1"] <= 6.0 + TOL, l                                     # dialogue: 2.5" to 6.0"


def test_page_numbers_top_right_from_page_two(lamp_pages):
    script = lamp_pages                                                     # (rendered without a title page)
    first = [l for l in script[0][2] if re.fullmatch(r"\d+\.", l["text"])]
    assert first == []
    for n, page in enumerate(script[1:], start=2):
        nums = [l for l in page[2] if re.fullmatch(r"\d+\.", l["text"])]
        assert [l["text"] for l in nums] == [f"{n}."]
        assert abs(nums[0]["x1"] - 7.5) <= TOL and abs(nums[0]["top"] - 0.5) <= 0.1


def test_the_body_starts_an_inch_down_and_holds_at_most_55_lines(lamp_pages):
    for page in lamp_pages:
        b = body(page)
        assert abs(b[0]["top"] - 1.0) <= 0.1
        assert (b[-1]["top"] - b[0]["top"]) * 6 + 1 <= 55 + 0.5


def test_dual_dialogue_sits_side_by_side(lamp_pages):
    rows = defaultdict(list)
    for i, p in enumerate(lamp_pages):
        for l in p[2]:
            rows[(i, round(l["top"], 2))].append(l)
    pairs = [sorted(v, key=lambda l: l["x0"]) for v in rows.values() if [l["text"] for l in sorted(v, key=lambda l: l["x0"])] == ["BRAM", "MARA"]]
    assert pairs and pairs[0][0]["x0"] < 4.0 < pairs[0][1]["x0"]


def test_centered_text_and_italic_lyrics(lamp_pages):
    (_, l), = find(lamp_pages, "THE NEXT MORNING")
    assert abs((l["x0"] + l["x1"]) / 2 - 4.5) <= 0.1
    lyric = [l for p in lamp_pages for l in p[2] if l["text"].startswith("Hush now")]
    assert lyric and "Italic" in lyric[0]["font"]


def test_a_page_break_starts_a_new_page(lamp_pages):
    (i, _), = find(lamp_pages, "THE NEXT MORNING")
    nxt = body(lamp_pages[i + 1])
    assert nxt[0]["text"] == "EXT. HOLLOWAY HOUSE - GARDEN - DAY"


# --- pagination ---------------------------------------------------------------------------------------------------------

FILL = " ".join(["word"] * 11)          # 54 characters: one printed line of action


def test_a_long_speech_breaks_with_more_and_contd(tmp_path):
    speech = " ".join(["Talking on and on about the house."] * 40)
    text = "INT. ROOM - DAY\n\n" + "\n".join([FILL] * 40) + "\n\nMARA (V.O.)\n(softly)\n" + speech + "\n"
    pages = render(text, tmp_path)
    p1, p2 = body(pages[0]), body(pages[1])
    assert p1[-1]["text"] == "(MORE)" and abs(p1[-1]["x0"] - 3.7) <= TOL
    assert abs(p1[-2]["x0"] - 2.5) <= TOL                                           # dialogue right above it
    assert p2[0]["text"] == "MARA (V.O.) (CONT'D)" and abs(p2[0]["x0"] - 3.7) <= TOL
    assert abs(p2[1]["x0"] - 2.5) <= TOL


def test_a_speech_never_breaks_after_its_cue_or_parenthetical(tmp_path):
    for fill in range(48, 55):
        text = "INT. ROOM - DAY\n\n" + "\n".join([FILL] * fill) + "\n\nMARA\n(softly)\n" + " ".join(["More words here."] * 30) + "\n"
        pages = render(text, tmp_path, f"f{fill}.pdf")
        for page in pages:
            b = body(page)
            assert b[-1]["text"] not in ("MARA", "(softly)"), fill
            if b[-1]["text"] == "(MORE)":
                assert abs(b[-2]["x0"] - 2.5) <= TOL


@pytest.mark.parametrize("fill", [49, 50, 51, 52, 53])
def test_a_scene_heading_is_never_alone_at_the_bottom_of_a_page(tmp_path, fill):
    text = "INT. ROOM - DAY\n\n" + "\n".join([FILL] * fill) + "\n\nEXT. YARD - NIGHT\n\nShe waits in the yard.\n"
    pages = render(text, tmp_path, f"h{fill}.pdf")
    for page in pages:
        assert not body(page)[-1]["text"].startswith(("INT.", "EXT."))
    (i, _), = find(pages, "EXT. YARD - NIGHT")
    assert any(l["text"] == "She waits in the yard." for l in pages[i][2])


def test_the_paginator_and_the_pdf_agree(tmp_path):
    text = FIXTURE.read_text(encoding="utf-8")
    pages = render(text, tmp_path)
    assert len(sp.paginate(text)) == len(pages)


# --- the title page -----------------------------------------------------------------------------------------------------------

@pytest.fixture
def lamp_story(home):
    settings.save_global({"author_name": "Andy Example", "address": "12 Example Road\nExampletown", "email": "andy@example.com", "phone": "555 0100"})
    u = vault.create_universe("Lamp", ["ghost story"])
    s = u.new_story("The Lamp in the Attic", {"structure": "Short Film"})
    s.script_path.parent.mkdir(parents=True, exist_ok=True)
    s.script_path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    return s


def test_the_title_page_from_settings(lamp_story):
    r = export.export(lamp_story, "pdf")
    title = pdf_pages(r["path"])[0][2]
    texts = [l["text"] for l in title]
    t = next(l for l in title if l["text"] == "The Lamp in the Attic")
    assert abs((t["x0"] + t["x1"]) / 2 - 4.25) <= 0.1 and 3.0 <= t["top"] <= 5.0
    assert texts[texts.index("The Lamp in the Attic") + 1] == "Written by" and "Andy Example" in texts
    contact = [l for l in title if l["text"] in ("12 Example Road", "Exampletown", "andy@example.com", "555 0100")]
    assert len(contact) == 4 and all(abs(l["x0"] - 1.5) <= TOL and l["top"] > 8.5 for l in contact)


def test_an_anonymous_script_has_no_name_or_contact(lamp_story):
    r = export.export(lamp_story, "pdf", anonymous=True)
    texts = [l["text"] for p in pdf_pages(r["path"]) for l in p[2]]
    assert "The Lamp in the Attic" in texts
    assert not any(t in texts for t in ("Andy Example", "Written by", "12 Example Road", "andy@example.com"))


def test_exports_go_to_the_manuscripts_folder_and_the_record(lamp_story):
    made = [export.export(lamp_story, f) for f in ("pdf", "fdx", "fountain")]
    folder = Path(made[0]["path"]).parent
    assert all(Path(m["path"]).parent == folder for m in made)
    assert ".storywheel" not in str(folder) and "library" not in str(folder)       # (the manuscripts folder, never inside the library)
    record = json.loads((folder / export.MANIFEST).read_text())
    formats = [e["format"] for e in record["exports"]]
    assert formats[-3:] == ["pdf", "fdx", "fountain"]
    assert export.last_export(lamp_story)["hash"] == export.content_hash(lamp_story)


def test_a_screenplay_asked_for_docx_gets_a_pdf(lamp_story):
    r = export.export(lamp_story, "docx")
    assert r["path"].endswith(".pdf") and r["format"] == "pdf" and "made a PDF" in r["warnings"][0]


def test_final_draft_file(lamp_story):
    r = export.export(lamp_story, "fdx")
    root = ET.parse(r["path"]).getroot()
    assert root.tag == "FinalDraft" and root.get("DocumentType") == "Script"
    types = [p.get("Type") for p in root.find("Content").iter("Paragraph")]
    assert types[0] == "Action" and "Scene Heading" in types and "Character" in types and "Parenthetical" in types and "Transition" in types
    assert root.find("Content").find("DualDialogue") is not None
    assert any(p.get("StartsNewPage") == "Yes" for p in root.find("Content").iter("Paragraph"))
    title = [t.text for t in root.find("TitlePage").iter("Text")]
    assert "The Lamp in the Attic" in title and "Andy Example" in title


def test_fountain_file_keeps_the_script_and_takes_the_title_page_from_settings(lamp_story):
    r = export.export(lamp_story, "fountain", anonymous=True)
    out = Path(r["path"]).read_text(encoding="utf-8")
    s = fountain.parse(out)
    assert s.title["title"] == ["The Lamp in the Attic"] and "author" not in s.title and "contact" not in s.title
    assert [e.type for e in s.elements] == [e.type for e in fountain.parse(FIXTURE.read_text(encoding="utf-8")).elements]
    r = export.export(lamp_story, "fountain")
    s = fountain.parse(Path(r["path"]).read_text(encoding="utf-8"))
    assert s.title["author"] == ["Andy Example"] and "andy@example.com" in s.title["contact"]


def test_the_exports_status_command_knows_scripts(lamp_story):
    from storywheel import cli_world
    export.export(lamp_story, "pdf")
    status = {d["story"]: d for d in cli_world.exports_status()}
    d = status[export.story_id(lamp_story)]
    assert d["state"] == "up to date" and d["default_format"] == "pdf" and d["last_export"]["format"] == "pdf"


def test_the_page_breaks_sample_shows_both_rules(tmp_path):
    """tests/fixtures/screenplay/page-breaks.fountain is the sample the owner opens: Edie's speech breaks across pages 1 and 2, and the
    last scene heading, which would land on the bottom line of page 2, starts page 3."""
    pages = render((FIXTURE.parent / "page-breaks.fountain").read_text(encoding="utf-8"), tmp_path)
    assert body(pages[0])[-1]["text"] == "(MORE)" and body(pages[1])[0]["text"] == "EDIE (CONT'D)"
    assert body(pages[2])[0]["text"] == "EXT. TOWN HALL - CONTINUOUS"
    assert body(pages[1])[-1]["top"] < 1.0 + 54 / 6 - 0.1                       # (page 2 ends early rather than strand the heading)
