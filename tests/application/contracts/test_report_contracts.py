from __future__ import annotations

import pytest

from optees.application.codecs.report_request_codec import report_request_from_dict
from optees.application.contracts.report import ReportFormat


def _request() -> dict:
    return {
        "contract_version": "1",
        "format": "markdown",
        "locale": "en",
        "title": "Production report",
        "sections": [
            {
                "section_id": "summary",
                "heading": "Executive summary",
                "blocks": [
                    {"type": "markdown", "content": "The plan is feasible."},
                    {"type": "job_status", "job_id": "job-123"},
                    {
                        "type": "artifact",
                        "artifact_id": "artifact-123",
                        "caption": "Production plan",
                    },
                ],
            }
        ],
        "metadata": {"author": "Example organization"},
    }


def test_report_codec_builds_a_strict_versioned_request():
    request = report_request_from_dict(_request())

    assert request.format is ReportFormat.MARKDOWN
    assert request.locale == "en"
    assert request.to_dict() == _request()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda payload: payload["sections"][0]["blocks"][0].update(
                {"content": "<script>alert(1)</script>"}
            ),
            "raw HTML",
        ),
        (
            lambda payload: payload["sections"][0]["blocks"][0].update(
                {"content": "[external](https://example.com)"}
            ),
            "external or unsafe",
        ),
        (
            lambda payload: payload.update({"destination_path": "/tmp/report.md"}),
            "unsupported fields",
        ),
        (
            lambda payload: payload["sections"][0]["blocks"][0].update(
                {"type": "shell"}
            ),
            "not a supported",
        ),
    ],
)
def test_report_codec_rejects_unsafe_or_undeclared_input(mutation, message):
    payload = _request()
    mutation(payload)

    with pytest.raises(ValueError, match=message):
        report_request_from_dict(payload)
