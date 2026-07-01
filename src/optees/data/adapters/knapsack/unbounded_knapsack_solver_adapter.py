from __future__ import annotations

from typing import Any, Dict, List

from optees.application.ports.unbounded_knapsack_solver_port import (
    UnboundedKnapsackSolverPort,
)
from optees.utility.knapsack_utils import solve_unbounded_knapsack


class UnboundedKnapsackSolverAdapter(UnboundedKnapsackSolverPort):
    """Concrete adapter around the exact unbounded-knapsack DP utility."""

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
            values_float = [float(value) for value in values]
            weights_int = [_normalize_int(weight, "weights") for weight in weights]

            if len(values_float) != len(weights_int):
                raise ValueError("values and weights must have the same length")
            if capacity_int < 0:
                raise ValueError("capacity must be non-negative")
            if any(weight < 0 for weight in weights_int):
                raise ValueError("weights must be non-negative")

            dp_cells = len(values_float) * (capacity_int + 1)
            if dp_cells > self._max_dp_cells:
                return _not_solved(
                    values=values,
                    capacity=capacity_int,
                    dp_cells=dp_cells,
                    max_dp_cells=self._max_dp_cells,
                    message=(
                        "Instance is too large for the current exact unbounded "
                        "dynamic-programming adapter; use a MILP/alternative solver."
                    ),
                )

            if any(
                weight == 0 and value > 0
                for value, weight in zip(values_float, weights_int)
            ):
                return _unbounded(
                    values=values,
                    capacity=capacity_int,
                    dp_cells=dp_cells,
                    max_dp_cells=self._max_dp_cells,
                    message=(
                        "Problem is unbounded because a positive-value item has "
                        "zero weight and can be selected indefinitely."
                    ),
                )

            objective, quantities = solve_unbounded_knapsack(
                values_float,
                weights_int,
                capacity_int,
            )
            total_weight = int(
                sum(weights_int[i] * quantities[i] for i in range(len(quantities)))
            )
            remaining = capacity_int - total_weight
            x = {
                str(item_names[i] if i < len(item_names) else f"Item {i + 1}"): quantities[i]
                for i in range(len(quantities))
            }
            return {
                "status": "Optimal",
                "objective": float(objective),
                "quantities": list(quantities),
                "x": x,
                "extras": {
                    "method": "unbounded_dynamic_programming",
                    "complexity": "O(n * capacity)",
                    "item_count": len(values_float),
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
    extras = _diagnostics_extras(
        values=values,
        capacity=capacity,
        dp_cells=dp_cells,
        max_dp_cells=max_dp_cells,
        message=message,
        success=False,
    )
    return {
        "status": "NotSolved",
        "objective": None,
        "quantities": [],
        "x": {},
        "extras": extras,
    }


def _unbounded(
    *,
    values: List[object],
    capacity: object,
    dp_cells: object,
    max_dp_cells: int,
    message: str,
) -> Dict[str, Any]:
    extras = _diagnostics_extras(
        values=values,
        capacity=capacity,
        dp_cells=dp_cells,
        max_dp_cells=max_dp_cells,
        message=message,
        success=False,
    )
    return {
        "status": "Unbounded",
        "objective": None,
        "quantities": [],
        "x": {},
        "extras": extras,
    }


def _diagnostics_extras(
    *,
    values: List[object],
    capacity: object,
    dp_cells: object,
    max_dp_cells: int,
    message: str,
    success: bool,
) -> Dict[str, Any]:
    return {
        "method": "unbounded_dynamic_programming",
        "complexity": "O(n * capacity)",
        "item_count": len(values),
        "capacity": capacity,
        "dp_cells": dp_cells,
        "max_dp_cells": max_dp_cells,
        "message": message,
        "success": success,
    }

