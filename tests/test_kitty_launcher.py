from storywheel import settings
from storywheel.cli import main as cli
from storywheel.cli_world import kitty_command


def test_defaults_use_the_writer_settings(home):
    settings.save_global({"writer_font": "Courier Prime", "writer_font_size": 17})
    argv = kitty_command()
    assert argv[0] == "kitty" and argv[-1] == "storywheel"
    assert "font_family=Courier Prime" in argv and "font_size=17" in argv and "modify_font=cell_height 140%" in argv
    assert "--class" in argv and "remember_window_size=no" in argv


def test_flags_override(home):
    argv = kitty_command("Iosevka", 20, 160)
    assert "font_family=Iosevka" in argv and "font_size=20.0" in argv or "font_size=20" in argv
    assert "modify_font=cell_height 160%" in argv


def test_print_shows_the_command_and_a_missing_kitty_says_how_to_fix_it(home, capsys, monkeypatch):
    cli(["kitty", "--font", "Iosevka Term", "--line-height", "150", "--print"])
    out = capsys.readouterr().out
    assert '"font_family=Iosevka Term"' in out and "cell_height 150%" in out.replace('"', "")
    monkeypatch.setattr("shutil.which", lambda n: None)
    import pytest
    with pytest.raises(SystemExit) as e:
        cli(["kitty"])
    assert "kitty isn't installed" in str(e.value) and "sudo apt install kitty" in str(e.value)
