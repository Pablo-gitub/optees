from __future__ import annotations

import pytest

from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.solution_validation import SolutionValidationStatus
from optees.application.validation.lp_solution_validator import (
    LPIndependentSolutionValidator,
)
from optees.utility.lp_json_io import lp_model_from_dict


def _model():
    return lp_model_from_dict(
        {
            "version": "1",
            "variables": [
                {"name": "x", "label": "", "lb": 0, "ub": 2},
                {"name": "y", "label": "", "lb": 0, "ub": None},
            ],
            "objective": {
                "sense": "max",
                "coefficients": [3, 2],
                "offset": 0,
            },
            "constraints": [
                {"coefficients": [1, 1], "relation": "<=", "rhs": 4},
                {"coefficients": [1, -1], "relation": ">=", "rhs": 0},
                {"coefficients": [0, 1], "relation": "=", "rhs": 2},
            ],
        }
    )


def _result(
    *,
    objective: object = 10.0,
    variables: object = None,
    status: MathematicalStatus = MathematicalStatus.OPTIMAL,
) -> SerializedResult:
    rows = (
        [{"name": "x", "value": 2.0}, {"name": "y", "value": 2.0}]
        if variables is None
        else variables
    )
    return SerializedResult(
        mathematical_status=status,
        result={"objective": objective, "variables": rows},  # type: ignore[dict-item]
    )


def _violation_codes(report) -> set[str]:
    return {violation.code for violation in report.violations}


def test_valid_lp_candidate_is_verified_independently():
    report = LPIndependentSolutionValidator()(_model(), _result())

    assert report.status is SolutionValidationStatus.VERIFIED
    assert [check.code for check in report.checks] == [
        "lp.variable_vector",
        "lp.bounds",
        "lp.constraints",
        "lp.objective",
    ]
    assert report.tolerances == {"absolute": 1e-7, "relative": 1e-7}
    assert report.limitations


def test_objective_mismatch_is_reported_without_changing_solver_status():
    report = LPIndependentSolutionValidator()(_model(), _result(objective=9.0))

    assert report.status is SolutionValidationStatus.FAILED
    assert _violation_codes(report) == {"objective_mismatch"}
    assert report.violations[0].path == "$.result.objective"


def test_bound_and_constraint_violations_are_reported_together():
    report = LPIndependentSolutionValidator()(
        _model(),
        _result(
            objective=12.0,
            variables=[
                {"name": "x", "value": 3.0},
                {"name": "y", "value": 1.5},
            ],
        ),
    )

    assert report.status is SolutionValidationStatus.FAILED
    assert "upper_bound_violation" in _violation_codes(report)
    assert "constraint_violation" in _violation_codes(report)


def test_candidate_on_configured_tolerance_boundary_is_accepted():
    report = LPIndependentSolutionValidator(
        absolute_tolerance=1e-6,
        relative_tolerance=0.0,
    )(
        _model(),
        _result(
            objective=10.000001,
            variables=[
                {"name": "x", "value": 2.0000005},
                {"name": "y", "value": 1.9999995},
            ],
        ),
    )

    assert report.status is SolutionValidationStatus.VERIFIED


@pytest.mark.parametrize(
    "variables",
    [
        [{"name": "x", "value": 2.0}],
        [
            {"name": "x", "value": 2.0},
            {"name": "x", "value": 2.0},
            {"name": "y", "value": 2.0},
        ],
        [
            {"name": "x", "value": 2.0},
            {"name": "unknown", "value": 2.0},
        ],
        [{"name": "x", "value": True}, {"name": "y", "value": 2.0}],
    ],
)
def test_incomplete_duplicate_unknown_or_non_numeric_vectors_fail(variables):
    report = LPIndependentSolutionValidator()(
        _model(),
        _result(variables=variables),
    )

    assert report.status is SolutionValidationStatus.FAILED
    assert _violation_codes(report) == {"invalid_variable_vector"}


@pytest.mark.parametrize(
    "status",
    [
        MathematicalStatus.INFEASIBLE,
        MathematicalStatus.UNBOUNDED,
        MathematicalStatus.NOT_SOLVED,
    ],
)
def test_outcomes_without_primal_candidate_are_explicitly_not_available(status):
    report = LPIndependentSolutionValidator()(_model(), _result(status=status))

    assert report.status is SolutionValidationStatus.NOT_AVAILABLE
    assert report.limitations
