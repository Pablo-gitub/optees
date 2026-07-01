from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class MultiDimensionalKnapsackResource:
    """Capacity dimension for a multi-dimensional knapsack model."""

    name: str
    capacity: float

    def __post_init__(self) -> None:
        name = str(self.name or "").strip()
        if not name:
            raise ValueError("resource name cannot be empty")

        capacity = _normalize_non_negative_finite(self.capacity, "resource capacity")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "capacity", capacity)

    def rename(self, new_name: str) -> "MultiDimensionalKnapsackResource":
        return MultiDimensionalKnapsackResource(new_name, self.capacity)

    def with_capacity(self, capacity: float) -> "MultiDimensionalKnapsackResource":
        return MultiDimensionalKnapsackResource(self.name, capacity)


def _normalize_non_negative_finite(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite non-negative number")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite non-negative number") from exc
    if not isfinite(normalized) or normalized < 0:
        raise ValueError(f"{label} must be a finite non-negative number")
    return normalized
