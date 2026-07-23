from __future__ import annotations

import pytest

from optees.application.contracts.execution import JobStatus
from optees.application.services.job_repository import (
    InMemoryJobRepository,
    JobRecord,
    JobRepositoryFullError,
)


def _record(job_id: str, status: JobStatus = JobStatus.QUEUED) -> JobRecord:
    return JobRecord(
        job_id=job_id,
        capability_id="test.capability",
        payload={},
        submitted_at=float(job_id.removeprefix("job-")),
        job_status=status,
    )


def test_repository_rejects_invalid_capacity_and_duplicate_ids():
    with pytest.raises(ValueError, match="positive integer"):
        InMemoryJobRepository(capacity=0)

    repository = InMemoryJobRepository(capacity=2)
    repository.add(_record("job-1"))
    with pytest.raises(ValueError, match="already exists"):
        repository.add(_record("job-1"))


def test_repository_never_evicts_active_jobs_when_full():
    repository = InMemoryJobRepository(capacity=2)
    repository.add(_record("job-1", JobStatus.RUNNING))
    repository.add(_record("job-2", JobStatus.QUEUED))

    with pytest.raises(JobRepositoryFullError, match="active jobs"):
        repository.add(_record("job-3"))

    assert [record.job_id for record in repository.list()] == ["job-1", "job-2"]


def test_repository_evicts_oldest_terminal_job_before_accepting_new_work():
    repository = InMemoryJobRepository(capacity=2)
    repository.add(_record("job-1", JobStatus.COMPLETED))
    repository.add(_record("job-2", JobStatus.FAILED))

    repository.add(_record("job-3"))

    assert repository.get("job-1") is None
    assert [record.job_id for record in repository.list()] == ["job-2", "job-3"]


def test_repository_add_many_is_atomic_when_capacity_is_insufficient():
    repository = InMemoryJobRepository(capacity=2)
    repository.add(_record("job-1", JobStatus.RUNNING))

    with pytest.raises(JobRepositoryFullError, match="active jobs"):
        repository.add_many((_record("job-2"), _record("job-3")))

    assert [record.job_id for record in repository.list()] == ["job-1"]


def test_job_snapshot_keeps_operational_and_mathematical_state_separate():
    snapshot = _record("job-1", JobStatus.RUNNING).snapshot()

    assert snapshot.job_status is JobStatus.RUNNING
    assert snapshot.mathematical_status is None
    assert snapshot.result_available is False
    assert snapshot.to_dict()["job_status"] == "running"
