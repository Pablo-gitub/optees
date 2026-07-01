from __future__ import annotations

from typing import Any, Dict, Protocol


class BoundedKnapsackSolverPort(Protocol):
    """Abstraction over bounded knapsack solver implementations."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        problem:
            Canonical bounded knapsack dict with values, weights,
            max_quantities, capacity and item names.

        Returns
        -------
        dict with keys: status, objective, quantities, x, extras.
        """
        ...
