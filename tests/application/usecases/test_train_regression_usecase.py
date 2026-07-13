from __future__ import annotations

from typing import Any, Dict

from optees.application.usecases.train_regression_usecase import TrainRegressionUseCase
from optees.domain.entities.regression.dataset import RegressionDataset
from optees.domain.models.regression.regression_model import RegressionModel, RegressionOptions
from optees.domain.value_objects.regression.regression_method import RegressionMethod
from optees.domain.value_objects.regression.regression_status import RegressionStatus


class FakeRegressionSolver:
    def __init__(self, response: Dict[str, Any]) -> None:
        self.response = response
        self.calls: list[Dict[str, Any]] = []

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append(problem)
        return self.response


def test_use_case_maps_model_and_normalizes_the_solver_result() -> None:
    dataset = RegressionDataset.from_rows(
        feature_names=("size",),
        target_name="price",
        rows=[((1,), 3), ((2,), 5), ((3,), 7), ((4,), 9)],
    )
    solver = FakeRegressionSolver(
        {
            "status": "Trained",
            "intercept": 1.0,
            "coefficients": {"size": 2.0},
            "train_metrics": {"mae": 0, "mse": 0, "rmse": 0, "r_squared": 1},
            "test_metrics": {"mae": 0.5, "mse": 0.25, "rmse": 0.5, "r_squared": 0.8},
            "predictions": [
                {"row_index": 0, "actual": 3, "predicted": 3, "residual": 0, "partition": "train"}
            ],
            "extras": {"method": "OLS"},
        }
    )
    model = RegressionModel(
        dataset,
        RegressionOptions(RegressionMethod.OLS, test_fraction=0.5, random_seed=9),
    )

    result = TrainRegressionUseCase(solver).execute(model)

    assert solver.calls == [
        {
            "feature_names": ["size"],
            "target_name": "price",
            "feature_rows": [[1.0], [2.0], [3.0], [4.0]],
            "target_values": [3.0, 5.0, 7.0, 9.0],
            "method": "OLS",
            "test_fraction": 0.5,
            "random_seed": 9,
            "ridge_alpha": 1.0,
        }
    ]
    assert result.status is RegressionStatus.TRAINED
    assert result.coefficients == {"size": 2.0}
    assert result.test_metrics.r_squared == 0.8
    assert result.predictions[0].partition == "train"
