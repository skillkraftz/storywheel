"""Settings > Keys: shortcut parsing, conflicts, saving, and the Writer using them."""
import asyncio

import pytest

from storywheel import keys, settings, settings_app, vault, writer
from test_notepad import run, story, AT, LINES  # noqa: F401


@pytest.mark.parametrize("text,expected", [("Alt+I", "<A-i>"), ("alt+i", "<A-i>"), ("<A-i>", "<A-i>"), ("ctrl+B", "<C-b>"), ("Ctrl+Alt+k", "<C-A-k>"),
                                           ("F9", "<F9>"), ("<f12>", "<F12>"), ("meta+s", "<A-s>"), ("Alt + J", "<A-j>")])
def test_keys_are_understood(text, expected):
    assert keys.normalize(text) == (True, expected)


@pytest.mark.parametrize("text", ["", "i", "Alt", "Alt+", "F13", "Hyper+x", "Alt+ab", "x y"])
def test_bad_keys_are_refused_with_a_message(text):
    ok, message = keys.normalize(text)
    assert not ok and message


def test_conflicts_are_found():
    current = dict(keys.DEFAULTS)
    assert keys.check("key_italic", "<A-b>", current)[0] is False and "bold" in keys.check("key_italic", "<A-b>", current)[1]
    assert keys.check("key_italic", "<C-c>", current) == (False, "Ctrl+C is already used for copy.")
    assert keys.check("key_italic", "<F2>", current)[0] is False
    assert keys.check("key_italic", "<A-i>", current)[0] is True                 # (its own current key is fine)
    assert keys.check("key_italic", "<A-z>", current)[0] is True


def test_labels():
    assert keys.label("<A-i>") == "Alt+I" and keys.label("<C-q>") == "Ctrl+Q" and keys.label("<F12>") == "F12" and keys.label("<C-A-k>") == "Ctrl+Alt+K"


def test_the_keys_tab_lists_every_shortcut_and_saves_valid_ones_only(home):
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            s = app.screen
            ids = [f"f-{k}" for k in keys.WRITER_KEYS]
            present = [bool(s.query(f"#{i}")) for i in ids]
            s.save_key("key_italic", "Alt+Z")
            ok1 = settings.load_global()["key_italic"]
            bad = s.save_key("key_bold", "Alt+Z")                       # taken by italic now
            msg = str(s.query_one("#status").content)
            bad2 = s.save_key("key_sidebar", "Ctrl+V")
            return present, ok1, bad, msg, bad2, settings.load_global()["key_bold"], settings.load_global()["key_sidebar"]
    present, ok1, bad, msg, bad2, bold, sidebar = asyncio.run(go())
    assert all(present) and ok1 == "<A-z>" and bad is False and "italic" in msg and bad2 is False
    assert bold == "<A-b>" and sidebar == "<F9>"


def test_the_writer_uses_the_configured_keys(home, story):
    settings.save_story(story.path, {"key_italic": "<A-z>", "key_scene_break": "<A-x>"})
    r = run(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'Hello' })\n" + AT % (1, 5), "<A-z>x<Esc><A-i>", LINES)
    assert r["lines"] == ["Hello*x*"]        # Alt+Z opened the italic pair and x went inside; the old Alt+I is no longer a shortcut and types nothing
    r = run(story, "vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'End.' })\n" + AT % (1, 0), "<A-x>", LINES)
    assert r["lines"] == ["End.", "***", ""]


def test_scene_marker_and_export_options_are_in_settings(home):
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            return [bool(app.screen.query(f"#f-{k}")) for k in ("scene_marker", "export_title_bold", "export_header", "export_anonymous", "export_one_space")]
    assert all(asyncio.run(go()))


def test_new_settings_reach_the_writer_through_the_story_settings(home):
    u = vault.create_universe("U")
    s = u.new_story("S")
    settings.save_global(dict(settings.load_global(), scene_marker="* * *", key_menu="<F10>"))
    st = settings.load_story(s.path)
    assert st["scene_marker"] == "* * *" and st["key_menu"] == "<F10>" and st["export_title_bold"] is True


def test_every_vim_space_action_has_a_notepad_key_and_none_clash():
    """Batch 20: each Space action of Vim mode has its own configurable key that works while typing; no two defaults are the same."""
    from storywheel import helpdoc
    for name in helpdoc.VIM_KEYS:
        assert name in keys.WRITER_KEYS or name in ("key_sidebar", "key_peek"), name
    values = [v[1] for v in keys.WRITER_KEYS.values()]
    assert len(values) == len(set(values)) and not set(values) & set(keys.RESERVED)
    assert keys.WRITER_KEYS["key_center"][1] == "<A-c>" and keys.WRITER_KEYS["key_center2"][1] == "<C-e>"
