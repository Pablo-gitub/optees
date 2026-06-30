from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

from optees.domain.entities.knapsack.unbounded_item import UnboundedKnapsackItem


def _drop_index[T](seq: Sequence[T], idx: int) -> Tuple[T, ...]:
    return tuple(x for i, x in enumerate(seq) if i != idx)


@dataclass(frozen=True)
class UnboundedKnapsackModel:
    """Aggregate root for an unbounded knapsack problem.

    The model maximizes total value under one integer capacity constraint:

        max sum_i value_i x_i
        s.t. sum_i weight_i x_i <= capacity
             x_i in {0, 1, 2, ...}

    Unlike 0/1 knapsack, an item can be selected repeatedly. Unlike bounded
    knapsack, there is no per-item maximum quantity; the capacity alone limits
    feasible quantities.
    """

    capacity: int
    items: Tuple[UnboundedKnapsackItem, ...]

    @staticmethod
    def empty(n: int = 0, capacity: int = 0) -> "UnboundedKnapsackModel":
        items = tuple(
            UnboundedKnapsackItem(name=f"Item {i}", value=0.0, weight=0)
            for i in range(1, n + 1)
        )
        return UnboundedKnapsackModel(capacity=capacity, items=items)

    @staticmethod
    def from_parts(
        items: Iterable[UnboundedKnapsackItem],
        *,
        capacity: int,
    ) -> "UnboundedKnapsackModel":
        return UnboundedKnapsackModel(capacity=capacity, items=tuple(items))

    def __post_init__(self) -> None:
        object.__setattr__(self, "capacity", _normalize_capacity(self.capacity))
        object.__setattr__(self, "items", tuple(self.items))

    def n_items(self) -> int:
        return len(self.items)

    def item(self, index: int) -> UnboundedKnapsackItem:
        return self.items[index]

    def values(self) -> Tuple[float, ...]:
        return tuple(item.value for item in self.items)

    def weights(self) -> Tuple[int, ...]:
        return tuple(item.weight for item in self.items)

    def item_names(self) -> Tuple[str, ...]:
        return tuple(item.name for item in self.items)

    def set_capacity(self, capacity: int) -> "UnboundedKnapsackModel":
        return UnboundedKnapsackModel(capacity=capacity, items=self.items)

    def add_item(
        self,
        item: Optional[UnboundedKnapsackItem] = None,
    ) -> "UnboundedKnapsackModel":
        new_item = item or UnboundedKnapsackItem(
            _next_default_name(self.items),
            0.0,
            0,
        )
        return UnboundedKnapsackModel(self.capacity, self.items + (new_item,))

    def remove_item(self, index: int) -> "UnboundedKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        return UnboundedKnapsackModel(self.capacity, _drop_index(self.items, index))

    def set_item_name(self, index: int, name: str) -> "UnboundedKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].rename(name)
        return UnboundedKnapsackModel(self.capacity, tuple(items))

    def set_item_value(self, index: int, value: float) -> "UnboundedKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].with_value(value)
        return UnboundedKnapsackModel(self.capacity, tuple(items))

    def set_item_weight(self, index: int, weight: int) -> "UnboundedKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].with_weight(weight)
        return UnboundedKnapsackModel(self.capacity, tuple(items))


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


def _next_default_name(items: Sequence[UnboundedKnapsackItem]) -> str:
    used = {item.name for item in items}
    i = len(items) + 1
    while f"Item {i}" in used:
        i += 1
    return f"Item {i}"
