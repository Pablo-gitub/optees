from __future__ import annotations
from enum import Enum


class MILPSolveStatus(str, Enum):
    OPTIMAL = "Optimal"
    FEASIBLE = "Feasible"
    INFEASIBLE = "Infeasible"
    UNBOUNDED = "Unbounded"
    NOT_SOLVED = "NotSolved"

    @staticmethod
    def from_str(status: object) -> "MILPSolveStatus":
        try:
            return MILPSolveStatus(str(status))
        except Exception:
            return MILPSolveStatus.NOT_SOLVED
