from __future__ import annotations

from time import monotonic, sleep

from tests.interfaces.http.test_local_api import ASGIClient, AUTH, TOKEN
from optees.interfaces.http.local_api import create_local_api


def test_authenticated_report_lifecycle_returns_verified_markdown():
    body = {
        "contract_version": "1",
        "format": "markdown",
        "locale": "en",
        "title": "Operations report",
        "sections": [
            {
                "section_id": "summary",
                "heading": "Summary",
                "blocks": [{"type": "markdown", "content": "The plan is feasible."}],
            }
        ],
        "metadata": {"author": "Example"},
    }
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        created = client.post("/api/v1/reports", headers=AUTH, json=body)
        assert created.status_code == 202
        report_id = created.json()["report_id"]
        deadline = monotonic() + 5
        status = None
        while monotonic() < deadline:
            status = client.get(f"/api/v1/reports/{report_id}", headers=AUTH)
            if status.json()["status"] == "available":
                break
            sleep(0.01)
        downloaded = client.get(
            f"/api/v1/reports/{report_id}/download",
            headers=AUTH,
        )

    assert status is not None
    assert status.json()["status"] == "available"
    assert downloaded.status_code == 200
    assert downloaded.headers["x-content-sha256"] == status.json()["sha256"]
    assert downloaded.headers["content-disposition"].endswith(f'"{report_id}.md"')
    assert "Optees · optees.it" in downloaded.text


def test_report_api_rejects_raw_html_and_arbitrary_destination_fields():
    body = {
        "contract_version": "1",
        "format": "markdown",
        "locale": "en",
        "title": "Unsafe",
        "sections": [
            {
                "section_id": "summary",
                "heading": "Summary",
                "blocks": [
                    {"type": "markdown", "content": "<script>alert(1)</script>"}
                ],
            }
        ],
    }
    with ASGIClient(create_local_api(token=TOKEN)) as client:
        unsafe = client.post("/api/v1/reports", headers=AUTH, json=body)
        arbitrary = client.post(
            "/api/v1/reports",
            headers=AUTH,
            json={**body, "destination_path": "/tmp/report.md"},
        )

    assert unsafe.status_code == 400
    assert unsafe.json()["error"]["code"] == "report_request_invalid"
    assert arbitrary.status_code == 422
    assert "/tmp/report.md" not in arbitrary.text
