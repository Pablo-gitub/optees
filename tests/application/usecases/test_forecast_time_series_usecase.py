from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest

from optees.application.contracts.forecasting import ForecastingAdapterOutput
from optees.application.usecases.forecast_time_series_usecase import (
    ForecastTimeSeriesUseCase,
)
from optees.data.adapters.forecasting import BaselineForecastingAdapter
from optees.domain.entities.forecasting import ForecastDiagnostic, ForecastObservation
from optees.domain.models.forecasting import (
    ForecastingEvaluationOptions,
    ForecastingModel,
)
from optees.domain.value_objects.forecasting import (
    EvaluationStrategy,
    ForecastEvaluationStatus,
    ForecastingFrequency,
    ForecastingMethod,
    ForecastingStatus,
)


def _model(
    values: tuple[float, ...],
    *,
    strategy: EvaluationStrategy,
    horizon: int = 3,
    holdout_size: int = 2,
    origin_count: int = 3,
    step: int = 1,
    evaluation_horizon: int = 2,
) -> ForecastingModel:
    origin = datetime(2026, 1, 1)
    return ForecastingModel(
        target_name="demand",
        observations=tuple(
            ForecastObservation(origin + timedelta(days=index), value)
            for index, value in enumerate(values)
        ),
        method=ForecastingMethod.NAIVE,
        horizon=horizon,
        frequency=ForecastingFrequency.DAILY,
        evaluation=ForecastingEvaluationOptions(
            strategy=strategy,
            holdout_size=holdout_size,
            origin_count=origin_count,
            step=step,
            evaluation_horizon=evaluation_horizon,
            minimum_training_size=2,
        ),
    )


def _use_case() -> ForecastTimeSeriesUseCase:
    return ForecastTimeSeriesUseCase(
        {ForecastingMethod.NAIVE: BaselineForecastingAdapter()}
    )


def test_execute_separates_holdout_evaluation_from_final_forecast() -> None:
    model = _model((10, 12, 14, 16), strategy=EvaluationStrategy.HOLDOUT)

    solution = _use_case().execute(model)

    assert solution.status is ForecastingStatus.FORECASTED
    assert solution.evaluation_status is ForecastEvaluationStatus.EVALUATED
    assert len(solution.evaluation_folds) == 1
    fold = solution.evaluation_folds[0]
    assert fold.training_size == 2
    assert tuple(point.predicted for point in fold.points) == (12.0, 12.0)
    assert solution.metrics.mae == pytest.approx(3.0)
    assert solution.metrics.rmse == pytest.approx(math.sqrt(10))
    assert solution.metrics.mape == pytest.approx(19.642857142857142)
    assert solution.metrics.mase == pytest.approx(1.5)
    assert tuple(point.predicted for point in solution.points[-3:]) == (
        16.0,
        16.0,
        16.0,
    )
    assert all(point.timestamp > model.forecast_origin for point in solution.points[-3:])


def test_rolling_origin_preserves_overlapping_targets_in_separate_folds() -> None:
    model = _model(
        (1, 2, 3, 4, 5, 6, 7, 8),
        strategy=EvaluationStrategy.ROLLING_ORIGIN,
    )

    evaluation = _use_case().evaluate(model)

    assert evaluation.status is ForecastEvaluationStatus.EVALUATED
    assert tuple(fold.training_size for fold in evaluation.folds) == (4, 5, 6)
    assert tuple(
        tuple(point.actual for point in fold.points) for fold in evaluation.folds
    ) == ((5.0, 6.0), (6.0, 7.0), (7.0, 8.0))
    assert evaluation.folds[0].points[1].timestamp == evaluation.folds[1].points[0].timestamp
    assert evaluation.metrics.mae == pytest.approx(1.5)
    assert evaluation.metrics.rmse == pytest.approx(math.sqrt(2.5))
    assert evaluation.metrics.mase == pytest.approx(1.5)


def test_no_evaluation_still_returns_fitted_and_future_segments() -> None:
    model = _model((3, 5, 8), strategy=EvaluationStrategy.NONE, horizon=2)

    solution = _use_case().execute(model)

    assert solution.evaluation_status is ForecastEvaluationStatus.NOT_REQUESTED
    assert solution.evaluation_folds == ()
    assert solution.metrics.mae is None
    assert tuple(point.predicted for point in solution.points) == (3.0, 5.0, 8.0, 8.0)


def test_execute_returns_cancelled_before_final_fit() -> None:
    model = _model((10, 12, 14, 16), strategy=EvaluationStrategy.HOLDOUT)

    solution = _use_case().execute(model, cancel_requested=lambda: True)

    assert solution.status is ForecastingStatus.CANCELLED
    assert solution.points == ()
    assert {diagnostic.code for diagnostic in solution.diagnostics} == {
        "forecast_evaluation_cancelled",
        "forecast_cancelled",
    }


def test_failed_evaluation_keeps_valid_final_forecast_as_partial() -> None:
    class FailsFirstAdapter:
        calls = 0

        def fit_and_predict(
            self,
            model: ForecastingModel,
            training_observations: tuple[ForecastObservation, ...],
            prediction_timestamps: tuple[datetime, ...],
        ) -> ForecastingAdapterOutput:
            self.calls += 1
            if self.calls == 1:
                return ForecastingAdapterOutput(
                    status=ForecastingStatus.FAILED,
                    predicted_values=(),
                    diagnostics=(
                        ForecastDiagnostic(
                            code="test_failure",
                            message="Evaluation failed.",
                            severity="error",
                        ),
                    ),
                )
            return ForecastingAdapterOutput(
                status=ForecastingStatus.FORECASTED,
                predicted_values=(training_observations[-1].value,)
                * len(prediction_timestamps),
                fitted_values=(None,)
                + tuple(item.value for item in training_observations[:-1]),
            )

    model = _model((10, 12, 14, 16), strategy=EvaluationStrategy.HOLDOUT)
    use_case = ForecastTimeSeriesUseCase(
        {ForecastingMethod.NAIVE: FailsFirstAdapter()}
    )

    solution = use_case.execute(model)

    assert solution.status is ForecastingStatus.PARTIAL
    assert solution.evaluation_status is ForecastEvaluationStatus.FAILED
    assert len(solution.points) == 6


def test_unregistered_method_is_rejected_explicitly() -> None:
    model = _model((10, 12, 14), strategy=EvaluationStrategy.NONE)

    with pytest.raises(ValueError, match="No forecasting solver"):
        ForecastTimeSeriesUseCase({}).forecast_future(model)
