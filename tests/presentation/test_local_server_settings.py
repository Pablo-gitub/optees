from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from optees.application.services.local_server_process import (
    LocalServerConnection,
    LocalServerSnapshot,
    LocalServerState,
)
from optees.presentation.controllers.local_server_controller import (
    LocalServerController,
)
from optees.presentation.views.settings_view import SettingsView


class FakeManager:
    def __init__(self) -> None:
        self.snapshot = LocalServerSnapshot(LocalServerState.STOPPED)
        self.started_ports = []
        self.stop_count = 0
        self.shutdown_count = 0

    def start(self, port):
        self.started_ports.append(port)
        self.snapshot = LocalServerSnapshot(
            LocalServerState.RUNNING,
            requested_port=port,
            actual_port=port,
            url=f"http://127.0.0.1:{port}",
        )
        return self.snapshot

    def stop(self):
        self.stop_count += 1
        self.snapshot = LocalServerSnapshot(LocalServerState.STOPPED)
        return self.snapshot

    def shutdown(self):
        self.shutdown_count += 1
        self.stop()

    def connection(self):
        return LocalServerConnection(
            base_url=self.snapshot.url,
            authorization="Bearer private-session-token",
            openapi_url=f"{self.snapshot.url}/api/v1/openapi.json",
        )

    def connection_json(self):
        return json.dumps(self.connection().to_dict())


def test_settings_controls_emit_requested_port_without_showing_a_token(qtbot):
    view = SettingsView()
    qtbot.addWidget(view)
    view.show()
    view.service_port.setValue(9021)

    with qtbot.waitSignal(view.service_start_requested, timeout=1000) as emitted:
        qtbot.mouseClick(view.service_start_button, Qt.LeftButton)

    assert emitted.args == [9021]
    assert "token" not in view.service_status_value.text().lower()
    assert view.service_copy_config_button.isEnabled() is False


def test_controller_starts_copies_configuration_stops_and_shuts_down(qtbot):
    view = SettingsView()
    qtbot.addWidget(view)
    manager = FakeManager()
    controller = LocalServerController(view, manager)
    view.service_port.setValue(9030)

    qtbot.mouseClick(view.service_start_button, Qt.LeftButton)
    qtbot.waitUntil(
        lambda: view._service_snapshot.state is LocalServerState.RUNNING,
        timeout=2000,
    )
    qtbot.mouseClick(view.service_copy_config_button, Qt.LeftButton)
    copied = json.loads(QApplication.clipboard().text())

    assert manager.started_ports == [9030]
    assert copied["authorization"] == "Bearer private-session-token"
    assert view.service_url_value.text() == "http://127.0.0.1:9030"

    qtbot.mouseClick(view.service_stop_button, Qt.LeftButton)
    qtbot.waitUntil(
        lambda: view._service_snapshot.state is LocalServerState.STOPPED,
        timeout=2000,
    )
    controller.shutdown()

    assert manager.stop_count == 2
    assert manager.shutdown_count == 1


def test_running_fallback_is_reported_and_locks_port_editor(qtbot):
    view = SettingsView()
    qtbot.addWidget(view)
    view.set_service_snapshot(
        LocalServerSnapshot(
            LocalServerState.RUNNING,
            requested_port=8765,
            actual_port=45123,
            url="http://127.0.0.1:45123",
            used_fallback_port=True,
        )
    )

    assert "45123" in view.service_status_value.text()
    assert view.service_port.isEnabled() is False
    assert view.service_stop_button.isEnabled() is True
