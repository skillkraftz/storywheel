"""Batch 23 B1: the optional LanguageTool n-gram data (a fake data dir and tests/fake_lt.py; the real 8 GB download is in the manual script)."""
import json
import os
import socket
import sys
import zipfile
from pathlib import Path

import pytest

from storywheel import grammar, settings
from storywheel.cli import main as cli

FAKE = Path(__file__).resolve().parent / "fake_lt.py"


def make_data(root):
    for d in ("1grams", "2grams", "3grams"):
        (Path(root) / "en" / d).mkdir(parents=True)
        (Path(root) / "en" / d / "data.bin").write_bytes(b"x" * 100)
    return Path(root)


def make_zip(path, prefix="en/", extra=()):
    with zipfile.ZipFile(path, "w") as z:
        for d in ("1grams", "2grams", "3grams"):
            z.writestr(f"{prefix}{d}/data.bin", "x" * 100)
        for n in extra:
            z.writestr(n, "bad")
    return path


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def plenty(monkeypatch):
    monkeypatch.setattr(grammar, "free_bytes", lambda p: 10 ** 15)


# --- the setting ------------------------------------------------------------------------------------------------------

def test_the_setting_lives_in_settings_local_toml_never_settings_toml(home, tmp_path):
    settings.save_global({"grammar_ngrams_dir": str(tmp_path / "ng"), "grammar": True})
    assert "grammar_ngrams_dir" in settings.local_path().read_text()
    assert "grammar_ngrams_dir" not in settings.global_path().read_text()
    assert settings.load_global()["grammar_ngrams_dir"] == str(tmp_path / "ng")


def test_the_root_is_the_folder_that_contains_en(home, tmp_path):
    data = make_data(tmp_path / "ng")
    settings.save_global({"grammar_ngrams_dir": str(data)})
    assert grammar.ngrams_root() == data
    settings.save_global({"grammar_ngrams_dir": str(data / "en")})              # (en itself was given: its parent is used)
    assert grammar.ngrams_root() == data
    settings.save_global({"grammar_ngrams_dir": str(tmp_path / "empty")})
    assert grammar.ngrams_root() is None
    settings.save_global({"grammar_ngrams_dir": ""})
    assert grammar.ngrams_root() is None and not grammar.ngrams_status()["configured"]


def test_a_set_but_unusable_folder_is_a_plain_problem_not_a_crash(home, tmp_path):
    settings.save_global({"grammar_ngrams_dir": str(tmp_path / "nothing-here")})
    st = grammar.ngrams_status()
    assert st["configured"] and not st["ok"] and "has no en/ folder" in st["problems"][0]
    assert any("grammar ngrams install" in p for p in grammar.status()["problems"])


# --- the server command and the categories ---------------------------------------------------------------------------------

def test_the_server_starts_with_the_language_model_when_the_data_is_set(home, tmp_path, monkeypatch):
    data = make_data(tmp_path / "ng")
    with zipfile.ZipFile(tmp_path / "lt.zip", "w") as z:
        z.writestr("LanguageTool-6.6/languagetool-server.jar", "jar")
    grammar.install(str(tmp_path / "lt.zip"))
    monkeypatch.setenv("STORYWHEEL_JAVA", sys.executable)
    monkeypatch.setattr(grammar, "java_version", lambda exe=None: 17)
    assert "--languageModel" not in grammar.server_command()
    settings.save_global({"grammar_ngrams_dir": str(data)})
    cmd = grammar.server_command()
    assert cmd[cmd.index("--languageModel") + 1] == str(data)


def test_no_category_setting_switches_off_the_confusion_rules_when_the_data_is_in_use(home, tmp_path):
    settings.save_global({"grammar_cat_confused": False})
    assert "CONFUSED_WORDS" in grammar.config()["disabledCategories"]            # (without the data the switch means what it says)
    settings.save_global({"grammar_ngrams_dir": str(make_data(tmp_path / "ng"))})
    cfg = grammar.config()
    assert "CONFUSED_WORDS" not in cfg["disabledCategories"] and cfg["ngrams"] == str(tmp_path / "ng")


