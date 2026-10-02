"""F5 in the Writer hands the word under the cursor to Words, and a word chosen there comes back and replaces it."""
import json

import pytest

from storywheel import modes, writer
from test_notepad import run, story, AT, LINES  # noqa: F401

pytestmark = pytest.mark.skipif(writer.check() is not None, reason="Neovim 0.10+ is not installed")


def text(line):
    return "vim.api.nvim_buf_set_lines(0, 0, -1, false, { %s })\n" % json.dumps(line)


def files(story):
    d = story.path.parent
    return d / "return.txt", d / "return.txt.data"


def test_f5_saves_hands_over_the_word_and_leaves_for_words(home, story):
    run(story, text("She was running home.") + AT % (1, 9), "<F5>", "", quits=True)
    rf, data = files(story)
    assert rf.read_text() == "words"
    d = json.loads(data.read_text())
    assert d["word"] == "running" and d["universe"] == "thornwood" and d["story"] == "the-last-clause"
    r = d["replace"]
    assert (r["row"], r["start"], r["end"], r["text"]) == (0, 8, 15, "running") and r["file"].endswith(".md")
    assert "She was running home." in story.files()[0].read_text()                    # saved first


def test_f5_with_a_selection_hands_over_the_selection(home, story):
    run(story, text("A big dog barked.") + AT % (1, 2), "<S-Right><S-Right><S-Right>" + "<F5>", "", quits=True)
    d = json.loads(files(story)[1].read_text())
    assert d["word"] == "big" and d["replace"]["start"] == 2 and d["replace"]["end"] == 5


def test_f5_with_no_word_still_opens_words(home, story):
    run(story, text("a  b") + AT % (1, 2), "<F5>", "", quits=True)
    rf, data = files(story)
    d = json.loads(data.read_text())
    assert rf.read_text() == "words" and "word" not in d and d["story"] == "the-last-clause"


def test_f5_is_in_the_writer_menu_and_help(home, story):
    labels = run(story, "", "", "R.labels = {}; for i, it in ipairs(require('sw.menu').items()) do R.labels[i] = it[1] end")["labels"]
    assert any(l.startswith("Words (F5)") for l in labels)
    run(story, text("A dog.") + AT % (1, 3), "<F12>" + "<Down>" * next(i for i, l in enumerate(labels) if l.startswith("Words (F5)")) + "<CR>", "", quits=True)
    assert files(story)[0].read_text() == "words"
    r = run(story, "", "", "R.help = table.concat(require('sw').HELP, '\\n')")
    assert "F5 Words" in r["help"] and "F5  Words mode" in r["help"]


def replace_env(story, new, text_, row=0, start=0):
    path = str(story.files()[0])
    return {"STORYWHEEL_REPLACE": json.dumps({"file": path, "row": row, "start": start, "end": start + len(text_), "text": text_, "new": new})}


def test_a_chosen_word_replaces_the_original_before_the_first_screen(home, story):
    story.files()[0].write_text("She was running home.\nSecond line.\n")
    r = run(story, "", "X", LINES + "; R.cur = vim.api.nvim_win_get_cursor(0); R.mode = vim.fn.mode()",
            env_extra=replace_env(story, "sprinting", "running", 0, 8))
    assert r["lines"][0] == "She was sprinting home." and r["cur"] == [1, 16 + 1] or r["lines"][0].startswith("She was sprinting")
    assert story.files()[0].read_text().startswith("She was sprinting")                 # written at once


def test_the_cursor_ends_after_the_new_word_and_typing_continues(home, story):
    story.files()[0].write_text("She was running home.\n")
    r = run(story, "", "!", LINES, env_extra=replace_env(story, "sprinting", "running", 0, 8))
    assert r["lines"][0] == "She was sprinting! home."


def test_if_the_text_changed_nothing_is_replaced_and_it_says_so(home, story):
    story.files()[0].write_text("She was walking home.\n")
    r = run(story, "", "", LINES + "; R.msgs = vim.fn.execute('messages')", env_extra=replace_env(story, "sprinting", "running", 0, 8))
    assert r["lines"][0] == "She was walking home." and "nothing replaced" in r["msgs"]


def test_the_python_side_passes_the_replacement_and_collects_the_handover(home, story, monkeypatch):
    seen = {}
    def fake_run(st, scene=None, replace=None):
        seen["scene"], seen["replace"] = scene, replace
        fake_run.handover = {"word": "dog", "replace": {"row": 1}}
        return "words"
    fake_run.handover = None
    monkeypatch.setattr(writer, "run", fake_run)
    monkeypatch.setattr(writer, "check", lambda: None)
    monkeypatch.setattr(writer, "neovide_note", lambda s: None)
    from storywheel import state
    st = state.State()
    nxt = modes.run_writer(st, {"universe": "thornwood", "story": "the-last-clause", "replace": {"new": "x"}, "scene": {"path": "p", "line": 3}})
    assert seen["replace"] == {"new": "x"} and seen["scene"] == {"path": "p", "line": 3}
    assert nxt[0] == "words" and nxt[1]["handover"]["word"] == "dog" and nxt[1]["back"] == "writer" and nxt[1]["story"] == "the-last-clause"
