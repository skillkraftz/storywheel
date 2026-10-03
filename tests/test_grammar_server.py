"""Grammar: the local LanguageTool server (install, status, start and stop) and the settings that shape what is asked."""
import json
import os
import socket
import sys
import zipfile
from pathlib import Path

import pytest

from storywheel import grammar, settings, vault
from storywheel.cli import main as cli

FAKE = Path(__file__).resolve().parent / "fake_lt.py"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def fake(home, monkeypatch):
    port = free_port()
    settings.save_global({"grammar_port": port})
    monkeypatch.setenv("STORYWHEEL_LT_CMD", f"{sys.executable} {FAKE} {{port}}")
    yield port
    grammar.stop()


def make_zip(path, name="LanguageTool-6.6/languagetool-server.jar", extra=()):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(name, "jar")
        z.writestr("LanguageTool-6.6/libs/x.jar", "x")
        for n in extra:
            z.writestr(n, "bad")
    return path


# --- install ----------------------------------------------------------------------------------------------------------------------------------

def test_install_from_a_zip_unpacks_it_and_finds_the_version(home, tmp_path):
    z = make_zip(tmp_path / "LanguageTool-stable.zip")
    assert grammar.install(str(z)) == "6.6"
    assert grammar.server_jar().name == "languagetool-server.jar" and grammar.version() == "6.6"
    assert z.exists()                                                         # (a zip you copied is never removed)
    assert grammar.install(str(z)) == "6.6"                                    # (installing again replaces it cleanly)


def test_install_refuses_things_that_are_not_languagetool(home, tmp_path):
    with pytest.raises(grammar.GrammarError, match="There is no file"):
        grammar.install(str(tmp_path / "missing.zip"))
    (tmp_path / "x.zip").write_text("not a zip")
    with pytest.raises(grammar.GrammarError, match="not a zip"):
        grammar.install(str(tmp_path / "x.zip"))
    other = tmp_path / "o.zip"
    with zipfile.ZipFile(other, "w") as z:
        z.writestr("hello.txt", "hi")
    with pytest.raises(grammar.GrammarError, match="not LanguageTool"):
        grammar.install(str(other))
    evil = make_zip(tmp_path / "e.zip", extra=("../escape.txt",))
    with pytest.raises(grammar.GrammarError, match="outside its folder"):
        grammar.install(str(evil))
    assert not (tmp_path / "escape.txt").exists() and grammar.server_jar() is None


def test_a_download_that_fails_says_how_to_install_from_a_file(home, monkeypatch):
    def boom(*a, **k):
        raise OSError("no route")
    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(grammar.GrammarError, match="install --from LanguageTool-stable.zip"):
        grammar.install()
    assert not (home / "home" / "languagetool-download.zip").exists()


