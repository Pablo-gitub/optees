from __future__ import annotations

import math
import pytest

from optees.application.contracts.execution import MathematicalStatus
from optees.application.services.scenario_reconstruction_service import (
    ScenarioReconstructionError,
    ScenarioReconstructionService,
)
from optees.application.services.scenario_reduction_service import (
    ScenarioReductionService,
)
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.entities.milp.solution import MILPSolution
from optees.domain.entities.scenario.constraint import ScenarioConstraint
from optees.domain.entities.scenario.scenario import Scenario
from optees.domain.entities.scenario.shared_objective import (
    ScenarioSharedObjective,
)
from optees.domain.entities.scenario.variable import ScenarioVariable
from optees.domain.models.scenario.scenario_model import ScenarioModel
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.lp.solve_status import SolveStatus
from optees.domain.value_objects.lp.solver_diagnostics import SolverDiagnostics
from optees.domain.value_objects.milp.integrality import Integrality
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus
from optees.domain.value_objects.milp.solver_diagnostics import (
    MILPSolverDiagnostics,
)
from optees.domain.value_objects.scenario.scenario_options import ScenarioOptions
from optees.domain.value_objects.scenario.scenario_orientation import (
    ScenarioOrientation,
)


def _make_example1_model() -> tuple[ScenarioModel, ScenarioReductionService]:
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
    return model, reduction


def _make_example2_model() -> tuple[ScenarioModel, ScenarioReductionService]:
    vars_ = (
        ScenarioVariable(name="x1", bounds=Bounds(0.0, 4.0)),
        ScenarioVariable(name="x2", bounds=Bounds(0.0, 4.0)),
    )
    scenarios = (
        Scenario(id="sA", coefficients=(4.0, -2.0), offset=-10.0),
        Scenario(id="sB", coefficients=(-2.0, 5.0), offset=-8.0),
        Scenario(id="sC", coefficients=(1.0, 1.0), offset=-5.0),
    )
    constraints = (
        ScenarioConstraint(
            name="budget",
            coefficients=(1.0, 1.0),
            relation=Relation.LE,
            rhs=6.0,
        ),
    )
    model = ScenarioModel(
        orientation=ScenarioOrientation.MAX_MIN_REWARD,
        variables=vars_,
        scenarios=scenarios,
        shared_constraints=constraints,
    )
    reduction = ScenarioReductionService.reduce(model)
    return model, reduction


def _make_example3_model() -> tuple[ScenarioModel, ScenarioReductionService]:
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
        options=ScenarioOptions(time_limit_seconds=10.0),
    )
    reduction = ScenarioReductionService.reduce(model)
    return model, reduction


def test_reconstruct_example1_min_max_loss_optimal() -> None:
    """Verify reconstruction of continuous min-max loss (Example 1) from real LPSolution."""
    model, reduction = _make_example1_model()
    x1_val = 37.0 / 7.0
    x2_val = 33.0 / 7.0
    guaranteed = 76.0 / 7.0

    lp_solution = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=guaranteed,
        values={
            "x1": x1_val,
            "x2": x2_val,
            "_aux_theta": guaranteed,
        },
        diagnostics=SolverDiagnostics(),
        extras={"backend": "highs", "iterations": 2},
    )

    result = ScenarioReconstructionService.reconstruct(model, reduction, lp_solution)

    assert result.status == MathematicalStatus.OPTIMAL
    assert result.is_optimal()
    assert result.has_candidate()
    assert result.orientation == ScenarioOrientation.MIN_MAX_LOSS
    assert math.isclose(result.guaranteed_value, guaranteed, abs_tol=1e-12)
    assert result.variables == {"x1": x1_val, "x2": x2_val}
    assert list(result.variables.keys()) == ["x1", "x2"]
    assert "_aux_theta" not in result.variables
    assert result.auxiliary_variable_name == "_aux_theta"
    assert math.isclose(result.auxiliary_value, guaranteed, abs_tol=1e-12)

    # Scenarios check: s1 and s2 binding ties, s3 non-binding
    assert len(result.scenario_values) == 3
    assert result.scenario_values[0].scenario_id == "s1"
    assert math.isclose(result.scenario_values[0].value, guaranteed, abs_tol=1e-12)
    assert result.scenario_values[0].is_binding is True

    assert result.scenario_values[1].scenario_id == "s2"
    assert math.isclose(result.scenario_values[1].value, guaranteed, abs_tol=1e-12)
    assert result.scenario_values[1].is_binding is True

    assert result.scenario_values[2].scenario_id == "s3"
    assert math.isclose(result.scenario_values[2].value, 6.0, abs_tol=1e-12)
    assert result.scenario_values[2].is_binding is False

    assert result.binding_scenario_ids == ("s1", "s2")
    assert result.delegated_solution is lp_solution


