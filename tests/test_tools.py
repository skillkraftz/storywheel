"""Every missing-tool message has one shape: what is missing, what needs it, and the exact command to fix it."""
import re

import pytest

from storywheel import dictionary, export, learn, tools, writer

PATTERN = re.compile(r"^.+ isn't installed\. [A-Z].+\. To fix it, run:  \S.*")


@pytest.mark.parametrize("name", list(tools.TOOLS))
def test_every_tool_message_has_the_shape(name):
    text = tools.missing(name)
    assert PATTERN.match(text), text
    assert tools.TOOLS[name][2] in text


def test_the_commands_are_the_exact_ones():
    assert "storywheel dictionary install" in tools.missing("dictionary")
    assert "pipx inject storywheel wordfreq" in tools.missing("wordfreq")
    assert "sudo apt install xclip" in tools.missing("clipboard")


def test_the_places_that_say_it_use_that_shape(home, monkeypatch, tmp_path):
    assert PATTERN.match(dictionary.NOT_INSTALLED) and "about 40 MB" in dictionary.NOT_INSTALLED
    assert PATTERN.match(learn.MISSING)
    monkeypatch.setattr(writer, "nvim_exe", lambda: None)
    assert PATTERN.match(writer.check())
    from storywheel import vault
    s = vault.create_universe("U").new_story("S")
    s.add_scene("A", "Hello there.")
    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(export.ExportError) as e:
        export.convert(tmp_path / "x.docx", "pdf")
    assert PATTERN.match(str(e.value)) and "The .docx was written." in str(e.value)
    monkeypatch.setenv("STORYWHEEL_NEOVIDE", "no-such-neovide")
    from storywheel import settings
    settings.save_story(s.path, {"neovide": True})
    note = writer.neovide_note(s)
    assert PATTERN.match(note.split("   Or ")[0]) and "Settings (F4)" in note


def test_the_writers_clipboard_messages_use_the_shape(home):
    from pathlib import Path
    lua = (Path(writer.__file__).parent / "nvim" / "lua" / "sw")
    for name in ("notepad.lua", "init.lua"):
        text = (lua / name).read_text()
        assert "isn't installed" in text and "To fix it, run:  sudo apt install xclip" in text
