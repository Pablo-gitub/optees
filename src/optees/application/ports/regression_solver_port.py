from __future__ import annotations

from typing import Any, Dict, Protocol


class RegressionSolverPort(Protocol):
    """Boundary for a local supervised-regression implementation."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Fit the requested estimator and return normalized diagnostics."""
        ...