def test_reconstruct_example2_max_min_reward_negative_guarantee() -> None:
    """Verify reconstruction of continuous max-min reward with negative guarantee (Example 2)."""
    model, reduction = _make_example2_model()
    x1_val = 44.0 / 13.0
    x2_val = 34.0 / 13.0
    guaranteed = -22.0 / 13.0

    lp_solution = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=guaranteed,
        values={
            "x1": x1_val,
            "x2": x2_val,
            "_aux_tau": guaranteed,
        },
        diagnostics=SolverDiagnostics(),
        extras={},
    )

    result = ScenarioReconstructionService.reconstruct(model, reduction, lp_solution)

    assert result.status == MathematicalStatus.OPTIMAL
    assert result.orientation == ScenarioOrientation.MAX_MIN_REWARD
    assert math.isclose(result.guaranteed_value, guaranteed, abs_tol=1e-12)
    assert result.guaranteed_value < 0.0
    assert result.variables == {"x1": x1_val, "x2": x2_val}
    assert result.binding_scenario_ids == ("sA", "sB")
    assert result.scenario_values[2].value == 1.0
    assert result.scenario_values[2].is_binding is False


def test_reconstruct_example3_discrete_binary_optimal_and_feasible() -> None:
    """Verify reconstruction of discrete MILP candidate (Example 3) from real MILPSolution."""
    model, reduction = _make_example3_model()

    # Case A: Optimal
    milp_solution = MILPSolution(
        status=MILPSolveStatus.OPTIMAL,
        objective=15.0,
        values={"x1": 1.0, "x2": 1.0, "x3": 0.0, "_aux_theta": 15.0},
        diagnostics=MILPSolverDiagnostics(),
        extras={"nodes": 1},
    )

    result = ScenarioReconstructionService.reconstruct(model, reduction, milp_solution)
    assert result.status == MathematicalStatus.OPTIMAL
    assert result.guaranteed_value == 15.0
    assert result.variables == {"x1": 1.0, "x2": 1.0, "x3": 0.0}
    assert result.binding_scenario_ids == ("s2",)

    # Case B: Feasible incumbent
    milp_feasible = MILPSolution(
        status=MILPSolveStatus.FEASIBLE,
        objective=15.0,
        values={"x1": 1.0, "x2": 1.0, "x3": 0.0, "_aux_theta": 15.0},
        diagnostics=MILPSolverDiagnostics(),
        extras={"nodes": 10},
    )

    result_feas = ScenarioReconstructionService.reconstruct(model, reduction, milp_feasible)
    assert result_feas.status == MathematicalStatus.FEASIBLE
    assert result_feas.has_candidate() is True
    assert result_feas.is_optimal() is False
    assert result_feas.guaranteed_value == 15.0


def test_reconstruction_restores_original_variable_order_from_shuffled_solver_output() -> None:
    """Verify that user variables are strictly returned in original_variable_order regardless of solver mapping order."""
    model, reduction = _make_example1_model()

    # Solver returns variables in shuffled key order
    shuffled_values = {
        "x2": 33.0 / 7.0,
        "_aux_theta": 76.0 / 7.0,
        "x1": 37.0 / 7.0,
    }
    lp_solution = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=76.0 / 7.0,
        values=shuffled_values,
        diagnostics=SolverDiagnostics(),
        extras={},
    )

    result = ScenarioReconstructionService.reconstruct(model, reduction, lp_solution)
    assert list(result.variables.keys()) == ["x1", "x2"]


