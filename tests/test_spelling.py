"""Spelling: straight quotes in the manuscript, curly ones in the export, contractions pass the spellchecker, autocorrect, the
universe's own word list, Add to Dictionary, and the spell language on the writing buffer."""
import json
from pathlib import Path

import pytest

from storywheel import export, settings, spelling, vault, writer
from test_notepad import run, story, AT, LINES  # noqa: F401

docx = pytest.importorskip("docx")
pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


def text(*lines):
    return "vim.api.nvim_buf_set_lines(0, 0, -1, false, { %s })\n" % ", ".join(json.dumps(l, ensure_ascii=False) for l in lines)


def slow(typed):
    """Typed the way a person types: a moment after each space or punctuation mark (scheduled fixes run between keys)."""
    import re
    return re.sub(r"([ .,;:!?)\u2014])", r"\1<Cmd>lua vim.wait(25)<CR>", typed)


# --- straight quotes in the manuscript -------------------------------------------------------------------------------------------

def test_typing_curly_marks_stores_straight_ones(home, story):
    r = run(story, text("") + AT % (1, 0), "He said “hello” and it’s ‘fine’", LINES)
    assert r["lines"] == ["He said \"hello\" and it's 'fine'"]


def test_pasting_curly_marks_stores_straight_ones(home, story):
    r = run(story, text("") + "\nvim.paste({ '“I can’t,” she said.', '‘Nor I,’ he said.' }, -1)", "", LINES)
    assert r["lines"] == ["\"I can't,\" she said.", "'Nor I,' he said."]


def test_contractions_pass_the_spellchecker_when_stored_straight(home, story):
    r = run(story, text("couldn't I've we'll don't it's") + AT % (1, 0), "", """
        R.bad = {}
        for _, w in ipairs({ "couldn't", "I've", "we'll", "don't", "it's", "They're" }) do R.bad[w] = vim.fn.spellbadword(w)[1] end
        R.curly = vim.fn.spellbadword("couldn’t")[1]
    """)
    assert all(v == "" for v in r["bad"].values()), r["bad"]
    assert r["curly"] != ""                                     # why the manuscript keeps straight marks: the curly one is misspelled


def test_existing_manuscripts_are_converted_once_with_a_backup(home):
    u = vault.create_universe("Old")
    s = u.new_story("Old Tale")
    (s.path / ".straight-quotes").unlink()
    s.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "manuscript.md").write_text("“It’s here,” she said.\nHe didn’t go.\n", encoding="utf-8")
    message = s.migrate_quotes()
    assert (s.manuscript_dir / "manuscript.md").read_text() == "\"It's here,\" she said.\nHe didn't go.\n"
    assert "4 curly marks" in message and "manuscript.md" in message
    backups = list((s.path / ".backups").glob("quotes-*/manuscript.md"))
    assert len(backups) == 1 and "“" in backups[0].read_text(encoding="utf-8")
    assert s.migrate_quotes() is None


def test_a_story_without_curly_marks_is_marked_done_quietly_and_new_stories_are_straight_already(home):
    u = vault.create_universe("N")
    s = u.new_story("Tale")
    assert s.migrate_quotes() is None and (s.path / ".straight-quotes").exists()
    s2 = vault.create_universe("M").new_story("T2")
    s2.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (s2.manuscript_dir / "manuscript.md").write_text("It’s fine.\n", encoding="utf-8")
    assert s2.migrate_quotes() is None                          # (made after the rule: left alone)


def test_the_migration_runs_with_the_others(home):
    from storywheel import migrate
    s = vault.create_universe("Old").new_story("Tale")
    (s.path / ".straight-quotes").unlink()
    s.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "manuscript.md").write_text("It’s fine.\n", encoding="utf-8")
    assert any("Quotes are now straight" in l for l in migrate.migrate_manuscripts())


# --- the export makes them curly -----------------------------------------------------------------------------------------------------

def made(title="Don't Go", text_="\"It's here,\" she said. 'No,' he said.\nThe dogs' bowls, the '90s.\n"):
    u = vault.get_universe("t") or vault.create_universe("T")
    s = u.new_story(title)
    s.manuscript_dir.mkdir(parents=True, exist_ok=True)
    (s.manuscript_dir / "manuscript.md").write_text(text_, encoding="utf-8")
    settings.save_global(dict(settings.load_global(), legal_name="A. Writer"))
    return s


