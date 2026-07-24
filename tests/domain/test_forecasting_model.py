from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from optees.domain.entities.forecasting import ForecastObservation
from optees.domain.models.forecasting import (
    ForecastingEvaluationOptions,
    ForecastingMethodOptions,
    ForecastingModel,
)
from optees.domain.value_objects.forecasting import (
    EvaluationStrategy,
    ForecastingFrequency,
    ForecastingMethod,
)


def _daily_observations(count: int = 6) -> tuple[ForecastObservation, ...]:
    origin = datetime(2026, 1, 1)
    return tuple(
        ForecastObservation(origin + timedelta(days=index), index + 1)
        for index in range(count)
    )


def test_model_normalizes_options_and_builds_future_timestamps() -> None:
    model = ForecastingModel(
        target_name=" demand ",
        observations=_daily_observations(),
        method="naive",  # type: ignore[arg-type]
        horizon=3,
        frequency="daily",  # type: ignore[arg-type]
        evaluation=ForecastingEvaluationOptions(strategy="holdout", holdout_size=2),  # type: ignore[arg-type]
        method_options=ForecastingMethodOptions(max_iterations=50, tolerance=1e-6),
    )

    assert model.target_name == "demand"
    assert model.method is ForecastingMethod.NAIVE
    assert model.frequency is ForecastingFrequency.DAILY
    assert model.future_timestamps() == (
        datetime(2026, 1, 7),
        datetime(2026, 1, 8),
        datetime(2026, 1, 9),
    )


def test_observation_normalizes_aware_timestamps_to_utc() -> None:
    observation = ForecastObservation(
        datetime(2026, 1, 1, 12, tzinfo=timezone(timedelta(hours=2))),
        4,
    )

    assert observation.timestamp == datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    assert observation.value == 4.0


def test_calendar_frequency_preserves_original_anchor() -> None:
    origin = datetime(2025, 1, 30)

    assert ForecastingFrequency.MONTHLY.advance(origin, 1) == datetime(2025, 2, 28)
    assert ForecastingFrequency.MONTHLY.advance(origin, 2) == datetime(2025, 3, 30)


@pytest.mark.parametrize(
    ("observations", "message"),
    [
        (
            (
                ForecastObservation(datetime(2026, 1, 1), 1),
                ForecastObservation(datetime(2026, 1, 1), 2),
            ),
            "strictly increasing",
        ),
        (
            (
                ForecastObservation(datetime(2026, 1, 1), 1),
                ForecastObservation(datetime(2026, 1, 3), 2),
            ),
            "missing or off-frequency",
        ),
        (
            (
                ForecastObservation(datetime(2026, 1, 1), 1),
                ForecastObservation(datetime(2026, 1, 2, tzinfo=timezone.utc), 2),
            ),
            "mix timezone",
        ),
    ],
)
def test_model_rejects_invalid_timestamp_sequences(
    observations: tuple[ForecastObservation, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ForecastingModel(
            "demand",
            observations,
            ForecastingMethod.NAIVE,
            1,
            ForecastingFrequency.DAILY,
            evaluation=ForecastingEvaluationOptions(strategy=EvaluationStrategy.NONE),
        )

def test_seasonal_model_requires_two_complete_seasons() -> None:
    with pytest.raises(ValueError, match="two complete seasons"):
        ForecastingModel(
            "demand",
            _daily_observations(5),
            ForecastingMethod.SEASONAL_NAIVE,
            1,
            ForecastingFrequency.DAILY,
            season_length=3,
            evaluation=ForecastingEvaluationOptions(strategy=EvaluationStrategy.NONE),
        )


def test_holdout_cannot_remove_required_seasonal_training_history() -> None:
    with pytest.raises(ValueError, match="insufficient training history"):
        ForecastingModel(
            "demand",
            _daily_observations(8),
            ForecastingMethod.SEASONAL_NAIVE,
            1,
            ForecastingFrequency.DAILY,
            season_length=3,
            evaluation=ForecastingEvaluationOptions(holdout_size=3),
        )


def test_rolling_origin_is_bounded_by_available_history() -> None:
    with pytest.raises(ValueError, match="requires more historical"):
        ForecastingModel(
            "demand",
            _daily_observations(6),
            ForecastingMethod.NAIVE,
            1,
            ForecastingFrequency.DAILY,
            evaluation=ForecastingEvaluationOptions(
                strategy=EvaluationStrategy.ROLLING_ORIGIN,
                origin_count=4,
                evaluation_horizon=2,
                minimum_training_size=2,
            ),
        )


@pytest.mark.parametrize("value", [True, 0, -1, 10_001])
def test_horizon_is_bounded(value: object) -> None:
    with pytest.raises(ValueError, match="horizon"):
        ForecastingModel(
            "demand",
            _daily_observations(),
            ForecastingMethod.NAIVE,
            value,  # type: ignore[arg-type]
            ForecastingFrequency.DAILY,
            evaluation=ForecastingEvaluationOptions(strategy=EvaluationStrategy.NONE),
        )
