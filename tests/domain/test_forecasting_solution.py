from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from optees.domain.entities.forecasting import (
    ForecastMetricSet,
    ForecastPoint,
    ForecastSegment,
    ForecastingSolution,
    PredictionInterval,
)
from optees.domain.value_objects.forecasting import ForecastingMethod, ForecastingStatus


def test_solution_keeps_validated_points_metrics_and_parameters() -> None:
    timestamp = datetime(2026, 1, 1)
    solution = ForecastingSolution(
        status=ForecastingStatus.FORECASTED,
        method=ForecastingMethod.NAIVE,
        origin=timestamp,
        points=(
            ForecastPoint(
                timestamp,
                predicted=8,
                actual=10,
                residual=2,
                segment=ForecastSegment.HOLDOUT,
            ),
        ),
        metrics=ForecastMetricSet(mae=2, rmse=2),
        parameters=(("last_value", 8),),
    )

    assert solution.points[0].predicted == 8.0
    assert solution.metrics.mae == 2.0
    assert solution.parameters == (("last_value", 8.0),)


def test_future_point_rejects_actual_values() -> None:
    with pytest.raises(ValueError, match="Future"):
        ForecastPoint(
            datetime(2026, 1, 1),
            predicted=8,
            actual=10,
            residual=2,
            segment=ForecastSegment.FUTURE,
        )


def test_point_rejects_inconsistent_residual() -> None:
    with pytest.raises(ValueError, match="residual"):
        ForecastPoint(
            datetime(2026, 1, 1),
            predicted=8,
            actual=10,
            residual=3,
            segment=ForecastSegment.FITTED,
        )


@pytest.mark.parametrize(
    "interval",
    [
        {"lower": 2, "upper": 1, "coverage": 0.95},
        {"lower": 1, "upper": 2, "coverage": 0},
        {"lower": 1, "upper": 2, "coverage": 1},
    ],
)
def test_prediction_interval_rejects_invalid_ranges(interval: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        PredictionInterval(**interval)


def test_metrics_reject_negative_or_non_finite_values() -> None:
    with pytest.raises(ValueError):
        ForecastMetricSet(mae=-1)
    with pytest.raises(ValueError):
        ForecastMetricSet(rmse=float("nan"))


def test_solution_rejects_future_point_at_or_before_origin() -> None:
    origin = datetime(2026, 1, 2)

    with pytest.raises(ValueError, match="after the forecast origin"):
        ForecastingSolution(
            status=ForecastingStatus.FORECASTED,
            method=ForecastingMethod.NAIVE,
            origin=origin,
            points=(ForecastPoint(origin, 8, ForecastSegment.FUTURE),),
        )


def test_solution_rejects_mixed_timestamp_awareness() -> None:
    with pytest.raises(ValueError, match="mix aware and naive"):
        ForecastingSolution(
            status=ForecastingStatus.FORECASTED,
            method=ForecastingMethod.NAIVE,
            origin=datetime(2026, 1, 1, tzinfo=timezone.utc),
            points=(
                ForecastPoint(
                    datetime(2026, 1, 2),
                    8,
                    ForecastSegment.FUTURE,
                ),
            ),
        )


def test_solution_rejects_non_increasing_timestamps() -> None:
    origin = datetime(2026, 1, 1)

    with pytest.raises(ValueError, match="strictly increasing"):
        ForecastingSolution(
            status=ForecastingStatus.FORECASTED,
            method=ForecastingMethod.NAIVE,
            origin=origin,
            points=(
                ForecastPoint(origin + timedelta(days=2), 8, ForecastSegment.FUTURE),
                ForecastPoint(origin + timedelta(days=1), 8, ForecastSegment.FUTURE),
            ),
        )
