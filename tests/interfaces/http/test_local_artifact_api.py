from __future__ import annotations

import asyncio
from time import monotonic, sleep

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from optees.application.contracts.artifact import (
    ArtifactFormat,
    AvailableArtifact,
)
from optees.application.contracts.artifact_rendering import (
    ArtifactRenderContext,
    RenderedArtifact,
)
from optees.application.contracts.execution import MathematicalStatus
from optees.application.services.artifact_generation_service import (
    ArtifactGenerationService,
    ArtifactRendererRegistration,
)
from optees.composition.local_agent import create_local_job_service
from optees.data.adapters.artifacts.local_artifact_store import LocalArtifactStore
from optees.interfaces.http.local_api import create_local_api


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
        self._loop.run_until_complete(
            self._lifespan.__aexit__(exc_type, exc, traceback)
        )
        self._loop.close()

    def get(self, path: str, **kwargs):
        return self._loop.run_until_complete(self._client.get(path, **kwargs))

    def post(self, path: str, **kwargs):
        return self._loop.run_until_complete(self._client.post(path, **kwargs))


class CsvRenderer:
    renderer_version = "test-http-1"

    def render(self, _context: ArtifactRenderContext) -> RenderedArtifact:
        return RenderedArtifact("text/csv", b"variable,value\nx,1\n")


def _lp_payload() -> dict:
    return {
        "version": "1",
        "variables": [{"name": "x", "label": "", "lb": 0, "ub": 1}],
        "objective": {"sense": "max", "coefficients": [1], "offset": 0},
        "constraints": [],
    }


def _lp_2d_payload() -> dict:
    return {
        "version": "1",
        "variables": [
            {"name": "x", "label": "Product X", "lb": 0, "ub": 4},
            {"name": "y", "label": "Product Y", "lb": 0, "ub": 4},
        ],
        "objective": {"sense": "max", "coefficients": [1, 1], "offset": 0},
        "constraints": [
            {"coefficients": [1, 1], "relation": "<=", "rhs": 4}
        ],
    }


def _artifact_request() -> dict:
    return {
        "contract_version": "1",
        "requests": [
            {
                "artifact_type": "solution_table",
                "formats": ["csv"],
                "options": {"locale": "en"},
            }
        ],
    }


def _app(tmp_path):
    jobs = create_local_job_service()
    artifacts = ArtifactGenerationService(
        jobs,
        LocalArtifactStore(parent_directory=tmp_path),
        registrations=(
            ArtifactRendererRegistration(
                capability_id="lp.continuous",
                descriptor=AvailableArtifact(
                    "solution_table",
                    "Solution table",
                    (ArtifactFormat.CSV,),
                    (MathematicalStatus.OPTIMAL,),
                ),
                renderer=CsvRenderer(),
                media_types={ArtifactFormat.CSV: "text/csv"},
            ),
        ),
    )
    return create_local_api(
        token=TOKEN,
        job_service=jobs,
        artifact_service=artifacts,
    )


def test_artifact_routes_require_authentication(tmp_path):
    with ASGIClient(_app(tmp_path)) as client:
        create = client.post(
            "/api/v1/jobs/missing/artifacts",
            json=_artifact_request(),
        )
        listing = client.get("/api/v1/jobs/missing/artifacts")
        download = client.get("/api/v1/artifacts/artifact-missing")

    assert create.status_code == 401
    assert listing.status_code == 401
    assert download.status_code == 401


def test_rest_artifact_generation_polling_and_verified_download(tmp_path):
    with ASGIClient(_app(tmp_path)) as client:
        submitted = client.post(
            "/api/v1/jobs",
            headers=AUTH,
            json={"capability_id": "lp.continuous", "problem": _lp_payload()},
        )
        job_id = submitted.json()["job_id"]
        deadline = monotonic() + 5
        while monotonic() < deadline:
            job = client.get(f"/api/v1/jobs/{job_id}", headers=AUTH)
            if job.json()["job_status"] == "completed":
                break
            sleep(0.01)

        created = client.post(
            f"/api/v1/jobs/{job_id}/artifacts",
            headers=AUTH,
            json=_artifact_request(),
        )
        assert created.status_code == 202

        artifact = None
        while monotonic() < deadline:
            listing = client.get(
                f"/api/v1/jobs/{job_id}/artifacts",
                headers=AUTH,
            )
            artifact = listing.json()["artifact_batches"][0]["artifacts"][0]
            if artifact["status"] == "available":
                break
            sleep(0.01)

        assert artifact is not None
        downloaded = client.get(
            f"/api/v1/artifacts/{artifact['artifact_id']}",
            headers=AUTH,
        )

    assert artifact["status"] == "available"
    assert downloaded.status_code == 200
    assert downloaded.content == b"variable,value\nx,1\n"
    assert downloaded.headers["content-type"].startswith("text/csv")
    assert downloaded.headers["x-content-sha256"] == artifact["sha256"]
    assert downloaded.headers["etag"] == f'"sha256-{artifact["sha256"]}"'
    assert downloaded.headers["cache-control"] == "private, no-store"


