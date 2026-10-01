"""What `pipx install .` ships must be everything the app reads at run time."""
import fnmatch
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def patterns():
    text = (ROOT / "pyproject.toml").read_text()
    block = re.search(r"\[tool\.setuptools\.package-data\]\s*storywheel = \[(.*?)\]", text, re.S).group(1)
    return re.findall(r'"([^"]+)"', block)


def test_every_data_file_is_shipped():
    pkg = ROOT / "storywheel"
    shipped = patterns()
    files = [p.relative_to(pkg).as_posix() for p in (pkg / "data").rglob("*.json")]
    assert len(files) > 100
    missing = [f for f in files if not any(fnmatch.fnmatch(f, pat) for pat in shipped)]
    assert not missing, missing[:5]


def test_structures_and_genres_are_among_them():
    shipped = patterns()
    for f in ("data/genres.json", "data/structures/kishotenketsu.json", "data/lists/job/everyday.json",
              "data/templates/want/general.json"):
        assert any(fnmatch.fnmatch(f, pat) for pat in shipped), f


def test_textual_is_a_dependency():
    assert re.search(r'dependencies = \[[^\]]*"textual', (ROOT / "pyproject.toml").read_text())
