from __future__ import annotations

from dataclasses import dataclass
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
from optees.domain.entities.scenario.scenario_value import ScenarioValue
from optees.domain.entities.scenario.shared_objective import (
    ScenarioSharedObjective,
)
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
        ScenarioVariable(name="x1", bounds=Bounds(0.0, 10.0)),
        ScenarioVariable(name="x2", bounds=Bounds(0.0, 10.0)),
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
        ScenarioVariable(name="x3", integrality=Integrality.INTEGER, bounds=Bounds(0.0, 5.0)),
    )
    scenarios = (
        Scenario(id="s1", coefficients=(10.0, 2.0, 3.0), offset=0.0),
        Scenario(id="s2", coefficients=(3.0, 12.0, 1.0), offset=0.0),
        Scenario(id="s3", coefficients=(6.0, 5.0, 4.0), offset=0.0),
    )
    constraints = (
        ScenarioConstraint(
            name="cardinality",
            coefficients=(1.0, 1.0, 1.0),
            relation=Relation.LE,
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


def _make_continuous_reward_negative_fixture() -> tuple[ScenarioModel, ScenarioResult, LPSolution]:
    vars_ = (
        ScenarioVariable(name="x1", bounds=Bounds(0.0, 5.0)),
        ScenarioVariable(name="x2", bounds=Bounds(0.0, 5.0)),
    )
    shared_obj = ScenarioSharedObjective(
        coefficients=(-1.0, -1.0),
        offset=-10.0,
    )
    scenarios = (
        Scenario(id="s1", coefficients=(-2.0, 1.0), offset=1.0),
        Scenario(id="s2", coefficients=(1.0, -3.0), offset=2.0),
    )
    constraints = (
        ScenarioConstraint(
            name="min_activity",
            coefficients=(1.0, 1.0),
            relation=Relation.GE,
            rhs=2.0,
        ),
    )
    model = ScenarioModel(
        orientation=ScenarioOrientation.MAX_MIN_REWARD,
        variables=vars_,
        scenarios=scenarios,
        shared_objective=shared_obj,
        shared_constraints=constraints,
    )
    reduction = ScenarioReductionService.reduce(model)
    lp_sol = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=-12.0,
        values={
            "x1": 1.0,
            "x2": 1.0,
            "_aux_tau": -12.0,
        },
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    result = ScenarioReconstructionService.reconstruct(model, reduction, lp_sol)
    return model, result, lp_sol


def test_validator_continuous_optimal_all_checks_passed() -> None:
    """Verify that a valid continuous model passes all 10 applicable checks with VERIFIED status."""
    model, result, _ = _make_continuous_loss_fixture()
    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, result)

    assert report.status is SolutionValidationStatus.VERIFIED
    assert len(report.checks) == 10
    assert len(report.violations) == 0

    expected_codes = [
        "scenario.orientation",
        "scenario.status_coherence",
        "scenario.variable_vector",
        "scenario.scenario_values",
        "scenario.bounds",
        "scenario.constraints",
        "scenario.evaluations",
        "scenario.guarantee",
        "scenario.binding_set",
        "scenario.consistency",
    ]
    assert [c.code for c in report.checks] == expected_codes
    for check in report.checks:
        assert check.status is ValidationCheckStatus.PASSED


def test_validator_discrete_feasible_all_checks_passed() -> None:
    """Verify that a valid discrete model includes scenario.integrality and passes all 11 checks."""
    model, result, _ = _make_discrete_loss_fixture()
    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, result)

    assert report.status is SolutionValidationStatus.VERIFIED
    assert len(report.checks) == 11
    assert len(report.violations) == 0

    expected_codes = [
        "scenario.orientation",
        "scenario.status_coherence",
        "scenario.variable_vector",
        "scenario.scenario_values",
        "scenario.bounds",
        "scenario.integrality",
        "scenario.constraints",
        "scenario.evaluations",
        "scenario.guarantee",
        "scenario.binding_set",
        "scenario.consistency",
    ]
    assert [c.code for c in report.checks] == expected_codes
    for check in report.checks:
        assert check.status is ValidationCheckStatus.PASSED


