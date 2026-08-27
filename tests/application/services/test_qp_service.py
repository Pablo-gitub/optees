from __future__ import annotations

import time

from optees.application.contracts.capability_ids import QP_CAPABILITY_ID
from optees.application.contracts.execution import ExecutionEnvelope, JobStatus, MathematicalStatus
from optees.application.contracts.solution_validation import SolutionValidationStatus
from optees.composition.local_agent import (
    create_local_job_service,
    create_local_optimization_service,
)


def test_qp_optimization_service_execution() -> None:
    service = create_local_optimization_service()
    problem_payload = {
        "contract_version": "1",
        "problem_schema_version": "1",
        "capability_id": QP_CAPABILITY_ID,
        "problem_type": "quadratic_programming",
        "variables": [
            {"name": "x1", "label": "X1", "lower_bound": None, "upper_bound": None},
            {"name": "x2", "label": "X2", "lower_bound": None, "upper_bound": None},
        ],
        "objective": {
            "sense": "min",
            "linear_coefs": [-4.0, -6.0],
            "quadratic_matrix": [
                [2.0, 1.0],
                [1.0, 2.0],
            ],
            "offset": 0.0,
        },
        "constraints": [],
        "options": {
            "method": "osqp",
            "tolerance": 1e-7,
        },
    }

    envelope = service.solve(QP_CAPABILITY_ID, problem_payload)
    assert isinstance(envelope, ExecutionEnvelope)
    assert envelope.capability_id == QP_CAPABILITY_ID
    assert envelope.job_status == JobStatus.COMPLETED
    assert envelope.mathematical_status == MathematicalStatus.OPTIMAL
    assert envelope.result is not None
    assert abs(envelope.result["objective"] - (-28.0 / 3.0)) < 1e-5
    assert abs(envelope.result["variables"]["x1"] - (2.0 / 3.0)) < 1e-5
    assert abs(envelope.result["variables"]["x2"] - (8.0 / 3.0)) < 1e-5
    assert envelope.validation is not None
    assert envelope.validation.status in {
        SolutionValidationStatus.VERIFIED,
        SolutionValidationStatus.PARTIAL,
    }


def test_qp_job_service_lifecycle() -> None:
    job_service = create_local_job_service()
    problem_payload = {
        "contract_version": "1",
        "problem_schema_version": "1",
        "capability_id": QP_CAPABILITY_ID,
        "problem_type": "quadratic_programming",
        "variables": [
            {"name": "x1", "lower_bound": 0.0, "upper_bound": None},
            {"name": "x2", "lower_bound": 0.0, "upper_bound": None},
        ],
        "objective": {
            "sense": "min",
            "linear_coefs": [0.0, 0.0],
            "quadratic_matrix": [
                [1.0, 0.0],
                [0.0, 1.0],
            ],
            "offset": 0.0,
        },
        "constraints": [
            {"name": "c1", "coefs": [1.0, 1.0], "relation": ">=", "rhs": 2.0}
        ],
        "options": {"method": "osqp"},
    }

    outcome = job_service.submit(QP_CAPABILITY_ID, problem_payload)
    assert not hasattr(outcome, "code"), f"Submission failed: {outcome}"
    job_id = outcome.job_id

    # Wait for completion
    deadline = time.time() + 5.0
    completed = False
    while time.time() < deadline:
        snapshot = job_service.get(job_id)
        if snapshot and hasattr(snapshot, "job_status") and snapshot.job_status in {JobStatus.COMPLETED, JobStatus.FAILED}:
            completed = True
            break
        time.sleep(0.05)

    assert completed, "Job did not complete within deadline"
    result_envelope = job_service.result(job_id)
    assert isinstance(result_envelope, ExecutionEnvelope)
    assert result_envelope.job_status == JobStatus.COMPLETED
    assert result_envelope.mathematical_status == MathematicalStatus.OPTIMAL
    assert result_envelope.validation.status == SolutionValidationStatus.VERIFIED
    job_service.shutdown()
