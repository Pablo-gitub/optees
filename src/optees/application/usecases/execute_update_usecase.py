from __future__ import annotations

from collections.abc import Callable

from optees.application.ports.update_provider_port import UpdateVerificationError
from optees.application.services.update_staging import UpdateStagingService
from optees.application.usecases.download_update_usecase import DownloadUpdateUseCase
from optees.application.usecases.handoff_update_usecase import HandoffUpdateUseCase
from optees.domain.entities.update import (
    UpdateCheckResult,
    UpdateExecutionSnapshot,
    UpdateExecutionState,
    UpdateHandoffResult,
)

StateCallback = Callable[[UpdateExecutionSnapshot], None]
ProgressCallback = Callable[[int, int | None], None]


class UpdateExecutionError(RuntimeError):
    def __init__(self, snapshot: UpdateExecutionSnapshot) -> None:
        super().__init__(snapshot.message)
        self.snapshot = snapshot


class ExecuteUpdateUseCase:
    """Coordinate persistent staging, verified download, and native handoff."""

    def __init__(
        self,
        download: DownloadUpdateUseCase,
        handoff: HandoffUpdateUseCase,
        staging: UpdateStagingService,
    ) -> None:
        self._download = download
        self._handoff = handoff
        self._staging = staging

    def execute(
        self,
        result: UpdateCheckResult,
        *,
        on_state: StateCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> UpdateHandoffResult:
        plan = result.plan
        if not result.update_available or plan is None:
            raise ValueError("No executable update plan is available.")

        def emit(snapshot: UpdateExecutionSnapshot) -> None:
            if on_state is not None:
                on_state(snapshot)

        emit(
            UpdateExecutionSnapshot(
                plan=plan,
                state=UpdateExecutionState.DOWNLOADING,
                total_bytes=plan.artifact.size,
            )
        )
        try:
            path = self._download.execute(
                result,
                self._staging.directory_for(plan),
                progress=on_progress,
            )
        except UpdateVerificationError as exc:
            snapshot = UpdateExecutionSnapshot(
                plan=plan,
                state=UpdateExecutionState.VERIFICATION_FAILED,
                message=str(exc),
            )
            emit(snapshot)
            raise UpdateExecutionError(snapshot) from exc

        downloaded = UpdateExecutionSnapshot(
            plan=plan,
            state=UpdateExecutionState.DOWNLOADED,
            local_path=str(path),
            bytes_downloaded=path.stat().st_size,
            total_bytes=plan.artifact.size,
        )
        emit(downloaded)

        try:
            outcome = self._handoff.execute(plan, path)
        except Exception as exc:
            snapshot = UpdateExecutionSnapshot(
                plan=plan,
                state=UpdateExecutionState.DOWNLOADED,
                local_path=str(path),
                bytes_downloaded=path.stat().st_size,
                total_bytes=plan.artifact.size,
                message=str(exc),
            )
            emit(snapshot)
            raise UpdateExecutionError(snapshot) from exc

        emit(
            UpdateExecutionSnapshot(
                plan=plan,
                state=outcome.state,
                local_path=outcome.local_path,
                bytes_downloaded=path.stat().st_size,
                total_bytes=plan.artifact.size,
            )
        )
        return outcome