def test_validator_max_min_reward_negative_guarantee_valid() -> None:
    """Verify that max_min_reward with negative guarantee, shared objective, and GE constraint validates cleanly."""
    model, result, _ = _make_continuous_reward_negative_fixture()
    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, result)

    assert report.status is SolutionValidationStatus.VERIFIED
    assert result.guaranteed_value == -12.0
    assert len(report.violations) == 0


def test_validator_bounds_violations() -> None:
    """Verify lower and upper bound violations are detected with exact codes and paths."""
    model, valid_result, lp_sol = _make_continuous_loss_fixture()
    # x1=12.0 violates upper bound 10.0, x2=-1.0 violates lower bound 0.0
    corrupt_result = ForgedScenarioResultDouble(
        status=valid_result.status,
        orientation=valid_result.orientation,
        original_variable_order=valid_result.original_variable_order,
        scenario_order=valid_result.scenario_order,
        guaranteed_value=valid_result.guaranteed_value,
        variables={"x1": 12.0, "x2": -1.0},
        scenario_values=valid_result.scenario_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=lp_sol,
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=valid_result.auxiliary_value,
    )

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, corrupt_result)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    bounds_check = next(c for c in report.checks if c.code == "scenario.bounds")
    assert bounds_check.status is ValidationCheckStatus.FAILED

    violation_codes = {v.code for v in report.violations}
    assert "upper_bound_violation" in violation_codes
    assert "lower_bound_violation" in violation_codes

    v_ub = next(v for v in report.violations if v.code == "upper_bound_violation")
    assert v_ub.path == "$.variables.x1"
    assert v_ub.measurements["bound"] == 10.0

    v_lb = next(v for v in report.violations if v.code == "lower_bound_violation")
    assert v_lb.path == "$.variables.x2"
    assert v_lb.measurements["bound"] == 0.0


def test_validator_integrality_and_binary_violations_around_tolerance() -> None:
    """Verify discrete domain checks just inside and just outside tolerance."""
    model, valid_result, milp_sol = _make_discrete_loss_fixture()
    tol = 1e-5

    # 1. Just INSIDE tolerance -> should pass integrality
    inside_result = ForgedScenarioResultDouble(
        status=valid_result.status,
        orientation=valid_result.orientation,
        original_variable_order=valid_result.original_variable_order,
        scenario_order=valid_result.scenario_order,
        guaranteed_value=valid_result.guaranteed_value,
        variables={"x1": 1.0 + tol * 0.5, "x2": 1.0 - tol * 0.5, "x3": 0.0 + tol * 0.5},
        scenario_values=valid_result.scenario_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=milp_sol,
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=valid_result.auxiliary_value,
    )
    validator = ScenarioIndependentSolutionValidator(integrality_tolerance=tol)
    report_inside = validator(model, inside_result)  # type: ignore[arg-type]
    int_check = next(c for c in report_inside.checks if c.code == "scenario.integrality")
    assert int_check.status is ValidationCheckStatus.PASSED

    # 2. Just OUTSIDE tolerance -> should fail integrality
    outside_result = ForgedScenarioResultDouble(
        status=valid_result.status,
        orientation=valid_result.orientation,
        original_variable_order=valid_result.original_variable_order,
        scenario_order=valid_result.scenario_order,
        guaranteed_value=valid_result.guaranteed_value,
        variables={
            "x1": 1.0 + tol * 2.0,
            "x2": 0.5,
            "x3": 2.2,
        },  # x1 slightly off, x2 far off binary, x3 off integer
        scenario_values=valid_result.scenario_values,
        binding_scenario_ids=valid_result.binding_scenario_ids,
        delegated_solution=milp_sol,
        auxiliary_variable_name=valid_result.auxiliary_variable_name,
        auxiliary_value=valid_result.auxiliary_value,
    )
    report_outside = validator(model, outside_result)  # type: ignore[arg-type]
    assert report_outside.status is SolutionValidationStatus.FAILED
    int_check_out = next(c for c in report_outside.checks if c.code == "scenario.integrality")
    assert int_check_out.status is ValidationCheckStatus.FAILED

    codes = {v.code for v in report_outside.violations}
    assert "binary_domain_violation" in codes
    assert "integrality_violation" in codes


