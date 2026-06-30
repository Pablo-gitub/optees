from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class UnboundedKnapsackItem:
    """Item for an unbounded knapsack model.

    The decision variable associated with this item is an integer quantity:

        x_i in {0, 1, 2, ...}

    There is no item-specific upper bound; capacity is the only limit on how
    many copies can be selected.
    """

    name: str
    value: float
    weight: int

    def __post_init__(self) -> None:
        name = str(self.name or "").strip()
        if not name:
            raise ValueError("item name cannot be empty")

        try:
            value = float(self.value)
        except (TypeError, ValueError) as exc:
            raise ValueError("item value must be a finite non-negative number") from exc
        if not isfinite(value) or value < 0:
            raise ValueError("item value must be a finite non-negative number")

        weight = _normalize_non_negative_int(self.weight, "item weight")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "weight", weight)

    def rename(self, new_name: str) -> "UnboundedKnapsackItem":
        return UnboundedKnapsackItem(new_name, self.value, self.weight)

    def with_value(self, value: float) -> "UnboundedKnapsackItem":
        return UnboundedKnapsackItem(self.name, value, self.weight)

    def with_weight(self, weight: int) -> "UnboundedKnapsackItem":
        return UnboundedKnapsackItem(self.name, self.value, weight)


def _normalize_non_negative_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a non-negative integer")
    if isinstance(value, int):
        normalized = value
    elif isinstance(value, float) and value.is_integer():
        normalized = int(value)
    else:
        raise ValueError(f"{label} must be a non-negative integer")

    if normalized < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return normalized
