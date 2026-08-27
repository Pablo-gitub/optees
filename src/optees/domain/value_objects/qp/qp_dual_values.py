from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class QPDualValues:
    constraints: Tuple[float, ...] = ()
    lower_bounds: Tuple[float, ...] = ()
    upper_bounds: Tuple[float, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> QPDualValues:
        return cls(
            constraints=tuple(float(v) for v in data.get("constraints", ()) or ()),
            lower_bounds=tuple(float(v) for v in data.get("lower_bounds", ()) or ()),
            upper_bounds=tuple(float(v) for v in data.get("upper_bounds", ()) or ()),
        )