def test_validator_shared_constraints_le_ge_eq_tolerance() -> None:
    """Verify shared constraints with LE, GE, and EQ relations just inside and just outside tolerance."""
    vars_ = (
        ScenarioVariable(name="x1"),
        ScenarioVariable(name="x2"),
    )
    scenarios = (Scenario(id="s1", coefficients=(1.0, 0.0)),)
    constraints = (
        ScenarioConstraint(name="c_eq", coefficients=(1.0, 1.0), relation=Relation.EQ, rhs=10.0),
        ScenarioConstraint(name="c_le", coefficients=(2.0, 0.0), relation=Relation.LE, rhs=8.0),
        ScenarioConstraint(name="c_ge", coefficients=(0.0, 2.0), relation=Relation.GE, rhs=6.0),
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
        objective=4.0,
        values={"x1": 4.0, "x2": 6.0, "_aux_theta": 4.0},
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    valid_res = ScenarioReconstructionService.reconstruct(model, reduction, lp_sol)

    validator = ScenarioIndependentSolutionValidator(absolute_tolerance=1e-6)

    # Valid candidate (x1=4.0, x2=6.0):
    # c_eq: 4+6=10 (EQ 10) OK
    # c_le: 2*4=8 (LE 8) OK
    # c_ge: 2*6=12 (GE 6) OK
    assert validator(model, valid_res).status is SolutionValidationStatus.VERIFIED

    # Violate c_eq (x1=4.1, x2=6.0 -> lhs=10.1 != 10.0)
    # Violate c_le (x1=4.1 -> lhs=8.2 > 8.0)
    # Violate c_ge (x2=2.0 -> lhs=4.0 < 6.0)
    corrupt_res = ForgedScenarioResultDouble(
        status=valid_res.status,
        orientation=valid_res.orientation,
        original_variable_order=valid_res.original_variable_order,
        scenario_order=valid_res.scenario_order,
        guaranteed_value=valid_res.guaranteed_value,
        variables={"x1": 4.1, "x2": 2.0},
        scenario_values=valid_res.scenario_values,
        binding_scenario_ids=valid_res.binding_scenario_ids,
        delegated_solution=lp_sol,
        auxiliary_variable_name=valid_res.auxiliary_variable_name,
        auxiliary_value=valid_res.auxiliary_value,
    )
    report = validator(model, corrupt_res)  # type: ignore[arg-type]
    assert report.status is SolutionValidationStatus.FAILED
    con_check = next(c for c in report.checks if c.code == "scenario.constraints")
    assert con_check.status is ValidationCheckStatus.FAILED

    con_violations = [v for v in report.violations if v.check_code == "scenario.constraints"]
    assert len(con_violations) == 3
    paths = {v.path for v in con_violations}
    assert paths == {
        "$.shared_constraints[0]",
        "$.shared_constraints[1]",
        "$.shared_constraints[2]",
    }


def test_validator_scenario_evaluations_mismatch() -> None:
    """Verify tampering with published scenario evaluation values fails scenario.evaluations."""
    model, valid_res, _ = _make_continuous_loss_fixture()

    # Tamper with scenario s2 value (reported 999.0 instead of recomputed ~12.2857)
    tampered_scen_vals = (
        valid_res.scenario_values[0],
        ScenarioValue("s2", 999.0, valid_res.scenario_values[1].is_binding),
        valid_res.scenario_values[2],
    )
    corrupt_res = ForgedScenarioResultDouble(
        status=valid_res.status,
        orientation=valid_res.orientation,
        original_variable_order=valid_res.original_variable_order,
        scenario_order=valid_res.scenario_order,
        guaranteed_value=valid_res.guaranteed_value,
        variables=valid_res.variables,
        scenario_values=tampered_scen_vals,
        binding_scenario_ids=valid_res.binding_scenario_ids,
        delegated_solution=valid_res.delegated_solution,
        auxiliary_variable_name=valid_res.auxiliary_variable_name,
        auxiliary_value=valid_res.auxiliary_value,
    )

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, corrupt_res)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    eval_check = next(c for c in report.checks if c.code == "scenario.evaluations")
    assert eval_check.status is ValidationCheckStatus.FAILED

    violation = next(v for v in report.violations if v.code == "scenario_evaluation_mismatch")
    assert violation.path == "$.scenario_values[1].value"
    assert violation.measurements["scenario_id"] == "s2"
    assert violation.measurements["reported"] == 999.0


