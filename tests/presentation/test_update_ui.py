from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from optees.domain.entities.update import AppRelease, ReleaseAsset, UpdateCheckResult


def _update_result(version: str = "0.2.0") -> UpdateCheckResult:
    asset = ReleaseAsset(
        name="optees-macos-arm64.dmg",
        download_url="https://example.test/optees-macos-arm64.dmg",
    )
    release = AppRelease(
        tag_name=f"v{version}",
        version=version,
        html_url="https://github.com/Pablo-gitub/optees/releases/latest",
        assets=(asset,),
    )
    return UpdateCheckResult(
        current_version="0.1.0",
        latest_version=version,
        update_available=True,
        release=release,
        asset=asset,
    )


def test_home_update_banner_is_hidden_until_update_available(window, qtbot):
    button = window.home_page.findChild(QPushButton, "updateBannerButton")

    assert button is not None
    assert button.isVisible() is False

    window.home_page.set_update_available(_update_result())

    assert button.isVisible() is True
    assert "0.2.0" in button.text()

    with qtbot.waitSignal(window.home_page.update_requested, timeout=1000):
        qtbot.mouseClick(button, Qt.LeftButton)


def test_settings_shows_update_status(window):
    window.settings_page.set_update_status(_update_result("0.3.0"))

    assert "0.1.0" in window.settings_page.value_version.text()
    assert "0.3.0" in window.settings_page.value_update.text()

    window.settings_page.set_update_error("offline")

    assert "offline" in window.settings_page.value_update.text()