def test_reconstruction_with_shared_objective_and_offsets() -> None:
    """Verify scenario evaluation recomputation when shared objective and offset are present."""
    vars_ = (
        ScenarioVariable(name="x1"),
        ScenarioVariable(name="x2"),
    )
    sh_obj = ScenarioSharedObjective(coefficients=(10.0, 20.0), offset=100.0)
    scenarios = (
        Scenario(id="s1", coefficients=(1.0, 2.0), offset=5.0),
        Scenario(id="s2", coefficients=(2.0, 1.0), offset=10.0),
    )
    model = ScenarioModel(
        orientation=ScenarioOrientation.MIN_MAX_LOSS,
        variables=vars_,
        scenarios=scenarios,
        shared_objective=sh_obj,
    )
    reduction = ScenarioReductionService.reduce(model)

    # For x = (1, 1):
    # s1: (10+1)*1 + (20+2)*1 + (100+5) = 11 + 22 + 105 = 138
    # s2: (10+2)*1 + (20+1)*1 + (100+10) = 12 + 21 + 110 = 143
    # guaranteed = max(138, 143) = 143
    lp_solution = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=143.0,
        values={"x1": 1.0, "x2": 1.0, "_aux_theta": 143.0},
        diagnostics=SolverDiagnostics(),
        extras={},
    )

    result = ScenarioReconstructionService.reconstruct(model, reduction, lp_solution)
    assert result.guaranteed_value == 143.0
    assert result.scenario_values[0].value == 138.0
    assert result.scenario_values[0].is_binding is False
    assert result.scenario_values[1].value == 143.0
    assert result.scenario_values[1].is_binding is True
    assert result.binding_scenario_ids == ("s2",)


def test_reconstruction_rejection_missing_user_variable() -> None:
    model, reduction = _make_example1_model()
    lp_solution = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=10.857143,
        values={"x1": 5.285714, "_aux_theta": 10.857143},  # missing x2
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    with pytest.raises(
        ScenarioReconstructionError,
        match="Declared variables missing from solution values",
    ):
        ScenarioReconstructionService.reconstruct(model, reduction, lp_solution)


def test_reconstruction_rejection_unknown_variable() -> None:
    model, reduction = _make_example1_model()
    lp_solution = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=10.857143,
        values={
            "x1": 5.285714,
            "x2": 4.714286,
            "x_unexpected": 0.0,
            "_aux_theta": 10.857143,
        },
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    with pytest.raises(
        ScenarioReconstructionError,
        match="Unknown variables present in solution values",
    ):
        ScenarioReconstructionService.reconstruct(model, reduction, lp_solution)


def test_reconstruction_rejection_non_finite_variable_value() -> None:
    model, reduction = _make_example1_model()
    lp_solution = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=10.857143,
        values={
            "x1": float("nan"),
            "x2": 4.714286,
            "_aux_theta": 10.857143,
        },
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    with pytest.raises(ScenarioReconstructionError, match="has non-finite value"):
        ScenarioReconstructionService.reconstruct(model, reduction, lp_solution)


def test_reconstruction_rejection_missing_auxiliary_variable() -> None:
    model, reduction = _make_example1_model()
    lp_solution = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=10.857143,
        values={"x1": 5.285714, "x2": 4.714286},  # missing _aux_theta
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    with pytest.raises(
        ScenarioReconstructionError,
        match="Auxiliary variable '_aux_theta' is missing",
    ):
        ScenarioReconstructionService.reconstruct(model, reduction, lp_solution)


def test_reconstruction_rejection_auxiliary_value_mismatch() -> None:
    model, reduction = _make_example1_model()
    # Auxiliary variable value tampered to 999.0
    lp_solution = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=76.0 / 7.0,
        values={
            "x1": 37.0 / 7.0,
            "x2": 33.0 / 7.0,
            "_aux_theta": 999.0,
        },
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    with pytest.raises(
        ScenarioReconstructionError,
        match="diverges from auxiliary variable value",
    ):
        ScenarioReconstructionService.reconstruct(model, reduction, lp_solution)


def test_reconstruction_rejection_delegated_objective_mismatch() -> None:
    model, reduction = _make_example1_model()
    # Delegated objective tampered to 0.0
    lp_solution = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=0.0,
        values={
            "x1": 37.0 / 7.0,
            "x2": 33.0 / 7.0,
            "_aux_theta": 76.0 / 7.0,
        },
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    with pytest.raises(ScenarioReconstructionError, match="diverges from delegated objective"):
        ScenarioReconstructionService.reconstruct(model, reduction, lp_solution)


