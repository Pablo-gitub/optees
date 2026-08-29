from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import pytest

from optees.application.contracts.solution_validation import (
    SolutionValidationStatus,
    ValidationCheckStatus,
)
from optees.application.services.scenario_reconstruction_service import (
    ScenarioReconstructionService,
)
from optees.application.services.scenario_reduction_service import (
    ScenarioReductionService,
)
from optees.application.validation.scenario_solution_validator import (
    ScenarioIndependentSolutionValidator,
)
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.entities.milp.solution import MILPSolution
from optees.domain.entities.scenario.constraint import ScenarioConstraint
from optees.domain.entities.scenario.scenario import Scenario
from optees.domain.entities.scenario.variable import ScenarioVariable
from optees.domain.models.scenario.scenario_model import ScenarioModel
from optees.domain.models.scenario.scenario_result import (
    ScenarioResult,
    ScenarioSolveStatus,
)
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.lp.solve_status import SolveStatus
from optees.domain.value_objects.lp.solver_diagnostics import SolverDiagnostics
from optees.domain.value_objects.milp.integrality import Integrality
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus
from optees.domain.value_objects.milp.solver_diagnostics import (
    MILPSolverDiagnostics,
)
from optees.domain.value_objects.scenario.scenario_orientation import (
    ScenarioOrientation,
)


@dataclass(frozen=True)
class ForgedScenarioValueDouble:
    """Test double for corrupted ScenarioValue instances."""

    scenario_id: Any
    value: Any
    is_binding: Any


@dataclass(frozen=True)
class ForgedScenarioResultDouble:
    """Test double used exclusively when ScenarioResult post-init invariants forbid corrupt states."""

    status: Any
    orientation: Any
    original_variable_order: Any
    scenario_order: Any
    guaranteed_value: Any
    variables: Any
    scenario_values: Any
    binding_scenario_ids: Any
    delegated_solution: Any
    auxiliary_variable_name: Any
    auxiliary_value: Any

    def has_candidate(self) -> bool:
        return (
            self.status in (ScenarioSolveStatus.OPTIMAL, ScenarioSolveStatus.FEASIBLE)
            and self.variables is not None
        )


def _make_continuous_loss_fixture() -> tuple[ScenarioModel, ScenarioResult, LPSolution]:
    vars_ = (
        ScenarioVariable(name="x1", bounds=Bounds(0.0, None)),
        ScenarioVariable(name="x2", bounds=Bounds(0.0, None)),
    )
    scenarios = (
        Scenario(id="s1", coefficients=(2.0, -1.0), offset=5.0),
        Scenario(id="s2", coefficients=(-1.0, 3.0), offset=2.0),
        Scenario(id="s3", coefficients=(1.0, 1.0), offset=-4.0),
    )
    constraints = (
        ScenarioConstraint(
            name="budget",
            coefficients=(1.0, 1.0),
            relation=Relation.EQ,
            rhs=10.0,
        ),
    )
    model = ScenarioModel(
        orientation=ScenarioOrientation.MIN_MAX_LOSS,
        variables=vars_,
        scenarios=scenarios,
        shared_constraints=constraints,
    )
    reduction = ScenarioReductionService.reduce(model)
    lp_sol = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=76.0 / 7.0,
        values={
            "x1": 37.0 / 7.0,
            "x2": 33.0 / 7.0,
            "_aux_theta": 76.0 / 7.0,
        },
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    result = ScenarioReconstructionService.reconstruct(model, reduction, lp_sol)
    return model, result, lp_sol


