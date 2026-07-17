from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from threading import RLock
from time import time
from typing import TypeAlias
from uuid import uuid4

from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import (
    ExecutionEnvelope,
    JobStatus,
    MathematicalStatus,
    TerminationReason,
)
from optees.application.contracts.job import JobSnapshot, TERMINAL_JOB_STATUSES
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.application.services.job_repository import (
    InMemoryJobRepository,
    JobRecord,
    JobRepositoryFullError,
)
from optees.application.services.optimization_service import (
    OptimizationService,
    ValidationOutcome,
)


JobOperationOutcome: TypeAlias = JobSnapshot | StructuredError
JobResultOutcome: TypeAlias = ExecutionEnvelope | StructuredError


class LocalJobService:
    """Bounded single-worker orchestration for local solver capabilities."""

    def __init__(
        self,
        optimization_service: OptimizationService,
        *,
        repository: InMemoryJobRepository | None = None,
        job_id_factory: Callable[[], str] | None = None,
        clock: Callable[[], float] = time,
    ) -> None:
        self._optimization = optimization_service
        self._repository = repository or InMemoryJobRepository()
        self._job_id_factory = job_id_factory or (lambda: f"job-{uuid4().hex}")
        self._clock = clock
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="optees-local-job",
        )
        self._futures: dict[str, Future[None]] = {}
        self._lock = RLock()
        self._accepting = True

    def submit(
        self,
        capability_id: str,
        payload: Mapping[str, object],
        *,
        request_id: str | None = None,
    ) -> JobOperationOutcome:
        with self._lock:
            if not self._accepting:
                return self._service_unavailable(request_id=request_id)
        validation = self._optimization.validate(
            capability_id,
            payload,
            request_id=request_id,
        )
        if isinstance(validation, StructuredError):
            return validation
        if not validation.available:
            return StructuredError(
                code=ErrorCode.DEPENDENCY_UNAVAILABLE,
                message="The capability is unavailable in this installation.",
                request_id=request_id,
                context={"capability_id": capability_id},
            )

        normalized = require_json_value(dict(payload), path="$.problem")
        assert isinstance(normalized, dict)
        record = JobRecord(
            job_id=self._job_id_factory(),
            capability_id=capability_id,
            payload=normalized,
            submitted_at=self._clock(),
        )
        with self._lock:
            if not self._accepting:
                return self._service_unavailable(request_id=request_id)
            try:
                self._repository.add(record)
            except JobRepositoryFullError:
                return StructuredError(
                    code=ErrorCode.JOB_CAPACITY_EXCEEDED,
                    message="The local job queue has reached its active-job capacity.",
                    request_id=request_id,
                )
            future = self._executor.submit(self._run_job, record.job_id)
            self._futures[record.job_id] = future
            future.add_done_callback(
                lambda _future, submitted_job_id=record.job_id: self._forget_future(
                    submitted_job_id
                )
            )
        return record.snapshot()

    def get(self, job_id: str) -> JobOperationOutcome:
        record = self._repository.get(job_id)
        if record is None:
            return self._job_not_found(job_id)
        return record.snapshot()

    def list_capabilities(self) -> tuple[dict[str, JsonValue], ...]:
        return self._optimization.list_capabilities()

    def validate(
        self,
        capability_id: str,
        payload: Mapping[str, object],
        *,
        request_id: str | None = None,
    ) -> ValidationOutcome:
        return self._optimization.validate(
            capability_id,
            payload,
            request_id=request_id,
        )

    def list_jobs(self) -> tuple[JobSnapshot, ...]:
        return tuple(record.snapshot() for record in self._repository.list())

    def result(self, job_id: str) -> JobResultOutcome:
        record = self._repository.get(job_id)
        if record is None:
            return self._job_not_found(job_id)
        if record.outcome is None:
            if record.job_status in TERMINAL_JOB_STATUSES:
                return StructuredError(
                    code=ErrorCode.JOB_RESULT_NOT_AVAILABLE,
                    message="The terminal job has no mathematical result.",
                    context={
                        "job_id": job_id,
                        "job_status": record.job_status.value,
                    },
                )
            return StructuredError(
                code=ErrorCode.JOB_RESULT_NOT_READY,
                message="The job has no result yet.",
                context={"job_id": job_id, "job_status": record.job_status.value},
            )
        return record.outcome

    def cancel(self, job_id: str) -> JobOperationOutcome:
        with self._lock:
            record = self._repository.get(job_id)
            if record is None:
                return self._job_not_found(job_id)
            if record.job_status in TERMINAL_JOB_STATUSES:
                return record.snapshot()

            future = self._futures.get(job_id)
            if record.job_status is JobStatus.QUEUED and future is not None:
                if future.cancel():
                    cancelled = self._repository.replace(
                        job_id,
                        job_status=JobStatus.CANCELLED,
                        cancellation_requested=True,
                        finished_at=self._clock(),
                    )
                    assert cancelled is not None
                    return cancelled.snapshot()

            if not self._optimization.supports_cancellation(record.capability_id):
                return StructuredError(
                    code=ErrorCode.CANCELLATION_NOT_SUPPORTED,
                    message="The running capability does not support cancellation.",
                    context={
                        "job_id": job_id,
                        "capability_id": record.capability_id,
                    },
                )
            updated = self._repository.replace(
                job_id,
                cancellation_requested=True,
            )
            assert updated is not None
            accepted = self._optimization.cancel(record.capability_id)
            if not accepted:
                self._repository.replace(
                    job_id,
                    cancellation_requested=False,
                )
                return StructuredError(
                    code=ErrorCode.CANCELLATION_NOT_SUPPORTED,
                    message="The backend could not accept the cancellation request.",
                    context={
                        "job_id": job_id,
                        "capability_id": record.capability_id,
                    },
                )
            current = self._repository.get(job_id)
            assert current is not None
            return current.snapshot()

    def shutdown(self, *, wait: bool = True, cancel_pending: bool = True) -> None:
        with self._lock:
            was_accepting = self._accepting
            if was_accepting:
                self._accepting = False
            job_ids = tuple(self._futures) if was_accepting else ()
        if cancel_pending and was_accepting:
            for job_id in job_ids:
                self.cancel(job_id)
        self._executor.shutdown(wait=wait, cancel_futures=False)

    def _run_job(self, job_id: str) -> None:
        record = self._repository.get(job_id)
        if record is None or record.job_status is not JobStatus.QUEUED:
            return
        running = self._repository.replace(
            job_id,
            job_status=JobStatus.RUNNING,
            started_at=self._clock(),
        )
        if running is None:
            return
        outcome = self._optimization.solve(
            running.capability_id,
            running.payload,
            job_id=job_id,
        )
        current = self._repository.get(job_id)
        cancellation_requested = bool(
            current is not None and current.cancellation_requested
        )
        if isinstance(outcome, ExecutionEnvelope):
            if cancellation_requested:
                outcome = _cancelled_envelope(outcome)
                status = JobStatus.CANCELLED
            else:
                status = JobStatus.COMPLETED
            self._repository.replace(
                job_id,
                job_status=status,
                finished_at=self._clock(),
                outcome=outcome,
            )
        else:
            self._repository.replace(
                job_id,
                job_status=(
                    JobStatus.CANCELLED
                    if cancellation_requested
                    else JobStatus.FAILED
                ),
                finished_at=self._clock(),
                outcome=outcome,
            )
    def _forget_future(self, job_id: str) -> None:
        with self._lock:
            self._futures.pop(job_id, None)

    @staticmethod
    def _job_not_found(job_id: str) -> StructuredError:
        return StructuredError(
            code=ErrorCode.JOB_NOT_FOUND,
            message="The requested job does not exist or is no longer retained.",
            context={"job_id": job_id},
        )

    @staticmethod
    def _service_unavailable(*, request_id: str | None) -> StructuredError:
        return StructuredError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="The local job service is shutting down.",
            request_id=request_id,
        )


def _cancelled_envelope(envelope: ExecutionEnvelope) -> ExecutionEnvelope:
    mathematical_status = envelope.mathematical_status
    warnings = envelope.warnings
    if mathematical_status is MathematicalStatus.OPTIMAL:
        mathematical_status = MathematicalStatus.FEASIBLE
        warnings = warnings + (
            "Cancellation was requested; the retained incumbent is not labelled optimal.",
        )
    return replace(
        envelope,
        job_status=JobStatus.CANCELLED,
        mathematical_status=mathematical_status,
        termination_reason=TerminationReason.CANCELLED,
        warnings=warnings,
    )
