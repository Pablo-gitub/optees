from __future__ import annotations

from typing import Any, Dict, List

from optees.application.ports.bounded_knapsack_solver_port import (
    BoundedKnapsackSolverPort,
)
from optees.utility.knapsack_utils import solve_bounded_knapsack


class BoundedKnapsackSolverAdapter(BoundedKnapsackSolverPort):
    """Concrete adapter around the exact bounded-knapsack DP utility."""

    def __init__(self, *, max_dp_states: int = 5_000_000) -> None:
        self._max_dp_states = int(max_dp_states)

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        values = list(problem.get("values") or [])
        weights = list(problem.get("weights") or [])
        max_quantities = list(problem.get("max_quantities") or [])
        capacity = problem.get("capacity", 0)
        item_names = list(
            problem.get("item_names")
            or problem.get("var_names")
            or [f"Item {i + 1}" for i in range(len(values))]
        )

        try:
            capacity_int = _normalize_int(capacity, "capacity")
            weights_int = [_normalize_int(weight, "weights") for weight in weights]
            quantities_int = [
                _normalize_int(quantity, "max_quantities")
                for quantity in max_quantities
            ]
            dp_states = _estimate_dp_states(weights_int, quantities_int, capacity_int)
            if dp_states > self._max_dp_states:
                return _not_solved(
                    values=values,
                    capacity=capacity_int,
                    dp_states=dp_states,
                    max_dp_states=self._max_dp_states,
                    message=(
                        "Instance is too large for the current exact bounded "
                        "dynamic-programming adapter; use a MILP/alternative solver."
                    ),
                )

            objective, quantities = solve_bounded_knapsack(
                values,
                weights_int,
                quantities_int,
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
                    "method": "bounded_dynamic_programming",
                    "complexity": "O(capacity * sum_i feasible_quantity_i)",
                    "item_count": len(values),
                    "capacity": capacity_int,
                    "dp_cells": dp_states,
                    "max_dp_cells": self._max_dp_states,
                    "dp_states": dp_states,
                    "max_dp_states": self._max_dp_states,
                    "total_weight": total_weight,
                    "remaining_capacity": remaining,
                    "success": True,
                },
            }
        except Exception as exc:
            return _not_solved(
                values=values,
                capacity=capacity,
                dp_states=None,
                max_dp_states=self._max_dp_states,
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


def _estimate_dp_states(
    weights: List[int],
    max_quantities: List[int],
    capacity: int,
) -> int:
    if len(weights) != len(max_quantities):
        raise ValueError("weights and max_quantities must have the same length")
    if capacity < 0:
        raise ValueError("capacity must be non-negative")
    states = 0
    for weight, max_quantity in zip(weights, max_quantities):
        if weight < 0 or max_quantity < 0:
            raise ValueError("weights and max_quantities must be non-negative")
        feasible_quantities = max_quantity if weight == 0 else min(max_quantity, capacity // weight)
        states += feasible_quantities + 1
    return (capacity + 1) * states


def _not_solved(
    *,
    values: List[object],
    capacity: object,
    dp_states: object,
    max_dp_states: int,
    message: str,
) -> Dict[str, Any]:
    extras = {
        "method": "bounded_dynamic_programming",
        "complexity": "O(capacity * sum_i feasible_quantity_i)",
        "item_count": len(values),
        "capacity": capacity,
        "dp_cells": dp_states,
        "max_dp_cells": max_dp_states,
        "dp_states": dp_states,
        "max_dp_states": max_dp_states,
        "message": message,
        "success": False,
    }
    return {
        "status": "NotSolved",
        "objective": None,
        "quantities": [],
        "x": {},
        "extras": extras,
    }
