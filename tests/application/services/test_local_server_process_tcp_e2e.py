from __future__ import annotations

import socket

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")

from optees.application.services.local_server_process import (
    LOOPBACK_HOST,
    LocalServerProcessManager,
    LocalServerState,
)


def test_real_manager_uses_fallback_serves_openapi_and_stops_child():
    occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupied.bind((LOOPBACK_HOST, 0))
    occupied.listen(1)
    requested_port = int(occupied.getsockname()[1])
    manager = LocalServerProcessManager(startup_timeout=12.0)
    try:
        snapshot = manager.start(requested_port)

        assert snapshot.state is LocalServerState.RUNNING
        assert snapshot.actual_port != requested_port
        assert snapshot.used_fallback_port is True
        connection = manager.connection()
        assert connection.base_url == snapshot.url
        assert connection.authorization.startswith("Bearer ")
        document = manager.openapi_document()
        assert document["info"]["title"] == "Optees Local Solver API"
    finally:
        stopped = manager.stop()
        occupied.close()

    assert stopped.state is LocalServerState.STOPPED
    with pytest.raises(RuntimeError, match="not running"):
        manager.connection()
