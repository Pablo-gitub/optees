from __future__ import annotations

import asyncio
from time import monotonic, sleep

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from optees.interfaces.http.local_api import create_local_api, run_local_api


TOKEN = "test-token-" + "x" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class ASGIClient:
    """Small synchronous harness over HTTPX's non-deprecated ASGI transport."""

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
        self._loop.run_until_complete(
            self._lifespan.__aexit__(exc_type, exc, traceback)
        )
        self._loop.close()

    def get(self, path: str, **kwargs):
        return self._loop.run_until_complete(self._client.get(path, **kwargs))

    def post(self, path: str, **kwargs):
        return self._loop.run_until_complete(self._client.post(path, **kwargs))


def _lp_payload() -> dict:
    return {
        "version": "1",
        "variables": [{"name": "x", "label": "", "lb": 0, "ub": 1}],
        "objective": {"sense": "max", "coefficients": [1], "offset": 0},
        "constraints": [],
    }


def _problem_request() -> dict:
    return {"capability_id": "lp.continuous", "problem": _lp_payload()}


def _batch_request() -> dict:
    return {
        "version": "1",
        "items": [
            {
                "client_item_id": f"scenario-{index}",
                "capability_id": "lp.continuous",
                "problem": _lp_payload(),
            }
            for index in range(1, 3)
        ],
    }


def _error_code(response) -> str:
    return response.json()["error"]["code"]


def test_configuration_rejects_weak_tokens_invalid_limits_and_non_loopback_host():
    with pytest.raises(ValueError, match="at least 32"):
        create_local_api(token="weak")
    with pytest.raises(ValueError, match="positive integer"):
        create_local_api(token=TOKEN, max_request_bytes=0)
    with pytest.raises(ValueError, match="only to 127.0.0.1"):
        run_local_api(token=TOKEN, host="0.0.0.0")


def test_health_is_public_but_info_requires_constant_contract_authentication():
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        health = client.get("/health")
        missing = client.get("/api/v1/info")
        wrong = client.get(
            "/api/v1/info",
            headers={"Authorization": "Bearer " + "y" * 40},
        )
        info = client.get("/api/v1/info", headers=AUTH)

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "api_version": "v1"}
    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.headers["WWW-Authenticate"] == "Bearer"
    assert _error_code(missing) == "authentication_failed"
    assert info.status_code == 200
    assert info.json()["bind_scope"] == "loopback_only"
    assert "token" not in str(info.json()).lower()


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("get", "/api/v1/capabilities", {}),
        ("get", "/api/v1/capabilities/lp.continuous", {}),
        ("post", "/api/v1/problems/validate", {"json": _problem_request()}),
        ("post", "/api/v1/jobs", {"json": _problem_request()}),
        ("get", "/api/v1/jobs", {}),
        ("get", "/api/v1/jobs/missing", {}),
        ("get", "/api/v1/jobs/missing/result", {}),
        ("post", "/api/v1/jobs/missing/cancel", {"json": {}}),
        (
            "post",
            "/api/v1/jobs/missing/artifacts",
            {
                "json": {
                    "contract_version": "1",
                    "requests": [
                        {
                            "artifact_type": "solution_table",
                            "formats": ["csv"],
                            "options": {},
                        }
                    ],
                }
            },
        ),
        ("get", "/api/v1/jobs/missing/artifacts", {}),
        ("get", "/api/v1/artifacts/artifact-missing", {}),
        (
            "post",
            "/api/v1/reports",
            {
                "json": {
                    "contract_version": "1",
                    "format": "markdown",
                    "locale": "en",
                    "title": "Test",
                    "sections": [
                        {
                            "section_id": "summary",
                            "heading": "Summary",
                            "blocks": [{"type": "markdown", "content": "Body"}],
                        }
                    ],
                }
            },
        ),
        ("get", "/api/v1/reports/report-missing", {}),
        ("get", "/api/v1/reports/report-missing/download", {}),
        ("post", "/api/v1/batches/validate", {"json": _batch_request()}),
        ("post", "/api/v1/batches", {"json": _batch_request()}),
        ("get", "/api/v1/batches/missing", {}),
        ("get", "/api/v1/batches/missing/result", {}),
        ("post", "/api/v1/batches/missing/cancel", {"json": {}}),
        ("get", "/api/v1/openapi.json", {}),
    ],
)
def test_every_documented_endpoint_except_health_requires_auth(method, path, kwargs):
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 401
    assert _error_code(response) == "authentication_failed"


def test_request_ids_are_returned_and_propagated_to_structured_errors():
    headers = {**AUTH, "X-Request-ID": "request-from-client"}
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        response = client.get("/api/v1/jobs/missing", headers=headers)

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "request-from-client"
    assert response.json()["error"]["request_id"] == "request-from-client"
    assert _error_code(response) == "job_not_found"


def test_discovery_exposes_capability_contracts_without_cors_headers():
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        response = client.get("/api/v1/capabilities", headers=AUTH)
        packing = client.get(
            "/api/v1/capabilities/packing.single_container_3d",
            headers=AUTH,
        )
        missing = client.get("/api/v1/capabilities/missing", headers=AUTH)

    capability_ids = {item["id"] for item in response.json()["capabilities"]}
    assert response.status_code == 200
    assert "lp.continuous" in capability_ids
    assert "packing.single_container_3d" in capability_ids
    assert "access-control-allow-origin" not in response.headers
    assert packing.json()["supports_cancellation"] is True
    assert missing.status_code == 404
    assert _error_code(missing) == "capability_not_found"


