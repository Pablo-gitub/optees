from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from optees.domain.models.knapsack.knapsack01_model import Knapsack01Model
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus
from optees.domain.value_objects.knapsack.solver_diagnostics import (
    KnapsackSolverDiagnostics,
)


@dataclass(frozen=True)
class KnapsackSolution:
    """Domain result for a 0/1 knapsack solve."""

    status: KnapsackSolveStatus
    objective: Optional[float]
    selected_indices: Tuple[int, ...]
    selected_item_names: Tuple[str, ...]
    total_value: float
    total_weight: int
    remaining_capacity: Optional[int]
    diagnostics: KnapsackSolverDiagnostics
    extras: Dict[str, object]

    @staticmethod
    def from_model_result(
        model: Knapsack01Model,
        *,
        status: object,
        objective: Optional[float],
        selected_indices: object,
        extras: Dict[str, object],
    ) -> "KnapsackSolution":
        status_value = KnapsackSolveStatus.from_str(status)
        selected = _normalize_selected_indices(selected_indices, model.n_items())
        total_value = float(sum(model.items[i].value for i in selected))
        total_weight = int(sum(model.items[i].weight for i in selected))
        remaining = model.capacity - total_weight
        names = tuple(model.items[i].name for i in selected)
        extras = dict(extras or {})

        return KnapsackSolution(
            status=status_value,
            objective=None if objective is None else float(objective),
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

