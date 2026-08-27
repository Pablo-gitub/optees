from __future__ import annotations

from enum import Enum


class QPSolveStatus(str, Enum):
    OPTIMAL = "Optimal"
    FEASIBLE = "Feasible"
    INFEASIBLE = "Infeasible"
    UNBOUNDED = "Unbounded"
    NOT_SOLVED = "NotSolved"

    @staticmethod
    def from_str(s: str) -> QPSolveStatus:
        try:
            return QPSolveStatus(s)
        except Exception:
            return QPSolveStatus.NOT_SOLVED
