from __future__ import annotations
from typing import Any, Dict, Protocol


class MILPSolverPort(Protocol):
    """Abstraction over MILP solver implementations."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        problem:
            Canonical MILP dict with sense, c, constraints, bounds,
            integrality, variable names, and optional solver options.

        Returns
        -------
        dict with keys: status, objective, x, extras.
        """
        ...
