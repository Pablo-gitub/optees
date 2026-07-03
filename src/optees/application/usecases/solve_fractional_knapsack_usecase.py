from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.fractional_knapsack_solver_port import (
    FractionalKnapsackSolverPort,
)
from optees.domain.entities.knapsack.fractional_solution import (
    FractionalKnapsackSolution,
)
from optees.domain.models.knapsack.fractional_knapsack_model import (
    FractionalKnapsackModel,
)


class SolveFractionalKnapsackUseCase:
    """Orchestrates FractionalKnapsackModel -> canonical dict -> solver -> solution."""

    def __init__(self, solver_port: FractionalKnapsackSolverPort):
        self._solver = solver_port

    def execute(self, model: FractionalKnapsackModel) -> FractionalKnapsackSolution:
        problem = self._map_model_to_problem(model)
        raw = self._solver.solve(problem)
        return FractionalKnapsackSolution.from_model_result(
            model,
            status=raw.get("status", "NotSolved"),
            objective=raw.get("objective"),
            fractions=raw.get("fractions", ()),
            extras=dict(raw.get("extras", {})),
        )

    def _map_model_to_problem(self, model: FractionalKnapsackModel) -> Dict[str, Any]:
        return {
            "values": [float(v) for v in model.values()],
            "weights": [float(w) for w in model.weights()],
            "capacity": float(model.capacity),
            "var_names": list(model.item_names()),
        }

