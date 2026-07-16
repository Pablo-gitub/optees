from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from math import isfinite
from typing import Iterable, Tuple

from optees.domain.value_objects.packing.rotation_policy import RotationPolicy


@dataclass(frozen=True)
class Dimensions3D:
    length: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = tuple(_positive_finite(value, label) for value, label in zip(
            (self.length, self.width, self.height),
            ("length", "width", "height"),
        ))
        object.__setattr__(self, "length", values[0])
        object.__setattr__(self, "width", values[1])
        object.__setattr__(self, "height", values[2])

    def as_tuple(self) -> Tuple[float, float, float]:
        return self.length, self.width, self.height

    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass(frozen=True)
class Orientation3D:
    code: str
    dimensions: Dimensions3D

    def __post_init__(self) -> None:
        code = str(self.code or "").strip().upper()
        if sorted(code) != ["H", "L", "W"]:
            raise ValueError("orientation code must be a permutation of 'LWH'")
        object.__setattr__(self, "code", code)


_POLICY_CODES = {
    RotationPolicy.FIXED: ("LWH",),
    RotationPolicy.KEEP_UPRIGHT: ("LWH", "WLH"),
    RotationPolicy.X_ONLY: ("LWH", "LHW"),
    RotationPolicy.Y_ONLY: ("LWH", "HWL"),
    RotationPolicy.Z_ONLY: ("LWH", "WLH"),
    RotationPolicy.ANY_ORTHOGONAL: tuple("".join(parts) for parts in permutations("LWH")),
}


def generate_orientations(
    dimensions: Dimensions3D,
    policy: RotationPolicy,
    custom_codes: Iterable[str] = (),
) -> Tuple[Orientation3D, ...]:
    """Return unique axis-aligned orientations in deterministic order.

    Geometrically identical dimension triples are collapsed. This is correct
    for the initial homogeneous-cuboid model, where faces have no labels or
    face-specific physical properties.
    """

    if policy is RotationPolicy.CUSTOM:
        codes = tuple(str(code).strip().upper() for code in custom_codes)
        if not codes:
            raise ValueError("custom rotation policy requires at least one orientation")
    else:
        codes = _POLICY_CODES[policy]

    axis_values = {
        "L": dimensions.length,
        "W": dimensions.width,
        "H": dimensions.height,
    }
    orientations = []
    seen_dimensions = set()
    for code in codes:
        if sorted(code) != ["H", "L", "W"]:
            raise ValueError(f"invalid orientation code: {code!r}")
        oriented_tuple = tuple(axis_values[axis] for axis in code)
        if oriented_tuple in seen_dimensions:
            continue
        seen_dimensions.add(oriented_tuple)
        orientations.append(
            Orientation3D(code=code, dimensions=Dimensions3D(*oriented_tuple))
        )
    return tuple(orientations)


def _positive_finite(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite positive number")
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite positive number") from exc
    if not isfinite(parsed) or parsed <= 0:
        raise ValueError(f"{label} must be a finite positive number")
    return parsed
