from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from .geometry import Dimensions3D
from .resource import ResourceCapacity


@dataclass(frozen=True)
class PackingContainer:
    container_id: str
    name: str
    dimensions: Dimensions3D
    capacities: Tuple[ResourceCapacity, ...] = ()

    @staticmethod
    def from_parts(
        container_id: str,
        name: str,
        dimensions: Dimensions3D,
        capacities: Iterable[ResourceCapacity] = (),
    ) -> "PackingContainer":
        return PackingContainer(container_id, name, dimensions, tuple(capacities))

    def __post_init__(self) -> None:
        object.__setattr__(self, "container_id", _required_text(self.container_id, "container id"))
        object.__setattr__(self, "name", _required_text(self.name, "container name"))
        object.__setattr__(self, "capacities", tuple(self.capacities))
        _ensure_unique_names(self.capacities, "container capacity")

    def capacity(self, name: str) -> float | None:
        key = str(name).casefold()
        return next((capacity.limit for capacity in self.capacities if capacity.name.casefold() == key), None)


def _required_text(value: object, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{label} cannot be empty")
    return normalized


def _ensure_unique_names(values: Iterable[ResourceCapacity], label: str) -> None:
    names = [value.name.casefold() for value in values]
    if len(names) != len(set(names)):
        raise ValueError(f"{label} names must be unique")
