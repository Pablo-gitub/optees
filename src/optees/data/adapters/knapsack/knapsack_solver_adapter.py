from __future__ import annotations

from typing import Any, Dict, List

from optees.application.ports.knapsack_solver_port import KnapsackSolverPort
from optees.utility.knapsack_utils import solve_knapsack_01


class KnapsackSolverAdapter(KnapsackSolverPort):
    """Concrete adapter around the exact dynamic-programming knapsack utility."""

    def __init__(self, *, max_dp_cells: int = 5_000_000) -> None:
        self._max_dp_cells = int(max_dp_cells)

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        values = list(problem.get("values") or [])
        weights = list(problem.get("weights") or [])
        capacity = problem.get("capacity", 0)
        item_names = list(
            problem.get("item_names")
            or problem.get("var_names")
            or [f"Item {i + 1}" for i in range(len(values))]
        )

        try:
            capacity_int = _normalize_int(capacity, "capacity")
            dp_cells = (len(values) + 1) * (capacity_int + 1)
            if dp_cells > self._max_dp_cells:
                return _not_solved(
                    values=values,
                    capacity=capacity_int,
                    dp_cells=dp_cells,
                    max_dp_cells=self._max_dp_cells,
                    message=(
                        "Instance is too large for the current exact dynamic-programming "
                        "adapter; use a MILP/alternative knapsack solver."
                    ),
                )

            objective, selected = solve_knapsack_01(values, weights, capacity_int)
            selected_set = set(selected)
            total_weight = int(sum(int(weights[i]) for i in selected))
            remaining = capacity_int - total_weight
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
                    "method": "dynamic_programming",
                    "complexity": "O(n * capacity)",
                    "item_count": len(values),
                    "capacity": capacity_int,
                    "dp_cells": dp_cells,
                    "max_dp_cells": self._max_dp_cells,
                    "total_weight": total_weight,
                    "remaining_capacity": remaining,
                    "success": True,
                },
            }
        except Exception as exc:
            return _not_solved(
                values=values,
                capacity=capacity,
                dp_cells=None,
                max_dp_cells=self._max_dp_cells,
                message=str(exc),
            )


def _normalize_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise ValueError(f"{label} must be an integer")


def _not_solved(
    *,
    values: List[object],
    capacity: object,
    dp_cells: object,
    max_dp_cells: int,
    message: str,
) -> Dict[str, Any]:
    extras = {
        "method": "dynamic_programming",
        "complexity": "O(n * capacity)",
        "item_count": len(values),
        "capacity": capacity,
        "dp_cells": dp_cells,
        "max_dp_cells": max_dp_cells,
        "message": message,
        "success": False,
    }
    return {
        "status": "NotSolved",
        "objective": None,
        "selected_indices": [],
        "x": {},
        "extras": extras,
    }
