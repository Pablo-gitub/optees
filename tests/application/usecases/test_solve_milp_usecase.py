from __future__ import annotations

import importlib.util

import pytest

from optees.application.usecases.solve_milp_usecase import SolveMILPUseCase
from optees.data.adapters.milp.milp_solver_adapter import MILPSolverAdapter
from optees.domain.entities.lp.constraint import Constraint
from optees.domain.entities.lp.objective import Objective
from optees.domain.entities.milp.variable import MILPVariable
from optees.domain.models.milp.milp_model import MILPModel
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.milp.integrality import Integrality
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus


def _assignment_model() -> MILPModel:
    variables = (
        MILPVariable("x11", bounds=Bounds(0, 1), integrality=Integrality.BINARY),
        MILPVariable("x12", bounds=Bounds(0, 1), integrality=Integrality.BINARY),
        MILPVariable("x21", bounds=Bounds(0, 1), integrality=Integrality.BINARY),
        MILPVariable("x22", bounds=Bounds(0, 1), integrality=Integrality.BINARY),
    )
    objective = Objective(ObjectiveSense.MIN, (1, 2, 2, 1), 0)
    constraints = (
        Constraint((1, 1, 0, 0), Relation.EQ, 1),
        Constraint((0, 0, 1, 1), Relation.EQ, 1),
        Constraint((1, 0, 1, 0), Relation.EQ, 1),
        Constraint((0, 1, 0, 1), Relation.EQ, 1),
    )
    return MILPModel.from_parts(variables, objective, constraints, time_limit=5.0)


class RecordingPort:
    def __init__(self):
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Feasible",
            "objective": 4.0,
            "x": {"x11": 1.0},
            "extras": {"backend": "stub", "best_bound": 3.0, "relative_gap": 0.25},
        }


def test_maps_model_to_canonical_problem_and_result():
    port = RecordingPort()
    usecase = SolveMILPUseCase(port)

    solution = usecase.execute(_assignment_model())

    assert port.problem["sense"] == "min"
    assert port.problem["c"] == [1.0, 2.0, 2.0, 1.0]
    assert port.problem["integrality"] == ["B", "B", "B", "B"]
    assert port.problem["bounds"] == [(0, 1), (0, 1), (0, 1), (0, 1)]
    assert port.problem["A_eq"] == [
        [1.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 1.0],
        [1.0, 0.0, 1.0, 0.0],
        [0.0, 1.0, 0.0, 1.0],
    ]
    assert port.problem["time_limit"] == pytest.approx(5.0)
    assert solution.status is MILPSolveStatus.FEASIBLE
    assert solution.has_incumbent()
    assert solution.diagnostics.backend == "stub"


def test_binary_variable_keeps_canonical_bounds_after_bound_update():
    variable = MILPVariable("x").with_integrality("B").with_bounds(2, 5)

    assert variable.integrality is Integrality.BINARY
    assert variable.bounds.lb == pytest.approx(0.0)
    assert variable.bounds.ub == pytest.approx(1.0)


@pytest.mark.skipif(importlib.util.find_spec("ortools") is None, reason="ortools not installed")
def test_adapter_solves_assignment_model():
    usecase = SolveMILPUseCase(MILPSolverAdapter())

    solution = usecase.execute(_assignment_model())

    assert solution.status is MILPSolveStatus.OPTIMAL
    assert solution.objective == pytest.approx(2.0)
    assert solution.values["x11"] == pytest.approx(1.0)
    assert solution.values["x22"] == pytest.approx(1.0)
    assert solution.diagnostics.backend in {"cp-sat", "cbc"}
