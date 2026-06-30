from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

from optees.domain.entities.knapsack.item import KnapsackItem


def _drop_index[T](seq: Sequence[T], idx: int) -> Tuple[T, ...]:
    return tuple(x for i, x in enumerate(seq) if i != idx)


@dataclass(frozen=True)
class Knapsack01Model:
    """Aggregate root for a 0/1 knapsack problem.

    Each item can be selected once or excluded. The objective is to maximize the
    total selected value without exceeding the integer capacity:

        max sum_i value_i x_i
        s.t. sum_i weight_i x_i <= capacity
             x_i in {0, 1}

    The dynamic-programming solver used in the first implementation requires
    integer weights and integer capacity, so the domain validates them here.
    """

    capacity: int
    items: Tuple[KnapsackItem, ...]

    @staticmethod
    def empty(n: int = 0, capacity: int = 0) -> "Knapsack01Model":
        items = tuple(
            KnapsackItem(name=f"Item {i}", value=0.0, weight=0)
            for i in range(1, n + 1)
        )
        return Knapsack01Model(capacity=capacity, items=items)

    @staticmethod
    def from_parts(
        items: Iterable[KnapsackItem],
        *,
        capacity: int,
    ) -> "Knapsack01Model":
        return Knapsack01Model(capacity=capacity, items=tuple(items))

    def __post_init__(self) -> None:
        object.__setattr__(self, "capacity", _normalize_capacity(self.capacity))
        object.__setattr__(self, "items", tuple(self.items))

    def n_items(self) -> int:
        return len(self.items)

    def item(self, index: int) -> KnapsackItem:
        return self.items[index]

    def values(self) -> Tuple[float, ...]:
        return tuple(item.value for item in self.items)

    def weights(self) -> Tuple[int, ...]:
        return tuple(item.weight for item in self.items)

    def item_names(self) -> Tuple[str, ...]:
        return tuple(item.name for item in self.items)

    def set_capacity(self, capacity: int) -> "Knapsack01Model":
        return Knapsack01Model(capacity=capacity, items=self.items)

    def add_item(self, item: Optional[KnapsackItem] = None) -> "Knapsack01Model":
        new_item = item or KnapsackItem(_next_default_name(self.items), 0.0, 0)
        return Knapsack01Model(self.capacity, self.items + (new_item,))

    def remove_item(self, index: int) -> "Knapsack01Model":
        if not (0 <= index < self.n_items()):
            return self
        return Knapsack01Model(self.capacity, _drop_index(self.items, index))

    def set_item_name(self, index: int, name: str) -> "Knapsack01Model":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].rename(name)
        return Knapsack01Model(self.capacity, tuple(items))

    def set_item_value(self, index: int, value: float) -> "Knapsack01Model":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].with_value(value)
        return Knapsack01Model(self.capacity, tuple(items))

    def set_item_weight(self, index: int, weight: int) -> "Knapsack01Model":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].with_weight(weight)
        return Knapsack01Model(self.capacity, tuple(items))


def _normalize_capacity(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("capacity must be a non-negative integer")
    if isinstance(value, int):
        normalized = value
    elif isinstance(value, float) and value.is_integer():
        normalized = int(value)
    else:
        raise ValueError("capacity must be a non-negative integer")

    if normalized < 0:
        raise ValueError("capacity must be a non-negative integer")
    return normalized


def _next_default_name(items: Sequence[KnapsackItem]) -> str:
    used = {item.name for item in items}
    i = len(items) + 1
    while f"Item {i}" in used:
        i += 1
    return f"Item {i}"
