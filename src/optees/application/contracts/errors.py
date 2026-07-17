from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from optees.application.contracts.json_value import JsonValue, require_json_value


class ErrorCode(str, Enum):
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
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"


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
