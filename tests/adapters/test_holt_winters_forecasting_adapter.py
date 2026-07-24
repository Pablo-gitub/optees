from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import optees.data.adapters.forecasting.holt_winters_forecasting_adapter as adapter_module
from optees.data.adapters.forecasting import HoltWintersForecastingAdapter
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
    ForecastingStatus,
)


def _model(
    values: tuple[float, ...],
    *,
    max_iterations: int = 1_000,
) -> ForecastingModel:
    origin = datetime(2026, 1, 1)
    return ForecastingModel(
        target_name="demand",
        observations=tuple(
            ForecastObservation(origin + timedelta(days=index), value)
            for index, value in enumerate(values)
        ),
        method=ForecastingMethod.HOLT_WINTERS_ADDITIVE,
        horizon=4,
        frequency=ForecastingFrequency.DAILY,
        season_length=3,
        evaluation=ForecastingEvaluationOptions(strategy=EvaluationStrategy.NONE),
        method_options=ForecastingMethodOptions(max_iterations=max_iterations),
    )


def test_holt_winters_preserves_additive_seasonal_cycle() -> None:
    model = _model((10, 20, 30, 10, 20, 30, 10, 20, 30, 10, 20, 30))

    output = HoltWintersForecastingAdapter().fit_and_predict(
        model,
        model.observations,
        model.future_timestamps(),
    )

    assert output.status is ForecastingStatus.FORECASTED
    assert output.predicted_values == pytest.approx((10, 20, 30, 10), abs=1e-6)
    assert len(output.fitted_values) == len(model.observations)
    assert dict(output.parameters).keys() >= {
        "smoothing_level",
        "smoothing_trend",
        "smoothing_seasonal",
    }
    assert output.diagnostics == ()


def test_holt_winters_rejects_non_prefix_training_history() -> None:
    model = _model((10, 20, 30, 10, 20, 30))

    with pytest.raises(ValueError, match="exact model-history prefix"):
        HoltWintersForecastingAdapter().fit_and_predict(
            model,
            model.observations[1:],
            model.future_timestamps(),
        )


def test_holt_winters_maps_backend_failure_without_leaking_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingBackend:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def fit(self, **_kwargs: object) -> object:
            raise RuntimeError("sensitive backend detail")

    monkeypatch.setattr(adapter_module, "ExponentialSmoothing", FailingBackend)
    model = _model((10, 20, 30, 10, 20, 30))

    output = HoltWintersForecastingAdapter().fit_and_predict(
        model,
        model.observations,
        model.future_timestamps(),
    )

    assert output.status is ForecastingStatus.FAILED
    assert output.predicted_values == ()
    assert output.diagnostics[0].code == "forecast_fit_failed"
    assert "sensitive" not in output.diagnostics[0].message


def test_holt_winters_forwards_bounded_iteration_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class SuccessfulFit:
        fittedvalues = [10.0, 20.0, 30.0, 10.0, 20.0, 30.0]
        params = {
            "smoothing_level": 0.4,
            "smoothing_trend": 0.1,
            "smoothing_seasonal": 0.2,
        }
        mle_retvals = {"success": True}

        @staticmethod
        def forecast(count: int) -> list[float]:
            return [12.0] * count

    class CapturingBackend:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def fit(self, **kwargs: object) -> SuccessfulFit:
            captured.update(kwargs)
            return SuccessfulFit()

    monkeypatch.setattr(adapter_module, "ExponentialSmoothing", CapturingBackend)
    model = _model((10, 20, 30, 10, 20, 30), max_iterations=17)

    output = HoltWintersForecastingAdapter().fit_and_predict(
        model,
        model.observations,
        model.future_timestamps(),
    )

    assert output.status is ForecastingStatus.FORECASTED
    assert captured["minimize_kwargs"] == {
        "options": {"maxiter": 17, "ftol": model.method_options.tolerance}
    }
