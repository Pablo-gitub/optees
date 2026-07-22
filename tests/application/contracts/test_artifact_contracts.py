from __future__ import annotations

import json

import pytest

from optees.application.contracts.artifact import (
    ArtifactBatchManifest,
    ArtifactBatchRequest,
    ArtifactFormat,
    ArtifactManifestEntry,
    ArtifactProvenance,
    ArtifactRequest,
    ArtifactStatus,
    AvailableArtifact,
)
from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import MathematicalStatus


def _provenance(job_id: str = "job-1") -> ArtifactProvenance:
    return ArtifactProvenance(
        capability_id="lp.continuous",
        job_id=job_id,
        problem_schema_version="1",
        result_schema_version="1",
        renderer_version="1",
        locale="en",
        theme="light",
    )


def test_available_artifact_has_strict_discovery_shape():
    descriptor = AvailableArtifact(
        artifact_type="solution_table",
        title="Solution table",
        formats=(ArtifactFormat.JSON, ArtifactFormat.CSV),
        required_mathematical_statuses=(MathematicalStatus.OPTIMAL,),
        options_schema={"type": "object", "additionalProperties": False},
    )

    payload = descriptor.to_dict()

    assert payload["formats"] == ["json", "csv"]
    assert payload["required_mathematical_statuses"] == ["optimal"]
    json.dumps(payload, allow_nan=False)


def test_artifact_batch_counts_expanded_outputs():
    request = ArtifactBatchRequest(
        requests=(
            ArtifactRequest(
                artifact_type="solution_table",
                formats=(ArtifactFormat.JSON, ArtifactFormat.CSV),
                options={"locale": "it"},
            ),
        )
    )

    assert request.to_dict()["requests"][0]["options"] == {"locale": "it"}


def test_artifact_batch_rejects_duplicate_formats_and_too_many_requests():
    with pytest.raises(ValueError, match="duplicates"):
        ArtifactRequest(
            artifact_type="solution_table",
            formats=(ArtifactFormat.JSON, ArtifactFormat.JSON),
        )

    single = ArtifactRequest(
        artifact_type="solution_table",
        formats=(ArtifactFormat.JSON,),
    )
    with pytest.raises(ValueError, match="at most 8 requests"):
        ArtifactBatchRequest(requests=(single,) * 9)

    with pytest.raises(ValueError, match="duplicate outputs"):
        ArtifactBatchRequest(requests=(single, single))


def test_available_manifest_requires_hash_and_size_and_has_no_download_url():
    entry = ArtifactManifestEntry(
        artifact_id="artifact-1",
        artifact_type="solution_table",
        format=ArtifactFormat.CSV,
        media_type="text/csv",
        status=ArtifactStatus.AVAILABLE,
        provenance=_provenance(),
        created_at="2026-07-23T10:00:00Z",
        expires_at="2026-07-23T11:00:00Z",
        size_bytes=42,
        sha256="a" * 64,
    )
    manifest = ArtifactBatchManifest(
        artifact_batch_id="artifact-batch-1",
        job_id="job-1",
        artifacts=(entry,),
    )

    payload = manifest.to_dict()

    assert payload["artifacts"][0]["status"] == "available"
    assert "download_url" not in payload["artifacts"][0]
    json.dumps(payload, allow_nan=False)


def test_failed_manifest_requires_and_serializes_structured_error():
    error = StructuredError(
        code=ErrorCode.ARTIFACT_RENDER_FAILED,
        message="The artifact could not be rendered.",
    )
    entry = ArtifactManifestEntry(
        artifact_id="artifact-2",
        artifact_type="variable_chart",
        format=ArtifactFormat.SVG,
        media_type="image/svg+xml",
        status=ArtifactStatus.FAILED,
        provenance=_provenance(),
        created_at="2026-07-23T10:00:00Z",
        expires_at="2026-07-23T11:00:00Z",
        error=error,
    )

    assert entry.to_dict()["error"]["code"] == "artifact_render_failed"

    with pytest.raises(ValueError, match="require a structured error"):
        ArtifactManifestEntry(
            artifact_id="artifact-3",
            artifact_type="variable_chart",
            format=ArtifactFormat.SVG,
            media_type="image/svg+xml",
            status=ArtifactStatus.FAILED,
            provenance=_provenance(),
            created_at="2026-07-23T10:00:00Z",
            expires_at="2026-07-23T11:00:00Z",
        )


def test_manifest_rejects_artifact_from_another_job():
    entry = ArtifactManifestEntry(
        artifact_id="artifact-4",
        artifact_type="solution_table",
        format=ArtifactFormat.JSON,
        media_type="application/json",
        status=ArtifactStatus.QUEUED,
        provenance=_provenance("job-other"),
        created_at="2026-07-23T10:00:00Z",
        expires_at="2026-07-23T11:00:00Z",
    )

    with pytest.raises(ValueError, match="manifest job"):
        ArtifactBatchManifest(
            artifact_batch_id="artifact-batch-2",
            job_id="job-1",
            artifacts=(entry,),
        )


def test_manifest_rejects_non_integer_size_and_duplicate_ids():
    with pytest.raises(ValueError, match="non-negative integer"):
        ArtifactManifestEntry(
            artifact_id="artifact-5",
            artifact_type="solution_table",
            format=ArtifactFormat.JSON,
            media_type="application/json",
            status=ArtifactStatus.AVAILABLE,
            provenance=_provenance(),
            created_at="2026-07-23T10:00:00Z",
            expires_at="2026-07-23T11:00:00Z",
            size_bytes=1.5,  # type: ignore[arg-type]
            sha256="b" * 64,
        )

    entry = ArtifactManifestEntry(
        artifact_id="artifact-6",
        artifact_type="solution_table",
        format=ArtifactFormat.JSON,
        media_type="application/json",
        status=ArtifactStatus.QUEUED,
        provenance=_provenance(),
        created_at="2026-07-23T10:00:00Z",
        expires_at="2026-07-23T11:00:00Z",
    )
    with pytest.raises(ValueError, match="IDs must be unique"):
        ArtifactBatchManifest(
            artifact_batch_id="artifact-batch-3",
            job_id="job-1",
            artifacts=(entry, entry),
        )
