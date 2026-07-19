from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal

from optees.application.usecases.check_for_updates_usecase import CheckForUpdatesUseCase
from optees.application.usecases.execute_update_usecase import ExecuteUpdateUseCase
from optees.domain.entities.update import UpdateCheckResult


class UpdateController(QObject):
    """Runs update checks/downloads off the UI thread."""

    check_completed = Signal(object)
    check_failed = Signal(str)
    download_started = Signal(object)
    execution_state_changed = Signal(object)
    download_progress = Signal(int, int)
    handoff_completed = Signal(object)
    download_failed = Signal(str)

    def __init__(
        self,
        check_usecase: CheckForUpdatesUseCase,
        execute_usecase: ExecuteUpdateUseCase,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._check_usecase = check_usecase
        self._execute_usecase = execute_usecase
        self._last_result: UpdateCheckResult | None = None
        self._checking = False
        self._downloading = False

    def latest_result(self) -> UpdateCheckResult | None:
        return self._last_result

    def check_for_updates(self) -> None:
        if self._checking:
            return
        self._checking = True
        thread = threading.Thread(target=self._run_check, name="optees-update-check", daemon=True)
        thread.start()

    def download_and_launch_update(self) -> None:
        if self._downloading:
            return
        result = self._last_result
        if result is None or not result.update_available:
            self.download_failed.emit("No update is available.")
            return
        self._downloading = True
        self.download_started.emit(result)
        thread = threading.Thread(
            target=self._run_download,
            args=(result,),
            name="optees-update-download",
            daemon=True,
        )
        thread.start()

    def _run_check(self) -> None:
        try:
            result = self._check_usecase.execute()
            self._last_result = result
            self.check_completed.emit(result)
        except Exception as exc:
            self.check_failed.emit(str(exc))
        finally:
            self._checking = False

    def _run_download(self, result: UpdateCheckResult) -> None:
        try:
            outcome = self._execute_usecase.execute(
                result,
                on_state=self.execution_state_changed.emit,
                on_progress=lambda downloaded, total: self.download_progress.emit(
                    downloaded, total if total is not None else -1
                ),
            )
            self.handoff_completed.emit(outcome)
        except Exception as exc:
            self.download_failed.emit(str(exc))
        finally:
            self._downloading = False
