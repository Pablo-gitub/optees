from __future__ import annotations

import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from optees.application.usecases.check_for_updates_usecase import CheckForUpdatesUseCase
from optees.application.usecases.download_update_usecase import DownloadUpdateUseCase
from optees.application.usecases.handoff_update_usecase import HandoffUpdateUseCase
from optees.domain.entities.update import UpdateCheckResult


class UpdateController(QObject):
    """Runs update checks/downloads off the UI thread."""

    check_completed = Signal(object)
    check_failed = Signal(str)
    download_started = Signal(object)
    handoff_completed = Signal(object)
    download_failed = Signal(str)

    def __init__(
        self,
        check_usecase: CheckForUpdatesUseCase,
        download_usecase: DownloadUpdateUseCase,
        handoff_usecase: HandoffUpdateUseCase,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._check_usecase = check_usecase
        self._download_usecase = download_usecase
        self._handoff_usecase = handoff_usecase
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
            base_dir = Path(tempfile.gettempdir()) / "optees-updates"
            version = result.latest_version or "latest"
            target_dir = base_dir / version
            path = self._download_usecase.execute(result, target_dir)
            if result.plan is None:
                raise ValueError("The selected update has no platform handoff plan.")
            outcome = self._handoff_usecase.execute(result.plan, path)
            self.handoff_completed.emit(outcome)
        except Exception as exc:
            self.download_failed.emit(str(exc))
        finally:
            self._downloading = False
