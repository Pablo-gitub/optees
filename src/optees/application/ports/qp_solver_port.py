from __future__ import annotations

from typing import Any, Dict, Protocol


class QPSolverPort(Protocol):
    """Abstraction over a Continuous Convex Quadratic Programming solver backend."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Solve a canonical QP problem dictionary and return status, objective, values, and diagnostics."""
        ...
