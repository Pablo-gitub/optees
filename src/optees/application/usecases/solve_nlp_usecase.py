from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.nlp_solver_port import NLPSolverPort
from optees.domain.entities.nlp.solution import NLPSolution
from optees.domain.models.nlp.nlp_model import NLPModel


class SolveNLPUseCase:
    """Map an NLPModel to the canonical solver contract and back to a result."""

    def __init__(self, solver_port: NLPSolverPort):
        self._solver = solver_port

    def execute(self, model: NLPModel) -> NLPSolution:
        raw = self._solver.solve(self._map_model_to_problem(model))
        return NLPSolution.from_solver_result(
            status=raw.get("status", "NotSolved"),
            objective=raw.get("objective"),
            values=raw.get("x", {}),
            extras=raw.get("extras", {}),
        )

    def _map_model_to_problem(self, model: NLPModel) -> Dict[str, Any]:
        return {
            "sense": model.objective.sense.value,
            "expression": model.objective.expression,
            "variables": list(model.variable_names()),
            "initial_point": list(model.initial_point()),
            "bounds": list(model.bounds()),
            "method": model.options.method.value,
            "max_iterations": model.options.max_iterations,
            "tolerance": model.options.tolerance,
        }
