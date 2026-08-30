from __future__ import annotations

import asyncio
from time import monotonic, sleep

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from optees.interfaces.http.local_api import create_local_api  # noqa: E402

TOKEN = "test-token-" + "x" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class ASGIClient:
    def __init__(self, app) -> None:
        self._app = app
        self._loop = asyncio.new_event_loop()
        self._lifespan = app.router.lifespan_context(app)
        self._client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        )

    def __enter__(self):
        self._loop.run_until_complete(self._lifespan.__aenter__())
        self._loop.run_until_complete(self._client.__aenter__())
        return self

    def __exit__(self, exc_type, exc, traceback):
        self._loop.run_until_complete(self._client.__aexit__(exc_type, exc, traceback))
        self._loop.run_until_complete(self._lifespan.__aexit__(exc_type, exc, traceback))
        self._loop.close()

    def get(self, path: str, **kwargs):
        return self._loop.run_until_complete(self._client.get(path, **kwargs))

    def post(self, path: str, **kwargs):
        return self._loop.run_until_complete(self._client.post(path, **kwargs))


def _loss_payload() -> dict:
    return {
        "version": "1",
        "problem_type": "linear_scenario",
        "orientation": "minimize_maximum_loss",
        "variables": [
            {"name": "x1", "lower_bound": 0.0, "upper_bound": 10.0},
            {"name": "x2", "lower_bound": 0.0, "upper_bound": 10.0},
        ],
        "scenarios": [
            {"id": "s1", "coefficients": [2.0, -1.0], "offset": 5.0},
            {"id": "s2", "coefficients": [-1.0, 3.0], "offset": 2.0},
            {"id": "s3", "coefficients": [1.0, 1.0], "offset": -4.0},
        ],
        "shared_constraints": [
            {
                "name": "budget",
                "coefficients": [1.0, 1.0],
                "relation": "=",
                "rhs": 10.0,
            }
        ],
    }


def test_api_list_capabilities_contains_scenario_capabilities() -> None:
    app = create_local_api(token=TOKEN)
    with ASGIClient(app) as client:
        response = client.get("/api/v1/capabilities", headers=AUTH)
        assert response.status_code == 200
        cap_ids = [c["id"] for c in response.json()["capabilities"]]
        assert "scenario.linear.min_max_loss" in cap_ids
        assert "scenario.linear.max_min_reward" in cap_ids


def test_api_validate_scenario_problem() -> None:
    app = create_local_api(token=TOKEN)
    with ASGIClient(app) as client:
        response = client.post(
            "/api/v1/problems/validate",
            headers=AUTH,
            json={
                "capability_id": "scenario.linear.min_max_loss",
                "problem": _loss_payload(),
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is True


def test_api_solve_scenario_problem_job() -> None:
    app = create_local_api(token=TOKEN)
    with ASGIClient(app) as client:
        submitted = client.post(
            "/api/v1/jobs",
            headers=AUTH,
            json={
                "capability_id": "scenario.linear.min_max_loss",
                "problem": _loss_payload(),
            },
        )
        assert submitted.status_code == 202
        job_id = submitted.json()["job_id"]

        deadline = monotonic() + 5
        snapshot = None
        while monotonic() < deadline:
            snapshot = client.get(f"/api/v1/jobs/{job_id}", headers=AUTH)
            if snapshot.json()["job_status"] == "completed":
                break
            sleep(0.01)

        result_resp = client.get(f"/api/v1/jobs/{job_id}/result", headers=AUTH)

    assert snapshot is not None
    assert snapshot.json()["job_status"] == "completed"
    assert snapshot.json()["mathematical_status"] == "optimal"
    assert result_resp.status_code == 200
    res_data = result_resp.json()
    assert res_data["result"]["orientation"] == "minimize_maximum_loss"
    assert res_data["result"]["guaranteed_value"] == pytest.approx(76.0 / 7.0)
    assert res_data["validation"]["status"] == "verified"
