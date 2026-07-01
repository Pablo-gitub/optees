from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.unbounded_knapsack_solver_port import (
    UnboundedKnapsackSolverPort,
)
from optees.domain.entities.knapsack.unbounded_solution import (
    UnboundedKnapsackSolution,
)
from optees.domain.models.knapsack.unbounded_knapsack_model import (
    UnboundedKnapsackModel,
)


class SolveUnboundedKnapsackUseCase:
    """Orchestrates UnboundedKnapsackModel -> canonical dict -> solver -> solution."""

    def __init__(self, solver_port: UnboundedKnapsackSolverPort):
        self._solver = solver_port

    def execute(self, model: UnboundedKnapsackModel) -> UnboundedKnapsackSolution:
        problem = self._map_model_to_problem(model)
        raw = self._solver.solve(problem)
        return UnboundedKnapsackSolution.from_model_result(
            model,
            status=raw.get("status", "NotSolved"),
            objective=raw.get("objective"),
            quantities=raw.get("quantities", ()),
            extras=dict(raw.get("extras", {})),
        )

    def _map_model_to_problem(self, model: UnboundedKnapsackModel) -> Dict[str, Any]:
        return {
            "values": [float(v) for v in model.values()],
            "weights": [int(w) for w in model.weights()],
            "capacity": int(model.capacity),
            "var_names": list(model.item_names()),
        }

