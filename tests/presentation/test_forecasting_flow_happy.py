from __future__ import annotations

from datetime import datetime

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt

from optees.domain.entities.forecasting import ForecastObservation
from optees.domain.models.forecasting import (
    ForecastingEvaluationOptions,
    ForecastingModel,
)
from optees.domain.value_objects.forecasting import (
    EvaluationStrategy,
    ForecastingFrequency,
    ForecastingMethod,
    ForecastingStatus,
)


def _model() -> ForecastingModel:
    return ForecastingModel(
        target_name="monthly demand",
        observations=tuple(
            ForecastObservation(datetime(2024, month, 1), value)
            for month, value in enumerate((10, 12, 11, 14, 15), start=1)
        ),
        method=ForecastingMethod.NAIVE,
        horizon=2,
        frequency=ForecastingFrequency.MONTHLY,
        evaluation=ForecastingEvaluationOptions(
            strategy=EvaluationStrategy.HOLDOUT,
            holdout_size=1,
            minimum_training_size=2,
        ),
    )


def test_home_card_opens_forecasting_page(window, qtbot) -> None:
    assert window.home_page.card_forecasting.parentWidget() is window.home_page.cat_ml

    qtbot.mouseClick(window.home_page.card_forecasting, Qt.LeftButton)

    assert window.stack.currentWidget() is window.forecasting_page


def test_forecasting_form_solves_and_navigates_to_solution(window, qtbot) -> None:
    window.forecasting_page.set_model(_model())
    window.goto("forecasting")

    with qtbot.waitSignal(window.forecasting_page.solve_completed, timeout=2000) as blocker:
        qtbot.mouseClick(window.forecasting_page.btn_forecast, Qt.LeftButton)

    solution = blocker.args[0]
    assert solution.status is ForecastingStatus.FORECASTED
    assert window.stack.currentWidget() is window.forecasting_solution_page
    assert window.forecasting_solution_page.metrics_table.rowCount() >= 1
    assert window.forecasting_solution_page.parameters_table.rowCount() == 1
    assert window.forecasting_solution_page.points_table.rowCount() >= 2
    assert window.forecasting_solution_page.chart.visualization_state == "ready"


def test_forecasting_target_name_is_required(window) -> None:
    window.forecasting_page.set_model(_model())
    window.forecasting_page.edit_target.clear()

    with pytest.raises(ValueError, match="target name"):
        window.forecasting_page.current_model()
