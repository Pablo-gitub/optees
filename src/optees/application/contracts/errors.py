from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from optees.application.contracts.json_value import JsonValue, require_json_value


class ErrorCode(str, Enum):
    AUTHENTICATION_FAILED = "authentication_failed"
    INVALID_REQUEST = "invalid_request"
    VALIDATION_FAILED = "validation_failed"
    CAPABILITY_NOT_FOUND = "capability_not_found"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    EXECUTION_FAILED = "execution_failed"
    CANCELLATION_NOT_SUPPORTED = "cancellation_not_supported"
    JOB_NOT_FOUND = "job_not_found"
    JOB_RESULT_NOT_READY = "job_result_not_ready"
    JOB_RESULT_NOT_AVAILABLE = "job_result_not_available"
    JOB_CAPACITY_EXCEEDED = "job_capacity_exceeded"
    BATCH_NOT_FOUND = "batch_not_found"
    BATCH_RESULT_NOT_READY = "batch_result_not_ready"
    BATCH_CAPACITY_EXCEEDED = "batch_capacity_exceeded"
    ARTIFACT_NOT_SUPPORTED = "artifact_not_supported"
    ARTIFACT_RESULT_NOT_AVAILABLE = "artifact_result_not_available"
    ARTIFACT_REQUEST_INVALID = "artifact_request_invalid"
    ARTIFACT_RENDER_FAILED = "artifact_render_failed"
    ARTIFACT_NOT_FOUND = "artifact_not_found"
    ARTIFACT_EXPIRED = "artifact_expired"
    ARTIFACT_CAPACITY_EXCEEDED = "artifact_capacity_exceeded"
    ARTIFACT_BACKEND_UNAVAILABLE = "artifact_backend_unavailable"
    REPORT_REQUEST_INVALID = "report_request_invalid"
    REPORT_ARTIFACT_NOT_AVAILABLE = "report_artifact_not_available"
    REPORT_BACKEND_UNAVAILABLE = "report_backend_unavailable"
    REPORT_COMPOSITION_FAILED = "report_composition_failed"
    REPORT_NOT_FOUND = "report_not_found"
    REPORT_EXPIRED = "report_expired"
    REPORT_CAPACITY_EXCEEDED = "report_capacity_exceeded"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"


class CodedValidationError(ValueError):
    """Validation failure carrying a stable public detail code and JSON path."""

    def __init__(self, message: str, *, detail_code: str, path: str = "$") -> None:
        super().__init__(message)
        self.detail_code = detail_code
        self.path = path


@dataclass(frozen=True)
class ErrorDetail:
    path: str
    message: str
    code: str = "invalid_value"

    def to_dict(self) -> dict[str, JsonValue]:
        return {"path": self.path, "message": self.message, "code": self.code}


@dataclass(frozen=True)
class StructuredError:
    code: ErrorCode
    message: str
    request_id: str | None = None
    details: tuple[ErrorDetail, ...] = ()
    context: dict[str, JsonValue] = field(default_factory=dict)
    contract_version: str = "1"

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, object] = {
            "contract_version": self.contract_version,
            "error": {
                "code": self.code.value,
                "message": self.message,
                "request_id": self.request_id,
                "details": [detail.to_dict() for detail in self.details],
                "context": self.context,
            },
        }
        normalized = require_json_value(payload)
        assert isinstance(normalized, dict)
        return normalized
