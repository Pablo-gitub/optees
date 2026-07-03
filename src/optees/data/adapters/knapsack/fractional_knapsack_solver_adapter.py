from __future__ import annotations

from typing import Any, Dict, List

from optees.application.ports.fractional_knapsack_solver_port import (
    FractionalKnapsackSolverPort,
)
from optees.utility.knapsack_utils import solve_fractional_knapsack


class FractionalKnapsackSolverAdapter(FractionalKnapsackSolverPort):
    """Concrete adapter around the exact fractional-knapsack greedy utility."""

    def __init__(self, *, max_items: int = 1_000_000) -> None:
        self._max_items = int(max_items)

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        values = list(problem.get("values") or [])
        weights = list(problem.get("weights") or [])
        capacity = problem.get("capacity", 0.0)
        item_names = list(
            problem.get("item_names")
            or problem.get("var_names")
            or [f"Item {i + 1}" for i in range(len(values))]
        )

        try:
            if len(values) > self._max_items:
                return _not_solved(
                    values=values,
                    capacity=capacity,
                    max_items=self._max_items,
                    message=(
                        "Instance is too large for the current exact greedy "
                        "adapter; reduce item count or use an alternative solver."
                    ),
                )

            objective, fractions = solve_fractional_knapsack(
                values,
                weights,
                capacity,
            )
            weights_float = [float(weight) for weight in weights]
            capacity_float = float(capacity)
            total_weight = float(
                sum(weights_float[i] * fractions[i] for i in range(len(fractions)))
            )
            remaining = capacity_float - total_weight
            x = {
                str(item_names[i] if i < len(item_names) else f"Item {i + 1}"): fractions[i]
                for i in range(len(fractions))
            }
            return {
                "status": "Optimal",
                "objective": float(objective),
                "fractions": list(fractions),
                "x": x,
                "extras": {
                    "method": "fractional_greedy_density",
                    "complexity": "O(n log n)",
                    "item_count": len(values),
                    "capacity": capacity_float,
                    "max_items": self._max_items,
                    "total_weight": total_weight,
                    "remaining_capacity": remaining,
                    "success": True,
                },
            }
        except Exception as exc:
            return _not_solved(
                values=values,
                capacity=capacity,
                max_items=self._max_items,
                message=str(exc),
            )


def _not_solved(
    *,
    values: List[object],
    capacity: object,
    max_items: int,
    message: str,
) -> Dict[str, Any]:
    return {
        "status": "NotSolved",
        "objective": None,
        "fractions": [],
        "x": {},
        "extras": {
            "method": "fractional_greedy_density",
            "complexity": "O(n log n)",
            "item_count": len(values),
            "capacity": capacity,
            "max_items": max_items,
            "message": message,
            "success": False,
        },
    }

