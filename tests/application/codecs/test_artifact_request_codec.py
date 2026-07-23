from __future__ import annotations

import pytest

from optees.application.codecs.artifact_request_codec import (
    artifact_batch_request_from_dict,
)
from optees.application.contracts.artifact import ArtifactFormat


def test_artifact_request_codec_normalizes_transport_payload():
    request = artifact_batch_request_from_dict(
        [
            {
                "artifact_type": "solution_table",
                "formats": ["json", "csv"],
                "options": {"locale": "it"},
            }
        ]
    )

    assert request.contract_version == "1"
    assert request.requests[0].formats == (
        ArtifactFormat.JSON,
        ArtifactFormat.CSV,
    )
    assert request.requests[0].options == {"locale": "it"}


@pytest.mark.parametrize(
    "payload, message",
    [
        ([{"artifact_type": "solution_table", "formats": "json"}], "array"),
        ([{"artifact_type": "solution_table", "formats": ["pdf"]}], "unsupported"),
        ([{"artifact_type": "solution_table", "formats": ["json"], "options": []}], "object"),
    ],
)
def test_artifact_request_codec_rejects_invalid_transport_values(payload, message):
    with pytest.raises(ValueError, match=message):
        artifact_batch_request_from_dict(payload)
