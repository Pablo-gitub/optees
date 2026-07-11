from __future__ import annotations

from enum import Enum


class NLPSolveStatus(str, Enum):
    CONVERGED = "Converged"
    ITERATION_LIMIT = "IterationLimit"
    FAILED = "Failed"
    NOT_SOLVED = "NotSolved"

    @classmethod
    def from_str(cls, value: object) -> "NLPSolveStatus":
        aliases = {
            "success": cls.CONVERGED,
            "converged": cls.CONVERGED,
            "iterationlimit": cls.ITERATION_LIMIT,
            "iteration_limit": cls.ITERATION_LIMIT,
            "failed": cls.FAILED,
            "notsolved": cls.NOT_SOLVED,
            "not_solved": cls.NOT_SOLVED,
        }
        normalized = str(value or "").replace(" ", "").lower()
        return aliases.get(normalized, cls.NOT_SOLVED)