def test_reconstruction_consistency_tolerance_boundary() -> None:
    """Verify that small numerical differences within tolerance pass, while differences above fail."""
    model, reduction = _make_example1_model()
    exact_guaranteed = 76.0 / 7.0
    # Tolerance is 1e-4
    tol = 1e-4

    # Just inside tolerance: 1e-5 difference
    lp_inside = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=exact_guaranteed + 1e-5,
        values={
            "x1": 37.0 / 7.0,
            "x2": 33.0 / 7.0,
            "_aux_theta": exact_guaranteed + 1e-5,
        },
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    res_inside = ScenarioReconstructionService.reconstruct(
        model, reduction, lp_inside, consistency_tolerance=tol
    )
    assert res_inside.guaranteed_value == exact_guaranteed

    # Just outside tolerance: 2e-3 difference
    lp_outside = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=exact_guaranteed + 2e-3,
        values={
            "x1": 37.0 / 7.0,
            "x2": 33.0 / 7.0,
            "_aux_theta": exact_guaranteed + 2e-3,
        },
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    with pytest.raises(
        ScenarioReconstructionError,
        match="diverges from auxiliary variable value",
    ):
        ScenarioReconstructionService.reconstruct(
            model, reduction, lp_outside, consistency_tolerance=tol
        )


def test_reconstruct_no_candidate_statuses() -> None:
    """Verify explicit no-candidate robust results for INFEASIBLE, UNBOUNDED, and NOT_SOLVED."""
    model, reduction = _make_example1_model()

    # 1. Infeasible LP
    lp_inf = LPSolution(
        status=SolveStatus.INFEASIBLE,
        objective=None,
        values={},
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    res_inf = ScenarioReconstructionService.reconstruct(model, reduction, lp_inf)
    assert res_inf.status == MathematicalStatus.INFEASIBLE
    assert res_inf.has_candidate() is False
    assert res_inf.guaranteed_value is None
    assert res_inf.variables is None
    assert res_inf.scenario_values == ()
    assert res_inf.binding_scenario_ids == ()
    assert res_inf.auxiliary_value is None

    # 2. Unbounded MILP
    milp_unb = MILPSolution(
        status=MILPSolveStatus.UNBOUNDED,
        objective=None,
        values={},
        diagnostics=MILPSolverDiagnostics(),
        extras={},
    )
    res_unb = ScenarioReconstructionService.reconstruct(model, reduction, milp_unb)
    assert res_unb.status == MathematicalStatus.UNBOUNDED
    assert res_unb.has_candidate() is False
    assert res_unb.guaranteed_value is None
    assert res_unb.variables is None

    # 3. Not solved LP
    lp_not_solved = LPSolution(
        status=SolveStatus.NOT_SOLVED,
        objective=None,
        values={},
        diagnostics=SolverDiagnostics(),
        extras={},
    )
    res_ns = ScenarioReconstructionService.reconstruct(model, reduction, lp_not_solved)
    assert res_ns.status == MathematicalStatus.NOT_SOLVED
    assert res_ns.has_candidate() is False


def test_reconstruction_purity_and_immutability() -> None:
    """Verify that reconstruction service does not mutate inputs and is deterministic."""
    model, reduction = _make_example1_model()
    x1_val = 37.0 / 7.0
    x2_val = 33.0 / 7.0
    guaranteed = 76.0 / 7.0

    original_values = {"x1": x1_val, "x2": x2_val, "_aux_theta": guaranteed}
    lp_solution = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=guaranteed,
        values=dict(original_values),
        diagnostics=SolverDiagnostics(),
        extras={"key": "original"},
    )

    res1 = ScenarioReconstructionService.reconstruct(model, reduction, lp_solution)
    res2 = ScenarioReconstructionService.reconstruct(model, reduction, lp_solution)

    assert res1.guaranteed_value == res2.guaranteed_value
    assert res1.variables == res2.variables
    assert res1.binding_scenario_ids == res2.binding_scenario_ids

    # Solution dict was not modified
    assert lp_solution.values == original_values
