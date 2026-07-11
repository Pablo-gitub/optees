from __future__ import annotations

from typing import Any, Dict, Protocol


class NLPSolverPort(Protocol):
    """Abstraction over a continuous nonlinear-programming solver."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Return status, objective, x mapping, and numerical diagnostics."""
        ...
