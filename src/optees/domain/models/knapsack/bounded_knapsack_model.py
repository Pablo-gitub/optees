from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

from optees.domain.entities.knapsack.bounded_item import BoundedKnapsackItem


def _drop_index[T](seq: Sequence[T], idx: int) -> Tuple[T, ...]:
    return tuple(x for i, x in enumerate(seq) if i != idx)


@dataclass(frozen=True)
class BoundedKnapsackModel:
    """Aggregate root for a bounded knapsack problem.

    The model maximizes total value under one integer capacity constraint:

        max sum_i value_i x_i
        s.t. sum_i weight_i x_i <= capacity
             x_i in {0, 1, ..., max_quantity_i}

    Compared with 0/1 knapsack, the binary choice is replaced by an integer
    quantity bounded above. The feasible set is still discrete, but each item
    contributes several admissible quantity levels instead of only yes/no.
    """

    capacity: int
    items: Tuple[BoundedKnapsackItem, ...]

    @staticmethod
    def empty(n: int = 0, capacity: int = 0) -> "BoundedKnapsackModel":
        items = tuple(
            BoundedKnapsackItem(name=f"Item {i}", value=0.0, weight=0, max_quantity=1)
            for i in range(1, n + 1)
        )
        return BoundedKnapsackModel(capacity=capacity, items=items)

    @staticmethod
    def from_parts(
        items: Iterable[BoundedKnapsackItem],
        *,
        capacity: int,
    ) -> "BoundedKnapsackModel":
        return BoundedKnapsackModel(capacity=capacity, items=tuple(items))

    def __post_init__(self) -> None:
        object.__setattr__(self, "capacity", _normalize_capacity(self.capacity))
        object.__setattr__(self, "items", tuple(self.items))

    def n_items(self) -> int:
        return len(self.items)

    def item(self, index: int) -> BoundedKnapsackItem:
        return self.items[index]

    def values(self) -> Tuple[float, ...]:
        return tuple(item.value for item in self.items)

    def weights(self) -> Tuple[int, ...]:
        return tuple(item.weight for item in self.items)

    def max_quantities(self) -> Tuple[int, ...]:
        return tuple(item.max_quantity for item in self.items)

    def item_names(self) -> Tuple[str, ...]:
        return tuple(item.name for item in self.items)

    def set_capacity(self, capacity: int) -> "BoundedKnapsackModel":
        return BoundedKnapsackModel(capacity=capacity, items=self.items)

    def add_item(
        self,
        item: Optional[BoundedKnapsackItem] = None,
    ) -> "BoundedKnapsackModel":
        new_item = item or BoundedKnapsackItem(
            _next_default_name(self.items),
            0.0,
            0,
            1,
        )
        return BoundedKnapsackModel(self.capacity, self.items + (new_item,))

    def remove_item(self, index: int) -> "BoundedKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        return BoundedKnapsackModel(self.capacity, _drop_index(self.items, index))

    def set_item_name(self, index: int, name: str) -> "BoundedKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].rename(name)
        return BoundedKnapsackModel(self.capacity, tuple(items))

    def set_item_value(self, index: int, value: float) -> "BoundedKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].with_value(value)
        return BoundedKnapsackModel(self.capacity, tuple(items))

    def set_item_weight(self, index: int, weight: int) -> "BoundedKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].with_weight(weight)
        return BoundedKnapsackModel(self.capacity, tuple(items))

    def set_item_max_quantity(
        self,
        index: int,
        max_quantity: int,
    ) -> "BoundedKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].with_max_quantity(max_quantity)
        return BoundedKnapsackModel(self.capacity, tuple(items))


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


def _next_default_name(items: Sequence[BoundedKnapsackItem]) -> str:
    used = {item.name for item in items}
    i = len(items) + 1
    while f"Item {i}" in used:
        i += 1
    return f"Item {i}"