def _make_discrete_loss_fixture() -> tuple[ScenarioModel, ScenarioResult, MILPSolution]:
    vars_ = (
        ScenarioVariable(name="x1", integrality=Integrality.BINARY),
        ScenarioVariable(name="x2", integrality=Integrality.BINARY),
        ScenarioVariable(name="x3", integrality=Integrality.BINARY),
    )
    scenarios = (
        Scenario(id="s1", coefficients=(10.0, 2.0, 8.0), offset=0.0),
        Scenario(id="s2", coefficients=(3.0, 12.0, 4.0), offset=0.0),
        Scenario(id="s3", coefficients=(6.0, 5.0, 9.0), offset=0.0),
    )
    constraints = (
        ScenarioConstraint(
            name="cardinality",
            coefficients=(1.0, 1.0, 1.0),
            relation=Relation.EQ,
            rhs=2.0,
        ),
    )
    model = ScenarioModel(
        orientation=ScenarioOrientation.MIN_MAX_LOSS,
        variables=vars_,
        scenarios=scenarios,
        shared_constraints=constraints,
    )
    reduction = ScenarioReductionService.reduce(model)
    milp_sol = MILPSolution(
        status=MILPSolveStatus.FEASIBLE,
        objective=15.0,
        values={
            "x1": 1.0,
            "x2": 1.0,
            "x3": 0.0,
            "_aux_theta": 15.0,
        },
        diagnostics=MILPSolverDiagnostics(),
        extras={},
    )
    result = ScenarioReconstructionService.reconstruct(model, reduction, milp_sol)
    return model, result, milp_sol


def test_validator_continuous_optimal_valid() -> None:
    """Verify that a valid continuous optimal candidate passes structural validation with VERIFIED status."""
    model, result, _ = _make_continuous_loss_fixture()
    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, result)

    assert report.status is SolutionValidationStatus.VERIFIED
    assert len(report.checks) == 4
    assert len(report.violations) == 0

    check_codes = [c.code for c in report.checks]
    assert check_codes == [
        "scenario.orientation",
        "scenario.status_coherence",
        "scenario.variable_vector",
        "scenario.scenario_values",
    ]
    for check in report.checks:
        assert check.status is ValidationCheckStatus.PASSED


def test_validator_discrete_feasible_valid() -> None:
    """Verify that a valid discrete feasible candidate passes structural validation with VERIFIED status."""
    model, result, _ = _make_discrete_loss_fixture()
    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, result)

    assert report.status is SolutionValidationStatus.VERIFIED
    assert len(report.checks) == 4
    assert len(report.violations) == 0

    for check in report.checks:
        assert check.status is ValidationCheckStatus.PASSED


@pytest.mark.parametrize(
    ("solver_status", "robust_status"),
    [
        (SolveStatus.INFEASIBLE, ScenarioSolveStatus.INFEASIBLE),
        (SolveStatus.UNBOUNDED, ScenarioSolveStatus.UNBOUNDED),
        (SolveStatus.NOT_SOLVED, ScenarioSolveStatus.NOT_SOLVED),
    ],
)
def test_validator_no_candidate_statuses_return_not_available(
    solver_status: SolveStatus, robust_status: ScenarioSolveStatus
) -> None:
    """Verify that clean no-candidate statuses honestly return NOT_AVAILABLE with zero passed checks."""
    model, _, _ = _make_continuous_loss_fixture()
    reduction = ScenarioReductionService.reduce(model)
    lp_sol = LPSolution(
        status=solver_status,
        objective=None,
        values={},
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    result = ScenarioReconstructionService.reconstruct(model, reduction, lp_sol)
    assert result.status == robust_status

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, result)

    assert report.status is SolutionValidationStatus.NOT_AVAILABLE
    assert len(report.checks) == 0
    assert len(report.violations) == 0
    assert (
        "No primal candidate is available for independent scenario validation."
        in report.limitations
    )


