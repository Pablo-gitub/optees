from __future__ import annotations

from dataclasses import dataclass

from optees.application.contracts.execution import (
    JobStatus,
    MathematicalStatus,
    TerminationReason,
)
from optees.application.contracts.json_value import JsonValue, require_json_value


TERMINAL_JOB_STATUSES = frozenset(
    {JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED}
)


@dataclass(frozen=True)
class JobSnapshot:
    """Public operational state; mathematical results remain in the envelope."""

    job_id: str
    capability_id: str
    job_status: JobStatus
    submitted_at: float
    started_at: float | None = None
    finished_at: float | None = None
    mathematical_status: MathematicalStatus | None = None
    termination_reason: TerminationReason | None = None
    cancellation_requested: bool = False
    result_available: bool = False
    error_available: bool = False
    contract_version: str = "1"

    def is_terminal(self) -> bool:
        return self.job_status in TERMINAL_JOB_STATUSES

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, object] = {
            "contract_version": self.contract_version,
            "job_id": self.job_id,
            "capability_id": self.capability_id,
            "job_status": self.job_status.value,
            "mathematical_status": (
                self.mathematical_status.value
                if self.mathematical_status is not None
                else None
            ),
            "termination_reason": (
                self.termination_reason.value
                if self.termination_reason is not None
                else None
            ),
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "cancellation_requested": self.cancellation_requested,
            "result_available": self.result_available,
            "error_available": self.error_available,
        }
        normalized = require_json_value(payload, path="$.job")
        assert isinstance(normalized, dict)
        return normalized
