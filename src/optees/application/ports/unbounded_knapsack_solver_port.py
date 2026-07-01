from __future__ import annotations

from typing import Any, Dict, Protocol


class UnboundedKnapsackSolverPort(Protocol):
    """Abstraction over unbounded knapsack solver implementations."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        problem:
            Canonical unbounded knapsack dict with values, weights, capacity
            and item names.

        Returns
        -------
        dict with keys: status, objective, quantities, x, extras.
        """
        ...

