from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from optees.application.contracts.errors import StructuredError
from optees.application.contracts.execution import MathematicalStatus
from optees.application.contracts.json_value import JsonValue, require_json_value


MAX_ARTIFACT_REQUESTS_PER_BATCH = 8
MAX_ARTIFACT_OUTPUTS_PER_BATCH = 16


class ArtifactFormat(str, Enum):
    JSON = "json"
    DATA_JSON = "data_json"
    CSV = "csv"
    MARKDOWN = "markdown"
    XLSX = "xlsx"
    SVG = "svg"
    PNG = "png"
    OBJ_MTL_ZIP = "obj_mtl_zip"


class ArtifactStatus(str, Enum):
    QUEUED = "queued"
    RENDERING = "rendering"
    AVAILABLE = "available"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass(frozen=True)
class AvailableArtifact:
    """One artifact type advertised by capability discovery."""

    artifact_type: str
    title: str
    formats: tuple[ArtifactFormat, ...]
    required_mathematical_statuses: tuple[MathematicalStatus, ...] = ()
    options_schema: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_identifier(self.artifact_type, "artifact_type")
        if not self.title.strip():
            raise ValueError("artifact title must not be empty")
        if not self.formats:
            raise ValueError("artifact formats must not be empty")
        if any(not isinstance(item, ArtifactFormat) for item in self.formats):
            raise ValueError("artifact formats must use ArtifactFormat values")
        if len(set(self.formats)) != len(self.formats):
            raise ValueError("artifact formats must not contain duplicates")
        if len(set(self.required_mathematical_statuses)) != len(
            self.required_mathematical_statuses
        ):
            raise ValueError(
                "required mathematical statuses must not contain duplicates"
            )
        if any(
            not isinstance(item, MathematicalStatus)
            for item in self.required_mathematical_statuses
        ):
            raise ValueError(
                "required mathematical statuses must use MathematicalStatus values"
            )
        require_json_value(self.options_schema, path="$.options_schema")

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, object] = {
            "artifact_type": self.artifact_type,
            "title": self.title,
            "formats": [item.value for item in self.formats],
            "required_mathematical_statuses": [
                item.value for item in self.required_mathematical_statuses
            ],
            "options_schema": self.options_schema,
        }
        return _strict_object(payload, path="$.available_artifact")


@dataclass(frozen=True)
class ArtifactRequest:
    artifact_type: str
    formats: tuple[ArtifactFormat, ...]
    options: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_identifier(self.artifact_type, "artifact_type")
        if not self.formats:
            raise ValueError("artifact request formats must not be empty")
        if any(not isinstance(item, ArtifactFormat) for item in self.formats):
            raise ValueError("artifact request formats must use ArtifactFormat values")
        if len(set(self.formats)) != len(self.formats):
            raise ValueError("artifact request formats must not contain duplicates")
        require_json_value(self.options, path="$.options")

    def to_dict(self) -> dict[str, JsonValue]:
        return _strict_object(
            {
                "artifact_type": self.artifact_type,
                "formats": [item.value for item in self.formats],
                "options": self.options,
            },
            path="$.artifact_request",
        )


@dataclass(frozen=True)
class ArtifactBatchRequest:
    requests: tuple[ArtifactRequest, ...]
    contract_version: str = "1"

    def __post_init__(self) -> None:
        if self.contract_version != "1":
            raise ValueError("unsupported artifact contract version")
        if not self.requests:
            raise ValueError("artifact batch requests must not be empty")
        if len(self.requests) > MAX_ARTIFACT_REQUESTS_PER_BATCH:
            raise ValueError(
                f"artifact batch accepts at most {MAX_ARTIFACT_REQUESTS_PER_BATCH} requests"
            )
        output_count = sum(len(request.formats) for request in self.requests)
        if output_count > MAX_ARTIFACT_OUTPUTS_PER_BATCH:
            raise ValueError(
                f"artifact batch accepts at most {MAX_ARTIFACT_OUTPUTS_PER_BATCH} outputs"
            )
        outputs = [
            (request.artifact_type, format_)
            for request in self.requests
            for format_ in request.formats
        ]
        if len(set(outputs)) != len(outputs):
            raise ValueError("artifact batch must not request duplicate outputs")

    def to_dict(self) -> dict[str, JsonValue]:
        return _strict_object(
            {
                "contract_version": self.contract_version,
                "requests": [request.to_dict() for request in self.requests],
            },
            path="$.artifact_batch_request",
        )


