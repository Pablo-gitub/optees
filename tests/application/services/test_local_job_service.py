from __future__ import annotations

from threading import Event, Lock
from time import monotonic, sleep

import pytest

from optees.application.contracts.batch import (
    BatchItemRequest,
    BatchRequest,
    BatchResult,
    BatchSnapshot,
    BatchStatus,
)
from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import (
    ExecutionEnvelope,
    JobStatus,
    MathematicalStatus,
    TerminationReason,
)
from optees.application.contracts.job import JobSnapshot
from optees.application.services.job_repository import InMemoryJobRepository
from optees.application.services.local_job_service import LocalJobService
from optees.composition.local_agent import (
    LP_CAPABILITY_ID,
    PACKING_CAPABILITY_ID,
    create_lp_optimization_service,
    create_packing_optimization_service,
    create_local_job_service,
)


class BlockingLPSolver:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.calls = 0
        self.active = 0
        self.maximum_active = 0
        self._lock = Lock()

    def solve(self, problem):
        with self._lock:
            self.calls += 1
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
        self.started.set()
        assert self.release.wait(timeout=5)
        with self._lock:
            self.active -= 1
        return _lp_response()


class CancellablePackingSolver:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.cancelled = False

    def solve(self, problem):
        self.started.set()
        assert self.release.wait(timeout=5)
        return {
            "status": "Optimal",
            "objective": 5,
            "placements": [
                {
                    "instance_id": "box#1",
                    "item_id": "box",
                    "item_name": "Box",
                    "unit_index": 1,
                    "orientation_code": "LWH",
                    "x": 0,
                    "y": 0,
                    "z": 0,
                    "length": 1,
                    "width": 1,
                    "height": 1,
                    "value": 5,
                }
            ],
            "excluded_instance_ids": [],
            "extras": {"backend": "fake"},
        }

    def cancel(self) -> bool:
        self.cancelled = True
        self.release.set()
        return True


class FailingLPSolver:
    def solve(self, problem):
        raise RuntimeError("private backend detail")


def _lp_payload() -> dict:
    return {
        "version": "1",
        "variables": [{"name": "x", "label": "", "lb": 0, "ub": 1}],
        "objective": {"sense": "max", "coefficients": [1], "offset": 0},
        "constraints": [],
    }


def _lp_response() -> dict:
    return {
        "status": "Optimal",
        "objective": 1,
        "x": {"x": 1},
        "extras": {
            "method": "highs",
            "success": True,
            "var_names": ["x"],
            "objective_sense": "max",
        },
    }


def _packing_payload() -> dict:
    return {
        "version": "1",
        "problem_type": "packing",
        "variant": "single_container_3d",
        "selection_policy": "optional",
        "gravity_mode": "simple",
        "container": {
            "id": "container",
            "name": "Container",
            "dimensions": {"length": 2, "width": 2, "height": 2},
            "capacities": [],
        },
        "items": [
            {
                "id": "box",
                "name": "Box",
                "dimensions": {"length": 1, "width": 1, "height": 1},
                "value": 5,
                "quantity": 1,
                "rotation_policy": "fixed",
                "allowed_orientations": [],
                "consumptions": [],
            }
        ],
        "solver_options": {"time_limit": 10, "mip_gap": 0.01},
    }


def _job_service(solver: BlockingLPSolver, *, capacity: int = 10) -> LocalJobService:
    ids = iter(f"job-{index}" for index in range(1, 20))
    return LocalJobService(
        create_lp_optimization_service(solver_port=solver),
        repository=InMemoryJobRepository(capacity=capacity),
        job_id_factory=lambda: next(ids),
    )


def _wait_for_status(
    service: LocalJobService,
    job_id: str,
    expected: JobStatus,
) -> JobSnapshot:
    deadline = monotonic() + 5
    while monotonic() < deadline:
        outcome = service.get(job_id)
        assert isinstance(outcome, JobSnapshot)
        if outcome.job_status is expected:
            return outcome
        sleep(0.01)
    raise AssertionError(f"job {job_id} did not reach {expected.value}")


def _batch(*payloads: dict) -> BatchRequest:
    return BatchRequest(
        tuple(
            BatchItemRequest(f"scenario-{index}", LP_CAPABILITY_ID, payload)
            for index, payload in enumerate(payloads, start=1)
        )
    )


def _wait_for_batch(
    service: LocalJobService,
    batch_id: str,
) -> BatchSnapshot:
    deadline = monotonic() + 5
    while monotonic() < deadline:
        outcome = service.get_batch(batch_id)
        assert isinstance(outcome, BatchSnapshot)
        if outcome.batch_status not in {BatchStatus.QUEUED, BatchStatus.RUNNING}:
            return outcome
        sleep(0.01)
    raise AssertionError(f"batch {batch_id} did not finish")


