from __future__ import annotations

import pytest

from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.solution_validation import SolutionValidationStatus
from optees.application.codecs.milp_problem_codec import milp_model_from_public_dict
from optees.application.validation.milp_solution_validator import (
    MILPIndependentSolutionValidator,
)


def _model():
    return milp_model_from_public_dict(
        {
            "version": "1",
            "variables": [
                {"name": "units", "lb": 0, "ub": 4, "integrality": "I"},
                {"name": "open", "lb": 0, "ub": 1, "integrality": "B"},
                {"name": "flow", "lb": 0, "ub": None, "integrality": "C"},
            ],
            "objective": {
                "sense": "max",
                "coefficients": [3, -1, 2],
                "offset": 0,
            },
            "constraints": [
                {"coefficients": [1, -4, 0], "relation": "<=", "rhs": 0},
                {"coefficients": [0, 0, 1], "relation": "<=", "rhs": 2},
            ],
        }
    )


def _result(
    *,
    objective: object = 15.0,
    variables: object = None,
    status: MathematicalStatus = MathematicalStatus.OPTIMAL,
) -> SerializedResult:
    rows = (
        [
            {"name": "units", "value": 4.0},
            {"name": "open", "value": 1.0},
            {"name": "flow", "value": 2.0},
        ]
        if variables is None
        else variables
    )
    return SerializedResult(
        mathematical_status=status,
        result={"objective": objective, "variables": rows},  # type: ignore[dict-item]
    )


def _violation_codes(report) -> set[str]:
    return {violation.code for violation in report.violations}


def test_valid_mixed_candidate_is_verified_independently():
    report = MILPIndependentSolutionValidator()(_model(), _result())

    assert report.status is SolutionValidationStatus.VERIFIED
    assert [check.code for check in report.checks] == [
        "milp.variable_vector",
        "milp.bounds",
        "milp.integrality",
        "milp.constraints",
        "milp.objective",
    ]
    assert report.tolerances == {
        "absolute": 1e-7,
        "relative": 1e-7,
        "integrality": 1e-7,
    }


def test_fractional_integer_candidate_fails_integrality_check():
    report = MILPIndependentSolutionValidator()(
        _model(),
        _result(
            objective=13.5,
            variables=[
                {"name": "units", "value": 3.5},
                {"name": "open", "value": 1.0},
                {"name": "flow", "value": 2.0},
            ],
        ),
    )

    assert report.status is SolutionValidationStatus.FAILED
    assert _violation_codes(report) == {"integrality_violation"}
    assert report.violations[0].path == "$.result.variables[0].value"


def test_non_binary_candidate_fails_binary_domain_check():
    report = MILPIndependentSolutionValidator()(
        _model(),
        _result(
            objective=9.5,
            variables=[
                {"name": "units", "value": 2.0},
                {"name": "open", "value": 0.5},
                {"name": "flow", "value": 2.0},
            ],
        ),
    )

    assert report.status is SolutionValidationStatus.FAILED
    assert _violation_codes(report) == {"binary_domain_violation"}


def test_integrality_tolerance_accepts_nearby_discrete_values():
    report = MILPIndependentSolutionValidator(
        absolute_tolerance=1e-6,
        relative_tolerance=0.0,
        integrality_tolerance=1e-6,
    )(
        _model(),
        _result(
            objective=14.99999985,
            variables=[
                {"name": "units", "value": 3.99999995},
                {"name": "open", "value": 0.99999995},
                {"name": "flow", "value": 2.0},
            ],
        ),
    )

    assert report.status is SolutionValidationStatus.VERIFIED


def test_linear_and_integrality_violations_are_reported_together():
    report = MILPIndependentSolutionValidator()(
        _model(),
        _result(
            objective=20.0,
            variables=[
                {"name": "units", "value": 4.5},
                {"name": "open", "value": 1.0},
                {"name": "flow", "value": 2.0},
            ],
        ),
    )

    assert report.status is SolutionValidationStatus.FAILED
    assert {
        "upper_bound_violation",
        "constraint_violation",
        "integrality_violation",
        "objective_mismatch",
    } <= _violation_codes(report)


def test_invalid_variable_vector_stops_dependent_checks():
    report = MILPIndependentSolutionValidator()(
        _model(),
        _result(variables=[{"name": "units", "value": 4.0}]),
    )

    assert report.status is SolutionValidationStatus.FAILED
    assert [check.code for check in report.checks] == ["milp.variable_vector"]
    assert _violation_codes(report) == {"invalid_variable_vector"}


@pytest.mark.parametrize(
    "status",
    [
        MathematicalStatus.INFEASIBLE,
        MathematicalStatus.UNBOUNDED,
        MathematicalStatus.NOT_SOLVED,
    ],
)
def test_outcomes_without_incumbent_are_explicitly_not_available(status):
    report = MILPIndependentSolutionValidator()(_model(), _result(status=status))

    assert report.status is SolutionValidationStatus.NOT_AVAILABLE
    assert report.limitations
