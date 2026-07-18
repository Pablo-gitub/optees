from __future__ import annotations

import json
import tempfile
from pathlib import Path
from threading import Thread

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication

from optees.application.services.local_server_process import (
    LocalServerProcessManager,
    LocalServerSnapshot,
    LocalServerState,
)


class LocalServerController(QObject):
    _operation_completed = Signal(object)
    _operation_failed = Signal(str)
    _document_ready = Signal(str)
    _document_failed = Signal()

    def __init__(self, view, manager: LocalServerProcessManager, parent=None) -> None:
        super().__init__(parent)
        self._view = view
        self._manager = manager
        self._busy = False
        self._operation_completed.connect(self._finish_operation)
        self._operation_failed.connect(self._fail_operation)
        self._document_ready.connect(self._open_document)
        self._document_failed.connect(
            lambda: self._view.set_service_action_error("openapi_failed")
        )
        view.service_start_requested.connect(self.start)
        view.service_stop_requested.connect(self.stop)
        view.service_copy_url_requested.connect(self.copy_url)
        view.service_copy_authorization_requested.connect(self.copy_authorization)
        view.service_copy_configuration_requested.connect(self.copy_configuration)
        view.service_open_docs_requested.connect(self.open_docs)
        view.set_service_snapshot(manager.snapshot)

    def start(self, port: int) -> None:
        if self._busy:
            return
        self._busy = True
        self._view.set_service_snapshot(
            LocalServerSnapshot(LocalServerState.STARTING, requested_port=port)
        )
        self._run(lambda: self._manager.start(port))

    def stop(self) -> None:
        if self._busy:
            return
        self._busy = True
        current = self._manager.snapshot
        self._view.set_service_snapshot(
            LocalServerSnapshot(
                LocalServerState.STOPPING,
                requested_port=current.requested_port,
                actual_port=current.actual_port,
                url=current.url,
                used_fallback_port=current.used_fallback_port,
            )
        )
        self._run(self._manager.stop)

    def copy_url(self) -> None:
        try:
            QApplication.clipboard().setText(self._manager.connection().base_url)
        except RuntimeError as exc:
            self._fail_operation(str(exc))

    def copy_configuration(self) -> None:
        try:
            QApplication.clipboard().setText(self._manager.connection_json())
        except RuntimeError as exc:
            self._fail_operation(str(exc))

    def copy_authorization(self) -> None:
        try:
            QApplication.clipboard().setText(
                self._manager.connection().authorization
            )
        except RuntimeError as exc:
            self._fail_operation(str(exc))

    def open_docs(self) -> None:
        def export_document() -> None:
            try:
                document = self._manager.openapi_document()
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    prefix="optees-openapi-",
                    suffix=".json",
                    encoding="utf-8",
                    delete=False,
                ) as output:
                    json.dump(document, output, indent=2, sort_keys=True)
                    path = output.name
                self._document_ready.emit(path)
            except Exception:
                self._document_failed.emit()

        Thread(target=export_document, name="optees-openapi", daemon=True).start()

    def shutdown(self) -> None:
        self._manager.shutdown()

    def _run(self, operation) -> None:
        def execute() -> None:
            try:
                self._operation_completed.emit(operation())
            except Exception as exc:
                self._operation_failed.emit(str(exc))

        Thread(target=execute, name="optees-local-server", daemon=True).start()

    def _finish_operation(self, snapshot: LocalServerSnapshot) -> None:
        self._busy = False
        self._view.set_service_snapshot(snapshot)

    def _fail_operation(self, message: str) -> None:
        self._busy = False
        current = self._manager.snapshot
        self._view.set_service_snapshot(
            LocalServerSnapshot(
                LocalServerState.ERROR,
                requested_port=current.requested_port,
                error_code="operation_failed",
                message=message,
            )
        )

    @staticmethod
    def _open_document(path: str) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path))))
