from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from enum import Enum
from threading import Event, RLock
from time import monotonic, sleep
from typing import Protocol
from urllib.request import Request, urlopen


LOOPBACK_HOST = "127.0.0.1"
DEFAULT_LOCAL_SERVER_PORT = 8765
LOCAL_SERVER_TOKEN_ENV = "OPTEES_LOCAL_SERVER_TOKEN"


class LocalServerState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass(frozen=True)
class LocalServerSnapshot:
    state: LocalServerState
    requested_port: int = DEFAULT_LOCAL_SERVER_PORT
    actual_port: int | None = None
    url: str | None = None
    used_fallback_port: bool = False
    error_code: str = ""
    message: str = ""


@dataclass(frozen=True)
class LocalServerConnection:
    base_url: str
    authorization: str
    openapi_url: str
    api_version: str = "v1"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class ProcessHandle(Protocol):
    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...

    def kill(self) -> None: ...


ProcessFactory = Callable[[list[str], Mapping[str, str]], ProcessHandle]
HealthProbe = Callable[[str, float], bool]


class LocalServerProcessManager:
    """Own one loopback server subprocess and its session-only credentials."""

    def __init__(
        self,
        *,
        process_factory: ProcessFactory | None = None,
        health_probe: HealthProbe | None = None,
        token_factory: Callable[[], str] | None = None,
        startup_timeout: float = 8.0,
        poll_interval: float = 0.05,
    ) -> None:
        if startup_timeout <= 0:
            raise ValueError("startup_timeout must be positive")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        self._process_factory = process_factory or _start_server_process
        self._health_probe = health_probe or _health_probe
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._startup_timeout = startup_timeout
        self._poll_interval = poll_interval
        self._lock = RLock()
        self._shutdown_requested = Event()
        self._process: ProcessHandle | None = None
        self._token: str | None = None
        self._snapshot = LocalServerSnapshot(LocalServerState.STOPPED)

    @property
    def snapshot(self) -> LocalServerSnapshot:
        with self._lock:
            return self._snapshot

    def start(self, requested_port: int = DEFAULT_LOCAL_SERVER_PORT) -> LocalServerSnapshot:
        port = _validated_port(requested_port)
        self._shutdown_requested.clear()
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return self._snapshot
            self._process = None
            self._token = None
            self._snapshot = LocalServerSnapshot(
                LocalServerState.STARTING,
                requested_port=port,
            )

        actual_port = port if _port_is_available(port) else _available_port()
        used_fallback = actual_port != port
        token = self._token_factory()
        if len(token) < 32:
            return self._set_error(port, "invalid_token")
        environment = dict(os.environ)
        environment[LOCAL_SERVER_TOKEN_ENV] = token

        try:
            process = self._process_factory(_server_command(actual_port), environment)
        except Exception:
            return self._set_error(port, "start_failed")

        with self._lock:
            self._process = process
            self._token = token

        url = f"http://{LOOPBACK_HOST}:{actual_port}"
        deadline = monotonic() + self._startup_timeout
        while monotonic() < deadline:
            if self._shutdown_requested.is_set():
                self._terminate_process(process)
                with self._lock:
                    self._process = None
                    self._token = None
                    self._snapshot = LocalServerSnapshot(
                        LocalServerState.STOPPED,
                        requested_port=port,
                    )
                    return self._snapshot
            exit_code = process.poll()
            if exit_code is not None:
                self._terminate_process(process)
                return self._set_error(
                    port,
                    "exited_during_startup",
                    str(exit_code),
                )
            if self._health_probe(f"{url}/health", min(0.5, self._poll_interval * 4)):
                snapshot = LocalServerSnapshot(
                    LocalServerState.RUNNING,
                    requested_port=port,
                    actual_port=actual_port,
                    url=url,
                    used_fallback_port=used_fallback,
                )
                with self._lock:
                    self._snapshot = snapshot
                return snapshot
            sleep(self._poll_interval)

        self._terminate_process(process)
        return self._set_error(port, "health_timeout")

    def stop(self) -> LocalServerSnapshot:
        with self._lock:
            process = self._process
            requested_port = self._snapshot.requested_port
            if process is None:
                self._token = None
                self._snapshot = LocalServerSnapshot(
                    LocalServerState.STOPPED,
                    requested_port=requested_port,
                )
                return self._snapshot
            self._snapshot = LocalServerSnapshot(
                LocalServerState.STOPPING,
                requested_port=requested_port,
                actual_port=self._snapshot.actual_port,
                url=self._snapshot.url,
                used_fallback_port=self._snapshot.used_fallback_port,
            )

        self._terminate_process(process)
        with self._lock:
            self._process = None
            self._token = None
            self._snapshot = LocalServerSnapshot(
                LocalServerState.STOPPED,
                requested_port=requested_port,
            )
            return self._snapshot

    def connection(self) -> LocalServerConnection:
        with self._lock:
            snapshot = self._snapshot
            token = self._token
        if snapshot.state is not LocalServerState.RUNNING or not snapshot.url or not token:
            raise RuntimeError("the local server is not running")
        return LocalServerConnection(
            base_url=snapshot.url,
            authorization=f"Bearer {token}",
            openapi_url=f"{snapshot.url}/api/v1/openapi.json",
        )

    def connection_json(self) -> str:
        return json.dumps(self.connection().to_dict(), indent=2, sort_keys=True)

    def openapi_document(self, timeout: float = 2.0) -> dict[str, object]:
        connection = self.connection()
        request = Request(
            connection.openapi_url,
            headers={"Authorization": connection.authorization},
        )
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
        if not isinstance(payload, dict):
            raise RuntimeError("the OpenAPI response is not a JSON object")
        return payload

    def shutdown(self) -> None:
        self._shutdown_requested.set()
        self.stop()

    def _set_error(
        self,
        requested_port: int,
        error_code: str,
        message: str = "",
    ) -> LocalServerSnapshot:
        with self._lock:
            self._process = None
            self._token = None
            self._snapshot = LocalServerSnapshot(
                LocalServerState.ERROR,
                requested_port=requested_port,
                error_code=error_code,
                message=message,
            )
            return self._snapshot

    @staticmethod
    def _terminate_process(process: ProcessHandle) -> None:
        if process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=3.0)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
                process.wait(timeout=1.0)
            except (OSError, subprocess.TimeoutExpired):
                pass


def _validated_port(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535:
        raise ValueError("port must be an integer in [1, 65535]")
    return value


def _server_command(port: int) -> list[str]:
    arguments = ["--port", str(port), "--log-level", "warning"]
    if getattr(sys, "frozen", False):
        return [sys.executable, "--local-server", *arguments]
    return [sys.executable, "-m", "optees.local_server", *arguments]


def _start_server_process(
    command: list[str],
    environment: Mapping[str, str],
) -> ProcessHandle:
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        command,
        env=dict(environment),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creation_flags,
    )


def _health_probe(url: str, timeout: float) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            payload = json.load(response)
        return response.status == 200 and payload.get("status") == "ok"
    except (OSError, ValueError):
        return False


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        try:
            candidate.bind((LOOPBACK_HOST, port))
        except OSError:
            return False
    return True


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        candidate.bind((LOOPBACK_HOST, 0))
        return int(candidate.getsockname()[1])
