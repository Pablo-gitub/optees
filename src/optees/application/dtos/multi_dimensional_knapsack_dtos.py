from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from optees.domain.models.knapsack.multi_dimensional_knapsack_model import (
        MultiDimensionalKnapsackModel,
    )


@dataclass(frozen=True)
class MultiDimensionalKnapsackRequest:
    model: MultiDimensionalKnapsackModel
    domain: str
    upper_bounds: tuple[float | None, ...]

    def __post_init__(self) -> None:
        if len(self.upper_bounds) != self.model.n_items():
            raise ValueError("upper bounds must match the number of items")
