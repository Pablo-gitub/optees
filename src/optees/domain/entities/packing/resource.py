from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ResourceCapacity:
    name: str
    limit: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _name(self.name))
        object.__setattr__(self, "limit", _non_negative(self.limit, "resource capacity"))


@dataclass(frozen=True)
class ResourceConsumption:
    name: str
    amount: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _name(self.name))
        object.__setattr__(self, "amount", _non_negative(self.amount, "resource consumption"))


def _name(value: object) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("resource name cannot be empty")
    return normalized


def _non_negative(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite non-negative number")
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite non-negative number") from exc
    if not isfinite(parsed) or parsed < 0:
        raise ValueError(f"{label} must be a finite non-negative number")
    return parsed
