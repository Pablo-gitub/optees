from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.knapsack_solver_port import KnapsackSolverPort
from optees.domain.entities.knapsack.solution import KnapsackSolution
from optees.domain.models.knapsack.knapsack01_model import Knapsack01Model


class SolveKnapsackUseCase:
    """Orchestrates Knapsack01Model -> canonical dict -> solver port -> solution."""

    def __init__(self, solver_port: KnapsackSolverPort):
        self._solver = solver_port

    def execute(self, model: Knapsack01Model) -> KnapsackSolution:
        problem = self._map_model_to_problem(model)
        raw = self._solver.solve(problem)
        return KnapsackSolution.from_model_result(
            model,
            status=raw.get("status", "NotSolved"),
            objective=raw.get("objective"),
            selected_indices=raw.get("selected_indices", ()),
            extras=dict(raw.get("extras", {})),
        )

    def _map_model_to_problem(self, model: Knapsack01Model) -> Dict[str, Any]:
        return {
            "values": [float(v) for v in model.values()],
            "weights": [int(w) for w in model.weights()],
            "capacity": int(model.capacity),
            "var_names": list(model.item_names()),
        }
