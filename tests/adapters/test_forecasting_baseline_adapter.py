from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from optees.data.adapters.forecasting import BaselineForecastingAdapter
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


def _observations(values: tuple[float, ...]) -> tuple[ForecastObservation, ...]:
    origin = datetime(2026, 1, 1)
    return tuple(
        ForecastObservation(origin + timedelta(days=index), value)
        for index, value in enumerate(values)
    )


def _model(
    values: tuple[float, ...],
    method: ForecastingMethod,
    *,
    season_length: int | None = None,
) -> ForecastingModel:
    return ForecastingModel(
        target_name="demand",
        observations=_observations(values),
        method=method,
        horizon=4,
        frequency=ForecastingFrequency.DAILY,
        season_length=season_length,
        evaluation=ForecastingEvaluationOptions(strategy=EvaluationStrategy.NONE),
    )


def test_naive_repeats_latest_training_value_without_future_leakage() -> None:
    model = _model((10, 12, 99, 101), ForecastingMethod.NAIVE)
    training = model.observations[:2]
    timestamps = tuple(item.timestamp for item in model.observations[2:])

    output = BaselineForecastingAdapter().fit_and_predict(model, training, timestamps)

    assert output.status is ForecastingStatus.FORECASTED
    assert output.predicted_values == (12.0, 12.0)
    assert output.parameters == (("last_value", 12.0),)


def test_seasonal_naive_repeats_latest_complete_training_season() -> None:
    model = _model(
        (5, 7, 9, 6, 8, 10),
        ForecastingMethod.SEASONAL_NAIVE,
        season_length=3,
    )
    timestamps = model.future_timestamps()

    output = BaselineForecastingAdapter().fit_and_predict(
        model,
        model.observations,
        timestamps,
    )

    assert output.predicted_values == (6.0, 8.0, 10.0, 6.0)
    assert output.parameters == (("season_length", 3.0),)


def test_adapter_rejects_non_prefix_training_history() -> None:
    model = _model((10, 12, 14), ForecastingMethod.NAIVE)

    with pytest.raises(ValueError, match="exact model-history prefix"):
        BaselineForecastingAdapter().fit_and_predict(
            model,
            model.observations[1:],
            (datetime(2026, 1, 4),),
        )


def test_adapter_rejects_off_frequency_prediction_timestamps() -> None:
    model = _model((10, 12, 14), ForecastingMethod.NAIVE)

    with pytest.raises(ValueError, match="immediately follow"):
        BaselineForecastingAdapter().fit_and_predict(
            model,
            model.observations,
            (datetime(2026, 1, 5),),
        )


def test_seasonal_adapter_rejects_training_with_only_one_season() -> None:
    model = _model(
        (5, 7, 9, 6, 8, 10),
        ForecastingMethod.SEASONAL_NAIVE,
        season_length=3,
    )

    with pytest.raises(ValueError, match="two complete seasons"):
        BaselineForecastingAdapter().fit_and_predict(
            model,
            model.observations[:3],
            tuple(item.timestamp for item in model.observations[3:]),
        )


def test_baseline_adapter_rejects_holt_winters() -> None:
    model = _model(
        (5, 7, 9, 6, 8, 10),
        ForecastingMethod.HOLT_WINTERS_ADDITIVE,
        season_length=3,
    )

    with pytest.raises(ValueError, match="Unsupported baseline"):
        BaselineForecastingAdapter().fit_and_predict(
            model,
            model.observations,
            model.future_timestamps(),
        )
