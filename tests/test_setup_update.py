"""storywheel setup (a questionnaire that remembers) and storywheel update (git pull, reinstall only on a new version)."""
import subprocess
import sys
from pathlib import Path

import pytest

from storywheel import __version__, paths, settings, setup_wizard, update
from storywheel.cli import main as cli


class Answers:
    def __init__(self, *answers):
        self.answers, self.asked = list(answers), []

    def __call__(self, prompt):
        self.asked.append(prompt)
        return self.answers.pop(0) if self.answers else ""


def run_setup(answers, again=False, defaults=False):
    said = []
    ask = Answers(*answers)
    done = setup_wizard.run(ask, said.append, again=again, defaults=defaults)
    return done, said, ask


@pytest.fixture(autouse=True)
def no_dictionary(monkeypatch, tmp_path):
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(tmp_path / "none.sqlite"))
    from storywheel import dictionary
    dictionary.forget()
    monkeypatch.setattr("shutil.which", lambda name: None)


def test_setup_asks_everything_once_and_stores_the_answers(home, tmp_path):
    lib, man = tmp_path / "L", tmp_path / "M"
    done, said, ask = run_setup(["Andy W", "Andrew Writer", "1 Main St / Town ST", "a@b.c", "555", str(lib), str(man),
                                 "y", "n", "n", ""])
    assert done == list(setup_wizard.QUESTIONS)
    g = settings.load_global()
    assert (g["author_name"], g["legal_name"], g["email"], g["phone"]) == ("Andy W", "Andrew Writer", "a@b.c", "555")
    assert g["address"] == "1 Main St\nTown ST"
    assert g["library"] == str(lib) and g["manuscripts_dir"] == str(man) and lib.is_dir() and man.is_dir()
    assert g["neovide"] is False and g["transparent_background"] is True
    assert set(g["setup_done"]) == set(setup_wizard.QUESTIONS)
    assert any("Neovide" in s and "To fix it" in s for s in said)                       # (not installed: said plainly, optional)
    assert any("Skipped" in s and "storywheel dictionary install" in s for s in said)


def test_running_it_again_asks_nothing_and_a_new_question_only_asks_that_one(home):
    run_setup([], defaults=True)
    done, said, ask = run_setup([])
    assert done == [] and ask.asked == [] and any("already done" in s for s in said)
    settings.save_global({"setup_done": ["author", "folders", "window", "transparent", "dictionary"]})      # (an older setup: "update" is new)
    done, said, ask = run_setup(["origin-url"])
    assert done == ["update"] and len(ask.asked) == 1
    assert settings.load_global()["update_remote"] == "origin-url"


def test_again_asks_every_question_with_the_current_answers_as_defaults(home):
    run_setup(["Ada", "Ada V", "", "ada@x.y", ""] + [""] * 12, defaults=False)
    done, said, ask = run_setup([""] * 14, again=True)
    assert done == list(setup_wizard.QUESTIONS)
    assert settings.load_global()["email"] == "ada@x.y" and any("[ada@x.y]" in a for a in ask.asked)


def test_defaults_mode_asks_nothing(home):
    done, said, ask = run_setup([], defaults=True)
    assert ask.asked == [] and done == list(setup_wizard.QUESTIONS)


def test_the_command(home, capsys):
    cli(["setup", "--defaults"])
    out = capsys.readouterr().out
    assert "6 question(s)" in out and "Done." in out
    cli(["setup"])
    assert "already done" in capsys.readouterr().out


# --- update ---------------------------------------------------------------------------------------------------------------------------------

def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def remote_and_clone(tmp_path):
    """A 'remote' repo with storywheel's package files, and a clone of it that update() works on."""
    origin = tmp_path / "origin"
    (origin / "storywheel").mkdir(parents=True)
    (origin / "storywheel" / "__init__.py").write_text(f'__version__ = "{__version__}"\n')
    (origin / "CHANGELOG.md").write_text(f"# Changelog\n\n## {__version__} — now\n- start\n")
    git(tmp_path, "init", "-q", "-b", "main", str(origin))
    git(origin, "config", "user.email", "t@t")
    git(origin, "config", "user.name", "t")
    git(origin, "add", "-A")
    git(origin, "commit", "-q", "-m", "first")
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
    git(clone, "config", "user.email", "t@t")
    git(clone, "config", "user.name", "t")
    return origin, clone


def commit(origin, text, version=None, note=""):
    if version:
        (origin / "storywheel" / "__init__.py").write_text(f'__version__ = "{version}"\n')
        old = (origin / "CHANGELOG.md").read_text()
        (origin / "CHANGELOG.md").write_text(old.replace("# Changelog\n", f"# Changelog\n\n## {version} — new\n- {note}\n", 1))
    (origin / "note.txt").write_text(text)
    git(origin, "add", "-A")
    git(origin, "commit", "-q", "-m", text)


class FakeRun:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="  Migrations and rebuilds are done.\n", stderr="")


@pytest.fixture
def at(monkeypatch, remote_and_clone):
    origin, clone = remote_and_clone
    monkeypatch.setattr(update, "checkout_dir", lambda: clone)
    return origin, clone


