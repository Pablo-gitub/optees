from __future__ import annotations

from optees.application.services.local_server_process import LOCAL_SERVER_TOKEN_ENV
from optees import local_server


def test_server_entrypoint_requires_session_token(monkeypatch, capsys):
    monkeypatch.delenv(LOCAL_SERVER_TOKEN_ENV, raising=False)

    exit_code = local_server.main([])

    assert exit_code == 2
    assert LOCAL_SERVER_TOKEN_ENV in capsys.readouterr().err


def test_server_entrypoint_passes_validated_session_to_http_runner(monkeypatch):
    captured = {}
    token = "entrypoint-token-" + "x" * 32
    monkeypatch.setenv(LOCAL_SERVER_TOKEN_ENV, token)
    monkeypatch.setattr(
        "optees.interfaces.http.run_local_api",
        lambda **kwargs: captured.update(kwargs),
    )

    exit_code = local_server.main(["--port", "9020", "--log-level", "error"])

    assert exit_code == 0
    assert captured == {"token": token, "port": 9020, "log_level": "error"}
