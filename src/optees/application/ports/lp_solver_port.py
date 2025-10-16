# src/optees/application/ports/lp_solver_port.py
from __future__ import annotations
from typing import Protocol, Dict, Any

class LPSolverPort(Protocol):
    """Abstraction over any LP solver implementation."""
    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        problem: canonical LP dict

        Returns
        -------
        dict with keys:
          - status: str ("Optimal" | "Infeasible" | "Unbounded" | "NotSolved")
          - objective: float | None
          - x: dict[str, float]            # var -> value
          - extras: dict                   # diagnostics (method, nit, message, ...)
        """
        ... 
