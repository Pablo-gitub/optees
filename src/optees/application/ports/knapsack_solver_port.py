from __future__ import annotations

from typing import Any, Dict, Protocol


class KnapsackSolverPort(Protocol):
    """Abstraction over 0/1 knapsack solver implementations."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        problem:
            Canonical knapsack dict with values, weights, capacity and item names.

        Returns
        -------
        dict with keys: status, objective, selected_indices, x, extras.
        """
        ...

