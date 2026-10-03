"""Neovide has no arm64 build: Settings and setup say so and do not offer it."""
import asyncio

import pytest

from storywheel import settings, settings_app, setup_wizard, tools, vault, writer
from conftest import screen_text


@pytest.fixture
def arm(monkeypatch):
    monkeypatch.setenv("STORYWHEEL_ARCH", "aarch64")
    monkeypatch.setenv("STORYWHEEL_NEOVIDE", "no-such-neovide")


def test_arm_detection(monkeypatch):
    monkeypatch.setenv("STORYWHEEL_ARCH", "arm64")
    assert tools.is_arm64()
    monkeypatch.setenv("STORYWHEEL_ARCH", "x86_64")
    assert not tools.is_arm64()


def test_setup_says_so_and_does_not_ask(home, arm, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    said, asked = [], []
    s = setup_wizard.Setup(lambda p: asked.append(p) or "", said.append)
    s.ask_window()
    assert asked == [] and any("no ready-made build for arm64" in m for m in said)
    assert settings.load_global()["neovide"] is False


def test_the_writer_launch_note_is_the_arm64_one(home, arm):
    s = vault.create_universe("U").new_story("S")
    settings.save_story(s.path, {"neovide": True})
    assert writer.neovide_note(s) == tools.NEOVIDE_ARM64 and "cargo install neovide" in tools.NEOVIDE_ARM64


def test_settings_refuses_the_switch_and_shows_why(home, arm):
    async def go():
        app = settings_app.SettingsApp(None, "builder")
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            app.screen.query_one("#tabs").active = "t-writer"
            await pilot.pause()
            shown = str(app.screen.query_one("#writer-tools").render())
            app.screen.save("neovide", True)
            return shown, settings.load_global()["neovide"]
    shown, saved = asyncio.run(go())
    assert "not available on arm64" in shown and saved is False
