from __future__ import annotations

from dataclasses import dataclass, field

from optees.application.contracts.json_value import JsonValue, require_json_value


@dataclass(frozen=True)
class CapabilityDescriptor:
    """Public, versioned description of one executable mathematical workflow."""

    capability_id: str
    title: str
    problem_type: str
    input_schema: dict[str, JsonValue]
    result_schema: dict[str, JsonValue]
    default_options: dict[str, JsonValue] = field(default_factory=dict)
    available: bool = True
    unavailable_reason: str | None = None
    backend_candidates: tuple[str, ...] = ()
    supports_time_limit: bool = False
    supports_cancellation: bool = False
    contract_version: str = "1"
    problem_schema_version: str = "1"
    result_schema_version: str = "1"

    def __post_init__(self) -> None:
        if not self.capability_id.strip():
            raise ValueError("capability_id must not be empty.")
        if not self.title.strip():
            raise ValueError("title must not be empty.")
        if not self.problem_type.strip():
            raise ValueError("problem_type must not be empty.")
        if self.available and self.unavailable_reason is not None:
            raise ValueError(
                "unavailable_reason must be null when the capability is available."
            )
        if not self.available and not (self.unavailable_reason or "").strip():
            raise ValueError(
                "unavailable_reason is required when the capability is unavailable."
            )
        require_json_value(self.to_dict())

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, object] = {
            "id": self.capability_id,
            "contract_version": self.contract_version,
            "title": self.title,
            "problem_type": self.problem_type,
            "problem_schema_version": self.problem_schema_version,
            "result_schema_version": self.result_schema_version,
            "input_schema": self.input_schema,
            "result_schema": self.result_schema,
            "default_options": self.default_options,
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
            "backend_candidates": list(self.backend_candidates),
            "supports_time_limit": self.supports_time_limit,
            "supports_cancellation": self.supports_cancellation,
        }
        normalized = require_json_value(payload)
        assert isinstance(normalized, dict)
        return normalized


@dataclass(frozen=True)
class ProblemValidation:
    capability_id: str
    problem_schema_version: str
    available: bool
    warnings: tuple[str, ...] = ()
    contract_version: str = "1"

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, object] = {
            "contract_version": self.contract_version,
            "capability_id": self.capability_id,
            "valid": True,
            "available": self.available,
            "problem_schema_version": self.problem_schema_version,
            "warnings": list(self.warnings),
        }
        normalized = require_json_value(payload)
        assert isinstance(normalized, dict)
        return normalized
