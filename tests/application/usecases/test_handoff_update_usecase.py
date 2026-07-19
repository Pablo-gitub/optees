from __future__ import annotations

from pathlib import Path

import pytest

from optees.application.usecases.handoff_update_usecase import HandoffUpdateUseCase
from optees.domain.entities.update import (
    CpuArchitecture,
    ReleaseAsset,
    UpdateArtifactKind,
    UpdateExecutionState,
    UpdateHandoffMethod,
    UpdatePlan,
    UpdatePlatform,
)


class FakeHandoff:
    def __init__(self, accepted: bool = True) -> None:
        self.accepted = accepted
        self.calls: list[tuple[UpdatePlan, Path]] = []

    def start(self, plan: UpdatePlan, local_path: Path) -> bool:
        self.calls.append((plan, local_path))
        return self.accepted


def _plan(method: UpdateHandoffMethod) -> UpdatePlan:
    asset = ReleaseAsset("optees-macos-arm64.dmg", "https://example.test/optees.dmg")
    return UpdatePlan(
        platform=UpdatePlatform.MACOS,
        architecture=CpuArchitecture.ARM64,
        artifact=asset,
        artifact_kind=UpdateArtifactKind.MACOS_DMG,
        handoff_method=method,
        staging_subdirectory="0.2.0/macos-arm64",
    )


def test_handoff_reports_manual_action_for_current_packages(tmp_path):
    path = tmp_path / "optees-macos-arm64.dmg"
    path.write_bytes(b"release")
    adapter = FakeHandoff()

    result = HandoffUpdateUseCase(adapter).execute(
        _plan(UpdateHandoffMethod.OPEN_DISK_IMAGE), path
    )

    assert result.started is True
    assert result.state is UpdateExecutionState.MANUAL_ACTION_REQUIRED
    assert adapter.calls == [(_plan(UpdateHandoffMethod.OPEN_DISK_IMAGE), path.resolve())]


def test_handoff_reports_installer_launched(tmp_path):
    path = tmp_path / "optees-macos-arm64.dmg"
    path.write_bytes(b"release")

    result = HandoffUpdateUseCase(FakeHandoff()).execute(
        _plan(UpdateHandoffMethod.LAUNCH_INSTALLER), path
    )

    assert result.state is UpdateExecutionState.INSTALLER_LAUNCHED


def test_handoff_rejects_missing_file(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        HandoffUpdateUseCase(FakeHandoff()).execute(
            _plan(UpdateHandoffMethod.OPEN_DISK_IMAGE),
            tmp_path / "optees-macos-arm64.dmg",
        )


def test_handoff_rejects_unexpected_filename(tmp_path):
    path = tmp_path / "unexpected.dmg"
    path.write_bytes(b"release")

    with pytest.raises(ValueError, match="filename"):
        HandoffUpdateUseCase(FakeHandoff()).execute(
            _plan(UpdateHandoffMethod.OPEN_DISK_IMAGE), path
        )


def test_handoff_rejects_failed_os_launch(tmp_path):
    path = tmp_path / "optees-macos-arm64.dmg"
    path.write_bytes(b"release")

    with pytest.raises(RuntimeError, match="did not accept"):
        HandoffUpdateUseCase(FakeHandoff(accepted=False)).execute(
            _plan(UpdateHandoffMethod.OPEN_DISK_IMAGE), path
        )
