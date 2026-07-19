from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from optees.core.string_manager import strings as S
from optees.domain.entities.update import (
    AppRelease,
    ReleaseAsset,
    UpdateCheckResult,
    UpdateExecutionState,
)


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

    assert window.settings_page.value_update.text() == S.t(
        "settings.update_error",
        detail=S.t("error_feedback.update.check"),
    )


def test_update_progress_is_visible_in_home_and_settings(window):
    result = _update_result("0.3.0")
    window.home_page.set_update_available(result)
    window.home_page.set_update_download_in_progress(result)
    window.home_page.set_update_download_progress(25, 100)
    window.settings_page.set_update_status(result)
    window.settings_page.set_update_download_progress(25, 100)

    button = window.home_page.findChild(QPushButton, "updateBannerButton")
    assert "25%" in button.text()
    assert "25%" in window.settings_page.value_update.text()


def test_settings_distinguishes_verification_and_manual_handoff(window):
    window.settings_page.set_update_verification_failed("bad digest")
    assert window.settings_page.value_update.text() == S.t(
        "settings.update_verification_failed"
    )

    window.settings_page.set_update_manual_action_required("/tmp/optees.dmg")
    assert window.settings_page.value_update.text() == S.t(
        "settings.update_manual_action_required"
    )


def test_manual_handoff_completion_keeps_manual_action_message(window):
    window.main_controller._on_update_handoff_completed(
        SimpleNamespace(
            state=UpdateExecutionState.MANUAL_ACTION_REQUIRED,
            local_path="/tmp/optees.dmg",
            started=False,
        )
    )

    assert window.settings_page.value_update.text() == S.t(
        "settings.update_manual_action_required"
    )


def test_source_run_marks_update_check_as_development(window):
    assert window.home_page.findChild(QPushButton, "updateBannerButton").isVisible() is False
    assert "Development" in window.settings_page.value_update.text() or (
        "sviluppo" in window.settings_page.value_update.text().lower()
    )
