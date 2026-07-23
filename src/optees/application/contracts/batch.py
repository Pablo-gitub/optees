from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum

from optees.application.contracts.errors import StructuredError
from optees.application.contracts.execution import ExecutionEnvelope, JobStatus
from optees.application.contracts.job import JobSnapshot
from optees.application.contracts.json_value import JsonValue, require_json_value


MAX_BATCH_ITEMS = 32


class BatchStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class BatchItemRequest:
    client_item_id: str
    capability_id: str
    problem: dict[str, JsonValue]

    def __post_init__(self) -> None:
        client_item_id = self.client_item_id.strip()
        capability_id = self.capability_id.strip()
        if not client_item_id:
            raise ValueError("batch client_item_id must not be empty")
        if not capability_id:
            raise ValueError("batch capability_id must not be empty")
        problem = require_json_value(
            self.problem,
            path="$.batch.items[].problem",
        )
        assert isinstance(problem, dict)
        object.__setattr__(self, "client_item_id", client_item_id)
        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "problem", problem)


@dataclass(frozen=True)
class BatchRequest:
    items: tuple[BatchItemRequest, ...]
    version: str = "1"

    def __post_init__(self) -> None:
        if self.version != "1":
            raise ValueError("unsupported batch contract version")
        if not self.items:
            raise ValueError("batch requests must contain at least one item")
        if len(self.items) > MAX_BATCH_ITEMS:
            raise ValueError(
                f"batch requests accept at most {MAX_BATCH_ITEMS} items"
            )
        identifiers = [item.client_item_id for item in self.items]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("batch client_item_id values must be unique")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "version": self.version,
            "items": [
                {
                    "client_item_id": item.client_item_id,
                    "capability_id": item.capability_id,
                    "problem": item.problem,
                }
                for item in self.items
            ],
        }


@dataclass(frozen=True)
class BatchValidationItem:
    client_item_id: str
    capability_id: str
    valid: bool
    available: bool
    validation: dict[str, JsonValue] | None = None
    error: dict[str, JsonValue] | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, object] = {
            "client_item_id": self.client_item_id,
            "capability_id": self.capability_id,
            "valid": self.valid,
            "available": self.available,
            "validation": self.validation,
            "error": self.error,
        }
        normalized = require_json_value(payload, path="$.batch_validation.items[]")
        assert isinstance(normalized, dict)
        return normalized


@dataclass(frozen=True)
class BatchValidation:
    items: tuple[BatchValidationItem, ...]
    contract_version: str = "1"

    @property
    def valid(self) -> bool:
        return all(item.valid and item.available for item in self.items)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "contract_version": self.contract_version,
            "valid": self.valid,
            "item_count": len(self.items),
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True)
class BatchItemSnapshot:
    client_item_id: str
    job: JobSnapshot

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "client_item_id": self.client_item_id,
            "job": self.job.to_dict(),
        }


@dataclass(frozen=True)
class BatchSnapshot:
    batch_id: str
    batch_status: BatchStatus
    submitted_at: float
    items: tuple[BatchItemSnapshot, ...]
    finished_at: float | None = None
    contract_version: str = "1"

    def to_dict(self) -> dict[str, JsonValue]:
        counts = Counter(item.job.job_status.value for item in self.items)
        payload: dict[str, object] = {
            "contract_version": self.contract_version,
            "batch_id": self.batch_id,
            "batch_status": self.batch_status.value,
            "submitted_at": self.submitted_at,
            "finished_at": self.finished_at,
            "item_count": len(self.items),
            "counts": dict(sorted(counts.items())),
            "items": [item.to_dict() for item in self.items],
        }
        normalized = require_json_value(payload, path="$.batch")
        assert isinstance(normalized, dict)
        return normalized


@dataclass(frozen=True)
class BatchResultItem:
    client_item_id: str
    job: JobSnapshot
    result: ExecutionEnvelope | None = None
    error: StructuredError | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, object] = {
            "client_item_id": self.client_item_id,
            "job": self.job.to_dict(),
            "result": self.result.to_dict() if self.result is not None else None,
            "error": self.error.to_dict() if self.error is not None else None,
        }
        normalized = require_json_value(payload, path="$.batch_result.items[]")
        assert isinstance(normalized, dict)
        return normalized


@dataclass(frozen=True)
class BatchResult:
    batch: BatchSnapshot
    items: tuple[BatchResultItem, ...]
    contract_version: str = "1"

    def to_dict(self) -> dict[str, JsonValue]:
        validation_counts = Counter(
            (
                item.result.validation.status.value
                if item.result is not None
                else "not_available"
            )
            for item in self.items
        )
        mathematical_counts = Counter(
            (
                item.result.mathematical_status.value
                if item.result is not None
                and item.result.mathematical_status is not None
                else "not_available"
            )
            for item in self.items
        )
        payload: dict[str, object] = {
            "contract_version": self.contract_version,
            "batch": self.batch.to_dict(),
            "summary": {
                "validation_status_counts": dict(sorted(validation_counts.items())),
                "mathematical_status_counts": dict(
                    sorted(mathematical_counts.items())
                ),
            },
            "items": [item.to_dict() for item in self.items],
        }
        normalized = require_json_value(payload, path="$.batch_result")
        assert isinstance(normalized, dict)
        return normalized


def aggregate_batch_status(statuses: tuple[JobStatus, ...]) -> BatchStatus:
    if all(status is JobStatus.QUEUED for status in statuses):
        return BatchStatus.QUEUED
    terminal = {JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED}
    if any(status not in terminal for status in statuses):
        return BatchStatus.RUNNING
    if all(status is JobStatus.COMPLETED for status in statuses):
        return BatchStatus.COMPLETED
    if all(status is JobStatus.CANCELLED for status in statuses):
        return BatchStatus.CANCELLED
    if all(status is JobStatus.FAILED for status in statuses):
        return BatchStatus.FAILED
    return BatchStatus.PARTIAL
