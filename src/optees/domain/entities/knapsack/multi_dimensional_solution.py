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
class MultiDimensionalKnapsackSolution:
    """Domain result for a multi-dimensional 0/1 knapsack solve."""

    status: KnapsackSolveStatus
    objective: Optional[float]
    selected_indices: Tuple[int, ...]
    selected_item_names: Tuple[str, ...]
    total_value: float
    resource_usage_totals: Tuple[float, ...]
    remaining_capacities: Tuple[float, ...]
    diagnostics: KnapsackSolverDiagnostics
    extras: Dict[str, object]

    @staticmethod
    def from_model_result(
        model: MultiDimensionalKnapsackModel,
        *,
        status: object,
        objective: Optional[float],
        selected_indices: object,
        extras: Dict[str, object],
    ) -> "MultiDimensionalKnapsackSolution":
        status_value = KnapsackSolveStatus.from_str(status)
        selected = _normalize_selected_indices(selected_indices, model.n_items())
        total_value = float(sum(model.items[i].value for i in selected))
        resource_usage = tuple(
            float(sum(model.items[i].resource_usage[r] for i in selected))
            for r in range(model.n_resources())
        )
        remaining = tuple(
            float(model.resources[r].capacity - resource_usage[r])
            for r in range(model.n_resources())
        )
        names = tuple(model.items[i].name for i in selected)
        extras = dict(extras or {})

        return MultiDimensionalKnapsackSolution(
            status=status_value,
            objective=None if objective is None else float(objective),
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
        return bool(self.selected_indices)


def _normalize_selected_indices(value: object, item_count: int) -> Tuple[int, ...]:
    if value is None:
        return tuple()
    try:
        indices = tuple(int(i) for i in value)  # type: ignore[arg-type]
    except TypeError:
        return tuple()
    return tuple(i for i in indices if 0 <= i < item_count)