def test_validator_orientation_mismatch() -> None:
    """Verify that orientation discrepancy fails scenario.orientation check with exact detail code and path."""
    model, valid_result, _ = _make_continuous_loss_fixture()
    # Forge a double with wrong orientation
    corrupt_result = ForgedScenarioResultDouble(
        status=valid_result.status,
        orientation=ScenarioOrientation.MAX_MIN_REWARD,  # model is MIN_MAX_LOSS
        original_variable_order=valid_result.original_variable_order,
        scenario_order=valid_result.scenario_order,
        guaranteed_value=valid_result.guaranteed_value,
        variables=valid_result.variables,
        scenario_values=valid_result.scenario_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=valid_result.delegated_solution,
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=valid_result.auxiliary_value,
    )

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, corrupt_result)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    orientation_check = next(c for c in report.checks if c.code == "scenario.orientation")
    assert orientation_check.status is ValidationCheckStatus.FAILED

    violation = next(v for v in report.violations if v.code == "orientation_mismatch")
    assert violation.check_code == "scenario.orientation"
    assert violation.path == "$.orientation"
    assert "Result orientation" in violation.message


def test_validator_status_mismatch() -> None:
    """Verify that robust status inconsistent with delegated status fails scenario.status_coherence."""
    model, valid_result, lp_sol = _make_continuous_loss_fixture()
    # Robust status is FEASIBLE, but LPSolution status is OPTIMAL
    corrupt_result = ForgedScenarioResultDouble(
        status=ScenarioSolveStatus.FEASIBLE,
        orientation=valid_result.orientation,
        original_variable_order=valid_result.original_variable_order,
        scenario_order=valid_result.scenario_order,
        guaranteed_value=valid_result.guaranteed_value,
        variables=valid_result.variables,
        scenario_values=valid_result.scenario_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=lp_sol,  # SolveStatus.OPTIMAL
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=valid_result.auxiliary_value,
    )

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, corrupt_result)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    status_check = next(c for c in report.checks if c.code == "scenario.status_coherence")
    assert status_check.status is ValidationCheckStatus.FAILED

    violation = next(v for v in report.violations if v.code == "status_mismatch")
    assert violation.check_code == "scenario.status_coherence"
    assert violation.path == "$.status"


def test_validator_solution_type_mismatch() -> None:
    """Verify that continuous model paired with MILPSolution fails scenario.status_coherence."""
    model, valid_result, _ = _make_continuous_loss_fixture()
    # Model is continuous, but solution is MILPSolution
    fake_milp_sol = MILPSolution(
        status=MILPSolveStatus.OPTIMAL,
        objective=valid_result.guaranteed_value,
        values=dict(valid_result.variables or {}),
        diagnostics=MILPSolverDiagnostics(),
        extras={},
    )
    corrupt_result = ForgedScenarioResultDouble(
        status=valid_result.status,
        orientation=valid_result.orientation,
        original_variable_order=valid_result.original_variable_order,
        scenario_order=valid_result.scenario_order,
        guaranteed_value=valid_result.guaranteed_value,
        variables=valid_result.variables,
        scenario_values=valid_result.scenario_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=fake_milp_sol,
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=valid_result.auxiliary_value,
    )

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, corrupt_result)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    violation = next(v for v in report.violations if v.code == "solution_type_mismatch")
    assert violation.check_code == "scenario.status_coherence"
    assert violation.path == "$.delegated_solution"


def test_validator_unexpected_candidate_on_no_candidate_status() -> None:
    """Verify that candidate attached to INFEASIBLE fails with unexpected_candidate violation."""
    model, valid_result, _ = _make_continuous_loss_fixture()
    lp_inf = LPSolution(
        status=SolveStatus.INFEASIBLE,
        objective=None,
        values={},
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    corrupt_result = ForgedScenarioResultDouble(
        status=ScenarioSolveStatus.INFEASIBLE,
        orientation=valid_result.orientation,
        original_variable_order=valid_result.original_variable_order,
        scenario_order=valid_result.scenario_order,
        guaranteed_value=10.0,  # Unexpected candidate!
        variables={"x1": 5.0, "x2": 5.0},  # Unexpected candidate!
        scenario_values=valid_result.scenario_values,  # Unexpected!
        binding_scenario_ids=("s1",),  # Unexpected!
        delegated_solution=lp_inf,
        auxiliary_variable_name="_aux_theta",
        auxiliary_value=10.0,  # Unexpected!
    )

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, corrupt_result)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    unexpected_violations = [v for v in report.violations if v.code == "unexpected_candidate"]
    assert len(unexpected_violations) >= 1
    paths = {v.path for v in unexpected_violations}
    assert "$.variables" in paths
    assert "$.guaranteed_value" in paths


