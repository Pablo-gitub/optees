from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Tuple

from optees.domain.entities.packing.container import PackingContainer
from optees.domain.entities.packing.item import PackingItem
from optees.domain.value_objects.packing.selection_policy import PackingSelectionPolicy
from optees.domain.value_objects.packing.gravity_mode import PackingGravityMode


@dataclass(frozen=True)
class SingleContainerPackingModel:
    container: PackingContainer
    items: Tuple[PackingItem, ...]
    selection_policy: PackingSelectionPolicy = PackingSelectionPolicy.OPTIONAL
    gravity_mode: PackingGravityMode = PackingGravityMode.SIMPLE
    time_limit: float | None = None
    mip_gap: float | None = None

    @staticmethod
    def from_parts(
        container: PackingContainer,
        items: Iterable[PackingItem],
        *,
        selection_policy: PackingSelectionPolicy = PackingSelectionPolicy.OPTIONAL,
        gravity_mode: PackingGravityMode = PackingGravityMode.SIMPLE,
        time_limit: float | None = None,
        mip_gap: float | None = None,
    ) -> "SingleContainerPackingModel":
        return SingleContainerPackingModel(
            container=container,
            items=tuple(items),
            selection_policy=selection_policy,
            gravity_mode=gravity_mode,
            time_limit=time_limit,
            mip_gap=mip_gap,
        )

    def __post_init__(self) -> None:
        items = tuple(self.items)
        if not items:
            raise ValueError("packing model requires at least one item")
        ids = [item.item_id.casefold() for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("packing item ids must be unique")

        container_resources = {capacity.name.casefold() for capacity in self.container.capacities}
        for item in items:
            unknown = {
                consumption.name
                for consumption in item.consumptions
                if consumption.name.casefold() not in container_resources
            }
            if unknown:
                raise ValueError(
                    f"item {item.item_id!r} uses resources absent from the container: "
                    + ", ".join(sorted(unknown))
                )

        policy = (
            self.selection_policy
            if isinstance(self.selection_policy, PackingSelectionPolicy)
            else PackingSelectionPolicy.from_str(self.selection_policy)
        )
        gravity_mode = (
            self.gravity_mode
            if isinstance(self.gravity_mode, PackingGravityMode)
            else PackingGravityMode.from_str(self.gravity_mode)
        )
        object.__setattr__(self, "items", items)
        object.__setattr__(self, "selection_policy", policy)
        object.__setattr__(self, "gravity_mode", gravity_mode)
        object.__setattr__(self, "time_limit", _optional_positive(self.time_limit, "time limit"))
        object.__setattr__(self, "mip_gap", _optional_gap(self.mip_gap))

    def unit_count(self) -> int:
        return sum(item.quantity for item in self.items)


def _optional_positive(value: object, label: str) -> float | None:
    if value is None:
        return None
    parsed = float(value)
    if not isfinite(parsed) or parsed <= 0:
        raise ValueError(f"{label} must be a finite positive number")
    return parsed


def _optional_gap(value: object) -> float | None:
    if value is None:
        return None
    parsed = float(value)
    if not isfinite(parsed) or not 0 <= parsed < 1:
        raise ValueError("mip gap must be in [0, 1)")
    return parsed
