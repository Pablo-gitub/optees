from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class FractionalKnapsackItem:
    """Item for a fractional knapsack model.

    The decision variable associated with this item is a selected fraction:

        0 <= x_i <= 1

    A value of 1 means the whole item is selected, 0.35 means 35% of the item
    is selected, and 0 means the item is excluded. Positive finite weight is
    required so the greedy value/weight ordering is mathematically defined.
    """

    name: str
    value: float
    weight: float

    def __post_init__(self) -> None:
        name = str(self.name or "").strip()
        if not name:
            raise ValueError("item name cannot be empty")

        value = _normalize_non_negative_finite(self.value, "item value")
        weight = _normalize_positive_finite(self.weight, "item weight")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "weight", weight)

    @property
    def value_density(self) -> float:
        return self.value / self.weight

    def rename(self, new_name: str) -> "FractionalKnapsackItem":
        return FractionalKnapsackItem(new_name, self.value, self.weight)

    def with_value(self, value: float) -> "FractionalKnapsackItem":
        return FractionalKnapsackItem(self.name, value, self.weight)

    def with_weight(self, weight: float) -> "FractionalKnapsackItem":
        return FractionalKnapsackItem(self.name, self.value, weight)


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


def _normalize_positive_finite(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite positive number")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite positive number") from exc
    if not isfinite(normalized) or normalized <= 0:
        raise ValueError(f"{label} must be a finite positive number")
    return normalized
