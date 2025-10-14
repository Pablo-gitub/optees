# src/optees/domain/value_objects/lp/bounds.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Bounds:
    """Closed interval [lb, ub] with None meaning -inf/+inf respectively."""
    lb: Optional[float] = 0.0
    ub: Optional[float] = None

    def __post_init__(self):
        # Validate lb <= ub when both finite
        if (self.lb is not None) and (self.ub is not None) and (self.lb > self.ub):
            raise ValueError(f"Invalid bounds: lb({self.lb}) > ub({self.ub})")

    def is_unbounded_below(self) -> bool: return self.lb is None
    def is_unbounded_above(self) -> bool: return self.ub is None

    def contains(self, x: float) -> bool:
        if (self.lb is not None) and (x < self.lb): return False
        if (self.ub is not None) and (x > self.ub): return False
        return True

    def with_lb(self, new_lb: Optional[float]) -> "Bounds":
        return Bounds(new_lb, self.ub)

    def with_ub(self, new_ub: Optional[float]) -> "Bounds":
        return Bounds(self.lb, new_ub)
