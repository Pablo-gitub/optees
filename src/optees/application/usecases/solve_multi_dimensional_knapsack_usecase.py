from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.multi_dimensional_knapsack_solver_port import (
    MultiDimensionalKnapsackSolverPort,
)
from optees.domain.entities.knapsack.multi_dimensional_solution import (
    MultiDimensionalKnapsackSolution,
)
from optees.domain.models.knapsack.multi_dimensional_knapsack_model import (
    MultiDimensionalKnapsackModel,
)


class SolveMultiDimensionalKnapsackUseCase:
    """Orchestrates multi-dimensional model -> canonical dict -> solver."""

    def __init__(self, solver_port: MultiDimensionalKnapsackSolverPort):
        self._solver = solver_port

    def execute(
        self,
        model: MultiDimensionalKnapsackModel,
    ) -> MultiDimensionalKnapsackSolution:
        problem = self._map_model_to_problem(model)
        raw = self._solver.solve(problem)
        return MultiDimensionalKnapsackSolution.from_model_result(
            model,
            status=raw.get("status", "NotSolved"),
            objective=raw.get("objective"),
            selected_indices=raw.get("selected_indices", ()),
            extras=dict(raw.get("extras", {})),
        )

    def _map_model_to_problem(
        self,
        model: MultiDimensionalKnapsackModel,
    ) -> Dict[str, Any]:
        return {
            "values": [float(v) for v in model.values()],
            "usage_matrix": [
                [float(amount) for amount in row]
                for row in model.usage_matrix()
            ],
            "capacities": [float(capacity) for capacity in model.capacities()],
            "var_names": list(model.item_names()),
            "resource_names": list(model.resource_names()),
        }

