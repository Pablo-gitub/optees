from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from optees.domain.models.knapsack.multi_dimensional_knapsack_model import (
    MultiDimensionalKnapsackModel,
)
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus
from optees.domain.value_objects.knapsack.solver_diagnostics import (
    KnapsackSolverDiagnostics,
)


@dataclass(frozen=True)
class MultiDimensionalQuantityKnapsackSolution:
    """Result for multi-dimensional knapsack variants with quantity variables."""

    status: KnapsackSolveStatus
    objective: Optional[float]
    quantities: Tuple[float, ...]
    selected_indices: Tuple[int, ...]
    selected_item_names: Tuple[str, ...]
    total_value: float
    resource_usage_totals: Tuple[float, ...]
    remaining_capacities: Tuple[float, ...]
    diagnostics: KnapsackSolverDiagnostics
    extras: Dict[str, object]

    @staticmethod
    def from_model_quantities(
        model: MultiDimensionalKnapsackModel,
        *,
        status: object,
        objective: Optional[float],
        quantities: object,
        extras: Dict[str, object],
    ) -> "MultiDimensionalQuantityKnapsackSolution":
        status_value = KnapsackSolveStatus.from_str(status)
        quantity_tuple = _normalize_quantities(quantities, model.n_items())
        selected = tuple(
            index for index, quantity in enumerate(quantity_tuple) if quantity > 1e-9
        )
        total_value = float(
            sum(model.items[i].value * quantity_tuple[i] for i in range(model.n_items()))
        )
        resource_usage = tuple(
            float(
                sum(
                    model.items[i].resource_usage[r] * quantity_tuple[i]
                    for i in range(model.n_items())
                )
            )
            for r in range(model.n_resources())
        )
        remaining = tuple(
            float(model.resources[r].capacity - resource_usage[r])
            for r in range(model.n_resources())
        )
        names = tuple(model.items[i].name for i in selected)
        extras = dict(extras or {})

        return MultiDimensionalQuantityKnapsackSolution(
            status=status_value,
            objective=None if objective is None else float(objective),
            quantities=quantity_tuple,
            selected_indices=selected,
            selected_item_names=names,
            total_value=total_value,
            resource_usage_totals=resource_usage,
            remaining_capacities=remaining,
            diagnostics=KnapsackSolverDiagnostics.from_extras(extras),
            extras=extras,
        )

    def is_optimal(self) -> bool:
        return self.status is KnapsackSolveStatus.OPTIMAL

    def has_selection(self) -> bool:
        return any(quantity > 1e-9 for quantity in self.quantities)


def _normalize_quantities(value: object, item_count: int) -> Tuple[float, ...]:
    if value is None:
        return (0.0,) * item_count
    try:
        quantities = tuple(float(quantity) for quantity in value)  # type: ignore[arg-type]
    except TypeError:
        return (0.0,) * item_count
    padded = quantities[:item_count] + (0.0,) * max(0, item_count - len(quantities))
    return tuple(max(0.0, quantity) for quantity in padded)
