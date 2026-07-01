from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

from optees.domain.entities.knapsack.multi_dimensional_item import (
    MultiDimensionalKnapsackItem,
)
from optees.domain.entities.knapsack.multi_dimensional_resource import (
    MultiDimensionalKnapsackResource,
)


def _drop_index[T](seq: Sequence[T], idx: int) -> Tuple[T, ...]:
    return tuple(x for i, x in enumerate(seq) if i != idx)


@dataclass(frozen=True)
class MultiDimensionalKnapsackModel:
    """Aggregate root for a multi-dimensional 0/1 knapsack problem.

    The model maximizes value while respecting several resource capacities:

        max sum_i value_i x_i
        s.t. sum_i usage_{i,r} x_i <= capacity_r    for every resource r
             x_i in {0, 1}

    This is still a 0/1 selection problem, but each selected item consumes a
    vector of resources instead of one scalar weight.
    """

    resources: Tuple[MultiDimensionalKnapsackResource, ...]
    items: Tuple[MultiDimensionalKnapsackItem, ...]

    @staticmethod
    def empty(
        n: int = 0,
        resources: Optional[Iterable[MultiDimensionalKnapsackResource]] = None,
    ) -> "MultiDimensionalKnapsackModel":
        resource_tuple = tuple(resources) if resources is not None else (
            MultiDimensionalKnapsackResource("Resource 1", 0.0),
        )
        items = tuple(
            MultiDimensionalKnapsackItem(
                name=f"Item {i}",
                value=0.0,
                resource_usage=(0.0,) * len(resource_tuple),
            )
            for i in range(1, n + 1)
        )
        return MultiDimensionalKnapsackModel(resources=resource_tuple, items=items)

    @staticmethod
    def from_parts(
        resources: Iterable[MultiDimensionalKnapsackResource],
        items: Iterable[MultiDimensionalKnapsackItem],
    ) -> "MultiDimensionalKnapsackModel":
        return MultiDimensionalKnapsackModel(
            resources=tuple(resources),
            items=tuple(items),
        )

    def __post_init__(self) -> None:
        resources = tuple(self.resources)
        if not resources:
            raise ValueError("multi-dimensional knapsack requires at least one resource")
        _validate_unique_resource_names(resources)

        items = tuple(self.items)
        resource_count = len(resources)
        for item in items:
            if len(item.resource_usage) != resource_count:
                raise ValueError(
                    "item resource usage dimension must match resource count"
                )

        object.__setattr__(self, "resources", resources)
        object.__setattr__(self, "items", items)

    def n_resources(self) -> int:
        return len(self.resources)

    def n_items(self) -> int:
        return len(self.items)

    def resource(self, index: int) -> MultiDimensionalKnapsackResource:
        return self.resources[index]

    def item(self, index: int) -> MultiDimensionalKnapsackItem:
        return self.items[index]

    def resource_names(self) -> Tuple[str, ...]:
        return tuple(resource.name for resource in self.resources)

    def capacities(self) -> Tuple[float, ...]:
        return tuple(resource.capacity for resource in self.resources)

    def item_names(self) -> Tuple[str, ...]:
        return tuple(item.name for item in self.items)

    def values(self) -> Tuple[float, ...]:
        return tuple(item.value for item in self.items)

    def usage_matrix(self) -> Tuple[Tuple[float, ...], ...]:
        return tuple(item.resource_usage for item in self.items)

    def set_resource_name(
        self,
        index: int,
        name: str,
    ) -> "MultiDimensionalKnapsackModel":
        if not (0 <= index < self.n_resources()):
            return self
        resources = list(self.resources)
        resources[index] = resources[index].rename(name)
        return MultiDimensionalKnapsackModel(tuple(resources), self.items)

    def set_resource_capacity(
        self,
        index: int,
        capacity: float,
    ) -> "MultiDimensionalKnapsackModel":
        if not (0 <= index < self.n_resources()):
            return self
        resources = list(self.resources)
        resources[index] = resources[index].with_capacity(capacity)
        return MultiDimensionalKnapsackModel(tuple(resources), self.items)

    def add_resource(
        self,
        resource: Optional[MultiDimensionalKnapsackResource] = None,
    ) -> "MultiDimensionalKnapsackModel":
        new_resource = resource or MultiDimensionalKnapsackResource(
            _next_default_resource_name(self.resources),
            0.0,
        )
        items = tuple(
            item.with_resource_usage(item.resource_usage + (0.0,))
            for item in self.items
        )
        return MultiDimensionalKnapsackModel(
            self.resources + (new_resource,),
            items,
        )

    def remove_resource(self, index: int) -> "MultiDimensionalKnapsackModel":
        if not (0 <= index < self.n_resources()) or self.n_resources() <= 1:
            return self
        resources = _drop_index(self.resources, index)
        items = tuple(
            item.with_resource_usage(_drop_index(item.resource_usage, index))
            for item in self.items
        )
        return MultiDimensionalKnapsackModel(resources, items)

    def add_item(
        self,
        item: Optional[MultiDimensionalKnapsackItem] = None,
    ) -> "MultiDimensionalKnapsackModel":
        new_item = item or MultiDimensionalKnapsackItem(
            _next_default_item_name(self.items),
            0.0,
            (0.0,) * self.n_resources(),
        )
        return MultiDimensionalKnapsackModel(
            self.resources,
            self.items + (new_item,),
        )

    def remove_item(self, index: int) -> "MultiDimensionalKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        return MultiDimensionalKnapsackModel(
            self.resources,
            _drop_index(self.items, index),
        )

    def set_item_name(
        self,
        index: int,
        name: str,
    ) -> "MultiDimensionalKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].rename(name)
        return MultiDimensionalKnapsackModel(self.resources, tuple(items))

    def set_item_value(
        self,
        index: int,
        value: float,
    ) -> "MultiDimensionalKnapsackModel":
        if not (0 <= index < self.n_items()):
            return self
        items = list(self.items)
        items[index] = items[index].with_value(value)
        return MultiDimensionalKnapsackModel(self.resources, tuple(items))

    def set_item_resource_amount(
        self,
        item_index: int,
        resource_index: int,
        amount: float,
    ) -> "MultiDimensionalKnapsackModel":
        if not (0 <= item_index < self.n_items()):
            return self
        items = list(self.items)
        items[item_index] = items[item_index].with_resource_amount(
            resource_index,
            amount,
        )
        return MultiDimensionalKnapsackModel(self.resources, tuple(items))

    def set_item_resource_usage(
        self,
        item_index: int,
        resource_usage: Iterable[float],
    ) -> "MultiDimensionalKnapsackModel":
        if not (0 <= item_index < self.n_items()):
            return self
        items = list(self.items)
        items[item_index] = items[item_index].with_resource_usage(resource_usage)
        return MultiDimensionalKnapsackModel(self.resources, tuple(items))


def _validate_unique_resource_names(
    resources: Sequence[MultiDimensionalKnapsackResource],
) -> None:
    normalized = [resource.name.casefold() for resource in resources]
    if len(normalized) != len(set(normalized)):
        raise ValueError("resource names must be unique")


def _next_default_resource_name(
    resources: Sequence[MultiDimensionalKnapsackResource],
) -> str:
    used = {resource.name for resource in resources}
    i = len(resources) + 1
    while f"Resource {i}" in used:
        i += 1
    return f"Resource {i}"


def _next_default_item_name(items: Sequence[MultiDimensionalKnapsackItem]) -> str:
    used = {item.name for item in items}
    i = len(items) + 1
    while f"Item {i}" in used:
        i += 1
    return f"Item {i}"
