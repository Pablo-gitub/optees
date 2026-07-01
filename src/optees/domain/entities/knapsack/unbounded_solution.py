from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from optees.domain.models.knapsack.unbounded_knapsack_model import (
    UnboundedKnapsackModel,
)
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus
from optees.domain.value_objects.knapsack.solver_diagnostics import (
    KnapsackSolverDiagnostics,
)


@dataclass(frozen=True)
class UnboundedKnapsackSolution:
    """Domain result for an unbounded knapsack solve."""

    status: KnapsackSolveStatus
    objective: Optional[float]
    quantities: Tuple[int, ...]
    selected_indices: Tuple[int, ...]
    selected_item_names: Tuple[str, ...]
    total_value: float
    total_weight: int
    remaining_capacity: Optional[int]
    diagnostics: KnapsackSolverDiagnostics
    extras: Dict[str, object]

    @staticmethod
    def from_model_result(
        model: UnboundedKnapsackModel,
        *,
        status: object,
        objective: Optional[float],
        quantities: object,
        extras: Dict[str, object],
    ) -> "UnboundedKnapsackSolution":
        status_value = KnapsackSolveStatus.from_str(status)
        quantity_tuple = _normalize_quantities(quantities, model.n_items())
        selected = tuple(
            index for index, quantity in enumerate(quantity_tuple) if quantity > 0
        )
        total_value = float(
            sum(model.items[i].value * quantity_tuple[i] for i in range(model.n_items()))
        )
        total_weight = int(
            sum(model.items[i].weight * quantity_tuple[i] for i in range(model.n_items()))
        )
        remaining = model.capacity - total_weight
        names = tuple(model.items[i].name for i in selected)
        extras = dict(extras or {})

        return UnboundedKnapsackSolution(
            status=status_value,
            objective=None if objective is None else float(objective),
            quantities=quantity_tuple,
            selected_indices=selected,
            selected_item_names=names,
            total_value=total_value,
            total_weight=total_weight,
            remaining_capacity=remaining,
            diagnostics=KnapsackSolverDiagnostics.from_extras(extras),
            extras=extras,
        )

    def is_optimal(self) -> bool:
        return self.status is KnapsackSolveStatus.OPTIMAL

    def is_unbounded(self) -> bool:
        return self.status is KnapsackSolveStatus.UNBOUNDED

    def has_selection(self) -> bool:
        return any(quantity > 0 for quantity in self.quantities)


def _normalize_quantities(value: object, item_count: int) -> Tuple[int, ...]:
    if value is None:
        return (0,) * item_count
    try:
        quantities = tuple(int(q) for q in value)  # type: ignore[arg-type]
    except TypeError:
        return (0,) * item_count
    padded = quantities[:item_count] + (0,) * max(0, item_count - len(quantities))
    return tuple(max(0, q) for q in padded)

