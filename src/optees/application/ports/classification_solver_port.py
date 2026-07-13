from __future__ import annotations

from typing import Any, Dict, Protocol


class ClassificationSolverPort(Protocol):
    """Boundary for a local binary-classification implementation."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Train an estimator and return normalized diagnostics."""
        ...