def test_the_command_line_installs_and_reports(home, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("STORYWHEEL_JAVA", "no-such-java")
    z = make_zip(tmp_path / "lt.zip")
    cli(["grammar", "install", "--from", str(z)])
    out = capsys.readouterr().out
    assert "LanguageTool 6.6 is installed" in out and "Java isn't installed" in out and "sudo apt install default-jre-headless" in out
    cli(["grammar", "status"])
    out = capsys.readouterr().out
    assert "version 6.6" in out and "Java: not found" in out and "not running" in out and "free rules, not the Premium rules" in out
    assert "Memory: wants about 762 MB (512 MB heap + Java)" in out
    cli(["grammar", "status", "--json"])
    st = json.loads(capsys.readouterr().out)
    assert st["installed"] and not st["java_ok"] and st["memory_limit_mb"] == 512 and st["version"] == "6.6"


def test_status_without_anything_installed_lists_each_missing_piece(home, monkeypatch):
    monkeypatch.setenv("STORYWHEEL_JAVA", "no-such-java")
    problems = " ".join(grammar.status()["problems"])
    assert "Java isn't installed" in problems and "LanguageTool isn't installed" in problems and "storywheel grammar install" in problems


def test_java_version_and_memory_are_read(home, tmp_path, monkeypatch):
    fake_java = tmp_path / "java"
    fake_java.write_text('#!/bin/sh\necho \'openjdk version "17.0.9" 2023-10-17\' >&2\n')
    fake_java.chmod(0o755)
    monkeypatch.setenv("STORYWHEEL_JAVA", str(fake_java))
    assert grammar.java_version() == 17
    fake_java.write_text('#!/bin/sh\necho \'java version "1.8.0_292"\' >&2\n')
    assert grammar.java_version() == 8
    st = grammar.status()
    assert any("too old" in p for p in st["problems"]) and not st["java_ok"]
    total, avail = grammar.memory_mb()
    assert total is None or total >= avail > 0


def test_low_memory_is_reported(home, monkeypatch):
    monkeypatch.setattr(grammar, "memory_mb", lambda: (1000, 300))
    assert any("Only 300 MB of memory is free" in p for p in grammar.status()["problems"])


# --- the server ----------------------------------------------------------------------------------------------------------------------------------

def test_start_runs_the_server_once_and_stop_ends_it(fake):
    assert not grammar.running()
    url = grammar.start(wait=20)
    assert url == f"http://127.0.0.1:{fake}" and grammar.running()
    assert grammar.start(wait=20) == url                                          # (already running: nothing new is started)
    assert grammar.stop() is True and not grammar.running()
    assert grammar.stop() is False


def test_cli_start_and_stop_speak_json(fake, capsys):
    cli(["grammar", "start", "--json"])
    assert json.loads(capsys.readouterr().out) == {"ok": True, "url": f"http://127.0.0.1:{fake}"}
    cli(["grammar", "stop", "--json"])
    assert json.loads(capsys.readouterr().out) == {"ok": True, "stopped": True}


def test_a_server_that_dies_at_once_is_reported(home, monkeypatch):
    settings.save_global({"grammar_port": free_port()})
    monkeypatch.setenv("STORYWHEEL_LT_CMD", f"{sys.executable} -c raise SystemExit(3)")
    with pytest.raises(grammar.GrammarError, match="stopped right away"):
        grammar.start(wait=10)


def test_starting_without_java_or_the_program_says_what_to_do(home, monkeypatch):
    monkeypatch.delenv("STORYWHEEL_LT_CMD", raising=False)
    with pytest.raises(grammar.GrammarError, match="LanguageTool isn't installed.*storywheel grammar install"):
        grammar.start()
    make_zip(home / "lt.zip")
    grammar.install(str(home / "lt.zip"))
    monkeypatch.setenv("STORYWHEEL_JAVA", "no-such-java")
    with pytest.raises(grammar.GrammarError, match="Java isn't installed"):
        grammar.start()


def test_the_real_command_line_has_the_memory_limit_and_port(home, tmp_path, monkeypatch):
    monkeypatch.delenv("STORYWHEEL_LT_CMD", raising=False)
    make_zip(tmp_path / "lt.zip")
    grammar.install(str(tmp_path / "lt.zip"))
    j = tmp_path / "java"
    j.write_text('#!/bin/sh\necho \'openjdk version "21.0.1"\' >&2\n')
    j.chmod(0o755)
    monkeypatch.setenv("STORYWHEEL_JAVA", str(j))
    settings.save_global({"grammar_memory_mb": 640, "grammar_port": 19999})
    cmd = grammar.server_command()
    assert cmd[0] == str(j) and "-Xmx640m" in cmd and cmd[-2:] == ["--port", "19999"] and "org.languagetool.server.HTTPServer" in cmd


# --- settings --------------------------------------------------------------------------------------------------------------------------------------

def test_picky_categories_start_off_and_the_others_on(home):
    c = grammar.config()
    off = set(c["disabledCategories"].split(","))
    assert {"STYLE", "REDUNDANCY", "PLAIN_ENGLISH", "COLLOQUIALISMS", "REPETITIONS_STYLE", "TYPOS", "TYPOGRAPHY"} <= off
    assert not off & {"GRAMMAR", "PUNCTUATION", "CASING", "CONFUSED_WORDS"}
    assert c["language"] == "en-US" and c["pause_ms"] == 1500 and c["memory_mb"] == 512


def test_switching_a_category_and_turning_off_rules(home, capsys):
    settings.save_global({"grammar_cat_style": True, "grammar_cat_casing": False})
    off = grammar.config()["disabledCategories"].split(",")
    assert "STYLE" not in off and "CASING" in off
    assert grammar.turn_off_rule("COMMA_X") == ["COMMA_X"]
    assert grammar.turn_off_rule("OTHER") == ["COMMA_X", "OTHER"] and grammar.turn_off_rule("COMMA_X") == ["COMMA_X", "OTHER"]
    assert grammar.config()["disabledRules"] == "COMMA_X,OTHER"
    cli(["grammar", "rule-off", "THIRD", "--json"])
    assert json.loads(capsys.readouterr().out)["rules"] == ["COMMA_X", "OTHER", "THIRD"]


def test_memory_and_port_are_machine_settings_the_rest_is_shared(home):
    settings.save_global({"grammar": True, "grammar_memory_mb": 300, "grammar_port": 12345})
    shared = (home / "home" / "settings.toml").read_text()
    local = (home / "home" / "settings.local.toml").read_text()
    assert "grammar = true" in shared and "grammar_memory_mb" not in shared and "grammar_memory_mb = 300" in local and "grammar_port = 12345" in local


def test_ignored_items_are_per_story(home, capsys):
    u = vault.create_universe("U")
    a, b = u.new_story("A"), u.new_story("B")
    grammar.ignore_path(a.path).write_text(json.dumps([{"rule": "ALOT", "text": "alot"}]))
    assert grammar.ignored(a.path) == [{"rule": "ALOT", "text": "alot"}] and grammar.ignored(b.path) == []
    cli(["grammar", "ignored", f"{u.slug}/{a.slug}"])
    assert "ALOT: alot" in capsys.readouterr().out
    cli(["grammar", "ignored", f"{u.slug}/{a.slug}", "--clear"])
    assert "Forgot 1 ignored item" in capsys.readouterr().out and grammar.ignored(a.path) == []


def test_the_settings_screen_has_a_grammar_tab(home):
    import asyncio
    from storywheel import settings_app
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            app.screen.query_one("#tabs").active = "t-grammar"
            await pilot.pause()
            ids = {w.id for w in app.screen.query("Switch") if w.id}
            text = str(app.screen.query_one("#grammar-tools").render())
            return ids, text
    ids, text = asyncio.run(go())
    assert {"f-grammar", "f-grammar_cat_style", "f-grammar_cat_grammar", "f-grammar_cat_typos"} <= ids
    assert "free rules, not the Premium rules" in text and "grammar-ignore.json" in text
