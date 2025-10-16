# src/optees/domain/value_objects/lp/solve_status.py
from __future__ import annotations
from enum import Enum

class SolveStatus(str, Enum):
    OPTIMAL = "Optimal"
    INFEASIBLE = "Infeasible"
    UNBOUNDED = "Unbounded"
    NOT_SOLVED = "NotSolved"

    @staticmethod
    def from_str(s: str) -> "SolveStatus":
        try:
            return SolveStatus(s)
        except Exception:
            return SolveStatus.NOT_SOLVED
