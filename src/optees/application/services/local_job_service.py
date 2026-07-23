from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from threading import RLock
from time import time
from typing import TypeAlias
from uuid import uuid4

from optees.application.contracts.batch import (
    BatchItemSnapshot,
    BatchRequest,
    BatchResult,
    BatchResultItem,
    BatchSnapshot,
    BatchStatus,
    BatchValidation,
    BatchValidationItem,
    aggregate_batch_status,
)
from optees.application.contracts.artifact_rendering import ArtifactSource
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
BatchOperationOutcome: TypeAlias = BatchSnapshot | StructuredError
BatchResultOutcome: TypeAlias = BatchResult | StructuredError


@dataclass
class _BatchRecord:
    batch_id: str
    submitted_at: float
    items: tuple[tuple[str, str], ...]
    terminal_jobs: dict[str, JobRecord] = field(default_factory=dict)


class LocalJobService:
    """Bounded single-worker orchestration for local solver capabilities."""

    def __init__(
        self,
        optimization_service: OptimizationService,
        *,
        repository: InMemoryJobRepository | None = None,
        job_id_factory: Callable[[], str] | None = None,
        batch_id_factory: Callable[[], str] | None = None,
        batch_capacity: int = 20,
        clock: Callable[[], float] = time,
    ) -> None:
        if (
            isinstance(batch_capacity, bool)
            or not isinstance(batch_capacity, int)
            or batch_capacity < 1
        ):
            raise ValueError("batch_capacity must be a positive integer")
        self._optimization = optimization_service
        self._repository = repository or InMemoryJobRepository()
        self._job_id_factory = job_id_factory or (lambda: f"job-{uuid4().hex}")
        self._batch_id_factory = batch_id_factory or (
            lambda: f"batch-{uuid4().hex}"
        )
        self._batch_capacity = batch_capacity
        self._clock = clock
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="optees-local-job",
        )
        self._futures: dict[str, Future[None]] = {}
        self._batches: dict[str, _BatchRecord] = {}
        self._job_batches: dict[str, str] = {}
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
            self._schedule(record.job_id)
        return record.snapshot()

    def validate_batch(
        self,
        request: BatchRequest,
        *,
        request_id: str | None = None,
    ) -> BatchValidation:
        items: list[BatchValidationItem] = []
        for item in request.items:
            outcome = self._optimization.validate(
                item.capability_id,
                item.problem,
                request_id=request_id,
            )
            if isinstance(outcome, StructuredError):
                items.append(
                    BatchValidationItem(
                        client_item_id=item.client_item_id,
                        capability_id=item.capability_id,
                        valid=False,
                        available=False,
                        error=outcome.to_dict(),
                    )
                )
                continue
            items.append(
                BatchValidationItem(
                    client_item_id=item.client_item_id,
                    capability_id=item.capability_id,
                    valid=True,
                    available=outcome.available,
                    validation=outcome.to_dict(),
                )
            )
        return BatchValidation(tuple(items))

    def submit_batch(
        self,
        request: BatchRequest,
        *,
        request_id: str | None = None,
    ) -> BatchOperationOutcome:
        with self._lock:
            if not self._accepting:
                return self._service_unavailable(request_id=request_id)
        validation = self.validate_batch(request, request_id=request_id)
        if not validation.valid:
            return StructuredError(
                code=ErrorCode.VALIDATION_FAILED,
                message=(
                    "Every batch item must be valid and available before any "
                    "job is submitted."
                ),
                request_id=request_id,
                context={"batch_validation": validation.to_dict()},
            )

        submitted_at = self._clock()
        records = tuple(
            JobRecord(
                job_id=self._job_id_factory(),
                capability_id=item.capability_id,
                payload=item.problem,
                submitted_at=submitted_at,
            )
            for item in request.items
        )
        batch = _BatchRecord(
            batch_id=self._batch_id_factory(),
            submitted_at=submitted_at,
            items=tuple(
                (item.client_item_id, record.job_id)
                for item, record in zip(request.items, records, strict=True)
            ),
        )
        with self._lock:
            if not self._accepting:
                return self._service_unavailable(request_id=request_id)
            if not self._make_batch_space():
                return StructuredError(
                    code=ErrorCode.BATCH_CAPACITY_EXCEEDED,
                    message="The local batch registry is occupied by active batches.",
                    request_id=request_id,
                )
            try:
                self._repository.add_many(records)
            except JobRepositoryFullError:
                return StructuredError(
                    code=ErrorCode.JOB_CAPACITY_EXCEEDED,
                    message=(
                        "The local job queue cannot accept every item in this "
                        "batch atomically."
                    ),
                    request_id=request_id,
                    context={"item_count": len(records)},
                )
            self._batches[batch.batch_id] = batch
            for record in records:
                self._job_batches[record.job_id] = batch.batch_id
                self._schedule(record.job_id)
        return self._batch_snapshot(batch)

    def get_batch(self, batch_id: str) -> BatchOperationOutcome:
        with self._lock:
            batch = self._batches.get(batch_id)
            if batch is None:
                return self._batch_not_found(batch_id)
            return self._batch_snapshot(batch)

    def batch_result(self, batch_id: str) -> BatchResultOutcome:
        with self._lock:
            batch = self._batches.get(batch_id)
            if batch is None:
                return self._batch_not_found(batch_id)
            snapshot = self._batch_snapshot(batch)
            if snapshot.batch_status in {BatchStatus.QUEUED, BatchStatus.RUNNING}:
                return StructuredError(
                    code=ErrorCode.BATCH_RESULT_NOT_READY,
                    message="The batch still contains active jobs.",
                    context={
                        "batch_id": batch_id,
                        "batch_status": snapshot.batch_status.value,
                    },
                )
            items: list[BatchResultItem] = []
            for client_item_id, job_id in batch.items:
                record = self._batch_job_record(batch, job_id)
                assert record is not None
                items.append(
                    BatchResultItem(
                        client_item_id=client_item_id,
                        job=record.snapshot(),
                        result=(
                            record.outcome
                            if isinstance(record.outcome, ExecutionEnvelope)
                            else None
                        ),
                        error=(
                            record.outcome
                            if isinstance(record.outcome, StructuredError)
                            else None
                        ),
                    )
                )
            return BatchResult(snapshot, tuple(items))

    def cancel_batch(self, batch_id: str) -> BatchOperationOutcome:
        with self._lock:
            batch = self._batches.get(batch_id)
            if batch is None:
                return self._batch_not_found(batch_id)
            job_ids = tuple(job_id for _client_item_id, job_id in batch.items)
        for job_id in job_ids:
            snapshot = self.get(job_id)
            if (
                isinstance(snapshot, JobSnapshot)
                and snapshot.job_status not in TERMINAL_JOB_STATUSES
            ):
                self.cancel(job_id)
        return self.get_batch(batch_id)

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

    def artifact_source(self, job_id: str) -> ArtifactSource | StructuredError:
        """Return the retained normalized problem and usable execution envelope."""

        record = self._repository.get(job_id)
        if record is None:
            return self._job_not_found(job_id)
        if not isinstance(record.outcome, ExecutionEnvelope):
            return StructuredError(
                code=ErrorCode.ARTIFACT_RESULT_NOT_AVAILABLE,
                message="The job does not have a usable execution result.",
                context={
                    "job_id": job_id,
                    "job_status": record.job_status.value,
                },
            )
        problem = require_json_value(record.payload, path="$.artifact_source.problem")
        assert isinstance(problem, dict)
        return ArtifactSource(
            capability_id=record.capability_id,
            problem=problem,
            envelope=record.outcome,
        )

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
                    self._capture_terminal_batch_job(cancelled)
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
            completed = self._repository.replace(
                job_id,
                job_status=status,
                finished_at=self._clock(),
                outcome=outcome,
            )
        else:
            completed = self._repository.replace(
                job_id,
                job_status=(
                    JobStatus.CANCELLED
                    if cancellation_requested
                    else JobStatus.FAILED
                ),
                finished_at=self._clock(),
                outcome=outcome,
            )
        if completed is not None:
            self._capture_terminal_batch_job(completed)

    def _schedule(self, job_id: str) -> None:
        future = self._executor.submit(self._run_job, job_id)
        self._futures[job_id] = future
        future.add_done_callback(
            lambda _future, submitted_job_id=job_id: self._forget_future(
                submitted_job_id
            )
        )

    def _forget_future(self, job_id: str) -> None:
        with self._lock:
            self._futures.pop(job_id, None)

    def _capture_terminal_batch_job(self, record: JobRecord) -> None:
        with self._lock:
            batch_id = self._job_batches.get(record.job_id)
            if batch_id is None:
                return
            batch = self._batches.get(batch_id)
            if batch is not None:
                batch.terminal_jobs[record.job_id] = record

    def _batch_snapshot(self, batch: _BatchRecord) -> BatchSnapshot:
        items: list[BatchItemSnapshot] = []
        finished_at: float | None = None
        for client_item_id, job_id in batch.items:
            record = self._batch_job_record(batch, job_id)
            assert record is not None
            items.append(BatchItemSnapshot(client_item_id, record.snapshot()))
            if record.finished_at is not None:
                finished_at = max(
                    finished_at or record.finished_at,
                    record.finished_at,
                )
        status = aggregate_batch_status(
            tuple(item.job.job_status for item in items)
        )
        return BatchSnapshot(
            batch_id=batch.batch_id,
            batch_status=status,
            submitted_at=batch.submitted_at,
            finished_at=(
                finished_at
                if status not in {BatchStatus.QUEUED, BatchStatus.RUNNING}
                else None
            ),
            items=tuple(items),
        )

    def _batch_job_record(
        self,
        batch: _BatchRecord,
        job_id: str,
    ) -> JobRecord | None:
        return self._repository.get(job_id) or batch.terminal_jobs.get(job_id)

    def _make_batch_space(self) -> bool:
        while len(self._batches) >= self._batch_capacity:
            terminal_id = next(
                (
                    batch_id
                    for batch_id, batch in self._batches.items()
                    if self._batch_snapshot(batch).batch_status
                    not in {BatchStatus.QUEUED, BatchStatus.RUNNING}
                ),
                None,
            )
            if terminal_id is None:
                return False
            removed = self._batches.pop(terminal_id)
            for _client_item_id, job_id in removed.items:
                self._job_batches.pop(job_id, None)
        return True

    @staticmethod
    def _job_not_found(job_id: str) -> StructuredError:
        return StructuredError(
            code=ErrorCode.JOB_NOT_FOUND,
            message="The requested job does not exist or is no longer retained.",
            context={"job_id": job_id},
        )

    @staticmethod
    def _batch_not_found(batch_id: str) -> StructuredError:
        return StructuredError(
            code=ErrorCode.BATCH_NOT_FOUND,
            message="The requested batch does not exist or is no longer retained.",
            context={"batch_id": batch_id},
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
