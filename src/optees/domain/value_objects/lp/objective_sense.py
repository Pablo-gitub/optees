# src/optees/domain/value_objects/lp/objective_sense.py
from __future__ import annotations
from enum import Enum

class ObjectiveSense(Enum):
    MIN = "min"
    MAX = "max"

    @staticmethod
    def from_str(s: str) -> "ObjectiveSense":
        s = (s or "").strip().lower()
        if s == "min":
            return ObjectiveSense.MIN
        if s == "max":
            return ObjectiveSense.MAX
        raise ValueError(f"Invalid objective sense: {s}")

    def is_min(self) -> bool: return self is ObjectiveSense.MIN
    def is_max(self) -> bool: return self is ObjectiveSense.MAX
