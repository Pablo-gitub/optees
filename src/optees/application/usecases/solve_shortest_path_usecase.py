from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.shortest_path_solver_port import ShortestPathSolverPort
from optees.domain.entities.graph.solution import ShortestPathSolution
from optees.domain.models.graph.shortest_path_model import ShortestPathModel


class SolveShortestPathUseCase:
    """Map the graph domain model to Dijkstra's canonical solver payload."""

    def __init__(self, solver_port: ShortestPathSolverPort) -> None:
        self._solver = solver_port

    def execute(self, model: ShortestPathModel) -> ShortestPathSolution:
        raw = self._solver.solve(self._map_model_to_problem(model))
        return ShortestPathSolution.from_solver_result(
            status=raw.get("status", "NotSolved"),
            distance=raw.get("distance"),
            path=raw.get("path", ()),
            extras=raw.get("extras", {}),
        )

    @staticmethod
    def _map_model_to_problem(model: ShortestPathModel) -> Dict[str, Any]:
        return {
            "vertices": [vertex.identifier for vertex in model.vertices],
            "edges": [
                {"source": edge.source, "target": edge.target, "weight": edge.weight}
                for edge in model.edges
            ],
            "source": model.source,
            "destination": model.destination,
            "directed": model.directed,
        }
