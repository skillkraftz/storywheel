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


def make_repo(path, version):
    (path / "storywheel").mkdir(parents=True)
    (path / "storywheel" / "__init__.py").write_text(f'__version__ = "{version}"\n')
    (path / "CHANGELOG.md").write_text(f"# Changelog\n\n## {version} — now\n- start\n")
    git(path.parent, "init", "-q", "-b", "main", str(path))
    git(path, "config", "user.email", "t@t")
    git(path, "config", "user.name", "t")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "first")


def release(repo, version, note="a brand new thing"):
    (repo / "storywheel" / "__init__.py").write_text(f'__version__ = "{version}"\n')
    old = (repo / "CHANGELOG.md").read_text()
    (repo / "CHANGELOG.md").write_text(old.replace("# Changelog\n", f"# Changelog\n\n## {version} — new\n- {note}\n", 1))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"release {version}")


class FakeRun:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="  Migrations and rebuilds are done.\n", stderr="")

    def installs(self):
        return [c for c in self.calls if "install" in c]


@pytest.fixture
def install(monkeypatch):
    """Pretend storywheel 0.5.0 is installed from a folder; returns a function to say which folder and whether it is editable."""
    monkeypatch.setattr(update, "installed_version", lambda: "0.5.0")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pipx" if name == "pipx" else None)
    def from_folder(folder, editable=False):
        monkeypatch.setattr(update, "installed_source", lambda: (folder, editable))
    return from_folder


def test_the_installed_version_is_compared_with_the_source_folder_not_with_a_clone(home, tmp_path, install):
    """The bug: a clone was compared with the remote, so 'already up to date' was said while 0.6.0 was waiting."""
    src = tmp_path / "projects" / "storywheel"
    make_repo(src, "0.6.0")                                           # xps: no remote at all
    install(src)
    said, run = [], FakeRun()
    assert update.update(said.append, runner=run) == "updated"
    text = "\n".join(said)
    assert "Installed: 0.5.0 " in text and f"Source {paths.tilde(src)}: 0.6.0 (commit " in text and "Reinstalling." in text and "## 0.6.0" in text
    assert run.installs() == [["/usr/bin/pipx", "install", "--force", str(src)]]
    assert run.calls[-1][1:] == ["-m", "storywheel", "post-update"]                 # then the usual migrations and rebuilds
    assert not (paths.home() / "source").exists()                                  # no private clone any more


def test_the_same_version_and_the_same_commit_says_so_and_does_nothing(home, tmp_path, install):
    src = tmp_path / "storywheel"
    make_repo(src, "0.5.0")
    update.record_install(src, update.fingerprint(src))                  # (what an earlier update or install.sh recorded)
    install(src)
    said, run = [], FakeRun()
    assert update.update(said.append, runner=run) == "up-to-date"
    assert any(m.startswith("Installed: 0.5.0 (commit ") and "Source" in m and "0.5.0 (commit " in m for m in said) and "Already up to date." in said and run.calls == []


def test_a_fix_committed_without_a_version_bump_is_reinstalled(home, tmp_path, install):
    """The gap: 'same version, new commits' used to skip the reinstall, so such fixes never reached a non-editable install."""
    src = tmp_path / "storywheel"
    make_repo(src, "0.5.0")
    first = update.fingerprint(src)
    update.record_install(src, first)
    install(src)
    (src / "fix.txt").write_text("a fix")
    git(src, "add", "-A")
    git(src, "commit", "-q", "-m", "fix without a bump")
    said, run = [], FakeRun()
    assert update.update(said.append, runner=run) == "updated"
    text = "\n".join(said)
    assert "Same version number, but the source is at commit" in text and update.short(first) in text and "Reinstalling." in text
    assert run.installs() == [["/usr/bin/pipx", "install", "--force", str(src)]]
    assert update.recorded()["fingerprint"] == update.fingerprint(src) != first                   # recorded at install time
    run2, said2 = FakeRun(), []
    assert update.update(said2.append, runner=run2) == "up-to-date" and run2.calls == []         # and now it is up to date


def test_an_unrecorded_install_is_reinstalled_once_to_record_it(home, tmp_path, install):
    src = tmp_path / "storywheel"
    make_repo(src, "0.5.0")
    install(src)
    said, run = [], FakeRun()
    assert update.update(said.append, runner=run) == "updated"
    assert "does not know which commit is installed" in " ".join(said) and "(which commit is not recorded)" in " ".join(said) and len(run.installs()) == 1
    assert update.recorded()["fingerprint"] == update.fingerprint(src)
    run2 = FakeRun()
    assert update.update(lambda m: None, runner=run2) == "up-to-date" and run2.calls == []