def test_validate_returns_success_and_structured_domain_failures():
    invalid = _problem_request()
    invalid["problem"]["objective"]["coefficients"] = [1, 2]
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        valid_response = client.post(
            "/api/v1/problems/validate",
            headers=AUTH,
            json=_problem_request(),
        )
        invalid_response = client.post(
            "/api/v1/problems/validate",
            headers=AUTH,
            json=invalid,
        )

    assert valid_response.status_code == 200
    assert valid_response.json()["valid"] is True
    assert invalid_response.status_code == 422
    assert _error_code(invalid_response) == "validation_failed"


def test_http_contract_validation_does_not_echo_rejected_payload_values():
    body = _problem_request()
    body["unexpected"] = "CONFIDENTIAL-CUSTOMER-VALUE"
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        response = client.post(
            "/api/v1/jobs",
            headers=AUTH,
            json=body,
        )

    assert response.status_code == 422
    assert _error_code(response) == "invalid_request"
    assert "CONFIDENTIAL-CUSTOMER-VALUE" not in response.text


def test_mutation_endpoints_enforce_json_content_type_and_body_size():
    with ASGIClient(
        create_local_api(token=TOKEN, max_request_bytes=100)
    ) as client:
        wrong_type = client.post(
            "/api/v1/jobs",
            headers=AUTH,
            content="{}",
        )
        oversized = client.post(
            "/api/v1/jobs",
            headers={**AUTH, "Content-Type": "application/json"},
            content="{" + '"padding":"' + "x" * 200 + '"}',
        )

    assert wrong_type.status_code == 415
    assert oversized.status_code == 413
    assert _error_code(wrong_type) == "invalid_request"
    assert _error_code(oversized) == "invalid_request"


def test_job_api_executes_from_submission_to_versioned_result():
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        submitted = client.post(
            "/api/v1/jobs",
            headers=AUTH,
            json=_problem_request(),
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

        result = client.get(f"/api/v1/jobs/{job_id}/result", headers=AUTH)
        jobs = client.get("/api/v1/jobs", headers=AUTH)

    assert snapshot is not None
    assert snapshot.json()["job_status"] == "completed"
    assert snapshot.json()["mathematical_status"] == "optimal"
    assert result.status_code == 200
    assert result.json()["job_id"] == job_id
    assert result.json()["result"]["objective"] == pytest.approx(1.0)
    assert job_id in {item["job_id"] for item in jobs.json()["jobs"]}


def test_cancel_and_result_for_unknown_job_use_stable_status_codes():
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        cancelled = client.post(
            "/api/v1/jobs/missing/cancel",
            headers=AUTH,
            json={},
        )
        result = client.get("/api/v1/jobs/missing/result", headers=AUTH)

    assert cancelled.status_code == 404
    assert result.status_code == 404
    assert _error_code(cancelled) == "job_not_found"
    assert _error_code(result) == "job_not_found"


def test_batch_api_validates_submits_and_aggregates_individual_results():
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        validated = client.post(
            "/api/v1/batches/validate",
            headers=AUTH,
            json=_batch_request(),
        )
        submitted = client.post(
            "/api/v1/batches",
            headers=AUTH,
            json=_batch_request(),
        )
        batch_id = submitted.json()["batch_id"]

        deadline = monotonic() + 5
        snapshot = None
        while monotonic() < deadline:
            snapshot = client.get(f"/api/v1/batches/{batch_id}", headers=AUTH)
            if snapshot.json()["batch_status"] == "completed":
                break
            sleep(0.01)
        result = client.get(
            f"/api/v1/batches/{batch_id}/result",
            headers=AUTH,
        )

    assert validated.status_code == 200
    assert validated.json()["valid"] is True
    assert submitted.status_code == 202
    assert snapshot is not None
    assert snapshot.json()["counts"] == {"completed": 2}
    assert result.status_code == 200
    assert result.json()["summary"]["mathematical_status_counts"] == {
        "optimal": 2
    }
    assert result.json()["summary"]["validation_status_counts"] == {
        "verified": 2
    }


def test_batch_api_rejects_duplicate_client_ids_as_invalid_request():
    duplicate = _batch_request()
    duplicate["items"][1]["client_item_id"] = "scenario-1"
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        response = client.post(
            "/api/v1/batches",
            headers=AUTH,
            json=duplicate,
        )

    assert response.status_code == 400
    assert _error_code(response) == "invalid_request"


def test_authenticated_openapi_matches_routes_and_bearer_security():
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        response = client.get("/api/v1/openapi.json", headers=AUTH)

    document = response.json()
    expected_paths = {
        "/health",
        "/api/v1/info",
        "/api/v1/capabilities",
        "/api/v1/capabilities/{capability_id}",
        "/api/v1/problems/validate",
        "/api/v1/jobs",
        "/api/v1/jobs/{job_id}",
        "/api/v1/jobs/{job_id}/result",
        "/api/v1/jobs/{job_id}/cancel",
            "/api/v1/jobs/{job_id}/artifacts",
            "/api/v1/artifacts/{artifact_id}",
            "/api/v1/artifacts/{artifact_id}/cancel",
            "/api/v1/reports",
            "/api/v1/reports/backends",
            "/api/v1/reports/{report_id}",
            "/api/v1/reports/{report_id}/cancel",
            "/api/v1/reports/{report_id}/download",
        "/api/v1/batches/validate",
        "/api/v1/batches",
        "/api/v1/batches/{batch_id}",
        "/api/v1/batches/{batch_id}/result",
        "/api/v1/batches/{batch_id}/cancel",
        "/api/v1/openapi.json",
    }
    assert response.status_code == 200
    assert set(document["paths"]) == expected_paths
    assert "HTTPBearer" in document["components"]["securitySchemes"]
    assert "security" not in document["paths"]["/health"]["get"]
    assert document["paths"]["/api/v1/info"]["get"]["security"] == [
        {"HTTPBearer": []}
    ]
