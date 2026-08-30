from __future__ import annotations

from typing import Any, Callable, Optional

import pytest

from optees.application.contracts.solution_validation import (
    SolutionValidationStatus,
)
from optees.application.ports.lp_solver_port import LPSolverPort
from optees.application.ports.milp_solver_port import MILPSolverPort
from optees.application.services.scenario_reconstruction_service import (
    ScenarioReconstructionError,
)
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from optees.application.usecases.solve_milp_usecase import SolveMILPUseCase
from optees.application.usecases.solve_scenario_usecase import (
    SolveScenarioUseCase,
)
from optees.application.validation.scenario_solution_validator import (
    ScenarioIndependentSolutionValidator,
)
from optees.domain.entities.scenario.constraint import ScenarioConstraint
from optees.domain.entities.scenario.scenario import Scenario
from optees.domain.entities.scenario.shared_objective import (
    ScenarioSharedObjective,
)
from optees.domain.entities.scenario.variable import ScenarioVariable
from optees.domain.models.scenario.scenario_model import ScenarioModel
from optees.domain.models.scenario.scenario_result import ScenarioSolveStatus
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.milp.integrality import Integrality
from optees.domain.value_objects.scenario.scenario_orientation import (
    ScenarioOrientation,
)


class RecordingLPSolverPort(LPSolverPort):
    def __init__(
        self,
        response_factory: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self._response_factory = response_factory

    def solve(self, problem: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(problem)
        if self._response_factory is not None:
            return self._response_factory(problem)
        return {
            "status": "Optimal",
            "objective": 0.0,
            "x": {},
            "extras": {},
        }


class RecordingMILPSolverPort(MILPSolverPort):
    def __init__(
        self,
        response_factory: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self._response_factory = response_factory

    def solve(self, problem: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(problem)
        if self._response_factory is not None:
            return self._response_factory(problem)
        return {
            "status": "Optimal",
            "objective": 0.0,
            "x": {},
            "extras": {},
        }


def _make_continuous_loss_model() -> ScenarioModel:
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
    return ScenarioModel(
        orientation=ScenarioOrientation.MIN_MAX_LOSS,
        variables=vars_,
        scenarios=scenarios,
        shared_constraints=constraints,
    )


def _make_continuous_reward_negative_model() -> ScenarioModel:
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
    return ScenarioModel(
        orientation=ScenarioOrientation.MAX_MIN_REWARD,
        variables=vars_,
        scenarios=scenarios,
        shared_objective=shared_obj,
        shared_constraints=constraints,
    )


def _make_discrete_loss_model() -> ScenarioModel:
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
    return ScenarioModel(
        orientation=ScenarioOrientation.MIN_MAX_LOSS,
        variables=vars_,
        scenarios=scenarios,
        shared_constraints=constraints,
    )


def test_solve_scenario_usecase_continuous_lp_routing() -> None:
    """Test continuous LP routing, problem shape, exact call counts, and external validation acceptance."""
    model = _make_continuous_loss_model()

    def fake_lp_solve(problem: dict[str, Any]) -> dict[str, Any]:
        assert problem["sense"] == "min"
        assert problem["c"] == [0.0, 0.0, 1.0]  # x1, x2, _aux_theta
        assert len(problem["bounds"]) == 3
        assert problem["bounds"][2] == (None, None)  # theta unbounded
        # Check equality constraint
        assert problem["A_eq"] == [[1.0, 1.0, 0.0]]
        assert problem["b_eq"] == [10.0]
        # Check scenario constraints in A_ub
        assert len(problem["A_ub"]) == 3
        return {
            "status": "Optimal",
            "objective": 76.0 / 7.0,
            "x": {
                "x1": 37.0 / 7.0,
                "x2": 33.0 / 7.0,
                "_aux_theta": 76.0 / 7.0,
            },
            "extras": {
                "backend": "fake_highs",
                "iterations": 4,
            },
        }

    lp_port = RecordingLPSolverPort(response_factory=fake_lp_solve)
    milp_port = RecordingMILPSolverPort()
    usecase = SolveScenarioUseCase(
        solve_lp_usecase=SolveLPUseCase(lp_port),
        solve_milp_usecase=SolveMILPUseCase(milp_port),
    )

    result = usecase.execute(model)

    # Exactly one LP port call, zero MILP port calls
    assert len(lp_port.calls) == 1
    assert len(milp_port.calls) == 0

    # Domain result verification
    assert result.status is ScenarioSolveStatus.OPTIMAL
    assert result.orientation is ScenarioOrientation.MIN_MAX_LOSS
    assert result.guaranteed_value == pytest.approx(76.0 / 7.0)
    assert result.variables == {
        "x1": pytest.approx(37.0 / 7.0),
        "x2": pytest.approx(33.0 / 7.0),
    }
    assert result.binding_scenario_ids == ("s1", "s2")
    assert result.auxiliary_variable_name == "_aux_theta"
    assert result.auxiliary_value == pytest.approx(76.0 / 7.0)
    assert result.delegated_solution.extras["backend"] == "fake_highs"
    assert result.delegated_solution.extras["iterations"] == 4

    # Single post-execution validation acceptance check
    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, result)
    assert report.status is SolutionValidationStatus.VERIFIED
    assert len(report.violations) == 0


def test_solve_scenario_usecase_continuous_reward_negative_guarantee() -> None:
    """Test max_min_reward LP routing with negative guarantee and shared objective terms."""
    model = _make_continuous_reward_negative_model()

    def fake_reward_solve(problem: dict[str, Any]) -> dict[str, Any]:
        assert problem["sense"] == "max"
        assert problem["c"] == [0.0, 0.0, 1.0]  # x1, x2, _aux_tau
        return {
            "status": "Optimal",
            "objective": -12.0,
            "x": {
                "x1": 1.0,
                "x2": 1.0,
                "_aux_tau": -12.0,
            },
            "extras": {
                "backend": "fake_scipy",
            },
        }

    lp_port = RecordingLPSolverPort(response_factory=fake_reward_solve)
    milp_port = RecordingMILPSolverPort()
    usecase = SolveScenarioUseCase(
        solve_lp_usecase=SolveLPUseCase(lp_port),
        solve_milp_usecase=SolveMILPUseCase(milp_port),
    )

    result = usecase.execute(model)

    assert len(lp_port.calls) == 1
    assert len(milp_port.calls) == 0
    assert result.status is ScenarioSolveStatus.OPTIMAL
    assert result.orientation is ScenarioOrientation.MAX_MIN_REWARD
    assert result.guaranteed_value == -12.0
    assert result.binding_scenario_ids == ("s1", "s2")
    assert result.auxiliary_variable_name == "_aux_tau"
    assert result.auxiliary_value == -12.0

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, result)
    assert report.status is SolutionValidationStatus.VERIFIED


def test_solve_scenario_usecase_discrete_milp_routing() -> None:
    """Test discrete MILP routing, integrality specifications, and feasible status handling."""
    model = _make_discrete_loss_model()

    def fake_milp_solve(problem: dict[str, Any]) -> dict[str, Any]:
        assert problem["integrality"] == ["B", "B", "I", None]
        assert problem["var_names"] == ["x1", "x2", "x3", "_aux_theta"]
        return {
            "status": "Feasible",
            "objective": 15.0,
            "x": {
                "x1": 1.0,
                "x2": 1.0,
                "x3": 0.0,
                "_aux_theta": 15.0,
            },
            "extras": {
                "backend": "fake_ortools",
                "wall_time": 0.012,
            },
        }

    lp_port = RecordingLPSolverPort()
    milp_port = RecordingMILPSolverPort(response_factory=fake_milp_solve)
    usecase = SolveScenarioUseCase(
        solve_lp_usecase=SolveLPUseCase(lp_port),
        solve_milp_usecase=SolveMILPUseCase(milp_port),
    )

    result = usecase.execute(model)

    assert len(milp_port.calls) == 1
    assert len(lp_port.calls) == 0
    assert result.status is ScenarioSolveStatus.FEASIBLE
    assert result.guaranteed_value == 15.0
    assert result.variables == {"x1": 1.0, "x2": 1.0, "x3": 0.0}
    assert result.binding_scenario_ids == ("s2",)
    assert result.delegated_solution.diagnostics.wall_time == 0.012

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, result)
    assert report.status is SolutionValidationStatus.VERIFIED


@pytest.mark.parametrize(
    ("raw_status", "expected_status"),
    [
        ("Infeasible", ScenarioSolveStatus.INFEASIBLE),
        ("Unbounded", ScenarioSolveStatus.UNBOUNDED),
        ("NotSolved", ScenarioSolveStatus.NOT_SOLVED),
    ],
)
def test_solve_scenario_usecase_no_candidate_statuses(
    raw_status: str, expected_status: ScenarioSolveStatus
) -> None:
    """Test clean propagation of no-candidate solver outcomes without fabricating solutions."""
    model = _make_continuous_loss_model()

    lp_port = RecordingLPSolverPort(
        response_factory=lambda _: {
            "status": raw_status,
            "objective": None,
            "x": {},
            "extras": {"reason": "no solution"},
        }
    )
    milp_port = RecordingMILPSolverPort()
    usecase = SolveScenarioUseCase(
        solve_lp_usecase=SolveLPUseCase(lp_port),
        solve_milp_usecase=SolveMILPUseCase(milp_port),
    )

    result = usecase.execute(model)

    assert result.status == expected_status
    assert result.guaranteed_value is None
    assert result.variables is None
    assert result.scenario_values == ()
    assert result.binding_scenario_ids == ()
    assert result.auxiliary_value is None
    assert result.delegated_solution.extras["reason"] == "no solution"

    validator = ScenarioIndependentSolutionValidator()
    report = validator(model, result)
    assert report.status is SolutionValidationStatus.NOT_AVAILABLE


def test_solve_scenario_usecase_solver_port_exception_propagates() -> None:
    """Test that solver port exceptions propagate untouched through use case."""
    model = _make_continuous_loss_model()

    def crashing_solve(_: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("Solver port hardware crash")

    lp_port = RecordingLPSolverPort(response_factory=crashing_solve)
    milp_port = RecordingMILPSolverPort()
    usecase = SolveScenarioUseCase(
        solve_lp_usecase=SolveLPUseCase(lp_port),
        solve_milp_usecase=SolveMILPUseCase(milp_port),
    )

    with pytest.raises(RuntimeError, match="Solver port hardware crash"):
        usecase.execute(model)


def test_solve_scenario_usecase_malformed_solver_response_raises_reconstruction_error() -> None:
    """Test that malformed raw solver responses (missing auxiliary variable) raise ScenarioReconstructionError."""
    model = _make_continuous_loss_model()

    # Raw response missing auxiliary variable '_aux_theta'
    lp_port = RecordingLPSolverPort(
        response_factory=lambda _: {
            "status": "Optimal",
            "objective": 10.0,
            "x": {"x1": 5.0, "x2": 5.0},
            "extras": {},
        }
    )
    milp_port = RecordingMILPSolverPort()
    usecase = SolveScenarioUseCase(
        solve_lp_usecase=SolveLPUseCase(lp_port),
        solve_milp_usecase=SolveMILPUseCase(milp_port),
    )

    with pytest.raises(
        ScenarioReconstructionError, match="Auxiliary variable '_aux_theta' is missing"
    ):
        usecase.execute(model)


def test_solve_scenario_usecase_inconsistent_auxiliary_raises_reconstruction_error() -> None:
    """Test that inconsistent solver values raise ScenarioReconstructionError."""
    model = _make_continuous_loss_model()

    # Solver returns x1=5, x2=5, but auxiliary value=999.0 (diverges from recomputed loss 10.0)
    lp_port = RecordingLPSolverPort(
        response_factory=lambda _: {
            "status": "Optimal",
            "objective": 999.0,
            "x": {"x1": 5.0, "x2": 5.0, "_aux_theta": 999.0},
            "extras": {},
        }
    )
    milp_port = RecordingMILPSolverPort()
    usecase = SolveScenarioUseCase(
        solve_lp_usecase=SolveLPUseCase(lp_port),
        solve_milp_usecase=SolveMILPUseCase(milp_port),
    )

    with pytest.raises(ScenarioReconstructionError, match="diverges from auxiliary variable value"):
        usecase.execute(model)


def test_solve_scenario_usecase_repeated_executions_preserve_immutability() -> None:
    """Test that repeated executions produce identical results without mutating the model or retaining state."""
    model = _make_continuous_loss_model()

    lp_port = RecordingLPSolverPort(
        response_factory=lambda _: {
            "status": "Optimal",
            "objective": 76.0 / 7.0,
            "x": {
                "x1": 37.0 / 7.0,
                "x2": 33.0 / 7.0,
                "_aux_theta": 76.0 / 7.0,
            },
            "extras": {},
        }
    )
    milp_port = RecordingMILPSolverPort()
    usecase = SolveScenarioUseCase(
        solve_lp_usecase=SolveLPUseCase(lp_port),
        solve_milp_usecase=SolveMILPUseCase(milp_port),
    )

    res1 = usecase.execute(model)
    res2 = usecase.execute(model)
    res3 = usecase.execute(model)

    assert len(lp_port.calls) == 3
    assert len(milp_port.calls) == 0

    assert res1.guaranteed_value == res2.guaranteed_value == res3.guaranteed_value
    assert res1.variables == res2.variables == res3.variables
    assert res1.binding_scenario_ids == res2.binding_scenario_ids == res3.binding_scenario_ids
    assert model.variable_names() == ("x1", "x2")


def test_solve_scenario_usecase_type_boundary_validation() -> None:
    """Test TypeError on boundary violations."""
    lp_port = RecordingLPSolverPort()
    milp_port = RecordingMILPSolverPort()
    lp_uc = SolveLPUseCase(lp_port)
    milp_uc = SolveMILPUseCase(milp_port)

    with pytest.raises(TypeError, match="solve_lp_usecase must be an instance"):
        SolveScenarioUseCase(solve_lp_usecase=None, solve_milp_usecase=milp_uc)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="solve_milp_usecase must be an instance"):
        SolveScenarioUseCase(solve_lp_usecase=lp_uc, solve_milp_usecase=None)  # type: ignore[arg-type]

    usecase = SolveScenarioUseCase(solve_lp_usecase=lp_uc, solve_milp_usecase=milp_uc)
    with pytest.raises(TypeError, match="model must be an instance of ScenarioModel"):
        usecase.execute(None)  # type: ignore[arg-type]
