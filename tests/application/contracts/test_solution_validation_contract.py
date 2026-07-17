from __future__ import annotations

import pytest

from optees.application.contracts.solution_validation import (
    SolutionValidation,
    SolutionValidationStatus,
    ValidationCheck,
    ValidationCheckStatus,
    ValidationViolation,
)


def _check(status=ValidationCheckStatus.PASSED):
    return ValidationCheck(
        code="objective.recomputed",
        status=status,
        description="Recompute the objective from the candidate vector.",
        measurements={"reported": 10.0, "recomputed": 10.0},
    )


def test_verified_report_serializes_checks_tolerances_and_limitations():
    report = SolutionValidation.from_checks(
        (_check(),),
        tolerances={"absolute": 1e-7, "relative": 1e-7},
        limitations=("Optimality is not independently proven.",),
    )

    payload = report.to_dict()

    assert report.status is SolutionValidationStatus.VERIFIED
    assert payload["status"] == "verified"
    assert payload["checks"][0]["status"] == "passed"
    assert payload["tolerances"] == {"absolute": 1e-7, "relative": 1e-7}
    assert payload["limitations"]


def test_failed_report_requires_a_violation_linked_to_a_failed_check():
    violation = ValidationViolation(
        code="objective_mismatch",
        check_code="objective.recomputed",
        path="$.result.objective",
        message="Reported and recomputed objectives differ.",
        measurements={"difference": 2.0},
    )
    report = SolutionValidation.from_checks(
        (_check(ValidationCheckStatus.FAILED),),
        violations=(violation,),
    )

    assert report.status is SolutionValidationStatus.FAILED
    assert report.to_dict()["violations"][0]["code"] == "objective_mismatch"

    with pytest.raises(ValueError, match="violations"):
        SolutionValidation.from_checks((_check(ValidationCheckStatus.FAILED),))


def test_partial_and_not_available_are_distinct_contract_states():
    partial = SolutionValidation.from_checks(
        (_check(),),
        partial=True,
        limitations=("Only finite values were checked.",),
    )
    unavailable = SolutionValidation.not_available("No validator is registered.")

    assert partial.status is SolutionValidationStatus.PARTIAL
    assert unavailable.status is SolutionValidationStatus.NOT_AVAILABLE
    assert unavailable.to_dict()["checks"] == []


@pytest.mark.parametrize("value", [-1.0, float("inf"), float("nan"), True])
def test_tolerances_must_be_finite_non_negative_numbers(value):
    with pytest.raises(ValueError, match="tolerances"):
        SolutionValidation.from_checks(
            (_check(),),
            tolerances={"absolute": value},
        )
