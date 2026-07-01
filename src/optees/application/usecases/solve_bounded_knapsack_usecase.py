from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.bounded_knapsack_solver_port import (
    BoundedKnapsackSolverPort,
)
from optees.domain.entities.knapsack.bounded_solution import BoundedKnapsackSolution
from optees.domain.models.knapsack.bounded_knapsack_model import BoundedKnapsackModel


class SolveBoundedKnapsackUseCase:
    """Orchestrates BoundedKnapsackModel -> canonical dict -> solver -> solution."""

    def __init__(self, solver_port: BoundedKnapsackSolverPort):
        self._solver = solver_port

    def execute(self, model: BoundedKnapsackModel) -> BoundedKnapsackSolution:
        problem = self._map_model_to_problem(model)
        raw = self._solver.solve(problem)
        return BoundedKnapsackSolution.from_model_result(
            model,
            status=raw.get("status", "NotSolved"),
            objective=raw.get("objective"),
            quantities=raw.get("quantities", ()),
            extras=dict(raw.get("extras", {})),
        )

    def _map_model_to_problem(self, model: BoundedKnapsackModel) -> Dict[str, Any]:
        return {
            "values": [float(v) for v in model.values()],
            "weights": [int(w) for w in model.weights()],
            "max_quantities": [int(q) for q in model.max_quantities()],
            "capacity": int(model.capacity),
            "var_names": list(model.item_names()),
        }
