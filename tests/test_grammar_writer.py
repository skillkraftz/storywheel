"""Grammar in the Writer, against a fake LanguageTool server: what is sent, where the underlines land, fixes, ignoring, failures."""
import json
import socket
import sys
from pathlib import Path

import pytest

from storywheel import grammar, settings, vault
from test_writer import run_lua, story  # noqa: F401

FAKE = Path(__file__).resolve().parent / "fake_lt.py"

SETUP = """
local g = require("sw.grammar")
local function wait_idle()
  vim.wait(20000, function() return g.state ~= "starting" and #g.queue == 0 and not g.busy end, 25)
end
local function enable()
  vim.api.nvim_buf_set_lines(g.buf(), 0, -1, false, { "" })          -- (start from an empty page: the story's own text is not under test)
  g.set(true, true)
  vim.wait(30000, function() return g.state ~= "starting" end, 25)
end
local function set_lines(lines)
  vim.api.nvim_buf_set_lines(g.buf(), 0, -1, false, lines)
end
"""


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def lt(home, story, monkeypatch, tmp_path):
    port = free_port()
    settings.save_global({"grammar_port": port, "grammar_pause_ms": 100})
    log = tmp_path / "lt.log"
    env = {"STORYWHEEL_LT_CMD": f"{sys.executable} {FAKE} {{port}}", "FAKE_LT_LOG": str(log)}
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    yield {"env": env, "log": log, "port": port}
    grammar.stop()


