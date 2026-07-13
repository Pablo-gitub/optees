from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.classification_solver_port import ClassificationSolverPort
from optees.domain.entities.classification.solution import ClassificationSolution
from optees.domain.models.classification.binary_classification_model import BinaryClassificationModel


class TrainClassificationUseCase:
    """Map a binary-classification formulation onto a local solver port."""

    def __init__(self, solver_port: ClassificationSolverPort):
        self._solver = solver_port

    def execute(self, model: BinaryClassificationModel) -> ClassificationSolution:
        return ClassificationSolution.from_solver_result(
            self._solver.solve(self._map_model_to_problem(model))
        )

    @staticmethod
    def _map_model_to_problem(model: BinaryClassificationModel) -> Dict[str, Any]:
        return {
            "feature_names": list(model.dataset.feature_names),
            "target_name": model.dataset.target_name,
            "feature_rows": [list(row) for row in model.dataset.feature_rows],
            "target_values": list(model.dataset.target_values),
            "method": model.options.method.value,
            "test_fraction": model.options.test_fraction,
            "random_seed": model.options.random_seed,
            "learning_rate": model.options.learning_rate,
            "max_iterations": model.options.max_iterations,
            "l2_alpha": model.options.l2_alpha,
        }