def test_artifact_http_validation_is_atomic_and_does_not_echo_values(tmp_path):
    request = _artifact_request()
    request["requests"][0]["formats"] = ["csv", "csv"]
    request["requests"][0]["options"] = {
        "locale": "CONFIDENTIAL-CUSTOMER-VALUE"
    }
    with ASGIClient(_app(tmp_path)) as client:
        response = client.post(
            "/api/v1/jobs/missing/artifacts",
            headers=AUTH,
            json=request,
        )

    assert response.status_code in {400, 404}
    assert "CONFIDENTIAL-CUSTOMER-VALUE" not in response.text


def test_production_composition_advertises_and_renders_lp_tables():
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        capabilities = client.get("/api/v1/capabilities", headers=AUTH)
        lp = next(
            item
            for item in capabilities.json()["capabilities"]
            if item["id"] == "lp.continuous"
        )
        assert lp["available_artifacts"] == [
            {
                "artifact_type": "solution_table",
                "title": "LP solution",
                "formats": ["json", "csv", "markdown"],
                "required_mathematical_statuses": ["optimal", "feasible"],
                "options_schema": {
                    "type": "object",
                    "properties": {
                        "locale": {"enum": ["en", "it"]},
                        "max_rows": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 1000,
                        },
                    },
                    "additionalProperties": False,
                },
            },
            {
                "artifact_type": "feasible_region",
                "title": "LP feasible region (2D/3D)",
                "formats": ["svg", "png"],
                "required_mathematical_statuses": ["optimal"],
                "options_schema": {
                    "type": "object",
                    "properties": {
                        "locale": {"enum": ["en", "it"]},
                        "theme": {"enum": ["light", "dark"]},
                        "width": {
                            "type": "integer",
                            "minimum": 320,
                            "maximum": 4096,
                        },
                        "height": {
                            "type": "integer",
                            "minimum": 240,
                            "maximum": 4096,
                        },
                    },
                    "additionalProperties": False,
                },
            },
        ]

        submitted = client.post(
            "/api/v1/jobs",
            headers=AUTH,
            json={"capability_id": "lp.continuous", "problem": _lp_2d_payload()},
        )
        job_id = submitted.json()["job_id"]
        deadline = monotonic() + 5
        while monotonic() < deadline:
            job = client.get(f"/api/v1/jobs/{job_id}", headers=AUTH)
            if job.json()["job_status"] == "completed":
                break
            sleep(0.01)

        created = client.post(
            f"/api/v1/jobs/{job_id}/artifacts",
            headers=AUTH,
            json={
                "contract_version": "1",
                "requests": [
                    {
                        "artifact_type": "solution_table",
                        "formats": ["json", "csv"],
                        "options": {"locale": "en"},
                    },
                    {
                        "artifact_type": "feasible_region",
                        "formats": ["png"],
                        "options": {
                            "locale": "en",
                            "theme": "dark",
                            "width": 480,
                            "height": 320,
                        },
                    }
                ],
            },
        )
        assert created.status_code == 202

        artifacts = []
        while monotonic() < deadline:
            listing = client.get(
                f"/api/v1/jobs/{job_id}/artifacts",
                headers=AUTH,
            )
            artifacts = listing.json()["artifact_batches"][0]["artifacts"]
            if all(item["status"] == "available" for item in artifacts):
                break
            sleep(0.01)

        assert [item["format"] for item in artifacts] == ["json", "csv", "png"]
        json_artifact = client.get(
            f"/api/v1/artifacts/{artifacts[0]['artifact_id']}",
            headers=AUTH,
        )
        csv_artifact = client.get(
            f"/api/v1/artifacts/{artifacts[1]['artifact_id']}",
            headers=AUTH,
        )
        png_artifact = client.get(
            f"/api/v1/artifacts/{artifacts[2]['artifact_id']}",
            headers=AUTH,
        )

    result_rows = json_artifact.json()["rows"]
    assert [row["name"] for row in result_rows] == ["x", "y"]
    assert csv_artifact.text.startswith("name,value\nx,")
    assert png_artifact.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_production_artifact_options_are_rejected_atomically():
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        submitted = client.post(
            "/api/v1/jobs",
            headers=AUTH,
            json={"capability_id": "lp.continuous", "problem": _lp_payload()},
        )
        job_id = submitted.json()["job_id"]
        deadline = monotonic() + 5
        while monotonic() < deadline:
            job = client.get(f"/api/v1/jobs/{job_id}", headers=AUTH)
            if job.json()["job_status"] == "completed":
                break
            sleep(0.01)

        rejected = client.post(
            f"/api/v1/jobs/{job_id}/artifacts",
            headers=AUTH,
            json={
                "contract_version": "1",
                "requests": [
                    {
                        "artifact_type": "solution_table",
                        "formats": ["markdown"],
                        "options": {"max_rows": 0},
                    }
                ],
            },
        )
        listing = client.get(
            f"/api/v1/jobs/{job_id}/artifacts",
            headers=AUTH,
        )

    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "artifact_request_invalid"
    assert listing.json()["artifact_batches"] == []
