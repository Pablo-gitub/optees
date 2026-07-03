from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from optees.domain.models.knapsack.fractional_knapsack_model import (
    FractionalKnapsackModel,
)
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus
from optees.domain.value_objects.knapsack.solver_diagnostics import (
    KnapsackSolverDiagnostics,
)


@dataclass(frozen=True)
class FractionalKnapsackSolution:
    """Domain result for a fractional knapsack solve."""

    status: KnapsackSolveStatus
    objective: Optional[float]
    fractions: Tuple[float, ...]
    selected_indices: Tuple[int, ...]
    selected_item_names: Tuple[str, ...]
    total_value: float
    total_weight: float
    remaining_capacity: Optional[float]
    diagnostics: KnapsackSolverDiagnostics
    extras: Dict[str, object]

    @staticmethod
    def from_model_result(
        model: FractionalKnapsackModel,
        *,
        status: object,
        objective: Optional[float],
        fractions: object,
        extras: Dict[str, object],
    ) -> "FractionalKnapsackSolution":
        status_value = KnapsackSolveStatus.from_str(status)
        fraction_tuple = _normalize_fractions(fractions, model.n_items())
        selected = tuple(
            index for index, fraction in enumerate(fraction_tuple) if fraction > 0
        )
        total_value = float(
            sum(model.items[i].value * fraction_tuple[i] for i in range(model.n_items()))
        )
        total_weight = float(
            sum(model.items[i].weight * fraction_tuple[i] for i in range(model.n_items()))
        )
        remaining = model.capacity - total_weight
        names = tuple(model.items[i].name for i in selected)
        extras = dict(extras or {})

        return FractionalKnapsackSolution(
            status=status_value,
            objective=None if objective is None else float(objective),
            fractions=fraction_tuple,
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
        return any(fraction > 0 for fraction in self.fractions)


def _normalize_fractions(value: object, item_count: int) -> Tuple[float, ...]:
    if value is None:
        return (0.0,) * item_count
    try:
        fractions = tuple(float(fraction) for fraction in value)  # type: ignore[arg-type]
    except TypeError:
        return (0.0,) * item_count
    padded = fractions[:item_count] + (0.0,) * max(0, item_count - len(fractions))
    return tuple(min(1.0, max(0.0, fraction)) for fraction in padded)

