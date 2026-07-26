from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from optees.core.string_manager import strings as S
from optees.domain.entities.forecasting import (
    ForecastObservation,
    ForecastPoint,
    ForecastSegment,
)
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


def test_forecasting_json_import_populates_form(window, qtbot, monkeypatch) -> None:
    fixture = Path("tests/data/forecasting/reference_cases.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))[0]["problem"]
    path = fixture.parent / "_forecasting_import_test.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        "optees.presentation.views.forecasting_view.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(path), ""),
    )
    try:
        qtbot.mouseClick(window.forecasting_page.btn_import_json, Qt.LeftButton)
        model = window.forecasting_page.current_model()
    finally:
        path.unlink(missing_ok=True)

    assert model.target_name == payload["target_name"]
    assert model.method.value == payload["method"]
    assert len(model.observations) == len(payload["observations"])


def test_forecasting_invalid_form_shows_local_error(window, qtbot, monkeypatch) -> None:
    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda _parent, title, body: messages.append((title, body)),
    )
    window.forecasting_page.set_model(_model())
    window.forecasting_page.edit_target.clear()

    qtbot.mouseClick(window.forecasting_page.btn_forecast, Qt.LeftButton)

    assert messages
    assert messages[0][0] == S.t("forecasting.validation.title")


def test_forecasting_educational_and_info_navigation(window, qtbot, monkeypatch) -> None:
    shown: list[bool] = []
    monkeypatch.setattr(
        "optees.presentation.views.forecasting_view._InfoDialog.exec",
        lambda _dialog: shown.append(True),
    )
    window.goto("forecasting")

    qtbot.mouseClick(window.forecasting_page.btn_json_info, Qt.LeftButton)
    assert shown
    qtbot.mouseClick(window.forecasting_page.btn_example, Qt.LeftButton)
    assert window.stack.currentWidget() is window.forecasting_example_page
    assert len(window.forecasting_example_page.browser.toPlainText()) > 500
    window.goto("forecasting")
    qtbot.mouseClick(window.forecasting_page.btn_problem, Qt.LeftButton)
    assert window.stack.currentWidget() is window.forecasting_problem_page
    assert window.forecasting_problem_page.browser.toPlainText().strip()


@pytest.mark.parametrize("language", ["en", "it"])
def test_forecasting_controls_retranslate_and_info_buttons_remain_visible(
    window,
    language: str,
) -> None:
    previous = S.current_language()
    try:
        S.set_language(language)
        window.forecasting_page.resize(1100, 760)
        assert window.forecasting_page.btn_forecast.text() == S.t(
            "forecasting.actions.forecast"
        )
        for button in (
            window.forecasting_page.btn_json_info,
            window.forecasting_page.btn_series_info,
            window.forecasting_page.btn_config_info,
        ):
            assert button.text() == "i"
            assert button.isVisibleTo(window.forecasting_page)
            assert button.width() > 0
    finally:
        S.set_language(previous)


@pytest.mark.parametrize(
    ("language", "series_terms", "config_terms"),
    [
        (
            "en",
            ("Series name", "Start date", "Timestamp", "Value", "Paste"),
            ("Method", "Horizon", "Frequency", "Season length", "Evaluation"),
        ),
        (
            "it",
            ("Nome serie", "Data iniziale", "Timestamp", "Valore", "Incolla"),
            ("Metodo", "Orizzonte", "Frequenza", "Lunghezza stagione", "Valutazione"),
        ),
    ],
)
def test_forecasting_section_info_explains_each_input_group(
    language: str,
    series_terms: tuple[str, ...],
    config_terms: tuple[str, ...],
) -> None:
    previous = S.current_language()
    try:
        S.set_language(language)
        series_info = S.t("forecasting.series.info_html")
        config_info = S.t("forecasting.config.info_html")

        assert all(term in series_info for term in series_terms)
        assert all(term in config_info for term in config_terms)
        assert "two complete seasons" in config_info or "due stagioni complete" in config_info
    finally:
        S.set_language(previous)


def test_forecasting_chart_bounds_long_history_sampling() -> None:
    from optees.presentation.views.forecasting_solution_view import _sample

    values = tuple(range(10_000))
    sampled = _sample(values, 500)

    assert len(sampled) <= 500
    assert sampled[0] == values[0]
    assert sampled[-1] == values[-1]


def test_future_plot_starts_from_last_observed_value() -> None:
    from optees.presentation.views.forecasting_solution_view import (
        _future_plot_series,
    )

    actual = (
        ForecastObservation(datetime(2025, 11, 1), 203),
        ForecastObservation(datetime(2025, 12, 1), 212),
    )
    future = (
        ForecastPoint(
            timestamp=datetime(2026, 1, 1),
            predicted=212,
            segment=ForecastSegment.FUTURE,
        ),
        ForecastPoint(
            timestamp=datetime(2026, 2, 1),
            predicted=212,
            segment=ForecastSegment.FUTURE,
        ),
    )

    timestamps, values = _future_plot_series(actual, future)

    assert timestamps == (
        datetime(2025, 12, 1),
        datetime(2026, 1, 1),
        datetime(2026, 2, 1),
    )
    assert values == (212, 212, 212)
