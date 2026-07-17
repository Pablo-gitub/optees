from __future__ import annotations

import json
import subprocess

import pytest

from optees.application.services import local_server_process as module
from optees.application.services.local_server_process import (
    LOCAL_SERVER_TOKEN_ENV,
    LocalServerProcessManager,
    LocalServerState,
)


class FakeProcess:
    def __init__(self, exit_code: int | None = None, *, ignore_terminate: bool = False):
        self.exit_code = exit_code
        self.ignore_terminate = ignore_terminate
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.exit_code

    def terminate(self):
        self.terminated = True
        if not self.ignore_terminate:
            self.exit_code = -15

    def wait(self, timeout=None):
        if self.exit_code is None:
            raise subprocess.TimeoutExpired("fake", timeout)
        return self.exit_code

    def kill(self):
        self.killed = True
        self.exit_code = -9


class ProcessFactory:
    def __init__(self, processes):
        self.processes = iter(processes)
        self.calls = []

    def __call__(self, command, environment):
        self.calls.append((command, dict(environment)))
        return next(self.processes)


def _tokens():
    values = iter(("a" * 40, "b" * 40, "c" * 40))
    return lambda: next(values)


@pytest.mark.parametrize("port", [0, 65536, True, 1.5, "8765"])
def test_start_rejects_invalid_ports(port):
    manager = LocalServerProcessManager()

    with pytest.raises(ValueError, match="port"):
        manager.start(port)  # type: ignore[arg-type]


def test_start_keeps_token_out_of_command_and_exposes_it_only_on_request(monkeypatch):
    process = FakeProcess()
    factory = ProcessFactory([process])
    monkeypatch.setattr(module, "_port_is_available", lambda _port: True)
    manager = LocalServerProcessManager(
        process_factory=factory,
        health_probe=lambda _url, _timeout: True,
        token_factory=lambda: "s" * 40,
    )

    snapshot = manager.start(8765)

    command, environment = factory.calls[0]
    assert snapshot.state is LocalServerState.RUNNING
    assert snapshot.url == "http://127.0.0.1:8765"
    assert "s" * 40 not in command
    assert environment[LOCAL_SERVER_TOKEN_ENV] == "s" * 40
    assert manager.connection().authorization == f"Bearer {'s' * 40}"
    assert json.loads(manager.connection_json())["base_url"] == snapshot.url


def test_occupied_requested_port_uses_a_loopback_fallback(monkeypatch):
    factory = ProcessFactory([FakeProcess()])
    monkeypatch.setattr(module, "_port_is_available", lambda _port: False)
    monkeypatch.setattr(module, "_available_port", lambda: 43123)
    manager = LocalServerProcessManager(
        process_factory=factory,
        health_probe=lambda _url, _timeout: True,
        token_factory=lambda: "t" * 40,
    )

    snapshot = manager.start(8765)

    assert snapshot.actual_port == 43123
    assert snapshot.used_fallback_port is True
    assert factory.calls[0][0][-3:-1] == ["43123", "--log-level"]


def test_failed_child_startup_is_reported_without_retaining_credentials(monkeypatch):
    factory = ProcessFactory([FakeProcess(exit_code=7)])
    monkeypatch.setattr(module, "_port_is_available", lambda _port: True)
    manager = LocalServerProcessManager(
        process_factory=factory,
        health_probe=lambda _url, _timeout: False,
        token_factory=lambda: "f" * 40,
    )

    snapshot = manager.start()

    assert snapshot.state is LocalServerState.ERROR
    assert snapshot.error_code == "exited_during_startup"
    assert snapshot.message == "7"
    with pytest.raises(RuntimeError, match="not running"):
        manager.connection()


def test_health_timeout_forces_a_child_that_ignores_terminate(monkeypatch):
    process = FakeProcess(ignore_terminate=True)
    factory = ProcessFactory([process])
    monkeypatch.setattr(module, "_port_is_available", lambda _port: True)
    manager = LocalServerProcessManager(
        process_factory=factory,
        health_probe=lambda _url, _timeout: False,
        token_factory=lambda: "h" * 40,
        startup_timeout=0.01,
        poll_interval=0.001,
    )

    snapshot = manager.start()

    assert snapshot.state is LocalServerState.ERROR
    assert process.terminated is True
    assert process.killed is True


def test_stop_and_restart_replace_the_session_token(monkeypatch):
    first = FakeProcess()
    second = FakeProcess()
    factory = ProcessFactory([first, second])
    monkeypatch.setattr(module, "_port_is_available", lambda _port: True)
    manager = LocalServerProcessManager(
        process_factory=factory,
        health_probe=lambda _url, _timeout: True,
        token_factory=_tokens(),
    )

    manager.start()
    first_authorization = manager.connection().authorization
    stopped = manager.stop()
    manager.start()
    second_authorization = manager.connection().authorization

    assert stopped.state is LocalServerState.STOPPED
    assert first.terminated is True
    assert first_authorization != second_authorization


def test_packaged_and_source_commands_use_the_same_server_entry_point(monkeypatch):
    monkeypatch.setattr(module.sys, "frozen", False, raising=False)
    source = module._server_command(9000)
    monkeypatch.setattr(module.sys, "frozen", True, raising=False)
    packaged = module._server_command(9000)

    assert source[1:3] == ["-m", "optees.local_server"]
    assert packaged[1] == "--local-server"
    assert source[-4:] == packaged[-4:]
