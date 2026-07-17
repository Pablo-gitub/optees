from __future__ import annotations

import socket
from threading import Thread
from time import monotonic, sleep

import pytest

httpx = pytest.importorskip("httpx")
uvicorn = pytest.importorskip("uvicorn")
pytest.importorskip("fastapi")

from optees.interfaces.http.local_api import LOOPBACK_HOST, create_local_api


TOKEN = "tcp-test-token-" + "x" * 32


def _problem_request() -> dict:
    return {
        "capability_id": "lp.continuous",
        "problem": {
            "version": "1",
            "variables": [{"name": "x", "label": "", "lb": 0, "ub": 1}],
            "objective": {
                "sense": "max",
                "coefficients": [1],
                "offset": 0,
            },
            "constraints": [],
        },
    }


def test_real_loopback_server_runs_health_discovery_job_and_result():
    app = create_local_api(token=TOKEN)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((LOOPBACK_HOST, 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    config = uvicorn.Config(
        app,
        host=LOOPBACK_HOST,
        port=port,
        log_level="critical",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = Thread(
        target=server.run,
        kwargs={"sockets": [sock]},
        name="optees-api-e2e",
        daemon=True,
    )
    thread.start()
    deadline = monotonic() + 5
    while not server.started and monotonic() < deadline:
        sleep(0.01)
    assert server.started

    base_url = f"http://{LOOPBACK_HOST}:{port}"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        with httpx.Client(base_url=base_url, timeout=5) as client:
            assert client.get("/health").json()["status"] == "ok"
            capabilities = client.get(
                "/api/v1/capabilities",
                headers=headers,
            )
            assert capabilities.status_code == 200
            assert any(
                item["id"] == "lp.continuous"
                for item in capabilities.json()["capabilities"]
            )

            submitted = client.post(
                "/api/v1/jobs",
                headers=headers,
                json=_problem_request(),
            )
            assert submitted.status_code == 202
            job_id = submitted.json()["job_id"]

            snapshot = None
            deadline = monotonic() + 5
            while monotonic() < deadline:
                snapshot = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
                if snapshot.json()["job_status"] == "completed":
                    break
                sleep(0.01)
            assert snapshot is not None
            assert snapshot.json()["job_status"] == "completed"

            result = client.get(
                f"/api/v1/jobs/{job_id}/result",
                headers=headers,
            )
            assert result.status_code == 200
            assert result.json()["mathematical_status"] == "optimal"
            assert result.json()["result"]["objective"] == pytest.approx(1.0)
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
    assert not thread.is_alive()