def requests(log):
    return [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []


def run(story, body, env=None):
    return run_lua(story, SETUP + body, env_extra=env)


def test_off_by_default_nothing_runs(lt, story):
    r = run(story, 'R.enabled, R.state = g.enabled, g.state; R.line = require("sw.stats").line()')
    assert r["enabled"] is False and r["state"] == "off" and "grammar" not in r["line"]
    assert not grammar.running() and not grammar.pid_path().exists() and requests(lt["log"]) == []


def test_strip_keeps_offsets_right_with_italics_quotes_and_emoji(story, home):
    plain_expected = 'She said "alot" and 😀 really alot.'
    first_offset = plain_expected.find("alot")
    second_char = plain_expected.rfind("alot")
    second_offset = len(plain_expected[:second_char].encode("utf-16-le")) // 2          # the emoji is two UTF-16 units
    r = run_lua(story, """
        local g = require("sw.grammar")
        local line = 'She said "*alot*" and 😀 *really* alot.'
        local plain, start, stop, units = g.strip(line)
        R.plain, R.units, R.line = plain, units, line
        local function raw(o) return { { offset = o, length = 4, message = "m", rule = { id = "ALOT", category = { id = "GRAMMAR" } }, replacements = { { value = "a lot" } } } } end
        R.first = g.map_matches(line, raw(%d), start, stop, units)
        R.second = g.map_matches(line, raw(%d), start, stop, units)
        R.bad = g.map_matches(line, raw(%d), start, stop, units)
    """ % (first_offset, second_offset, 200))
    assert r["plain"] == plain_expected
    line = r["line"].encode()
    first, second = r["first"][0], r["second"][0]
    assert line[first["scol"]:first["ecol"]].decode() == "alot" and first["replacements"] == ["a lot"]
    assert line[second["scol"]:second["ecol"]].decode() == "alot" and second["scol"] > first["ecol"]
    assert r["units"] == len(plain_expected) + 1                                                # (UTF-16: the emoji counts twice)
    assert r["bad"] == []                                                                       # (an offset past the end is dropped, not trusted)


def test_underlines_land_on_the_right_letters_and_only_prose_is_sent(lt, story):
    r = run(story, """
        enable()
        set_lines({ 'She said "*alot*" and left.', "* * *", "", "A *very* long road, alot of dust.", "Nothing wrong here at all." })
        g.scan(); wait_idle()
        local buf = g.buf()
        R.state = g.state
        R.marks = {}
        for _, m in ipairs(vim.api.nvim_buf_get_extmarks(buf, g.ns, 0, -1, { details = true })) do
          local line = vim.api.nvim_buf_get_lines(buf, m[2], m[2] + 1, false)[1]
          R.marks[#R.marks + 1] = { m[2] + 1, line:sub(m[3] + 1, m[4].end_col), m[4].hl_group }
        end
        R.status = g.status_text()
        R.count = g.count()
    """, lt["env"])
    assert r["state"] == "ready"
    assert r["marks"] == [[1, "alot", "SwGrammar"], [4, "alot", "SwGrammar"]]
    assert r["status"] == "grammar: 2 problems" and r["count"] == 2
    sent = [q["text"] for q in requests(lt["log"])]
    assert sorted(sent) == sorted(['She said "alot" and left.', "A very long road, alot of dust.", "Nothing wrong here at all."])      # no markup, no scene break
    assert "*" not in "".join(sent)


def test_picky_categories_and_rules_are_switched_off_on_the_server_side(lt, story):
    r = run(story, """
        enable()
        set_lines({ "teh dog was very big, alot." })
        g.scan(); wait_idle()
        R.rules = vim.tbl_map(function(m) return m.rule end, g.all())
    """, lt["env"])
    assert r["rules"] == ["ALOT"]                                       # TYPOS (teh) and STYLE (very) are off by default
    q = requests(lt["log"])[0]
    assert "STYLE" in q["cats"] and "TYPOS" in q["cats"] and "GRAMMAR" not in q["cats"]
    settings.save_global({"grammar_cat_style": True})
    r = run(story, """
        enable()
        set_lines({ "teh dog was very big, alot." })
        g.scan(); wait_idle()
        R.rules = vim.tbl_map(function(m) return m.rule end, g.all())
    """, lt["env"])
    assert r["rules"] == ["VERY_STYLE", "ALOT"]


def test_only_changed_paragraphs_are_checked_again_and_results_are_remembered_between_runs(lt, story):
    lines = '{ "One alot of text.", "Two is fine.", "Three is fine too." }'
    run(story, f"enable(); set_lines({lines}); g.scan(); wait_idle()", lt["env"])
    assert len(requests(lt["log"])) == 3
    assert json.loads((story.path / ".grammar-cache.json").read_text())["found"]
    lt["log"].unlink()
    r = run(story, f"""
        enable(); set_lines({lines}); g.scan(); wait_idle()
        R.same = #g.all()
        set_lines({{ "One alot of text.", "Two is changed alot.", "Three is fine too." }})
        g.scan(); wait_idle()
        R.after = #g.all()
    """, lt["env"])
    sent = [q["text"] for q in requests(lt["log"])]
    assert sent == ["Two is changed alot."]                              # the first run's answers came from the cache
    assert r["same"] == 1 and r["after"] == 2


def test_a_typing_pause_triggers_the_check_by_itself(lt, story):
    r = run(story, """
        enable()
        set_lines({ "Start." })
        vim.api.nvim_win_set_cursor(0, { 1, 0 })
        vim.api.nvim_buf_set_lines(g.buf(), 0, -1, false, { "He did it alot." })
        g.touch()
        vim.wait(10000, function() return #g.all() > 0 end, 25)
        R.n = #g.all()
    """, lt["env"])
    assert r["n"] == 1


def test_applying_a_fix_changes_the_text_and_the_problem_goes_after_a_recheck(lt, story):
    r = run(story, """
        enable()
        set_lines({ "He ate alot of *pie* today." })
        g.scan(); wait_idle()
        local m = g.problem_at(1, 8)
        R.found = m and m.rule
        R.reps = m and m.replacements
        g.apply(m, m.replacements[1])
        R.text = vim.api.nvim_buf_get_lines(g.buf(), 0, 1, false)[1]
        g.scan(); wait_idle()
        R.left = #g.all()
    """, lt["env"])
    assert r["found"] == "ALOT" and r["reps"] == ["a lot", "allot"]
    assert r["text"] == "He ate a lot of *pie* today." and r["left"] == 0


def test_the_menu_offers_the_message_the_fixes_ignore_and_turn_off(lt, story):
    r = run(story, """
        enable()
        set_lines({ "He ate alot today." })
        g.scan(); wait_idle()
        vim.api.nvim_win_set_cursor(0, { 1, 8 })
        g.menu(g.problem_at(1, 8))
        local m = g.last_menu
        R.lines = m.lines
        R.labels = vim.tbl_map(function(i) return i.label end, m.items)
        R.float = vim.api.nvim_win_get_config(m.win).relative
        m.items[1].run()
        R.text = vim.api.nvim_buf_get_lines(g.buf(), 0, 1, false)[1]
    """, lt["env"])
    assert "'alot' is not a word" in r["lines"][0]
    assert r["labels"] == ["Replace with “a lot”", "Replace with “allot”", "Ignore this one", "Turn off this rule (ALOT)", "Close"]
    assert r["text"] == "He ate a lot today." and r["float"] in ("cursor", "win")


def test_ignore_this_one_is_remembered_for_the_story_only(lt, story):
    r = run(story, """
        enable()
        set_lines({ "He ate alot today.", "She ate alot too." })
        g.scan(); wait_idle()
        R.before = #g.all()
        g.ignore(g.all()[1])
        R.after = #g.all()
    """, lt["env"])
    assert r["before"] == 2 and r["after"] == 0                      # (the same rule and text: both go)
    assert grammar.ignored(story.path) == [{"rule": "ALOT", "text": "alot"}]
    other = vault.create_universe("Other").new_story("S2")
    other.add_scene("A", "x")
    assert grammar.ignored(other.path) == []
    r = run(story, 'enable(); set_lines({ "Again alot." }); g.scan(); wait_idle(); R.n = #g.all()', lt["env"])
    assert r["n"] == 0                                               # (still ignored in a later session)


def test_turning_off_a_rule_removes_it_now_and_is_saved_in_the_settings(lt, story):
    r = run(story, """
        enable()
        set_lines({ "He ate alot today." })
        g.scan(); wait_idle()
        g.turn_off_rule(g.all()[1])
        R.after = #g.all()
    """, lt["env"])
    assert r["after"] == 0
    assert settings.load_global()["grammar_off_rules"] == "ALOT"
    run(story, 'enable(); set_lines({ "He ate alot today." }); g.scan(); wait_idle()', lt["env"])
    assert "ALOT" in requests(lt["log"])[-1]["rules"]                # (and the server is told next time)


def test_next_problem_and_the_list_of_problems(lt, story):
    r = run(story, """
        enable()
        set_lines({ "Fine one.", "Bad alot here.", "Fine two.", "More alot, and another alot." })
        g.scan(); wait_idle()
        vim.api.nvim_win_set_cursor(0, { 1, 0 })
        g.next(); R.a = vim.api.nvim_win_get_cursor(0)
        g.next(); R.b = vim.api.nvim_win_get_cursor(0)
        g.next(); R.c = vim.api.nvim_win_get_cursor(0)
        g.next(); R.d = vim.api.nvim_win_get_cursor(0)
        g.next(); R.wrap = vim.api.nvim_win_get_cursor(0)
        g.list()
        R.list = g.last_list.lines
        vim.api.nvim_win_set_cursor(g.last_list.win, { 3, 0 })
        g.last_list.go()
        R.jumped = vim.api.nvim_win_get_cursor(0)
    """, lt["env"])
    assert [r[k][0] for k in "abcd"] == [2, 4, 4, 2] or [r[k][0] for k in "abc"] == [2, 4, 4]
    assert r["a"] == [2, 4] and r["b"] == [4, 5]
    assert len(r["list"]) == 3 and "line 2" in r["list"][0] and "“alot”" in r["list"][0] and "'alot' is not a word" in r["list"][0]
    assert r["jumped"][0] == 4


def test_the_status_line_shows_grammar_only_when_on(lt, story):
    r = run(story, """
        R.off = require("sw.stats").line()
        enable(); set_lines({ "Clean sentence here." }); g.scan(); wait_idle()
        R.on = require("sw.stats").line()
    """, lt["env"])
    assert "grammar" not in r["off"] and r["on"].endswith("grammar: no problems")


def test_turning_it_off_stops_the_server_and_leaving_the_writer_does_too(lt, story):
    r = run(story, """
        enable()
        R.up = require("sw.util").cli_json({ "grammar", "status", "--json" }).running
        g.set(false, true)
        R.down = require("sw.util").cli_json({ "grammar", "status", "--json" }).running
        R.state = g.state
    """, lt["env"])
    assert r["up"] is True and r["down"] is False and r["state"] == "off"
    run(story, "enable()", lt["env"])                                    # the Writer closes with the server running ...
    assert not grammar.running()                                         # ... and takes it down


def test_a_missing_server_is_a_plain_message_and_the_writer_carries_on(lt, story, monkeypatch):
    broken = {"STORYWHEEL_LT_CMD": f"{sys.executable} -c raise SystemExit(1)"}
    r = run(story, """
        enable()
        set_lines({ "He ate alot." })
        g.scan()
        R.state, R.status = g.state, g.status_text()
        R.typed = vim.api.nvim_buf_get_lines(g.buf(), 0, 1, false)[1]
    """, broken)
    assert r["state"] == "error" and r["status"].startswith("grammar: unavailable (") and "stopped right away" in r["status"] and r["typed"] == "He ate alot."


def test_a_slow_server_is_given_up_on_and_retried_later(lt, story):
    env = dict(lt["env"], FAKE_LT_DELAY="3")
    r = run(story, """
        g.timeout = 1
        enable()
        set_lines({ "He ate alot." })
        g.scan(); wait_idle()
        R.state, R.message = g.state, g.message
        R.status = g.status_text()
    """, env)
    assert r["state"] == "error" and "too slow" in r["message"] and "unavailable" in r["status"]


def test_nonsense_from_the_server_is_not_trusted(lt, story):
    env = dict(lt["env"], FAKE_LT_BROKEN="1")
    r = run(story, 'enable(); set_lines({ "He ate alot." }); g.scan(); wait_idle(); R.state, R.message = g.state, g.message; R.n = #g.all()', env)
    assert r["state"] == "error" and "not understood" in r["message"] and r["n"] == 0


def test_settings_changes_invalidate_the_remembered_answers(lt, story):
    run(story, 'enable(); set_lines({ "He ate alot." }); g.scan(); wait_idle()', lt["env"])
    lt["log"].unlink()
    settings.save_global({"grammar_cat_casing": False})
    run(story, 'enable(); set_lines({ "He ate alot." }); g.scan(); wait_idle()', lt["env"])
    assert len(requests(lt["log"])) == 1                              # (a different set of categories: asked again)


def test_the_keys_and_menu_entries_exist(story, home):
    r = run_lua(story, """
        local g = require("sw.grammar")
        R.maps = vim.tbl_map(function(m) return m.lhs end, vim.tbl_filter(function(m) return m.desc and m.desc:find("grammar") end, vim.api.nvim_get_keymap("n")))
        local labels = vim.tbl_map(function(i) return i[1] end, require("sw.menu").items())
        R.menu = vim.tbl_filter(function(l) return l:find("rammar") end, labels)
    """)
    assert sorted(r["maps"]) == ["<F10>", "<S-F10>"]
    assert r["menu"][0].startswith("Grammar check: turn on") and "Next grammar problem (F10)" in r["menu"] and "List of grammar problems (Shift+F10)" in r["menu"]


def test_right_click_on_a_problem_in_a_real_terminal_opens_the_grammar_menu(lt, home):
    """Real terminal bytes (an SGR mouse click) into a real Neovim, with the screen read back through a terminal emulator."""
    import fcntl
    import os
    import pty
    import select
    import struct
    import termios
    import time
    pyte = pytest.importorskip("pyte")
    u = vault.create_universe("Clicks")
    s = u.new_story("Clicks")
    s.add_scene("One", "He ate alot today.")
    settings.save_story(s.path, {"grammar": True, "spellcheck": False})
    from storywheel import writer
    root = Path(__file__).resolve().parent.parent
    argv, env = writer.command(s, s.path.parent / "return-g.txt")
    env.update({"PYTHONPATH": str(root), "TERM": "xterm-256color", "STORYWHEEL_INTERNAL_CLIPBOARD": "1"})
    env.update(lt["env"])
    screen = pyte.Screen(120, 36)
    stream = pyte.ByteStream(screen)
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe(argv[0], argv, env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 36, 120, 0, 0))

    def drain(seconds):
        end = time.time() + seconds
        while time.time() < end:
            if select.select([fd], [], [], 0.1)[0]:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    return
                if not chunk:
                    return
                stream.feed(chunk)

    def find(text):
        for y, row in enumerate(screen.display):
            x = row.find(text)
            if x >= 0:
                return y, x
        return None

    try:
        for _ in range(40):                                        # the server starts, the paragraph is checked
            drain(0.5)
            if find("grammar: 1 problem"):
                break
        assert find("grammar: 1 problem"), "\n".join(screen.display)
        y, x = find("He ate")                                         # (the emulator garbles the underline codes, so aim from the line's start)
        col = x + len("He ate ") + 2                                 # 1-based screen column inside "alot"
        os.write(fd, f"\x1b[<2;{col};{y + 1}M\x1b[<2;{col};{y + 1}m".encode())            # right button press and release
        drain(1.0)
        shown = "\n".join(screen.display)
        assert "Replace with “a lot”" in shown and "Ignore this one" in shown and "Turn off this rule (ALOT)" in shown, shown
        os.write(fd, b"1")                                          # choose the first fix
        drain(1.0)
        assert find("He ate a lot today."), "\n".join(screen.display)
        os.write(fd, b"\x1bOQ")                                     # F2: save and leave
        drain(2.0)
        os.waitpid(pid, 0)
    finally:
        grammar.stop()
    assert "He ate a lot today." in s.manuscript_path.read_text() if hasattr(s, "manuscript_path") else "He ate a lot today." in "".join(p.read_text() for p in s.scenes())