def test_uncommitted_changes_in_the_source_count_as_different_code(home, tmp_path, install):
    src = tmp_path / "storywheel"
    make_repo(src, "0.5.0")
    update.record_install(src, update.fingerprint(src))
    install(src)
    (src / "storywheel" / "__init__.py").write_text('__version__ = "0.5.0"\n# edited\n')
    run = FakeRun()
    assert update.update(lambda m: None, runner=run) == "updated" and len(run.installs()) == 1
    assert "+" in update.recorded()["fingerprint"]
    run2 = FakeRun()
    assert update.update(lambda m: None, runner=run2) == "up-to-date"                         # (the same edit is not reinstalled again)
    (src / "storywheel" / "__init__.py").write_text('__version__ = "0.5.0"\n# edited again\n')
    assert update.update(lambda m: None, runner=FakeRun()) == "updated"


def test_check_only_reports_a_same_version_fix_and_changes_nothing(home, tmp_path, install):
    xps = tmp_path / "xps" / "storywheel"
    make_repo(xps, "0.5.0")
    typewriter = tmp_path / "t" / "storywheel"
    typewriter.parent.mkdir()
    subprocess.run(["git", "clone", "-q", str(xps), str(typewriter)], check=True)
    update.record_install(typewriter, update.fingerprint(typewriter))
    (xps / "fix.txt").write_text("x")
    git(xps, "add", "-A")
    git(xps, "commit", "-q", "-m", "fix")
    install(typewriter)
    said, run = [], FakeRun()
    assert update.update(said.append, check_only=True, runner=run) == "available" and run.calls == [] and "An update is available" in " ".join(said)
    assert not (typewriter / "fix.txt").exists()


def test_record_flag_remembers_the_installed_commit(home, tmp_path, install, capsys):
    src = tmp_path / "storywheel"
    make_repo(src, "0.5.0")
    install(src)
    cli(["update", "--record"])
    assert "Recorded the installed source" in capsys.readouterr().out and update.recorded()["fingerprint"] == update.fingerprint(src)


def test_a_source_older_than_the_installed_one_is_left_alone(home, tmp_path, install):
    src = tmp_path / "storywheel"
    make_repo(src, "0.4.0")
    install(src)
    run = FakeRun()
    said = []
    assert update.update(said.append, runner=run) == "up-to-date" and "older than what is installed" in " ".join(said) and run.calls == []


def test_a_checkout_with_a_remote_is_fetched_and_fast_forwarded_first(home, tmp_path, install):
    xps = tmp_path / "xps" / "storywheel"
    make_repo(xps, "0.5.0")
    typewriter = tmp_path / "typewriter" / "storywheel"
    typewriter.parent.mkdir()
    subprocess.run(["git", "clone", "-q", str(xps), str(typewriter)], check=True)
    git(typewriter, "config", "user.email", "t@t")
    git(typewriter, "config", "user.name", "t")
    release(xps, "0.6.0")                                              # work done on xps since
    install(typewriter)
    said, run = [], FakeRun()
    assert update.update(said.append, runner=run) == "updated"
    text = "\n".join(said)
    assert "1 new change(s) fetched from origin" in text and "release 0.6.0" in text
    assert "Installed: 0.5.0 " in text and f"Source {paths.tilde(typewriter)}: 0.6.0 (commit " in text and "Reinstalling." in text
    assert (typewriter / "storywheel" / "__init__.py").read_text() == '__version__ = "0.6.0"\n'
    assert run.installs() == [["/usr/bin/pipx", "install", "--force", str(typewriter)]]


def test_check_only_fetches_but_changes_and_installs_nothing(home, tmp_path, install):
    xps = tmp_path / "xps" / "storywheel"
    make_repo(xps, "0.5.0")
    typewriter = tmp_path / "t" / "storywheel"
    typewriter.parent.mkdir()
    subprocess.run(["git", "clone", "-q", str(xps), str(typewriter)], check=True)
    release(xps, "0.6.0")
    install(typewriter)
    said, run = [], FakeRun()
    assert update.update(said.append, check_only=True, runner=run) == "available"
    assert "Source" in " ".join(said) and "0.6.0" in " ".join(said) and "An update is available" in " ".join(said)
    assert (typewriter / "storywheel" / "__init__.py").read_text() == '__version__ = "0.5.0"\n' and run.calls == []


