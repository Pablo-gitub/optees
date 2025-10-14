# src/optees/domain/value_objects/lp/relation.py
from __future__ import annotations
from enum import Enum

class Relation(Enum):
    LE = "<="
    EQ = "="
    GE = ">="

    @staticmethod
    def from_symbol(s: str) -> "Relation":
        s = (s or "").strip()
        if s in ("<=", "≤"):
            return Relation.LE
        if s in ("=", "=="):
            return Relation.EQ
        if s in (">=", "≥"):
            return Relation.GE
        raise ValueError(f"Invalid relation symbol: {s}")

    def symbol(self) -> str:
        return self.value
