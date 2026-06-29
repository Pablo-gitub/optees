from __future__ import annotations

from enum import Enum


class KnapsackSolveStatus(str, Enum):
    OPTIMAL = "Optimal"
    FEASIBLE = "Feasible"
    INFEASIBLE = "Infeasible"
    NOT_SOLVED = "NotSolved"

    @staticmethod
    def from_str(value: object) -> "KnapsackSolveStatus":
        try:
            return KnapsackSolveStatus(str(value))
        except Exception:
            return KnapsackSolveStatus.NOT_SOLVED