def test_already_up_to_date(home, at):
    said = []
    assert update.update(said.append, runner=FakeRun()) == "up-to-date"
    assert said == [f"Already up to date (storywheel {__version__})."]


def test_new_commits_without_a_new_version_pull_but_do_not_reinstall(home, at):
    origin, clone = at
    commit(origin, "tweak")
    said, run = [], FakeRun()
    assert update.update(said.append, runner=run) == "updated"
    text = "\n".join(said)
    assert "1 new change(s)" in text and "tweak" in text and "unchanged, so storywheel was not reinstalled" in text
    assert (clone / "note.txt").read_text() == "tweak"
    assert all("pipx" not in " ".join(map(str, c)) for c in run.calls) and "-m" in run.calls[-1] and "post-update" in run.calls[-1]


def test_a_new_version_on_an_editable_checkout_shows_the_changelog_and_does_not_reinstall(home, at):
    origin, clone = at
    commit(origin, "bigger", version="9.9.9", note="a brand new thing")
    said, run = [], FakeRun()
    update.update(said.append, runner=run)
    text = "\n".join(said)
    assert f"Version {__version__} -> 9.9.9" in text and "a brand new thing" in text and "already in use" in text
    assert not any("pipx" in " ".join(map(str, c)) for c in run.calls)


def test_a_new_version_of_a_plain_install_is_reinstalled_with_pipx(home, tmp_path, remote_and_clone, monkeypatch):
    origin, _ = remote_and_clone
    monkeypatch.setattr(update, "checkout_dir", lambda: None)
    settings.save_global({"update_remote": str(origin)})
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pipx" if name == "pipx" else None)
    update.update(lambda m: None, runner=FakeRun())                          # (the first run clones the remote: up to date)
    commit(origin, "bigger", version="9.9.9", note="x")
    run = FakeRun()
    said = []
    update.update(said.append, runner=run)
    assert any(c[:3] == ["/usr/bin/pipx", "install", "--force"] for c in run.calls)
    assert (paths.home() / "source" / ".git").exists() and any("Reinstalling" in s for s in said)


def test_check_only_reports_without_changing_anything(home, at):
    origin, clone = at
    commit(origin, "tweak")
    said = []
    assert update.update(said.append, check_only=True, runner=FakeRun()) == "available"
    assert not (clone / "note.txt").exists() and "tweak" in "\n".join(said)


def test_it_never_overwrites_local_work(home, at):
    origin, clone = at
    commit(origin, "theirs")
    (clone / "mine.txt").write_text("uncommitted")
    git(clone, "add", "mine.txt")
    with pytest.raises(update.UpdateError, match="not committed"):
        update.update(lambda m: None, runner=FakeRun())
    git(clone, "commit", "-q", "-m", "mine")
    with pytest.raises(update.UpdateError, match="both changed"):
        update.update(lambda m: None, runner=FakeRun())
    assert (clone / "mine.txt").exists() and not (clone / "note.txt").exists()


def test_no_remote_says_what_to_do(home, monkeypatch):
    monkeypatch.setattr(update, "checkout_dir", lambda: None)
    with pytest.raises(update.UpdateError, match="no git remote"):
        update.update(lambda m: None, runner=FakeRun())


def test_changelog_since_only_lists_newer_entries(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text("# C\n\n## 0.5.0 — a\n- five\n\n## 0.4.0 — b\n- four\n\n## 0.3.0 — c\n- three\n")
    text = update.changelog_since(tmp_path, "0.4.0")
    assert "five" in text and "four" not in text and "three" not in text
    assert update._key("0.10.0") > update._key("0.9.9")


def test_the_command_reports_errors_plainly(home, monkeypatch, capsys):
    monkeypatch.setattr(update, "checkout_dir", lambda: None)
    with pytest.raises(SystemExit):
        cli(["update"])
    assert "no git remote" in capsys.readouterr().out


def test_post_update_runs_migrations_and_says_when_done(home, capsys):
    cli(["post-update"])
    assert "Migrations and rebuilds are done." in capsys.readouterr().out


def test_version_flag_and_the_version_live_in_one_place():
    r = subprocess.run([sys.executable, "-m", "storywheel", "--version"], capture_output=True, text=True)
    assert r.stdout.strip() == f"storywheel {__version__}"
    root = Path(__file__).resolve().parent.parent
    assert 'dynamic = ["version"]' in (root / "pyproject.toml").read_text()
    assert f"## {__version__}" in (root / "CHANGELOG.md").read_text()


def test_a_remote_is_given_to_git_exactly_as_written(home, monkeypatch):
    """Hostnames like xps:projects/storywheel (ssh style) must reach git untouched."""
    calls = []
    def fake_git(repo, *args, check=True):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="main\n" if "--abbrev-ref" in args else "", stderr="")
    monkeypatch.setattr(update, "checkout_dir", lambda: Path(__file__).parent.parent)
    monkeypatch.setattr(update, "git", fake_git)
    settings.save_global({"update_remote": "xps:projects/storywheel"})
    update.update(lambda m: None, check_only=True, runner=FakeRun())
    fetch = next(c for c in calls if c[0] == "fetch")
    assert fetch == ("fetch", "--", "xps:projects/storywheel", "main")