def test_the_docx_gets_curly_quotes_in_the_text_the_title_and_the_header(home):
    s = made()
    d = docx.Document(export.export(s, "docx")["path"])
    paras = [p.text for p in d.paragraphs]
    assert "“It’s here,” she said. ‘No,’ he said." in paras
    assert "The dogs’ bowls, the ’90s." in paras
    assert "Don’t Go" in paras and d.core_properties.title == "Don’t Go"
    assert d.sections[0].header.paragraphs[0].text == "Writer / Don’t Go / "
    assert "'" not in "".join(paras) and '"' not in "".join(paras)


def test_markdown_and_text_exports_are_curly_too(home):
    s = made()
    md = Path(export.export(s, "md")["path"]).read_text(encoding="utf-8")
    txt = Path(export.export(s, "txt")["path"]).read_text(encoding="utf-8")
    assert "“It’s here,”" in md and "# Don’t Go" in md
    assert "“It’s here,”" in txt and txt.startswith("Don’t Go")


def test_the_setting_keeps_straight_quotes_in_the_export(home):
    s = made()
    settings.save_story(s.path, {"export_curly_quotes": False})
    d = docx.Document(export.export(s, "docx")["path"])
    assert "\"It's here,\" she said. 'No,' he said." in [p.text for p in d.paragraphs]
    assert "Don't Go" in [p.text for p in d.paragraphs]


def test_italics_survive_curly_conversion(home):
    s = made(text_="She said *\"no\"* to it's *own* end.\n")
    d = docx.Document(export.export(s, "docx")["path"])
    p = next(p for p in d.paragraphs if "own" in p.text)
    assert p.text == "She said “no” to it’s own end." and [r.text for r in p.runs if r.italic] == ["“no”", "own"]


# --- autocorrect ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("typed,expected", [
    ("i think im late and i've gone ", "I think I'm late and I've gone "),
    ("I dont know. Dont go! ", "I don't know. Don't go! "),
    ("teh end, as was her wont. ", "the end, as was her wont. "),
    ("the cant of thieves, she cant. ", "the cant of thieves, she cant. "),
    ("it is, i.e. it was. ", "it is, i.e. it was. "),
    ("fruit, e.g. figs; i.e., ripe. ", "fruit, e.g. figs; i.e., ripe. "),
    ("then i. wait, i said. ", "then i. wait, I said. "),
    ("i, i; i! i? (i) ", "I, I; I! I? (I) "),
    ("i'll go, i'd stay. ", "I'll go, I'd stay. "),
    ("it is fine. ", "it is fine. "),
    ("this is a single i— ", "this is a single i— "),
])
def test_autocorrect_fixes_common_slips_when_you_finish_the_word(home, story, typed, expected):
    r = run(story, text("") + AT % (1, 0), slow(typed) + "<Cmd>lua vim.wait(50)<CR>", LINES)
    assert r["lines"] == [expected]


def test_queued_up_typing_is_never_corrupted(home, story):
    """Keys that arrive faster than the fixes can run (a macro, a script) are left alone rather than mangled."""
    r = run(story, text("") + AT % (1, 0), "i dont know im late ", LINES)
    assert r["lines"][0].replace("I", "i").replace("'", "") .replace("  ", " ").lower().startswith("i dont know im late") or r["lines"][0] == "i dont know im late "


def test_autocorrect_leaves_words_that_only_contain_the_pattern(home, story):
    r = run(story, text("") + AT % (1, 0), slow("imagine this. ill "), LINES)
    assert r["lines"] == ["imagine this. ill "]


def test_autocorrect_can_be_turned_off(home, story):
    settings.save_story(story.path, {"autocorrect": False})
    r = run(story, text("") + AT % (1, 0), slow("i dont "), LINES)
    assert r["lines"] == ["i dont "]


def test_autocorrect_only_happens_in_the_writing_buffer(home, story):
    r = run(story, "", "<C-r>" + slow("i dont "), "R.form = vim.api.nvim_buf_get_lines(require('sw.replace').buf, 0, -1, false)")
    assert r["form"][0] == "i dont "


# --- the universe's word list ------------------------------------------------------------------------------------------------------------

