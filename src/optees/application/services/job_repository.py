from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, replace
from threading import RLock

from optees.application.contracts.errors import StructuredError
from optees.application.contracts.execution import ExecutionEnvelope, JobStatus
from optees.application.contracts.job import JobSnapshot, TERMINAL_JOB_STATUSES
from optees.application.contracts.json_value import JsonValue


class JobRepositoryFullError(RuntimeError):
    pass


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    capability_id: str
    payload: dict[str, JsonValue]
    submitted_at: float
    job_status: JobStatus = JobStatus.QUEUED
    started_at: float | None = None
    finished_at: float | None = None
    cancellation_requested: bool = False
    outcome: ExecutionEnvelope | StructuredError | None = None

    def snapshot(self) -> JobSnapshot:
        envelope = self.outcome if isinstance(self.outcome, ExecutionEnvelope) else None
        return JobSnapshot(
            job_id=self.job_id,
            capability_id=self.capability_id,
            job_status=self.job_status,
            submitted_at=self.submitted_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
            mathematical_status=(
                envelope.mathematical_status if envelope is not None else None
            ),
            termination_reason=(
                envelope.termination_reason if envelope is not None else None
            ),
            cancellation_requested=self.cancellation_requested,
            result_available=envelope is not None,
            error_available=isinstance(self.outcome, StructuredError),
        )


class InMemoryJobRepository:
    """Thread-safe bounded store that never evicts active jobs."""

    def __init__(self, *, capacity: int = 100) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError("job repository capacity must be a positive integer")
        self._capacity = capacity
        self._records: OrderedDict[str, JobRecord] = OrderedDict()
        self._lock = RLock()

    @property
    def capacity(self) -> int:
        return self._capacity

    def add(self, record: JobRecord) -> None:
        with self._lock:
            if record.job_id in self._records:
                raise ValueError(f"job {record.job_id!r} already exists")
            self._evict_terminal_until_space()
            if len(self._records) >= self._capacity:
                raise JobRepositoryFullError(
                    "job repository capacity is occupied by active jobs"
                )
            self._records[record.job_id] = record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._records.get(job_id)

    def replace(self, job_id: str, **changes: object) -> JobRecord | None:
        with self._lock:
            current = self._records.get(job_id)
            if current is None:
                return None
            updated = replace(current, **changes)
            self._records[job_id] = updated
            return updated

    def list(self) -> tuple[JobRecord, ...]:
        with self._lock:
            return tuple(self._records.values())

    def _evict_terminal_until_space(self) -> None:
        while len(self._records) >= self._capacity:
            terminal_id = next(
                (
                    job_id
                    for job_id, record in self._records.items()
                    if record.job_status in TERMINAL_JOB_STATUSES
                ),
                None,
            )
            if terminal_id is None:
                return
            del self._records[terminal_id]