def test_validator_variable_order_mismatch() -> None:
    """Verify that variable order divergence fails scenario.variable_vector."""
    model, valid_result, _ = _make_continuous_loss_fixture()
    # Invert variables order to x2, x1
    corrupt_variables = MappingProxyType(
        {
            "x2": valid_result.variables["x2"],
            "x1": valid_result.variables["x1"],
        }
    )
    corrupt_result = ForgedScenarioResultDouble(
        status=valid_result.status,
        orientation=valid_result.orientation,
        original_variable_order=("x2", "x1"),  # Mismatched from model ("x1", "x2")
        scenario_order=valid_result.scenario_order,
        guaranteed_value=valid_result.guaranteed_value,
        variables=corrupt_variables,
        scenario_values=valid_result.scenario_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=valid_result.delegated_solution,
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=valid_result.auxiliary_value,
    )

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, corrupt_result)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    var_check = next(c for c in report.checks if c.code == "scenario.variable_vector")
    assert var_check.status is ValidationCheckStatus.FAILED

    violation_codes = [v.code for v in report.violations]
    assert "variable_order_mismatch" in violation_codes


def test_validator_missing_and_unknown_variables() -> None:
    """Verify that missing and unknown variables fail scenario.variable_vector with invalid_variable_vector."""
    model, valid_result, _ = _make_continuous_loss_fixture()
    # x2 missing, x_unknown present
    corrupt_variables = MappingProxyType(
        {
            "x1": valid_result.variables["x1"],
            "x_unknown": 99.0,
        }
    )
    corrupt_result = ForgedScenarioResultDouble(
        status=valid_result.status,
        orientation=valid_result.orientation,
        original_variable_order=valid_result.original_variable_order,
        scenario_order=valid_result.scenario_order,
        guaranteed_value=valid_result.guaranteed_value,
        variables=corrupt_variables,
        scenario_values=valid_result.scenario_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=valid_result.delegated_solution,
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=valid_result.auxiliary_value,
    )

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, corrupt_result)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    violation = next(v for v in report.violations if v.code == "invalid_variable_vector")
    assert violation.path == "$.variables"
    assert "x2" in violation.measurements["missing"]
    assert "x_unknown" in violation.measurements["unknown"]


def test_validator_scenario_order_and_identity_mismatch() -> None:
    """Verify that scenario order or identity mismatch fails scenario.scenario_values."""
    model, valid_result, _ = _make_continuous_loss_fixture()
    # Reordered scenario values (s2, s1, s3)
    corrupt_scen_values = (
        valid_result.scenario_values[1],
        valid_result.scenario_values[0],
        valid_result.scenario_values[2],
    )
    corrupt_result = ForgedScenarioResultDouble(
        status=valid_result.status,
        orientation=valid_result.orientation,
        original_variable_order=valid_result.original_variable_order,
        scenario_order=("s2", "s1", "s3"),  # Mismatched order
        guaranteed_value=valid_result.guaranteed_value,
        variables=valid_result.variables,
        scenario_values=corrupt_scen_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=valid_result.delegated_solution,
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=valid_result.auxiliary_value,
    )

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, corrupt_result)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    scen_check = next(c for c in report.checks if c.code == "scenario.scenario_values")
    assert scen_check.status is ValidationCheckStatus.FAILED

    violation = next(v for v in report.violations if v.code == "scenario_order_mismatch")
    assert violation.path in ("$.scenario_order", "$.scenario_values")