def test_validator_guarantee_mismatch() -> None:
    """Verify tampering with guaranteed_value fails scenario.guarantee."""
    model, valid_res, _ = _make_continuous_loss_fixture()

    corrupt_res = ForgedScenarioResultDouble(
        status=valid_res.status,
        orientation=valid_res.orientation,
        original_variable_order=valid_res.original_variable_order,
        scenario_order=valid_res.scenario_order,
        guaranteed_value=50.0,  # Tampered! Recomputed is ~10.857
        variables=valid_res.variables,
        scenario_values=valid_res.scenario_values,
        binding_scenario_ids=valid_res.binding_scenario_ids,
        delegated_solution=valid_res.delegated_solution,
        auxiliary_variable_name=valid_res.auxiliary_variable_name,
        auxiliary_value=valid_res.auxiliary_value,
    )

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, corrupt_res)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    guar_check = next(c for c in report.checks if c.code == "scenario.guarantee")
    assert guar_check.status is ValidationCheckStatus.FAILED

    violation = next(v for v in report.violations if v.code == "guarantee_mismatch")
    assert violation.path == "$.guaranteed_value"
    assert violation.measurements["reported"] == 50.0


def test_validator_binding_set_and_flag_mismatch() -> None:
    """Verify tampering with binding_scenario_ids or is_binding flags fails scenario.binding_set."""
    model, valid_res, _ = _make_continuous_loss_fixture()

    # Valid binding scenarios are ('s1', 's2')
    # Tamper binding_scenario_ids to only ('s1',) and invert is_binding flag on s2
    tampered_scen_vals = (
        valid_res.scenario_values[0],
        ScenarioValue("s2", valid_res.scenario_values[1].value, False),  # Tampered flag!
        valid_res.scenario_values[2],
    )
    corrupt_res = ForgedScenarioResultDouble(
        status=valid_res.status,
        orientation=valid_res.orientation,
        original_variable_order=valid_res.original_variable_order,
        scenario_order=valid_res.scenario_order,
        guaranteed_value=valid_res.guaranteed_value,
        variables=valid_res.variables,
        scenario_values=tampered_scen_vals,
        binding_scenario_ids=("s1",),  # Tampered binding list!
        delegated_solution=valid_res.delegated_solution,
        auxiliary_variable_name=valid_res.auxiliary_variable_name,
        auxiliary_value=valid_res.auxiliary_value,
    )

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, corrupt_res)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    bind_check = next(c for c in report.checks if c.code == "scenario.binding_set")
    assert bind_check.status is ValidationCheckStatus.FAILED

    codes = {v.code for v in report.violations}
    assert "binding_set_mismatch" in codes
    assert "binding_flag_mismatch" in codes


