from __future__ import annotations

import json

import pytest

from optees.application.contracts.errors import (
    ErrorCode,
    ErrorDetail,
    StructuredError,
)
from optees.application.contracts.execution import (
    ExecutionEnvelope,
    ExecutionMetadata,
    JobStatus,
    MathematicalStatus,
    TerminationReason,
)
from optees.application.contracts.json_value import dumps_json, require_json_value


def test_execution_envelope_is_strict_json_and_keeps_statuses_separate():
    envelope = ExecutionEnvelope(
        job_id="job-1",
        capability_id="lp.continuous",
        job_status=JobStatus.COMPLETED,
        mathematical_status=MathematicalStatus.OPTIMAL,
        termination_reason=TerminationReason.COMPLETED,
        result={"objective": 7.0},
        diagnostics={"iterations": None},
        metadata=ExecutionMetadata(
            optees_version="0.8.0",
            api_version="v1",
            problem_schema_version="1",
            result_schema_version="1",
        ),
    )

    payload = json.loads(envelope.to_json())

    assert payload["job_status"] == "completed"
    assert payload["mathematical_status"] == "optimal"
    assert payload["termination_reason"] == "completed"
    assert payload["validation"]["status"] == "not_available"
    assert payload["validation"]["contract_version"] == "1"
    assert payload["validation"]["limitations"]


def test_running_job_can_have_no_mathematical_status_or_termination_reason():
    envelope = ExecutionEnvelope(
        job_id="job-2",
        capability_id="lp.continuous",
        job_status=JobStatus.RUNNING,
        mathematical_status=None,
        termination_reason=None,
        result={},
        diagnostics={},
        metadata=ExecutionMetadata("0.8.0", "v1", "1", "1"),
    )

    payload = envelope.to_dict()

    assert payload["mathematical_status"] is None
    assert payload["termination_reason"] is None


def test_structured_error_has_stable_machine_readable_shape():
    error = StructuredError(
        code=ErrorCode.VALIDATION_FAILED,
        message="The problem payload is invalid.",
        request_id="request-1",
        details=(ErrorDetail("$.variables[0].lb", "Must be finite."),),
        context={"capability_id": "lp.continuous"},
    )

    payload = error.to_dict()

    assert payload["error"]["code"] == "validation_failed"
    assert payload["error"]["details"][0]["path"] == "$.variables[0].lb"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_public_json_rejects_non_finite_numbers(value):
    with pytest.raises(ValueError, match="non-finite"):
        dumps_json({"value": value})


def test_public_json_rejects_implicit_tuple_and_non_string_keys():
    with pytest.raises(ValueError, match="unsupported type tuple"):
        require_json_value({"items": (1, 2)})
    with pytest.raises(ValueError, match="non-string object key"):
        require_json_value({1: "value"})