def test_batch_preserves_individual_results_and_aggregates_validation():
    service = create_local_job_service(capacity=4)
    try:
        request = _batch(_lp_payload(), _lp_payload())
        validation = service.validate_batch(request)
        assert validation.valid is True

        submitted = service.submit_batch(request)
        assert isinstance(submitted, BatchSnapshot)
        completed = _wait_for_batch(service, submitted.batch_id)
        result = service.batch_result(submitted.batch_id)

        assert completed.batch_status is BatchStatus.COMPLETED
        assert isinstance(result, BatchResult)
        assert [item.client_item_id for item in result.items] == [
            "scenario-1",
            "scenario-2",
        ]
        payload = result.to_dict()
        assert payload["summary"]["mathematical_status_counts"] == {"optimal": 2}
        assert payload["summary"]["validation_status_counts"] == {"verified": 2}
        assert all(item.result is not None for item in result.items)
    finally:
        service.shutdown()


def test_invalid_batch_is_rejected_without_submitting_partial_work():
    service = create_local_job_service(capacity=4)
    invalid = _lp_payload()
    invalid["variables"] = []
    try:
        outcome = service.submit_batch(_batch(_lp_payload(), invalid))

        assert isinstance(outcome, StructuredError)
        assert outcome.code is ErrorCode.VALIDATION_FAILED
        assert service.list_jobs() == ()
    finally:
        service.shutdown()


def test_batch_capacity_failure_does_not_submit_a_partial_batch():
    service = create_local_job_service(capacity=1)
    try:
        outcome = service.submit_batch(_batch(_lp_payload(), _lp_payload()))

        assert isinstance(outcome, StructuredError)
        assert outcome.code is ErrorCode.JOB_CAPACITY_EXCEEDED
        assert service.list_jobs() == ()
    finally:
        service.shutdown()


def test_batch_result_survives_individual_terminal_job_eviction():
    service = create_local_job_service(capacity=2)
    try:
        submitted = service.submit_batch(_batch(_lp_payload(), _lp_payload()))
        assert isinstance(submitted, BatchSnapshot)
        _wait_for_batch(service, submitted.batch_id)

        later_job = service.submit(LP_CAPABILITY_ID, _lp_payload())
        assert isinstance(later_job, JobSnapshot)
        result = service.batch_result(submitted.batch_id)

        assert isinstance(result, BatchResult)
        assert len(result.items) == 2
        assert all(item.result is not None for item in result.items)
    finally:
        service.shutdown()


def test_job_service_runs_one_job_and_queues_following_work():
    solver = BlockingLPSolver()
    service = _job_service(solver)
    try:
        first = service.submit(LP_CAPABILITY_ID, _lp_payload())
        assert isinstance(first, JobSnapshot)
        assert solver.started.wait(timeout=2)
        second = service.submit(LP_CAPABILITY_ID, _lp_payload())
        assert isinstance(second, JobSnapshot)

        assert _wait_for_status(service, first.job_id, JobStatus.RUNNING)
        assert service.get(second.job_id).job_status is JobStatus.QUEUED
        assert solver.calls == 1

        solver.release.set()
        _wait_for_status(service, first.job_id, JobStatus.COMPLETED)
        _wait_for_status(service, second.job_id, JobStatus.COMPLETED)
        assert solver.maximum_active == 1
    finally:
        solver.release.set()
        service.shutdown()


def test_queued_job_can_be_cancelled_without_backend_support():
    solver = BlockingLPSolver()
    service = _job_service(solver)
    try:
        first = service.submit(LP_CAPABILITY_ID, _lp_payload())
        assert isinstance(first, JobSnapshot)
        assert solver.started.wait(timeout=2)
        second = service.submit(LP_CAPABILITY_ID, _lp_payload())
        assert isinstance(second, JobSnapshot)

        cancelled = service.cancel(second.job_id)

        assert isinstance(cancelled, JobSnapshot)
        assert cancelled.job_status is JobStatus.CANCELLED
        assert cancelled.cancellation_requested is True
        assert solver.calls == 1
        no_result = service.result(second.job_id)
        assert isinstance(no_result, StructuredError)
        assert no_result.code is ErrorCode.JOB_RESULT_NOT_AVAILABLE
    finally:
        solver.release.set()
        service.shutdown()


def test_running_non_cancellable_job_returns_structured_error():
    solver = BlockingLPSolver()
    service = _job_service(solver)
    try:
        job = service.submit(LP_CAPABILITY_ID, _lp_payload())
        assert isinstance(job, JobSnapshot)
        assert solver.started.wait(timeout=2)

        outcome = service.cancel(job.job_id)

        assert isinstance(outcome, StructuredError)
        assert outcome.code is ErrorCode.CANCELLATION_NOT_SUPPORTED
    finally:
        solver.release.set()
        service.shutdown()


