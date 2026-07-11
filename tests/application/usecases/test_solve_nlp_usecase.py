from __future__ import annotations

from typing import Any, Dict

from optees.application.usecases.solve_nlp_usecase import SolveNLPUseCase
from optees.domain.entities.nlp.objective import NLPObjective
from optees.domain.entities.nlp.variable import NLPVariable
from optees.domain.models.nlp.nlp_model import NLPModel, NLPOptions
from optees.domain.value_objects.nlp.solve_status import NLPSolveStatus
from optees.domain.value_objects.nlp.solver_method import NLPSolverMethod


class FakeNLPSolver:
    def __init__(self, response: Dict[str, Any]) -> None:
        self.response = response
        self.calls: list[Dict[str, Any]] = []

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append(problem)
        return self.response


def test_use_case_maps_model_to_canonical_nlp_problem_and_solution() -> None:
    model = NLPModel.from_parts(
        variables=[NLPVariable("x1", initial_value=1.0)],
        objective=NLPObjective("(x1 - 2)**2"),
        options=NLPOptions(method=NLPSolverMethod.BFGS, max_iterations=50, tolerance=1e-7),
    )
    solver = FakeNLPSolver(
        {
            "status": "Converged",
            "objective": 0.0,
            "x": {"x1": 2.0},
            "extras": {"iterations": 4, "evaluations": 6, "message": "done"},
        }
    )

    result = SolveNLPUseCase(solver).execute(model)

    assert solver.calls == [
        {
            "sense": "min",
            "expression": "(x1 - 2)**2",
            "variables": ["x1"],
            "initial_point": [1.0],
            "bounds": [(None, None)],
            "method": "BFGS",
            "max_iterations": 50,
            "tolerance": 1e-7,
        }
    ]
    assert result.status is NLPSolveStatus.CONVERGED
    assert result.objective == 0.0
    assert result.values == {"x1": 2.0}
    assert result.iterations == 4
    assert result.evaluations == 6
