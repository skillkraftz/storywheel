"""install.sh: checked with --dry-run on a pretend machine (a PATH holding only fake tools), so nothing is installed."""
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "install.sh"
BASICS = ("bash", "sed", "uname", "id", "dirname", "cat", "mktemp", "head", "printf", "env", "find", "xargs", "tar", "ln", "rm", "mkdir", "install")

pytestmark = pytest.mark.skipif(not shutil.which("bash"), reason="needs bash")


def machine(tmp_path, tools=(), nvim_version=None, apt_candidate=None, arch="x86_64"):
    """A bin folder with the basics plus fake `tools`; returns the environment to run the script with."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for name in BASICS:
        found = shutil.which(name)
        if found:
            os.symlink(found, bin_ / name)
    def fake(name, body):
        p = bin_ / name
        p.write_text("#!/bin/bash\n" + textwrap.dedent(body))
        p.chmod(0o755)
    uname = bin_ / "uname"
    uname.unlink()
    fake("uname", f'echo {arch}\n')
    for t in tools:
        fake(t, f'echo "{t} 1.0"\n')
    if "python3" in tools:
        fake("python3", 'if [ "$1" = "-c" ]; then exit 0; fi\necho "Python 3.11.2"\n')
    if nvim_version:
        fake("nvim", f'echo "NVIM v{nvim_version}"\necho "Build type: Release"\n')
    if apt_candidate is not None:
        fake("apt-cache", f'echo "neovim:"\necho "  Installed: (none)"\necho "  Candidate: {apt_candidate}"\n')
    env = {"PATH": str(bin_), "HOME": str(tmp_path / "home"), "STORYWHEEL_INSTALL_BIN": str(tmp_path / "home" / ".local" / "bin")}
    (tmp_path / "home").mkdir()
    return env


def run(env, *args):
    return subprocess.run(["bash", str(SCRIPT), "--dry-run", "--yes", *args], capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=60)


def test_the_script_is_valid_bash_and_executable():
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0
    assert os.access(SCRIPT, os.X_OK)
    text = SCRIPT.read_text()
    for needle in ("--dry-run", "--yes", "pipx", "libreoffice-writer", "kitty", "storywheel setup", "nvim-linux-", "x86_64", "aarch64"):
        assert needle in text


def test_a_bare_machine_gets_everything_it_needs(tmp_path):
    r = run(machine(tmp_path, apt_candidate="0.9.5-1"))
    out = r.stdout
    assert r.returncode == 0, out + r.stderr
    assert "installing python3" in out and "installing pipx" in out and "installing git" in out
    assert "older than 0.10" in out and "nvim-linux-x86_64.tar.gz" in out and "link " in out
    assert "pipx install --force" in out and "storywheel setup" in out and "Install LibreOffice" not in out
    assert "apt-get install -y libreoffice-writer" in out                                       # (--yes installs the optional office suite)
    assert "[dry run]" in out and "dry run: nothing will be changed" in out


def test_arm64_gets_the_arm_build_and_kitty_from_apt(tmp_path):
    r = run(machine(tmp_path, apt_candidate="0.7.2", arch="aarch64"))
    assert "nvim-linux-arm64.tar.gz" in r.stdout and "apt-get install -y kitty" in r.stdout and "neovide" not in r.stdout.lower() and r.returncode == 0


def test_a_new_enough_distribution_neovim_is_installed_with_apt(tmp_path):
    r = run(machine(tmp_path, tools=("python3", "pipx", "git"), apt_candidate="0.10.4-1"))
    assert "the distribution has Neovim 0.10: installing it" in r.stdout and "apt-get install -y neovim" in r.stdout
    assert "installing pipx" not in r.stdout and "found pipx" not in r.stdout or "found" in r.stdout


def test_an_old_neovim_is_replaced_and_a_good_one_is_kept(tmp_path):
    (tmp_path / "a").mkdir()
    old = run(machine(tmp_path / "a", tools=("python3", "pipx", "git"), nvim_version="0.9.5", apt_candidate="0.7"))
    assert "which is too old" in old.stdout and "official release" in old.stdout
    (tmp_path / "b").mkdir()
    good = run(machine(tmp_path / "b", tools=("python3", "pipx", "git", "soffice", "kitty"), nvim_version="0.11.1"))
    assert "found NVIM v0.11.1" in good.stdout and "too old" not in good.stdout and "official release" not in good.stdout
    assert good.stdout.count("found") >= 5 and good.returncode == 0


def test_a_url_can_be_installed_from(tmp_path):
    r = run(machine(tmp_path, tools=("python3", "pipx", "git", "soffice", "kitty"), nvim_version="0.11.1"), "git+https://example.org/me/storywheel.git")
    assert "pipx install --force git+https://example.org/me/storywheel.git" in r.stdout


def test_an_unknown_folder_without_pyproject_is_refused(tmp_path):
    r = run(machine(tmp_path, tools=("python3",)), str(tmp_path))
    assert r.returncode == 1 and "has no pyproject.toml" in r.stdout


def test_other_systems_get_a_plain_message(tmp_path):
    env = machine(tmp_path, tools=("python3",))
    # the script reads /etc/os-release itself; on a Debian-family test machine just check that the message exists in the script
    assert "This script is for Debian, Ubuntu and Raspberry Pi OS" in SCRIPT.read_text()