def test_validator_consistency_tampering_auxiliary_and_delegated_objective() -> None:
    """Verify tampering with auxiliary_value or delegated_solution.objective fails scenario.consistency."""
    model, valid_res, lp_sol = _make_continuous_loss_fixture()

    # 1. Tamper auxiliary value
    corrupt_aux = ForgedScenarioResultDouble(
        status=valid_res.status,
        orientation=valid_res.orientation,
        original_variable_order=valid_res.original_variable_order,
        scenario_order=valid_res.scenario_order,
        guaranteed_value=valid_res.guaranteed_value,
        variables=valid_res.variables,
        scenario_values=valid_res.scenario_values,
        binding_scenario_ids=valid_res.binding_scenario_ids,
        delegated_solution=valid_res.delegated_solution,
        auxiliary_variable_name=valid_res.auxiliary_variable_name,
        auxiliary_value=999.0,  # Tampered auxiliary
    )
    validator = ScenarioIndependentSolutionValidator()
    report_aux = validator(model, corrupt_aux)  # type: ignore[arg-type]
    assert report_aux.status is SolutionValidationStatus.FAILED
    assert any(v.code == "auxiliary_consistency_mismatch" for v in report_aux.violations)

    # 2. Tamper delegated objective
    tampered_lp = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=123.456,  # Tampered objective
        values=lp_sol.values,
        diagnostics=lp_sol.diagnostics,
        extras=lp_sol.extras,
    )
    corrupt_obj = ForgedScenarioResultDouble(
        status=valid_res.status,
        orientation=valid_res.orientation,
        original_variable_order=valid_res.original_variable_order,
        scenario_order=valid_res.scenario_order,
        guaranteed_value=valid_res.guaranteed_value,
        variables=valid_res.variables,
        scenario_values=valid_res.scenario_values,
        binding_scenario_ids=valid_res.binding_scenario_ids,
        delegated_solution=tampered_lp,
        auxiliary_variable_name=valid_res.auxiliary_variable_name,
        auxiliary_value=valid_res.auxiliary_value,
    )
    report_obj = validator(model, corrupt_obj)  # type: ignore[arg-type]
    assert report_obj.status is SolutionValidationStatus.FAILED
    assert any(v.code == "objective_consistency_mismatch" for v in report_obj.violations)


def test_validator_simultaneous_violations_no_duplicate_reporting() -> None:
    """Verify simultaneous bounds, constraints, evaluations, and consistency violations are deduplicated and reported cleanly."""
    model, valid_res, _ = _make_continuous_loss_fixture()

    tampered_lp = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=999.0,
        values={},
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    # x1=20 (violates UB 10 and constraint budget 10), x2=0
    corrupt_res = ForgedScenarioResultDouble(
        status=valid_res.status,
        orientation=valid_res.orientation,
        original_variable_order=valid_res.original_variable_order,
        scenario_order=valid_res.scenario_order,
        guaranteed_value=10.0,
        variables={"x1": 20.0, "x2": 0.0},
        scenario_values=valid_res.scenario_values,
        binding_scenario_ids=("s1",),
        delegated_solution=tampered_lp,
        auxiliary_variable_name="_aux_theta",
        auxiliary_value=10.0,
    )

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, corrupt_res)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    # Ensure every violation points to a unique, non-duplicated check failure
    violation_tuples = [(v.code, v.path) for v in report.violations]
    assert len(violation_tuples) == len(set(violation_tuples))


def test_validator_no_crash_on_structural_failure() -> None:
    """Verify validator safely stops and reports failure when candidate variables mapping is missing or corrupt."""
    model, valid_res, _ = _make_continuous_loss_fixture()

    corrupt_res = ForgedScenarioResultDouble(
        status=valid_res.status,
        orientation=valid_res.orientation,
        original_variable_order=valid_res.original_variable_order,
        scenario_order=valid_res.scenario_order,
        guaranteed_value=valid_res.guaranteed_value,
        variables="not_a_mapping",  # Malformed type!
        scenario_values=valid_res.scenario_values,
        binding_scenario_ids=valid_res.binding_scenario_ids,
        delegated_solution=valid_res.delegated_solution,
        auxiliary_variable_name=valid_res.auxiliary_variable_name,
        auxiliary_value=valid_res.auxiliary_value,
    )

    validator = ScenarioIndependentSolutionValidator()
    # Must produce a FAILED report without raising AttributeError or TypeError during bounds/constraint evaluation
    report = validator(model, corrupt_res)  # type: ignore[arg-type]

    assert report.status is SolutionValidationStatus.FAILED
    assert any(v.code == "invalid_variable_vector" for v in report.violations)
    # Mathematical checks that require candidate indexing must not have run
    check_codes = [c.code for c in report.checks]
    assert "scenario.bounds" not in check_codes
    assert "scenario.constraints" not in check_codes


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
