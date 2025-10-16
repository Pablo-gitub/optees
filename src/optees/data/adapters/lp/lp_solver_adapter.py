# src/optees/data/adapters/lp/lp_solver_adapter.py
from __future__ import annotations
from typing import Dict, Any
from optees.application.ports.lp_solver_port import LPSolverPort

# importa la tua utility (aggiusta il path se diverso)
from optees.utility.lp_utils import solve_lp  # solve_lp(problem, method="highs") -> (status, obj, x, extras)

class LPSolverAdapter(LPSolverPort):
    """Concrete adapter that calls the local utility-based LP solver."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expects a canonical problem dict (sense, c, A_ub, b_ub, A_eq, b_eq, bounds, var_names, obj_offset)
        and an optional "method" key (e.g., "highs", "highs-ipm", "highs-ds").
        Returns a dict {status, objective, x, extras} matching the Port contract.
        """
        method = problem.get("method", "highs")
        try:
            status, objective, x_dict, extras = solve_lp(problem, method=method)
            # normalize output dict
            extras = dict(extras or {})
            extras.setdefault("method", method)
            return {
                "status": status,
                "objective": objective,
                "x": x_dict or {},
                "extras": extras,
            }
        except Exception as e:
            # fallback robusto: mappa l'errore in un risultato NotSolved
            return {
                "status": "NotSolved",
                "objective": None,
                "x": {},
                "extras": {"message": str(e), "method": method, "success": False},
            }