@dataclass(frozen=True)
class ArtifactProvenance:
    capability_id: str
    job_id: str
    problem_schema_version: str
    result_schema_version: str
    renderer_version: str
    locale: str
    theme: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "capability_id",
            "job_id",
            "problem_schema_version",
            "result_schema_version",
            "renderer_version",
            "locale",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        if self.theme is not None and not self.theme.strip():
            raise ValueError("theme must be null or non-empty")

    def to_dict(self) -> dict[str, JsonValue]:
        return _strict_object(
            {
                "capability_id": self.capability_id,
                "job_id": self.job_id,
                "problem_schema_version": self.problem_schema_version,
                "result_schema_version": self.result_schema_version,
                "renderer_version": self.renderer_version,
                "locale": self.locale,
                "theme": self.theme,
            },
            path="$.artifact_provenance",
        )


@dataclass(frozen=True)
class ArtifactManifestEntry:
    artifact_id: str
    artifact_type: str
    format: ArtifactFormat
    media_type: str
    status: ArtifactStatus
    provenance: ArtifactProvenance
    created_at: str
    expires_at: str
    size_bytes: int | None = None
    sha256: str | None = None
    error: StructuredError | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.artifact_id, "artifact_id")
        _require_identifier(self.artifact_type, "artifact_type")
        if not isinstance(self.format, ArtifactFormat):
            raise ValueError("format must use an ArtifactFormat value")
        if not isinstance(self.status, ArtifactStatus):
            raise ValueError("status must use an ArtifactStatus value")
        if not self.media_type.strip():
            raise ValueError("media_type must not be empty")
        if not self.created_at.strip() or not self.expires_at.strip():
            raise ValueError("artifact timestamps must not be empty")
        if self.size_bytes is not None and (
            isinstance(self.size_bytes, bool)
            or not isinstance(self.size_bytes, int)
            or self.size_bytes < 0
        ):
            raise ValueError("size_bytes must be null or a non-negative integer")
        if self.sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("sha256 must be null or 64 lowercase hexadecimal characters")
        if self.status is ArtifactStatus.AVAILABLE:
            if self.size_bytes is None or self.sha256 is None:
                raise ValueError("available artifacts require size_bytes and sha256")
            if self.error is not None:
                raise ValueError("available artifacts must not contain an error")
        if self.status is ArtifactStatus.FAILED and self.error is None:
            raise ValueError("failed artifacts require a structured error")

    def to_dict(self) -> dict[str, JsonValue]:
        error_payload = None
        if self.error is not None:
            error_payload = self.error.to_dict()["error"]
        return _strict_object(
            {
                "artifact_id": self.artifact_id,
                "artifact_type": self.artifact_type,
                "format": self.format.value,
                "media_type": self.media_type,
                "status": self.status.value,
                "size_bytes": self.size_bytes,
                "sha256": self.sha256,
                "created_at": self.created_at,
                "expires_at": self.expires_at,
                "provenance": self.provenance.to_dict(),
                "error": error_payload,
            },
            path="$.artifact_manifest_entry",
        )


@dataclass(frozen=True)
class ArtifactBatchManifest:
    artifact_batch_id: str
    job_id: str
    artifacts: tuple[ArtifactManifestEntry, ...]
    contract_version: str = "1"

    def __post_init__(self) -> None:
        if self.contract_version != "1":
            raise ValueError("unsupported artifact contract version")
        _require_identifier(self.artifact_batch_id, "artifact_batch_id")
        _require_identifier(self.job_id, "job_id")
        if not self.artifacts:
            raise ValueError("artifact manifest must contain at least one artifact")
        artifact_ids = [item.artifact_id for item in self.artifacts]
        if len(set(artifact_ids)) != len(artifact_ids):
            raise ValueError("artifact manifest IDs must be unique")
        if any(item.provenance.job_id != self.job_id for item in self.artifacts):
            raise ValueError("every artifact must belong to the manifest job")

    def to_dict(self) -> dict[str, JsonValue]:
        return _strict_object(
            {
                "contract_version": self.contract_version,
                "artifact_batch_id": self.artifact_batch_id,
                "job_id": self.job_id,
                "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            },
            path="$.artifact_batch_manifest",
        )


def _require_identifier(value: str, name: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be empty")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise ValueError(f"{name} contains unsupported characters")


def _strict_object(payload: dict[str, object], *, path: str) -> dict[str, JsonValue]:
    normalized = require_json_value(payload, path=path)
    assert isinstance(normalized, dict)
    return normalized
