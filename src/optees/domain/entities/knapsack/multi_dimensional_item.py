from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Tuple


@dataclass(frozen=True)
class MultiDimensionalKnapsackItem:
    """Item for a multi-dimensional 0/1 knapsack model.

    The decision variable is binary:

        x_i in {0, 1}

    If selected, the item consumes one non-negative amount in every resource
    dimension. The model aggregate validates that each item's vector length
    matches the resource list.
    """

    name: str
    value: float
    resource_usage: Tuple[float, ...]

    def __init__(self, name: str, value: float, resource_usage: Iterable[float]):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "resource_usage", tuple(resource_usage))
        self.__post_init__()

    def __post_init__(self) -> None:
        name = str(self.name or "").strip()
        if not name:
            raise ValueError("item name cannot be empty")

        value = _normalize_non_negative_finite(self.value, "item value")
        resource_usage = tuple(
            _normalize_non_negative_finite(amount, "item resource usage")
            for amount in self.resource_usage
        )
        if not resource_usage:
            raise ValueError("item resource usage cannot be empty")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "resource_usage", resource_usage)

    def rename(self, new_name: str) -> "MultiDimensionalKnapsackItem":
        return MultiDimensionalKnapsackItem(new_name, self.value, self.resource_usage)

    def with_value(self, value: float) -> "MultiDimensionalKnapsackItem":
        return MultiDimensionalKnapsackItem(self.name, value, self.resource_usage)

    def with_resource_usage(
        self,
        resource_usage: Iterable[float],
    ) -> "MultiDimensionalKnapsackItem":
        return MultiDimensionalKnapsackItem(self.name, self.value, tuple(resource_usage))

    def with_resource_amount(
        self,
        index: int,
        amount: float,
    ) -> "MultiDimensionalKnapsackItem":
        if not (0 <= index < len(self.resource_usage)):
            return self
        usage = list(self.resource_usage)
        usage[index] = amount
        return self.with_resource_usage(usage)


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
