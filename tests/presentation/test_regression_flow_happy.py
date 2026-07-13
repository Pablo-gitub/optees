from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton

from _utils.fakes import FakeSolver
from optees.application.usecases.train_regression_usecase import TrainRegressionUseCase
from optees.core.string_manager import strings as S
from optees.domain.entities.regression.dataset import RegressionDataset
from optees.domain.models.regression.regression_model import RegressionModel, RegressionOptions
from optees.domain.value_objects.regression.regression_status import RegressionStatus


def _model() -> RegressionModel:
    return RegressionModel(
        RegressionDataset.from_rows(
            feature_names=("size",),
            target_name="price",
            rows=[
                ((1,), 3),
                ((2,), 5),
                ((3,), 7),
                ((4,), 9),
                ((5,), 11),
                ((6,), 13),
            ],
        ),
        RegressionOptions(test_fraction=1 / 3, random_seed=7),
    )


def _trained_response() -> dict[str, object]:
    return {
        "status": "Trained",
        "intercept": 1.0,
        "coefficients": {"size": 2.0},
        "train_metrics": {"mae": 0.0, "mse": 0.0, "rmse": 0.0, "r_squared": 1.0},
        "test_metrics": {"mae": 0.0, "mse": 0.0, "rmse": 0.0, "r_squared": 1.0},
        "predictions": [
            {
                "row_index": index,
                "actual": 3.0 + 2.0 * index,
                "predicted": 3.0 + 2.0 * index,
                "residual": 0.0,
                "partition": "test" if index in {1, 4} else "train",
            }
            for index in range(6)
        ],
        "extras": {"method": "OLS", "train_count": 4, "test_count": 2, "random_seed": 7},
    }


def test_home_card_opens_regression_page(window, qtbot) -> None:
    assert window.home_page.card_regression.parentWidget() is window.home_page.cat_ml

    qtbot.mouseClick(window.home_page.card_regression, Qt.LeftButton)

    assert window.stack.currentWidget() is window.regression_page


def test_regression_form_trains_and_navigates_to_solution(window, qtbot) -> None:
    fake = FakeSolver(_trained_response())
    window.regression_page.set_model(_model())
    window.regression_page.set_solve_usecase(TrainRegressionUseCase(fake))
    window.goto("regression")

    with qtbot.waitSignal(window.regression_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.regression_page.btn_train, Qt.LeftButton)

    solution = blocker.args[0]
    assert solution.status is RegressionStatus.TRAINED
    assert fake.last_problem == {
        "feature_names": ["size"],
        "target_name": "price",
        "feature_rows": [[1.0], [2.0], [3.0], [4.0], [5.0], [6.0]],
        "target_values": [3.0, 5.0, 7.0, 9.0, 11.0, 13.0],
        "method": "OLS",
        "test_fraction": pytest.approx(1 / 3),
        "random_seed": 7,
        "ridge_alpha": 1.0,
    }
    assert window.stack.currentWidget() is window.regression_solution_page
    assert window.regression_solution_page.coefficient_table.rowCount() == 1
    assert window.regression_solution_page.metrics_table.rowCount() == 2
    assert window.regression_solution_page.predictions_table.rowCount() == 6
    assert window.regression_solution_page.predictions_table.item(0, 2).textAlignment() == int(Qt.AlignCenter)
    assert window.regression_solution_page.fit_plot.visualization_state == "ready"


def test_regression_json_import_populates_schema_table_and_options(window, qtbot, monkeypatch, tmp_path) -> None:
    data = {
        "version": "1",
        "problem_type": "regression",
        "dataset": {
            "feature_names": ["area", "rooms"],
            "target_name": "price",
            "rows": [
                {"features": [40, 1], "target": 100},
                {"features": [50, 2], "target": 130},
                {"features": [60, 2], "target": 150},
                {"features": [70, 3], "target": 180},
            ],
        },
        "training_options": {
            "method": "Ridge",
            "test_fraction": 0.5,
            "random_seed": 11,
            "ridge_alpha": 2.0,
        },
    }
    path = tmp_path / "regression.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        "optees.presentation.views.regression_view.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(path), ""),
    )
    window.goto("regression")

    qtbot.mouseClick(window.regression_page.btn_import_json, Qt.LeftButton)

    assert window.regression_page.findChild(QLineEdit, "regressionFeatureNames").text() == "area, rooms"
    assert window.regression_page.findChild(QLineEdit, "regressionTargetName").text() == "price"
    assert window.regression_page.data_table.columnCount() == 3
    assert window.regression_page.data_table.rowCount() == 4
    assert window.regression_page.data_table.item(0, 0).text() == "40"
    assert window.regression_page.data_table.item(0, 2).text() == "100"
    method = window.regression_page.findChild(QComboBox, "regressionMethod")
    assert method is not None and method.currentData() == "Ridge"
    assert window.regression_page.findChild(QLineEdit, "regressionRandomSeed").text() == "11"


def test_regression_pages_and_controls_are_localized(window, qtbot) -> None:
    window.goto("regression")

    assert window.regression_page.findChild(QPushButton, "regressionImportJsonButton").text()
    assert window.regression_page.findChild(QPushButton, "regressionTrainButton").text()
    assert window.regression_page.btn_json_info.property("variant") == "info"
    assert window.regression_page.btn_json_info.text() == "i"

    qtbot.mouseClick(window.regression_page.btn_example, Qt.LeftButton)
    assert window.stack.currentWidget() is window.regression_example_page
    window.goto("regression")
    qtbot.mouseClick(window.regression_page.btn_problem, Qt.LeftButton)
    assert window.stack.currentWidget() is window.regression_problem_page


@pytest.mark.parametrize("language", ["en", "it"])
def test_regression_view_retranslates_in_each_supported_language(window, language: str) -> None:
    previous = S.current_language()
    try:
        S.set_language(language)
        assert window.regression_page.btn_train.text() == S.t("regression.actions.train")
        assert window.regression_page.btn_import_json.text() == S.t("regression.import.button")
        assert "regression." not in window.regression_page.title.text()
    finally:
        S.set_language(previous)
