from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.nlp_solver_port import NLPSolverPort
from optees.utility.nlp_utils import solve_nlp


class ScipyNLPSolverAdapter(NLPSolverPort):
    """Adapter that exposes the local SciPy NLP utility through the port."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        try:
            status, objective, values, extras = solve_nlp(problem)
            return {
                "status": status,
                "objective": objective,
                "x": values or {},
                "extras": dict(extras or {}),
            }
        except Exception as exc:
            return {
                "status": "Failed",
                "objective": None,
                "x": {},
                "extras": {"message": str(exc), "success": False},
            }
