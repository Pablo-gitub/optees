from __future__ import annotations

from typing import Any, Dict, Protocol


class FractionalKnapsackSolverPort(Protocol):
    """Abstraction over fractional knapsack solver implementations."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        problem:
            Canonical fractional knapsack dict with values, weights, capacity
            and item names.

        Returns
        -------
        dict with keys: status, objective, fractions, x, extras.
        """
        ...

