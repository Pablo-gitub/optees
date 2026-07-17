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
            extras = dict(extras or {})
            if _reached_time_limit(status, time_limit, extras):
                extras["termination_reason"] = "time_limit"
            return {
                "status": status,
                "objective": objective,
                "x": x_dict or {},
                "extras": extras,
            }
        except Exception as exc:
            return {
                "status": "NotSolved",
                "objective": None,
                "x": {},
                "extras": {"message": str(exc), "backend": None, "success": False},
            }


def _reached_time_limit(status: str, time_limit: object, extras: Dict[str, Any]) -> bool:
    if status not in {"Feasible", "NotSolved"} or time_limit is None:
        return False
    elapsed = extras.get("wall_time")
    if elapsed is None and extras.get("wall_time_ms") is not None:
        try:
            elapsed = float(extras["wall_time_ms"]) / 1000.0
        except (TypeError, ValueError, OverflowError):
            return False
    try:
        return float(time_limit) > 0 and float(elapsed) >= float(time_limit) * 0.9
    except (TypeError, ValueError, OverflowError):
        return False
