from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Optional, Sequence, Tuple

from optees.domain.entities.knapsack.fractional_item import FractionalKnapsackItem


def _drop_index[T](seq: Sequence[T], idx: int) -> Tuple[T, ...]:
    return tuple(x for i, x in enumerate(seq) if i != idx)


@dataclass(frozen=True)
class FractionalKnapsackModel:
    """Aggregate root for a fractional knapsack problem.

    The model maximizes total value under one continuous capacity constraint:

        max sum_i value_i x_i
        s.t. sum_i weight_i x_i <= capacity
             0 <= x_i <= 1

    Unlike 0/1, bounded, and unbounded knapsack, the decision variables are
    continuous fractions. This makes the classic single-capacity fractional
    problem solvable by sorting items by value/weight ratio and filling
    capacity greedily.
    """

    capacity: float
    items: Tuple[FractionalKnapsackItem, ...]

    @staticmethod
    def empty(n: int = 0, capacity: float = 0.0) -> "FractionalKnapsackModel":
        items = tuple(
            FractionalKnapsackItem(name=f"Item {i}", value=0.0, weight=1.0)
            for i in range(1, n + 1)
        )
        return FractionalKnapsackModel(capacity=capacity, items=items)

    @staticmethod
    def from_parts(
        items: Iterable[FractionalKnapsackItem],
        *,
        capacity: float,
    ) -> "FractionalKnapsackModel":
        return FractionalKnapsackModel(capacity=capacity, items=tuple(items))

    def __post_init__(self) -> None:
        object.__setattr__(self, "capacity", _normalize_capacity(self.capacity))
        object.__setattr__(self, "items", tuple(self.items))

    def n_items(self) -> int:
        return len(self.items)

    def item(self, index: int) -> FractionalKnapsackItem:
        return self.items[index]

    def values(self) -> Tuple[float, ...]:
        return tuple(item.value for item in self.items)

    def weights(self) -> Tuple[float, ...]:
        return tuple(item.weight for item in self.items)

    def value_densities(self) -> Tuple[float, ...]:
        return tuple(item.value_density for item in self.items)

    def item_names(self) -> Tuple[str, ...]:
        return tuple(item.name for item in self.items)

    def set_capacity(self, capacity: float) -> "FractionalKnapsackModel":
        return FractionalKnapsackModel(capacity=capacity, items=self.items)

    def add_item(
        self,
        item: Optional[FractionalKnapsackItem] = None,
    ) -> "FractionalKnapsackModel":
        new_item = item or FractionalKnapsackItem(
            _next_default_name(self.items),
            0.0,
            1.0,
        )
        return FractionalKnapsackModel(self.capacity, self.items + (new_item,))

    def remove_item(self, index: int) -> "FractionalKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        return FractionalKnapsackModel(self.capacity, _drop_index(self.items, index))

    def set_item_name(self, index: int, name: str) -> "FractionalKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].rename(name)
        return FractionalKnapsackModel(self.capacity, tuple(items))

    def set_item_value(self, index: int, value: float) -> "FractionalKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].with_value(value)
        return FractionalKnapsackModel(self.capacity, tuple(items))

    def set_item_weight(self, index: int, weight: float) -> "FractionalKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].with_weight(weight)
        return FractionalKnapsackModel(self.capacity, tuple(items))


def _normalize_capacity(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("capacity must be a finite non-negative number")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError("capacity must be a finite non-negative number") from exc

    if not isfinite(normalized) or normalized < 0:
        raise ValueError("capacity must be a finite non-negative number")
    return normalized


def _next_default_name(items: Sequence[FractionalKnapsackItem]) -> str:
    used = {item.name for item in items}
    i = len(items) + 1
    while f"Item {i}" in used:
        i += 1
    return f"Item {i}"