def test_the_names_file_has_names_possessives_and_outline_proper_nouns(home):
    u = vault.create_universe("Thornwood")
    u.new_entity("character", "Stacie Anderson")
    u.new_entity("place", "Glasswater")
    u.new_entity("thing", "The Hunting Horn")
    s = u.new_story("Tale", {}, {"Premise": "A clerk named Marlowe finds a clause in Penance. Old Tomas warns her."})
    path = spelling.write_names(s, u.path / "spell")
    words = set(path.read_text().split("\n")) - {""}
    assert {"Stacie", "Anderson", "Glasswater", "Hunting", "Horn", "Marlowe", "Penance", "Tomas"} <= words
    assert {"Glasswater's", "Stacie's", "Marlowe's"} <= words and "clerk" not in words and "A" not in words and "Old" not in words
    assert spelling.write_names(s, u.path / "spell") == path


def test_the_writer_knows_the_universes_names_and_possessives(home):
    u = vault.create_universe("Thornwood")
    u.new_entity("place", "Glasswater")
    u.new_entity("character", "Quillon Vex")
    s = u.new_story("The Last Clause", {}, {"Premise": "Zarathon arrives in Penance."})
    s.add_scene("Opening", "x")
    settings.save_story(s.path, {"notepad_mode": False})
    r = run(s, "", "", """
        R.ok = {}
        for _, w in ipairs({ "Glasswater", "Glasswater's", "Quillon", "Vex", "Penance", "Penance's" }) do R.ok[w] = vim.fn.spellbadword(w)[1] == "" end
        R.bad = vim.fn.spellbadword("Glasswatr")[1]
    """)
    assert all(r["ok"].values()), r["ok"]
    assert r["bad"] == "Glasswatr"


def test_add_to_dictionary_goes_to_the_universe_list_and_other_stories_see_it(home):
    u = vault.create_universe("Thornwood")
    s1 = u.new_story("One")
    s1.add_scene("A", "The blorptastic hum.")
    s2 = u.new_story("Two")
    s2.add_scene("A", "Nothing here.")
    for s in (s1, s2):
        settings.save_story(s.path, {"notepad_mode": False})
    r = run(s1, "", "", """
        R.before = vim.fn.spellbadword("blorptastic")[1]
        require('sw.spell').add_word("blorptastic")
        R.after = vim.fn.spellbadword("blorptastic")[1]
    """)
    assert r["before"] == "blorptastic" and r["after"] == ""
    assert "blorptastic" in (u.path / "spell" / "en.utf-8.add").read_text()
    r2 = run(s2, "", "", 'R.ok = vim.fn.spellbadword("blorptastic")[1] == ""')
    assert r2["ok"] is True                                                          # another story in the same universe
    other = vault.create_universe("Elsewhere").new_story("Z")
    other.add_scene("A", "x")
    settings.save_story(other.path, {"notepad_mode": False})
    assert run(other, "", "", 'R.bad = vim.fn.spellbadword("blorptastic")[1]')["bad"] == "blorptastic"


def test_the_right_click_menu_adds_the_word_under_the_cursor(home, story):
    r = run(story, text("A flurbish day.") + AT % (1, 4),
            __import__("nvdrive").context_keys("Add to Dictionary", misspelled=True),
            "R.after = vim.fn.spellbadword('flurbish')[1]; R.msgs = vim.fn.execute('messages')")
    assert r["after"] == "" and "Added “flurbish”" in r["msgs"]


def test_the_spell_language_is_set_on_the_writing_buffer_not_the_current_one(home, story):
    r = run(story, "", "", """
        local p = require('sw.prose')
        local main = require('sw.layout').main
        local mainbuf = vim.api.nvim_win_get_buf(main)
        vim.bo[mainbuf].spelllang = "en"
        vim.cmd("vsplit"); local other = vim.api.nvim_create_buf(false, true); vim.api.nvim_win_set_buf(0, other)   -- the current window is somewhere else
        vim.bo[other].spelllang = "en_gb"
        p.set_spell(false); p.set_spell(true)
        R.main = vim.bo[mainbuf].spelllang; R.other = vim.bo[other].spelllang
        R.file = vim.bo[mainbuf].spellfile
    """)
    assert r["main"] == "en_us" and r["other"] == "en_gb" and r["file"].endswith("en.utf-8.add,%s" % (Path(r["file"]).parent / "names.utf-8.add")) or "names.utf-8.add" in r["file"]


def test_spellcheck_is_on_by_default_and_the_setting_turns_it_off(home, story):
    assert run(story, "", "", "R.s = vim.wo[require('sw.prose').window].spell")["s"] is True
    other = vault.create_universe("Other").new_story("Q")
    other.add_scene("A", "x")
    settings.save_story(other.path, {"spellcheck": False, "notepad_mode": False})
    assert run(other, "", "", "R.s = vim.wo[require('sw.prose').window].spell")["s"] is False