def test_validator_non_finite_numerical_surfaces() -> None:
    """Verify that non-finite numbers (NaN, Inf) on any numerical surface are caught as violations."""
    model, valid_result, _ = _make_continuous_loss_fixture()

    # 1. Non-finite variable value
    corrupt_var_result = ForgedScenarioResultDouble(
        status=valid_result.status,
        orientation=valid_result.orientation,
        original_variable_order=valid_result.original_variable_order,
        scenario_order=valid_result.scenario_order,
        guaranteed_value=valid_result.guaranteed_value,
        variables={"x1": float("nan"), "x2": 4.714286},
        scenario_values=valid_result.scenario_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=valid_result.delegated_solution,
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=valid_result.auxiliary_value,
    )
    validator = ScenarioIndependentSolutionValidator()
    report_var = validator(model, corrupt_var_result)  # type: ignore[arg-type]
    assert report_var.status is SolutionValidationStatus.FAILED
    assert any(v.code == "non_finite_variable" for v in report_var.violations)

    # 2. Non-finite guarantee
    corrupt_guar_result = ForgedScenarioResultDouble(
        status=valid_result.status,
        orientation=valid_result.orientation,
        original_variable_order=valid_result.original_variable_order,
        scenario_order=valid_result.scenario_order,
        guaranteed_value=float("inf"),
        variables=valid_result.variables,
        scenario_values=valid_result.scenario_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=valid_result.delegated_solution,
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=valid_result.auxiliary_value,
    )
    report_guar = validator(model, corrupt_guar_result)  # type: ignore[arg-type]
    assert report_guar.status is SolutionValidationStatus.FAILED
    assert any(v.code == "non_finite_guarantee" for v in report_guar.violations)

    # 3. Non-finite auxiliary value
    corrupt_aux_result = ForgedScenarioResultDouble(
        status=valid_result.status,
        orientation=valid_result.orientation,
        original_variable_order=valid_result.original_variable_order,
        scenario_order=valid_result.scenario_order,
        guaranteed_value=valid_result.guaranteed_value,
        variables=valid_result.variables,
        scenario_values=valid_result.scenario_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=valid_result.delegated_solution,
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=float("-inf"),
    )
    report_aux = validator(model, corrupt_aux_result)  # type: ignore[arg-type]
    assert report_aux.status is SolutionValidationStatus.FAILED
    assert any(v.code == "non_finite_auxiliary" for v in report_aux.violations)

    # 4. Non-finite scenario value
    corrupt_sv_values = (
        ForgedScenarioValueDouble("s1", float("nan"), True),
        valid_result.scenario_values[1],
        valid_result.scenario_values[2],
    )
    corrupt_sv_result = ForgedScenarioResultDouble(
        status=valid_result.status,
        orientation=valid_result.orientation,
        original_variable_order=valid_result.original_variable_order,
        scenario_order=valid_result.scenario_order,
        guaranteed_value=valid_result.guaranteed_value,
        variables=valid_result.variables,
        scenario_values=corrupt_sv_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=valid_result.delegated_solution,
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=valid_result.auxiliary_value,
    )
    report_sv = validator(model, corrupt_sv_result)  # type: ignore[arg-type]
    assert report_sv.status is SolutionValidationStatus.FAILED
    assert any(v.code == "non_finite_scenario_value" for v in report_sv.violations)


def test_validator_rejects_invalid_type_inputs() -> None:
    """Verify TypeError on invalid Python types at boundary."""
    validator = ScenarioIndependentSolutionValidator()
    with pytest.raises(TypeError, match="model must be an instance"):
        validator(None, None)  # type: ignore[arg-type]

    model, result, _ = _make_continuous_loss_fixture()
    with pytest.raises(TypeError, match="result must be an instance"):
        validator(model, "invalid_result_string")  # type: ignore[arg-type]