def test_the_fake_server_is_started_with_the_model_and_still_answers(home, tmp_path, monkeypatch):
    data = make_data(tmp_path / "ng")
    args = tmp_path / "args.json"
    port = free_port()
    settings.save_global({"grammar_port": port, "grammar_ngrams_dir": str(data)})
    monkeypatch.setenv("STORYWHEEL_LT_CMD", f"{sys.executable} {FAKE} {{port}}")
    monkeypatch.setenv("FAKE_LT_ARGS", str(args))
    try:
        grammar.start(wait=20)
        assert json.loads(args.read_text()) == [str(port), "--languageModel", str(data)]
    finally:
        grammar.stop()


# --- install, status, remove ---------------------------------------------------------------------------------------------

def test_install_from_a_zip_unpacks_it_sets_the_setting_and_keeps_the_zip(home, tmp_path, plenty):
    z = make_zip(tmp_path / "ngram-en.zip")
    target = tmp_path / "disk" / "ng"
    assert grammar.ngrams_install(str(z), target) == target
    assert (target / "en" / "3grams" / "data.bin").exists() and z.exists()
    assert grammar.ngrams_root() == target and grammar.ngrams_status()["ok"]
    assert not (tmp_path / "disk" / "ng.new").exists()


def test_a_zip_with_the_data_inside_a_folder_works_too(home, tmp_path, plenty):
    z = make_zip(tmp_path / "n.zip", prefix="ngram-en-2015/en/")
    grammar.ngrams_install(str(z), tmp_path / "ng")
    assert grammar.ngrams_root() == tmp_path / "ng"


def test_install_refuses_what_is_not_the_data(home, tmp_path, plenty):
    with pytest.raises(grammar.GrammarError, match="There is no file"):
        grammar.ngrams_install(str(tmp_path / "missing.zip"), tmp_path / "ng")
    (tmp_path / "x.zip").write_text("not a zip")
    with pytest.raises(grammar.GrammarError, match="not a zip"):
        grammar.ngrams_install(str(tmp_path / "x.zip"), tmp_path / "ng")
    with zipfile.ZipFile(tmp_path / "other.zip", "w") as z:
        z.writestr("readme.txt", "hi")
    with pytest.raises(grammar.GrammarError, match="no en/ folder"):
        grammar.ngrams_install(str(tmp_path / "other.zip"), tmp_path / "ng")
    with zipfile.ZipFile(tmp_path / "half.zip", "w") as z:
        z.writestr("en/1grams/x", "x")
    with pytest.raises(grammar.GrammarError, match="no 1grams, 2grams and 3grams"):
        grammar.ngrams_install(str(tmp_path / "half.zip"), tmp_path / "ng")
    evil = make_zip(tmp_path / "evil.zip", extra=("en/../../escape.txt",))
    with pytest.raises(grammar.GrammarError, match="outside its folder"):
        grammar.ngrams_install(str(evil), tmp_path / "ng")
    assert not (tmp_path / "escape.txt").exists() and not (tmp_path / "ng").exists() and not (tmp_path / "ng.new").exists()
    assert grammar.ngrams_dir() is None                                             # (nothing was set)


def test_free_disk_space_is_checked_before_unpacking_and_before_downloading(home, tmp_path, monkeypatch):
    z = make_zip(tmp_path / "n.zip")
    monkeypatch.setattr(grammar, "free_bytes", lambda p: 10)
    with pytest.raises(grammar.GrammarError, match="Not enough free disk space for unpacking"):
        grammar.ngrams_install(str(z), tmp_path / "ng")
    assert not (tmp_path / "ng").exists()
    called = []
    from storywheel import download
    monkeypatch.setattr(download, "fetch", lambda *a, **k: called.append(a))
    with pytest.raises(grammar.GrammarError, match="Not enough free disk space for the n-gram download.*GB"):
        grammar.ngrams_install(None, tmp_path / "ng")
    assert called == []                                                             # (nothing was downloaded)


def test_the_download_goes_through_download_py_only_on_this_explicit_call(home, tmp_path, plenty, monkeypatch):
    from storywheel import download
    seen = {}

    def fake_fetch(url, dest, progress=lambda m: None, timeout=60):
        seen["url"] = url
        make_zip(dest)
        return dest
    monkeypatch.setattr(download, "fetch", fake_fetch)
    grammar.ngrams_install(None, tmp_path / "ng")
    assert seen["url"] == grammar.NGRAMS_URL and grammar.ngrams_status()["ok"]
    assert not list(tmp_path.glob("*download.zip"))                                 # (the zip is removed once unpacked)
    assert not list(tmp_path.glob("*-download.zip"))


