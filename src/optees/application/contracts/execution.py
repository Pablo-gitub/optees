from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from optees.application.contracts.json_value import JsonValue, dumps_json, require_json_value
from optees.application.contracts.solution_validation import SolutionValidation


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class MathematicalStatus(str, Enum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    UNBOUNDED = "unbounded"
    NOT_SOLVED = "not_solved"


class TerminationReason(str, Enum):
    COMPLETED = "completed"
    TIME_LIMIT = "time_limit"
    ITERATION_LIMIT = "iteration_limit"
    CANCELLED = "cancelled"
    DEPENDENCY_FAILURE = "dependency_failure"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class ExecutionMetadata:
    optees_version: str
    api_version: str
    problem_schema_version: str
    result_schema_version: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "optees_version": self.optees_version,
            "api_version": self.api_version,
            "problem_schema_version": self.problem_schema_version,
            "result_schema_version": self.result_schema_version,
        }


@dataclass(frozen=True)
class SerializedResult:
    mathematical_status: MathematicalStatus
    result: dict[str, JsonValue]
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    termination_reason: TerminationReason = TerminationReason.COMPLETED

    def __post_init__(self) -> None:
        require_json_value(self.result, path="$.result")
        require_json_value(self.diagnostics, path="$.diagnostics")


@dataclass(frozen=True)
class ExecutionEnvelope:
    job_id: str
    capability_id: str
    job_status: JobStatus
    mathematical_status: MathematicalStatus | None
    termination_reason: TerminationReason | None
    result: dict[str, JsonValue]
    diagnostics: dict[str, JsonValue]
    metadata: ExecutionMetadata
    validation: SolutionValidation = field(
        default_factory=lambda: SolutionValidation.not_available(
            "No independent validator is registered for this capability."
        )
    )
    warnings: tuple[str, ...] = ()
    contract_version: str = "1"

    def __post_init__(self) -> None:
        if not self.job_id.strip():
            raise ValueError("job_id must not be empty.")
        if not self.capability_id.strip():
            raise ValueError("capability_id must not be empty.")
        require_json_value(self.to_dict())

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, object] = {
            "contract_version": self.contract_version,
            "job_id": self.job_id,
            "capability_id": self.capability_id,
            "job_status": self.job_status.value,
            "mathematical_status": (
                self.mathematical_status.value if self.mathematical_status else None
            ),
            "termination_reason": (
                self.termination_reason.value if self.termination_reason else None
            ),
            "result": self.result,
            "diagnostics": self.diagnostics,
            "validation": self.validation.to_dict(),
            "warnings": list(self.warnings),
            "metadata": self.metadata.to_dict(),
        }
        normalized = require_json_value(payload)
        assert isinstance(normalized, dict)
        return normalized

    def to_json(self, *, indent: int | None = None) -> str:
        return dumps_json(self.to_dict(), indent=indent)
