from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Tuple

from optees.domain.value_objects.packing.rotation_policy import RotationPolicy

from .geometry import Dimensions3D, Orientation3D, generate_orientations
from .resource import ResourceConsumption


@dataclass(frozen=True)
class PackingItem:
    item_id: str
    name: str
    dimensions: Dimensions3D
    value: float = 1.0
    quantity: int = 1
    rotation_policy: RotationPolicy = RotationPolicy.ANY_ORTHOGONAL
    custom_orientation_codes: Tuple[str, ...] = ()
    consumptions: Tuple[ResourceConsumption, ...] = ()

    @staticmethod
    def from_parts(
        item_id: str,
        name: str,
        dimensions: Dimensions3D,
        *,
        value: float = 1.0,
        quantity: int = 1,
        rotation_policy: RotationPolicy = RotationPolicy.ANY_ORTHOGONAL,
        custom_orientation_codes: Iterable[str] = (),
        consumptions: Iterable[ResourceConsumption] = (),
    ) -> "PackingItem":
        return PackingItem(
            item_id=item_id,
            name=name,
            dimensions=dimensions,
            value=value,
            quantity=quantity,
            rotation_policy=rotation_policy,
            custom_orientation_codes=tuple(custom_orientation_codes),
            consumptions=tuple(consumptions),
        )

    def __post_init__(self) -> None:
        item_id = str(self.item_id or "").strip()
        name = str(self.name or "").strip()
        if not item_id:
            raise ValueError("item id cannot be empty")
        if not name:
            raise ValueError("item name cannot be empty")
        if isinstance(self.value, bool) or not isfinite(float(self.value)) or float(self.value) < 0:
            raise ValueError("item value must be a finite non-negative number")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("item quantity must be a positive integer")

        policy = (
            self.rotation_policy
            if isinstance(self.rotation_policy, RotationPolicy)
            else RotationPolicy.from_str(self.rotation_policy)
        )
        codes = tuple(str(code).strip().upper() for code in self.custom_orientation_codes)
        if policy is not RotationPolicy.CUSTOM and codes:
            raise ValueError(
                "custom orientation codes are allowed only with the custom rotation policy"
            )
        consumptions = tuple(self.consumptions)
        names = [consumption.name.casefold() for consumption in consumptions]
        if len(names) != len(set(names)):
            raise ValueError("item resource-consumption names must be unique")

        # Validate and normalize the orientation policy at the domain boundary.
        generate_orientations(self.dimensions, policy, codes)
        object.__setattr__(self, "item_id", item_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "value", float(self.value))
        object.__setattr__(self, "rotation_policy", policy)
        object.__setattr__(self, "custom_orientation_codes", codes)
        object.__setattr__(self, "consumptions", consumptions)

    def orientations(self) -> Tuple[Orientation3D, ...]:
        return generate_orientations(
            self.dimensions,
            self.rotation_policy,
            self.custom_orientation_codes,
        )

    def consumption(self, resource_name: str) -> float:
        key = str(resource_name).casefold()
        return next(
            (consumption.amount for consumption in self.consumptions if consumption.name.casefold() == key),
            0.0,
        )
