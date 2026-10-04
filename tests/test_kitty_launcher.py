"""`storywheel kitty`: storywheel in its own kitty window with kitty's normal spacing (the Writer's window has the writing settings)."""
from storywheel.cli import main as cli
from storywheel.cli_world import kitty_command, kitty_probe


def test_storywheels_own_window_keeps_normal_spacing(home):
    argv = kitty_command()
    assert argv[0] == "kitty" and argv[-1] == "storywheel" and "--class" in argv and "remember_window_size=no" in argv
    assert not any("modify_font" in a for a in argv) and not any(a.startswith("font_") for a in argv)           # kitty's own font and spacing


def test_a_font_and_size_are_used_only_when_given(home):
    argv = kitty_command("Iosevka", 20)
    assert "font_family=Iosevka" in argv and ("font_size=20.0" in argv or "font_size=20" in argv)
    assert not any("modify_font" in a for a in argv)


def test_there_is_no_line_height_option_any_more(home, capsys):
    import pytest
    with pytest.raises(SystemExit):
        cli(["kitty", "--line-height", "150", "--print"])


def test_print_shows_the_command_and_a_missing_kitty_says_how_to_fix_it(home, capsys, monkeypatch):
    cli(["kitty", "--font", "Iosevka Term", "--print"])
    out = capsys.readouterr().out
    assert '"font_family=Iosevka Term"' in out and "cell_height" not in out
    monkeypatch.setattr("shutil.which", lambda n: None)
    import pytest
    with pytest.raises(SystemExit) as e:
        cli(["kitty"])
    assert "kitty isn't installed" in str(e.value) and "sudo apt install kitty" in str(e.value)


def test_the_probe_reports_without_kitty(home, monkeypatch, capsys):
    monkeypatch.setattr("shutil.which", lambda n: None)
    assert "kitty isn't installed" in kitty_probe()[0]
    cli(["kitty", "--probe"])
    assert "kitty isn't installed" in capsys.readouterr().out


def test_the_probe_lists_the_remote_commands_a_kitty_knows(home, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda n: "/usr/bin/" + n)
    monkeypatch.setenv("KITTY_LISTEN_ON", "unix:/tmp/x")
    class R:
        def __init__(self, out):
            self.stdout = out
    def fake(argv):
        return R("kitty 0.40.1 created by Kovid Goyal" if "--version" in argv else "set-font-size set-spacing set-background-opacity launch resize-os-window")
    lines = kitty_probe(fake)
    assert lines[0].startswith("kitty 0.40.1")
    assert "  kitten @ set-font-size: yes" in lines and "  kitten @ load-config: no" in lines and "  kitten @ set-spacing: yes" in lines


def test_the_probe_says_how_to_switch_remote_control_on(home, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda n: "/usr/bin/" + n)
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)
    class R:
        stdout = "kitty 0.40.1"
    lines = kitty_probe(lambda argv: R())
    assert any("allow_remote_control=socket-only" in l for l in lines) and any("not switched on" in l for l in lines)