def test_new_commits_with_the_same_version_are_fetched_and_reinstalled(home, tmp_path, install):
    xps = tmp_path / "xps" / "storywheel"
    make_repo(xps, "0.5.0")
    typewriter = tmp_path / "t" / "storywheel"
    typewriter.parent.mkdir()
    subprocess.run(["git", "clone", "-q", str(xps), str(typewriter)], check=True)
    update.record_install(typewriter, update.fingerprint(typewriter))
    (xps / "note.txt").write_text("x")
    git(xps, "add", "-A")
    git(xps, "commit", "-q", "-m", "tweak")
    install(typewriter)
    run = FakeRun()
    said = []
    assert update.update(said.append, runner=run) == "updated" and len(run.installs()) == 1 and "tweak" in " ".join(said)
    assert run.calls[-1][1:] == ["-m", "storywheel", "post-update"]


def test_an_editable_install_is_not_reinstalled(home, tmp_path, install):
    src = tmp_path / "storywheel"
    make_repo(src, "0.6.0")
    install(src, editable=True)
    run = FakeRun()
    said = []
    assert update.update(said.append, runner=run) == "updated"
    assert "runs straight from that folder" in " ".join(said) and run.installs() == [] and run.calls[-1][1:] == ["-m", "storywheel", "post-update"]


def test_a_missing_source_folder_without_a_remote_says_what_to_do(home, tmp_path, install):
    install(tmp_path / "gone" / "storywheel")
    with pytest.raises(update.UpdateError) as e:
        update.update(lambda m: None, runner=FakeRun())
    assert "is not there any more" in str(e.value) and "no update remote is set" in str(e.value) and "Settings (F4) > Updates" in str(e.value)


def test_a_missing_source_folder_uses_the_update_remote_for_a_temporary_clone(home, tmp_path, install):
    remote = tmp_path / "remote" / "storywheel"
    make_repo(remote, "0.6.0")
    install(tmp_path / "gone")
    settings.save_global({"update_remote": str(remote)})
    said, run = [], FakeRun()
    assert update.update(said.append, runner=run) == "updated"
    text = "\n".join(said)
    assert "is gone; cloning" in text and "Reinstalling." in text
    target = run.installs()[0][-1]
    assert not Path(target).exists()                                 # (the temporary clone is removed again)


def test_a_dirty_checkout_with_a_remote_is_not_touched(home, tmp_path, install):
    xps = tmp_path / "xps" / "storywheel"
    make_repo(xps, "0.5.0")
    typewriter = tmp_path / "t" / "storywheel"
    typewriter.parent.mkdir()
    subprocess.run(["git", "clone", "-q", str(xps), str(typewriter)], check=True)
    (typewriter / "mine.txt").write_text("work")
    git(typewriter, "add", "mine.txt")
    install(typewriter)
    with pytest.raises(update.UpdateError, match="not committed"):
        update.update(lambda m: None, runner=FakeRun())


def test_a_diverged_checkout_is_not_merged(home, tmp_path, install):
    xps = tmp_path / "xps" / "storywheel"
    make_repo(xps, "0.5.0")
    typewriter = tmp_path / "t" / "storywheel"
    typewriter.parent.mkdir()
    subprocess.run(["git", "clone", "-q", str(xps), str(typewriter)], check=True)
    git(typewriter, "config", "user.email", "t@t")
    git(typewriter, "config", "user.name", "t")
    (typewriter / "mine.txt").write_text("work")
    git(typewriter, "add", "-A")
    git(typewriter, "commit", "-q", "-m", "mine")
    release(xps, "0.6.0")
    install(typewriter)
    with pytest.raises(update.UpdateError, match="both changed"):
        update.update(lambda m: None, runner=FakeRun())
    assert (typewriter / "mine.txt").exists()


