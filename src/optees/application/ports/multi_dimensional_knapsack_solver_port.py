from __future__ import annotations

from typing import Any, Dict, Protocol


class MultiDimensionalKnapsackSolverPort(Protocol):
    """Abstraction over multi-dimensional knapsack solver implementations."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        problem:
            Canonical multi-dimensional knapsack dict with values,
            usage_matrix, capacities, item names and resource names.

        Returns
        -------
        dict with keys: status, objective, selected_indices, x, extras.
        """
        ...

