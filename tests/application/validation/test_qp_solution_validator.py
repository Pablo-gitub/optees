from __future__ import annotations

import pytest

from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.solution_validation import (
    SolutionValidationStatus,
    ValidationCheckStatus,
)
from optees.application.validation.qp_solution_validator import (
    QPIndependentSolutionValidator,
)
from optees.domain.entities.qp.constraint import QPConstraint
from optees.domain.entities.qp.objective import QPObjective
from optees.domain.entities.qp.variable import QPVariable
from optees.domain.models.qp.qp_model import QPModel
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation


@pytest.fixture
def sample_qp_model() -> QPModel:
    vars_ = (
        QPVariable(name="x1", bounds=Bounds(0.0, 5.0)),
        QPVariable(name="x2", bounds=Bounds(0.0, 5.0)),
    )
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(0.0, 0.0),
        quadratic_matrix=((1.0, 0.0), (0.0, 1.0)),
        offset=0.0,
    )
    cons = (QPConstraint(name="c1", coefs=(1.0, 1.0), relation=Relation.GE, rhs=2.0),)
    return QPModel(variables=vars_, objective=obj, constraints=cons)


def test_validator_verified_with_duals(sample_qp_model: QPModel) -> None:
    # Optimum at x* = (1, 1), obj = 1.0, dual for Ax >= b (A = [1, 1], b = 2) is y = -1.0
    validator = QPIndependentSolutionValidator()
    serialized = SerializedResult(
        mathematical_status=MathematicalStatus.OPTIMAL,
        result={
            "variables": [{"name": "x1", "value": 1.0}, {"name": "x2", "value": 1.0}],
            "objective": 1.0,
            "dual_values": {
                "constraints": [-1.0],
                "lower_bounds": [0.0, 0.0],
                "upper_bounds": [0.0, 0.0],
            },
        },
    )
    report = validator(sample_qp_model, serialized)
    assert report.status == SolutionValidationStatus.VERIFIED
    assert len(report.violations) == 0
    assert len(report.checks) == 5
    assert all(c.status == ValidationCheckStatus.PASSED for c in report.checks)


def test_validator_partial_without_duals(sample_qp_model: QPModel) -> None:
    validator = QPIndependentSolutionValidator()
    serialized = SerializedResult(
        mathematical_status=MathematicalStatus.OPTIMAL,
        result={
            "variables": [{"name": "x1", "value": 1.0}, {"name": "x2", "value": 1.0}],
            "objective": 1.0,
        },
    )
    report = validator(sample_qp_model, serialized)
    assert report.status == SolutionValidationStatus.PARTIAL
    assert len(report.violations) == 0
    assert len(report.checks) == 4
    assert all(c.status == ValidationCheckStatus.PASSED for c in report.checks)


def test_validator_not_available_for_infeasible(sample_qp_model: QPModel) -> None:
    validator = QPIndependentSolutionValidator()
    serialized = SerializedResult(
        mathematical_status=MathematicalStatus.INFEASIBLE,
        result={},
    )
    report = validator(sample_qp_model, serialized)
    assert report.status == SolutionValidationStatus.NOT_AVAILABLE


def test_validator_detects_tampered_variable_vector(sample_qp_model: QPModel) -> None:
    validator = QPIndependentSolutionValidator()
    # Missing variable x2
    serialized = SerializedResult(
        mathematical_status=MathematicalStatus.OPTIMAL,
        result={"variables": [{"name": "x1", "value": 1.0}], "objective": 1.0},
    )
    report = validator(sample_qp_model, serialized)
    assert report.status == SolutionValidationStatus.FAILED
    assert any(v.check_code == "qp.variable_vector" for v in report.violations)


def test_validator_detects_tampered_bounds(sample_qp_model: QPModel) -> None:
    validator = QPIndependentSolutionValidator()
    # x1 = -1.0 violates lower bound 0.0
    serialized = SerializedResult(
        mathematical_status=MathematicalStatus.OPTIMAL,
        result={
            "variables": [{"name": "x1", "value": -1.0}, {"name": "x2", "value": 3.0}],
            "objective": 5.0,
        },
    )
    report = validator(sample_qp_model, serialized)
    assert report.status == SolutionValidationStatus.FAILED
    assert any(v.check_code == "qp.bounds" for v in report.violations)


def test_validator_detects_tampered_constraints(sample_qp_model: QPModel) -> None:
    validator = QPIndependentSolutionValidator()
    # x1 + x2 = 0.5 < 2.0 violates constraint c1 (>= 2.0)
    serialized = SerializedResult(
        mathematical_status=MathematicalStatus.OPTIMAL,
        result={
            "variables": [{"name": "x1", "value": 0.25}, {"name": "x2", "value": 0.25}],
            "objective": 0.0625,
        },
    )
    report = validator(sample_qp_model, serialized)
    assert report.status == SolutionValidationStatus.FAILED
    assert any(v.check_code == "qp.constraints" for v in report.violations)


def test_validator_detects_tampered_objective(sample_qp_model: QPModel) -> None:
    validator = QPIndependentSolutionValidator()
    # Actual objective is 0.5 * (1^2 + 1^2) = 1.0; reported is 99.0
    serialized = SerializedResult(
        mathematical_status=MathematicalStatus.OPTIMAL,
        result={
            "variables": [{"name": "x1", "value": 1.0}, {"name": "x2", "value": 1.0}],
            "objective": 99.0,
        },
    )
    report = validator(sample_qp_model, serialized)
    assert report.status == SolutionValidationStatus.FAILED
    assert any(v.check_code == "qp.objective" for v in report.violations)


def test_validator_detects_tampered_kkt_stationarity(sample_qp_model: QPModel) -> None:
    validator = QPIndependentSolutionValidator()
    # Gradient is [1, 1], with wrong constraint dual 50.0 => stationarity fails
    serialized = SerializedResult(
        mathematical_status=MathematicalStatus.OPTIMAL,
        result={
            "variables": [{"name": "x1", "value": 1.0}, {"name": "x2", "value": 1.0}],
            "objective": 1.0,
            "dual_values": {
                "constraints": [50.0],
                "lower_bounds": [0.0, 0.0],
                "upper_bounds": [0.0, 0.0],
            },
        },
    )
    report = validator(sample_qp_model, serialized)
    assert report.status == SolutionValidationStatus.FAILED
    assert any(v.check_code == "qp.kkt_stationarity" for v in report.violations)


def test_validator_detects_complementary_slackness_failure(
    sample_qp_model: QPModel,
) -> None:
    serialized = SerializedResult(
        mathematical_status=MathematicalStatus.OPTIMAL,
        result={
            "variables": [{"name": "x1", "value": 2.0}, {"name": "x2", "value": 2.0}],
            "objective": 4.0,
            "dual_values": {
                "constraints": [-2.0],
                "lower_bounds": [0.0, 0.0],
                "upper_bounds": [0.0, 0.0],
            },
        },
    )
    report = QPIndependentSolutionValidator()(sample_qp_model, serialized)
    assert report.status == SolutionValidationStatus.FAILED
    assert any(v.code == "qp.kkt_complementarity_violation" for v in report.violations)
