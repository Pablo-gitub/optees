from __future__ import annotations

import pytest

from optees.application.contracts.batch import (
    MAX_BATCH_ITEMS,
    BatchItemRequest,
    BatchRequest,
    BatchStatus,
    aggregate_batch_status,
)
from optees.application.contracts.execution import JobStatus


def _item(identifier: str) -> BatchItemRequest:
    return BatchItemRequest(identifier, "lp.continuous", {"version": "1"})


def test_batch_request_requires_unique_bounded_items():
    with pytest.raises(ValueError, match="at least one"):
        BatchRequest(())
    with pytest.raises(ValueError, match="unique"):
        BatchRequest((_item("same"), _item("same")))
    with pytest.raises(ValueError, match=str(MAX_BATCH_ITEMS)):
        BatchRequest(tuple(_item(str(index)) for index in range(33)))


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ((JobStatus.QUEUED, JobStatus.QUEUED), BatchStatus.QUEUED),
        ((JobStatus.RUNNING, JobStatus.QUEUED), BatchStatus.RUNNING),
        ((JobStatus.COMPLETED, JobStatus.COMPLETED), BatchStatus.COMPLETED),
        ((JobStatus.CANCELLED, JobStatus.CANCELLED), BatchStatus.CANCELLED),
        ((JobStatus.FAILED, JobStatus.FAILED), BatchStatus.FAILED),
        ((JobStatus.COMPLETED, JobStatus.FAILED), BatchStatus.PARTIAL),
    ],
)
def test_batch_status_is_aggregated_from_individual_jobs(statuses, expected):
    assert aggregate_batch_status(statuses) is expected
