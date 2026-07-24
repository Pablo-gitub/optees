from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from optees.application.codecs.forecasting_problem_codec import (
    forecasting_model_from_public_dict,
)
from optees.application.codecs.forecasting_result_codec import ForecastingResultCodec
from optees.application.contracts.execution import (
    MathematicalStatus,
    TerminationReason,
)
from optees.application.usecases.forecast_time_series_usecase import (
    ForecastTimeSeriesUseCase,
)
from optees.data.adapters.forecasting import BaselineForecastingAdapter
from optees.domain.value_objects.forecasting import (
    EvaluationStrategy,
    ForecastingFrequency,
    ForecastingMethod,
)


def _payload() -> dict[str, object]:
    return {
        "version": "1",
        "problem_type": "univariate_forecasting",
        "target_name": "demand",
        "frequency": "daily",
        "horizon": 2,
        "method": "naive",
        "missing_period_policy": "reject",
        "observations": [
            {"timestamp": f"2026-01-0{index + 1}T00:00:00", "value": value}
            for index, value in enumerate((10, 12, 14, 16))
        ],
        "evaluation": {
            "strategy": "holdout",
            "holdout_size": 1,
            "origin_count": 3,
            "step": 1,
            "evaluation_horizon": 1,
            "minimum_training_size": 2,
        },
        "method_options": {
            "max_iterations": 500,
            "tolerance": 1e-7,
        },
    }


def test_problem_codec_parses_complete_versioned_payload() -> None:
    model = forecasting_model_from_public_dict(_payload())  # type: ignore[arg-type]

    assert model.target_name == "demand"
    assert model.method is ForecastingMethod.NAIVE
    assert model.frequency is ForecastingFrequency.DAILY
    assert model.evaluation.strategy is EvaluationStrategy.HOLDOUT
    assert model.horizon == 2
    assert model.observations[-1].value == 16
    assert model.method_options.max_iterations == 500


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        (lambda payload: payload.update({"surprise": True}), "forecast.unknown_field"),
        (lambda payload: payload.update({"version": "2"}), "forecast.unsupported_version"),
        (
            lambda payload: payload["observations"][0].update({"extra": 1}),
            "forecast.unknown_field",
        ),
        (
            lambda payload: payload["observations"][0].update({"timestamp": "not-a-date"}),
            "forecast.invalid_timestamp",
        ),
        (
            lambda payload: payload["evaluation"].update({"random_split": True}),
            "forecast.unknown_field",
        ),
        (
            lambda payload: payload.update({"frequency": "day"}),
            "forecast.invalid_value",
        ),
        (
            lambda payload: payload.update({"method": "seasonal-naive"}),
            "forecast.invalid_value",
        ),
    ],
)
def test_problem_codec_rejects_invalid_or_unknown_fields(
    mutation,
    error_code: str,
) -> None:
    payload = _payload()
    mutation(payload)

    with pytest.raises(ValueError, match=error_code):
        forecasting_model_from_public_dict(payload)  # type: ignore[arg-type]


def test_result_codec_serializes_public_forecast_contract() -> None:
    model = forecasting_model_from_public_dict(_payload())  # type: ignore[arg-type]
    solution = ForecastTimeSeriesUseCase(
        {ForecastingMethod.NAIVE: BaselineForecastingAdapter()}
    ).execute(model)

    serialized = ForecastingResultCodec().serialize(solution)

    assert serialized.mathematical_status is MathematicalStatus.FEASIBLE
    assert serialized.termination_reason is TerminationReason.COMPLETED
    assert serialized.result["forecast_available"] is True
    assert serialized.result["method"] == "naive"
    assert serialized.result["origin"] == "2026-01-04T00:00:00"
    points = serialized.result["points"]
    assert isinstance(points, list)
    assert points[-1] == {
        "timestamp": "2026-01-06T00:00:00",
        "actual": None,
        "predicted": 16.0,
        "residual": None,
        "interval": None,
        "segment": "future",
    }
    evaluation = serialized.result["evaluation"]
    assert isinstance(evaluation, dict)
    assert evaluation["status"] == "evaluated"


def test_result_codec_preserves_timezone_normalization() -> None:
    payload = _payload()
    payload["observations"] = [
        {
            "timestamp": (
                datetime(2026, 1, 1) + timedelta(days=index)
            ).isoformat() + "+01:00",
            "value": value,
        }
        for index, value in enumerate((10, 12, 14, 16))
    ]
    model = forecasting_model_from_public_dict(payload)  # type: ignore[arg-type]
    solution = ForecastTimeSeriesUseCase(
        {ForecastingMethod.NAIVE: BaselineForecastingAdapter()}
    ).execute(model)

    serialized = ForecastingResultCodec().serialize(solution)

    assert serialized.result["origin"] == "2026-01-03T23:00:00+00:00"
