from __future__ import annotations

from pathlib import Path

import pytest

from optees.application.ports.update_provider_port import UpdateVerificationError
from optees.application.usecases.execute_update_usecase import (
    ExecuteUpdateUseCase,
    UpdateExecutionError,
)
from optees.domain.entities.update import (
    AppRelease,
    CpuArchitecture,
    ReleaseAsset,
    UpdateArtifactKind,
    UpdateCheckResult,
    UpdateExecutionState,
    UpdateHandoffMethod,
    UpdateHandoffResult,
    UpdatePlan,
    UpdatePlatform,
)


class FakeDownload:
    def __init__(self, path: Path, error: Exception | None = None) -> None:
        self.path = path
        self.error = error

    def execute(self, _result, _destination, *, progress=None):
        if progress is not None:
            progress(4, 8)
            progress(8, 8)
        if self.error is not None:
            raise self.error
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(b"12345678")
        return self.path


class FakeHandoff:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def execute(self, plan, path):
        if self.error is not None:
            raise self.error
        return UpdateHandoffResult(
            plan=plan,
            local_path=str(path),
            state=UpdateExecutionState.MANUAL_ACTION_REQUIRED,
            started=True,
        )


class FakeStaging:
    def __init__(self, path: Path) -> None:
        self.path = path

    def directory_for(self, _plan):
        return self.path


def _result(tmp_path: Path) -> tuple[UpdateCheckResult, Path]:
    asset = ReleaseAsset(
        "optees-macos-arm64.dmg",
        "https://example.test/optees.dmg",
        size=8,
    )
    release = AppRelease("v0.2.0", "0.2.0", "https://example.test", assets=(asset,))
    plan = UpdatePlan(
        platform=UpdatePlatform.MACOS,
        architecture=CpuArchitecture.ARM64,
        artifact=asset,
        artifact_kind=UpdateArtifactKind.MACOS_DMG,
        handoff_method=UpdateHandoffMethod.OPEN_DISK_IMAGE,
        staging_subdirectory="0.2.0/macos-arm64",
    )
    return (
        UpdateCheckResult(
            current_version="0.1.0",
            latest_version="0.2.0",
            update_available=True,
            release=release,
            asset=asset,
            plan=plan,
        ),
        tmp_path / asset.name,
    )


def test_execute_update_emits_ordered_states_and_progress(tmp_path):
    result, path = _result(tmp_path)
    states = []
    progress = []
    usecase = ExecuteUpdateUseCase(
        FakeDownload(path), FakeHandoff(), FakeStaging(tmp_path)
    )

    outcome = usecase.execute(
        result,
        on_state=lambda snapshot: states.append(snapshot.state),
        on_progress=lambda downloaded, total: progress.append((downloaded, total)),
    )

    assert states == [
        UpdateExecutionState.DOWNLOADING,
        UpdateExecutionState.DOWNLOADED,
        UpdateExecutionState.MANUAL_ACTION_REQUIRED,
    ]
    assert progress == [(4, 8), (8, 8)]
    assert outcome.started is True


def test_execute_update_reports_verification_failure(tmp_path):
    result, path = _result(tmp_path)
    states = []
    usecase = ExecuteUpdateUseCase(
        FakeDownload(path, UpdateVerificationError("bad digest")),
        FakeHandoff(),
        FakeStaging(tmp_path),
    )

    with pytest.raises(UpdateExecutionError) as error:
        usecase.execute(result, on_state=lambda snapshot: states.append(snapshot.state))

    assert states == [
        UpdateExecutionState.DOWNLOADING,
        UpdateExecutionState.VERIFICATION_FAILED,
    ]
    assert error.value.snapshot.state is UpdateExecutionState.VERIFICATION_FAILED


def test_execute_update_keeps_download_when_handoff_fails(tmp_path):
    result, path = _result(tmp_path)
    snapshots = []
    usecase = ExecuteUpdateUseCase(
        FakeDownload(path),
        FakeHandoff(RuntimeError("open failed")),
        FakeStaging(tmp_path),
    )

    with pytest.raises(UpdateExecutionError) as error:
        usecase.execute(result, on_state=snapshots.append)

    assert snapshots[-1].state is UpdateExecutionState.DOWNLOADED
    assert snapshots[-1].local_path == str(path)
    assert error.value.snapshot.message == "open failed"
