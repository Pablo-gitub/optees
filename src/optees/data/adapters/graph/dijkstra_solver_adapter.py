from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.shortest_path_solver_port import ShortestPathSolverPort
from optees.utility.graph_utils import solve_dijkstra


class DijkstraSolverAdapter(ShortestPathSolverPort):
    """Expose the local deterministic Dijkstra implementation through a port."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        try:
            status, distance, path, extras = solve_dijkstra(problem)
            return {
                "status": status,
                "distance": distance,
                "path": path,
                "extras": extras,
            }
        except Exception as exc:
            return {
                "status": "NotSolved",
                "distance": None,
                "path": (),
                "extras": {"message": str(exc)},
            }