def test_a_failed_download_names_the_by_hand_way_and_leaves_nothing(home, tmp_path, plenty, monkeypatch):
    from storywheel import download

    def boom(*a, **k):
        raise download.DownloadError("Couldn't download x: offline")
    monkeypatch.setattr(download, "fetch", boom)
    with pytest.raises(grammar.GrammarError, match="ngrams install --from ngram-en-20150817.zip"):
        grammar.ngrams_install(None, tmp_path / "ng")
    assert grammar.ngrams_dir() is None


def test_status_warns_about_an_sd_card_but_still_allows_it(home, tmp_path, monkeypatch):
    data = make_data(tmp_path / "ng")
    settings.save_global({"grammar_ngrams_dir": str(data)})
    mounts = tmp_path / "mounts"
    mounts.write_text(f"/dev/root / ext4 rw 0 0\n/dev/mmcblk0p2 {tmp_path} ext4 rw 0 0\n")
    monkeypatch.setattr(grammar, "PROC_MOUNTS", mounts)
    st = grammar.ngrams_status()
    assert st["ok"] and st["in_use"] and st["sd_card"] and st["device"] == "/dev/mmcblk0p2"
    assert "SD card" in st["problems"][0] and "SSD" in st["problems"][0]
    assert grammar.config()["ngrams"] == str(data)                                  # (still used)
    mounts.write_text(f"/dev/nvme0n1p2 {tmp_path} ext4 rw 0 0\n")
    assert not grammar.ngrams_status()["sd_card"] and grammar.ngrams_status()["problems"] == []


def test_remove_deletes_only_en_and_clears_the_setting(home, tmp_path):
    data = make_data(tmp_path / "ng")
    (data / "mine.txt").write_text("keep")
    settings.save_global({"grammar_ngrams_dir": str(data)})
    assert grammar.ngrams_remove() == 300
    assert not (data / "en").exists() and (data / "mine.txt").exists()
    assert grammar.ngrams_dir() is None
    empty = make_data(tmp_path / "ng2")
    settings.save_global({"grammar_ngrams_dir": str(empty)})
    grammar.ngrams_remove()
    assert not empty.exists()                                                       # (nothing else was in it)


def test_install_over_an_existing_copy_replaces_only_en(home, tmp_path, plenty):
    target = make_data(tmp_path / "ng")
    (target / "mine.txt").write_text("keep")
    grammar.ngrams_install(str(make_zip(tmp_path / "n.zip")), target)
    assert (target / "mine.txt").exists() and grammar.ngrams_status()["ok"]


# --- the command line --------------------------------------------------------------------------------------------------------

def test_cli_install_status_and_remove(home, tmp_path, plenty, capsys):
    z = make_zip(tmp_path / "n.zip")
    cli(["grammar", "ngrams", "status"])
    assert "No n-gram data is set" in capsys.readouterr().out
    cli(["grammar", "ngrams", "install", "--from", str(z), "--dir", str(tmp_path / "ng")])
    out = capsys.readouterr().out
    assert "is installed" in out and "their/there" in out
    cli(["grammar", "ngrams", "status", "--json"])
    st = json.loads(capsys.readouterr().out)
    assert st["ok"] and st["root"] == str(tmp_path / "ng")
    cli(["grammar", "status"])
    assert "N-gram data: in use" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli(["grammar", "ngrams", "remove"])                                        # (not on a terminal: it asks for --yes)
    assert (tmp_path / "ng" / "en").exists()
    cli(["grammar", "ngrams", "remove", "--yes"])
    assert "Removed" in capsys.readouterr().out and not (tmp_path / "ng").exists()


def test_cli_install_reports_errors_plainly(home, tmp_path, plenty, capsys):
    with pytest.raises(SystemExit):
        cli(["grammar", "ngrams", "install", "--from", str(tmp_path / "nope.zip")])
    assert "There is no file" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli(["grammar", "ngrams"])


def test_the_settings_screen_lists_the_folder_and_what_it_adds(home, tmp_path):
    from storywheel import settings_app
    assert "grammar_ngrams_dir" in [f[0] for sec in settings_app.SECTIONS for f in sec[1]]
    assert "grammar_ngrams_dir" in settings.LOCAL_KEYS
    assert "their/there" in grammar.NGRAMS_WHAT and "n-gram" in grammar.HELP_NOTE and "SSD" in grammar.HELP_NOTE