def test_the_source_folder_is_found_from_pips_direct_url(home, tmp_path, monkeypatch):
    import json
    class Dist:
        def __init__(self, text):
            self.text = text
        def read_text(self, name):
            return self.text if name == "direct_url.json" else None
    from importlib import metadata
    folder = tmp_path / "my projects" / "storywheel"
    monkeypatch.setattr(metadata, "distribution", lambda name: Dist(json.dumps({"url": "file://" + str(folder).replace(" ", "%20"), "dir_info": {}})))
    assert update.installed_source() == (folder, False)
    monkeypatch.setattr(metadata, "distribution", lambda name: Dist(json.dumps({"url": "file://" + str(folder), "dir_info": {"editable": True}})))
    assert update.installed_source() == (folder, True)
    monkeypatch.setattr(metadata, "distribution", lambda name: Dist(None))
    assert update.installed_source() is None
    monkeypatch.setattr(metadata, "distribution", lambda name: Dist(json.dumps({"url": "https://example.org/x.zip", "archive_info": {}})))
    assert update.installed_source() is None
    def missing(name):
        raise metadata.PackageNotFoundError(name)
    monkeypatch.setattr(metadata, "distribution", missing)
    assert update.installed_source() is None


def test_without_a_recorded_source_the_checkout_the_code_runs_from_is_used(home, tmp_path, monkeypatch):
    monkeypatch.setattr(update, "installed_source", lambda: None)
    monkeypatch.setattr(update, "checkout_dir", lambda: tmp_path)
    assert update.find_source() == (tmp_path, True)
    monkeypatch.setattr(update, "checkout_dir", lambda: None)
    assert update.find_source() == (None, False)


def test_a_remote_set_in_settings_reaches_git_exactly_as_written(home, tmp_path, install, monkeypatch):
    """Hostnames like xps:projects/storywheel (ssh style) must reach git untouched."""
    src = tmp_path / "storywheel"
    make_repo(src, "0.5.0")
    git(src, "remote", "add", "origin", "somewhere")
    install(src)
    calls = []
    real = update.git
    def spy(repo, *args, check=True):
        calls.append(args)
        if args[0] == "fetch":
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[0] == "rev-parse" and args[1] == "FETCH_HEAD":
            return real(repo, "rev-parse", "HEAD")
        return real(repo, *args, check=check)
    monkeypatch.setattr(update, "git", spy)
    settings.save_global({"update_remote": "xps:projects/storywheel"})
    update.update(lambda m: None, check_only=True, runner=FakeRun())
    assert next(c for c in calls if c[0] == "fetch") == ("fetch", "--", "xps:projects/storywheel", "main")


def test_the_real_installed_package_reports_where_it_came_from_or_none():
    found = update.installed_source()
    assert found is None or (isinstance(found[0], Path) and isinstance(found[1], bool))


def test_changelog_since_only_lists_newer_entries(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text("# C\n\n## 0.5.0 — a\n- five\n\n## 0.4.0 — b\n- four\n\n## 0.3.0 — c\n- three\n")
    text = update.changelog_since(tmp_path, "0.4.0")
    assert "five" in text and "four" not in text and "three" not in text
    assert update._key("0.10.0") > update._key("0.9.9")


def test_the_command_reports_errors_plainly(home, monkeypatch, capsys):
    monkeypatch.setattr(update, "installed_source", lambda: None)
    monkeypatch.setattr(update, "checkout_dir", lambda: None)
    with pytest.raises(SystemExit):
        cli(["update"])
    assert "no update remote is set" in capsys.readouterr().out


def test_post_update_runs_migrations_and_says_when_done(home, capsys):
    cli(["post-update"])
    assert "Migrations and rebuilds are done." in capsys.readouterr().out


def test_post_update_works_out_the_genre_fit_when_a_dictionary_is_there(home, tmp_path, monkeypatch, capsys):
    from dictfixture import build_fixture
    from storywheel import dictionary, genrefit
    out, _ = build_fixture(tmp_path / "dict")
    monkeypatch.setenv("STORYWHEEL_DICTIONARY", str(out))
    dictionary.forget()
    monkeypatch.setattr("storywheel.spelldict.ensure", lambda *a, **k: None)
    monkeypatch.setattr(genrefit, "ensure", lambda *a, **k: "Worked out which of 9 dictionary words fit each genre (1 scores).")
    cli(["post-update"])
    assert "Worked out which of 9 dictionary words" in capsys.readouterr().out
    dictionary.forget()


def test_version_flag_and_the_version_live_in_one_place():
    r = subprocess.run([sys.executable, "-m", "storywheel", "--version"], capture_output=True, text=True)
    assert r.stdout.strip() == f"storywheel {__version__}"
    root = Path(__file__).resolve().parent.parent
    assert 'dynamic = ["version"]' in (root / "pyproject.toml").read_text()
    assert f"## {__version__}" in (root / "CHANGELOG.md").read_text()
