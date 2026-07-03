from __future__ import annotations

from typing import Any, Dict, List

from optees.application.ports.multi_dimensional_knapsack_solver_port import (
    MultiDimensionalKnapsackSolverPort,
)
from optees.utility.knapsack_utils import solve_multi_dimensional_knapsack


class MultiDimensionalKnapsackSolverAdapter(MultiDimensionalKnapsackSolverPort):
    """Concrete adapter around the exact multi-dimensional branch-and-bound."""

    def __init__(self, *, max_items: int = 32) -> None:
        self._max_items = int(max_items)

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        values = list(problem.get("values") or [])
        usage_matrix = [list(row) for row in problem.get("usage_matrix") or []]
        capacities = list(problem.get("capacities") or [])
        item_names = list(
            problem.get("item_names")
            or problem.get("var_names")
            or [f"Item {i + 1}" for i in range(len(values))]
        )
        resource_names = list(
            problem.get("resource_names")
            or [f"Resource {i + 1}" for i in range(len(capacities))]
        )

        try:
            if len(values) > self._max_items:
                return _not_solved(
                    values=values,
                    capacities=capacities,
                    resource_names=resource_names,
                    max_items=self._max_items,
                    message=(
                        "Instance is too large for the current exact "
                        "branch-and-bound adapter; use a MILP/alternative solver."
                    ),
                )

            objective, selected = solve_multi_dimensional_knapsack(
                values,
                usage_matrix,
                capacities,
            )
            usage_totals = _resource_usage_totals(usage_matrix, selected, len(capacities))
            remaining = [
                float(capacities[index]) - usage_totals[index]
                for index in range(len(capacities))
            ]
            selected_set = set(selected)
            x = {
                str(item_names[i] if i < len(item_names) else f"Item {i + 1}"): (
                    1.0 if i in selected_set else 0.0
                )
                for i in range(len(values))
            }
            return {
                "status": "Optimal",
                "objective": float(objective),
                "selected_indices": list(selected),
                "x": x,
                "extras": {
                    "method": "multidimensional_branch_and_bound",
                    "complexity": "O(2^n * m)",
                    "item_count": len(values),
                    "resource_count": len(capacities),
                    "resource_names": resource_names,
                    "capacities": [float(capacity) for capacity in capacities],
                    "max_items": self._max_items,
                    "total_usage": usage_totals,
                    "remaining_capacities": remaining,
                    "success": True,
                },
            }
        except Exception as exc:
            return _not_solved(
                values=values,
                capacities=capacities,
                resource_names=resource_names,
                max_items=self._max_items,
                message=str(exc),
            )


def _resource_usage_totals(
    usage_matrix: List[List[object]],
    selected_indices: List[int],
    resource_count: int,
) -> List[float]:
    totals = [0.0] * resource_count
    for item_index in selected_indices:
        row = usage_matrix[item_index]
        for resource_index in range(resource_count):
            totals[resource_index] += float(row[resource_index])
    return totals


def _not_solved(
    *,
    values: List[object],
    capacities: List[object],
    resource_names: List[object],
    max_items: int,
    message: str,
) -> Dict[str, Any]:
    return {
        "status": "NotSolved",
        "objective": None,
        "selected_indices": [],
        "x": {},
        "extras": {
            "method": "multidimensional_branch_and_bound",
            "complexity": "O(2^n * m)",
            "item_count": len(values),
            "resource_count": len(capacities),
            "resource_names": resource_names,
            "capacities": capacities,
            "max_items": max_items,
            "message": message,
            "success": False,
        },
    }

