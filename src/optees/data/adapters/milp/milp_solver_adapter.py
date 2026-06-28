from __future__ import annotations
from typing import Any, Dict

from optees.application.ports.milp_solver_port import MILPSolverPort
from optees.utility.milp_utils import solve_milp


class MILPSolverAdapter(MILPSolverPort):
    """Concrete adapter that calls the local OR-Tools based MILP utility."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        time_limit = problem.get("time_limit")
        try:
            status, objective, x_dict, extras = solve_milp(problem, time_limit=time_limit)
            return {
                "status": status,
                "objective": objective,
                "x": x_dict or {},
                "extras": dict(extras or {}),
            }
        except Exception as exc:
            return {
                "status": "NotSolved",
                "objective": None,
                "x": {},
                "extras": {"message": str(exc), "backend": None, "success": False},
            }
