from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.regression_solver_port import RegressionSolverPort
from optees.domain.entities.regression.solution import RegressionSolution
from optees.domain.models.regression.regression_model import RegressionModel


class TrainRegressionUseCase:
    """Map a regression formulation to the local solver boundary."""

    def __init__(self, solver_port: RegressionSolverPort):
        self._solver = solver_port

    def execute(self, model: RegressionModel) -> RegressionSolution:
        return RegressionSolution.from_solver_result(
            self._solver.solve(self._map_model_to_problem(model))
        )

    @staticmethod
    def _map_model_to_problem(model: RegressionModel) -> Dict[str, Any]:
        return {
            "feature_names": list(model.dataset.feature_names),
            "target_name": model.dataset.target_name,
            "feature_rows": [list(row) for row in model.dataset.feature_rows],
            "target_values": list(model.dataset.target_values),
            "method": model.options.method.value,
            "test_fraction": model.options.test_fraction,
            "random_seed": model.options.random_seed,
            "ridge_alpha": model.options.ridge_alpha,
        }