def test_running_packing_cancellation_preserves_incumbent_as_feasible():
    solver = CancellablePackingSolver()
    service = LocalJobService(
        create_packing_optimization_service(solver_port=solver),
        job_id_factory=lambda: "job-packing",
    )
    try:
        job = service.submit(PACKING_CAPABILITY_ID, _packing_payload())
        assert isinstance(job, JobSnapshot)
        assert solver.started.wait(timeout=2)

        accepted = service.cancel(job.job_id)
        assert isinstance(accepted, JobSnapshot)
        assert accepted.cancellation_requested is True
        snapshot = _wait_for_status(service, job.job_id, JobStatus.CANCELLED)
        outcome = service.result(job.job_id)

        assert solver.cancelled is True
        assert snapshot.mathematical_status is MathematicalStatus.FEASIBLE
        assert isinstance(outcome, ExecutionEnvelope)
        assert outcome.job_status is JobStatus.CANCELLED
        assert outcome.mathematical_status is MathematicalStatus.FEASIBLE
        assert outcome.termination_reason is TerminationReason.CANCELLED
        assert outcome.result["requested"]["placements"]
    finally:
        solver.release.set()
        service.shutdown()


def test_result_is_not_available_until_execution_finishes():
    solver = BlockingLPSolver()
    service = _job_service(solver)
    try:
        job = service.submit(LP_CAPABILITY_ID, _lp_payload())
        assert isinstance(job, JobSnapshot)
        assert solver.started.wait(timeout=2)

        pending = service.result(job.job_id)
        assert isinstance(pending, StructuredError)
        assert pending.code is ErrorCode.JOB_RESULT_NOT_READY

        solver.release.set()
        _wait_for_status(service, job.job_id, JobStatus.COMPLETED)
        result = service.result(job.job_id)
        assert isinstance(result, ExecutionEnvelope)
        assert result.job_id == job.job_id
    finally:
        solver.release.set()
        service.shutdown()


def test_technical_solver_failure_moves_job_to_failed_without_leaking_detail():
    service = LocalJobService(
        create_lp_optimization_service(solver_port=FailingLPSolver()),
        job_id_factory=lambda: "job-failed",
    )
    try:
        job = service.submit(LP_CAPABILITY_ID, _lp_payload())
        assert isinstance(job, JobSnapshot)

        snapshot = _wait_for_status(service, job.job_id, JobStatus.FAILED)
        outcome = service.result(job.job_id)

        assert snapshot.error_available is True
        assert isinstance(outcome, StructuredError)
        assert outcome.code is ErrorCode.EXECUTION_FAILED
        assert "private backend detail" not in str(outcome.to_dict())
    finally:
        service.shutdown()


def test_shutdown_rejects_new_work_and_cancels_queued_jobs():
    solver = BlockingLPSolver()
    service = _job_service(solver)
    first = service.submit(LP_CAPABILITY_ID, _lp_payload())
    assert isinstance(first, JobSnapshot)
    assert solver.started.wait(timeout=2)
    second = service.submit(LP_CAPABILITY_ID, _lp_payload())
    assert isinstance(second, JobSnapshot)

    service.shutdown(wait=False, cancel_pending=True)

    rejected = service.submit(LP_CAPABILITY_ID, _lp_payload())
    assert isinstance(rejected, StructuredError)
    assert rejected.code is ErrorCode.SERVICE_UNAVAILABLE
    assert service.get(second.job_id).job_status is JobStatus.CANCELLED
    solver.release.set()
    service.shutdown(wait=True, cancel_pending=False)


def test_active_job_capacity_is_reported_without_dropping_existing_work():
    solver = BlockingLPSolver()
    service = _job_service(solver, capacity=1)
    try:
        first = service.submit(LP_CAPABILITY_ID, _lp_payload())
        assert isinstance(first, JobSnapshot)
        assert solver.started.wait(timeout=2)

        rejected = service.submit(LP_CAPABILITY_ID, _lp_payload())

        assert isinstance(rejected, StructuredError)
        assert rejected.code is ErrorCode.JOB_CAPACITY_EXCEEDED
        assert len(service.list_jobs()) == 1
    finally:
        solver.release.set()
        service.shutdown()


def test_missing_job_returns_stable_error():
    solver = BlockingLPSolver()
    service = _job_service(solver)
    try:
        outcome = service.get("missing")

        assert isinstance(outcome, StructuredError)
        assert outcome.code is ErrorCode.JOB_NOT_FOUND
    finally:
        service.shutdown()


def test_production_job_service_exposes_discovery_validation_and_execution():
    service = create_local_job_service(capacity=2)
    try:
        capability_ids = {item["id"] for item in service.list_capabilities()}
        assert LP_CAPABILITY_ID in capability_ids
        validation = service.validate(LP_CAPABILITY_ID, _lp_payload())
        assert validation.to_dict()["valid"] is True

        job = service.submit(LP_CAPABILITY_ID, _lp_payload())
        assert isinstance(job, JobSnapshot)
        snapshot = _wait_for_status(service, job.job_id, JobStatus.COMPLETED)
        result = service.result(job.job_id)

        assert snapshot.mathematical_status is MathematicalStatus.OPTIMAL
        assert isinstance(result, ExecutionEnvelope)
        assert result.result["objective"] == pytest.approx(1.0)
    finally:
        service.shutdown()
