from __future__ import annotations

import math
import warnings
from datetime import datetime
from typing import Any

from statsmodels.tsa.holtwinters import ExponentialSmoothing

from optees.application.contracts.forecasting import ForecastingAdapterOutput
from optees.application.ports.forecasting_solver_port import ForecastingSolverPort
from optees.domain.entities.forecasting import ForecastDiagnostic, ForecastObservation
from optees.domain.models.forecasting import ForecastingModel
from optees.domain.value_objects.forecasting import ForecastingMethod, ForecastingStatus


class HoltWintersForecastingAdapter(ForecastingSolverPort):
    """Additive Holt-Winters adapter over the maintained statsmodels backend."""

    def fit_and_predict(
        self,
        model: ForecastingModel,
        training_observations: tuple[ForecastObservation, ...],
        prediction_timestamps: tuple[datetime, ...],
    ) -> ForecastingAdapterOutput:
        training = tuple(training_observations)
        timestamps = tuple(prediction_timestamps)
        self._validate_request(model, training, timestamps)

        try:
            with warnings.catch_warnings(record=True) as caught_warnings:
                warnings.simplefilter("always")
                fitted = ExponentialSmoothing(
                    [observation.value for observation in training],
                    trend="add",
                    seasonal="add",
                    seasonal_periods=model.season_length,
                    initialization_method="estimated",
                ).fit(
                    optimized=True,
                    method="L-BFGS-B",
                    minimize_kwargs={
                        "options": {
                            "maxiter": model.method_options.max_iterations,
                            "ftol": model.method_options.tolerance,
                        }
                    },
                    use_brute=True,
                )
                predictions = tuple(float(value) for value in fitted.forecast(len(timestamps)))
        except (ArithmeticError, RuntimeError, ValueError) as exc:
            return self._failed_output(exc)

        if len(predictions) != len(timestamps) or any(
            not math.isfinite(value) for value in predictions
        ):
            return self._failed_output()

        diagnostics = [
            ForecastDiagnostic(
                code="forecast_backend_warning",
                message="The Holt-Winters backend reported a numerical warning.",
            )
            for _warning in caught_warnings
        ]
        convergence = getattr(fitted, "mle_retvals", None)
        converged = bool(
            convergence is None
            or self._result_value(convergence, "success", default=True)
        )
        if not converged:
            diagnostics.append(
                ForecastDiagnostic(
                    code="forecast_convergence_warning",
                    message=(
                        "Holt-Winters returned finite forecasts before confirming "
                        "numerical convergence."
                    ),
                )
            )

        return ForecastingAdapterOutput(
            status=(
                ForecastingStatus.FORECASTED
                if converged
                else ForecastingStatus.PARTIAL
            ),
            predicted_values=predictions,
            parameters=self._scalar_parameters(fitted),
            diagnostics=tuple(diagnostics),
        )

    @staticmethod
    def _validate_request(
        model: ForecastingModel,
        training: tuple[ForecastObservation, ...],
        timestamps: tuple[datetime, ...],
    ) -> None:
        if model.method is not ForecastingMethod.HOLT_WINTERS_ADDITIVE:
            raise ValueError(
                f"Unsupported Holt-Winters forecasting method: {model.method.value}"
            )
        if not training:
            raise ValueError("Forecast training history must not be empty")
        if training != model.observations[: len(training)]:
            raise ValueError("Forecast training history must be an exact model-history prefix")
        if len(training) < model.evaluation.minimum_training_size:
            raise ValueError("Forecast training history is shorter than the declared minimum")
        assert model.season_length is not None
        if len(training) < model.season_length * 2:
            raise ValueError("Holt-Winters training requires two complete seasons")
        if not timestamps:
            raise ValueError("Forecast prediction timestamps must not be empty")
        for index, timestamp in enumerate(timestamps, start=1):
            expected = model.frequency.advance(training[-1].timestamp, index)
            if timestamp != expected:
                raise ValueError(
                    "Forecast prediction timestamps must immediately follow training frequency"
                )

    @staticmethod
    def _scalar_parameters(fitted: Any) -> tuple[tuple[str, float], ...]:
        raw_parameters = getattr(fitted, "params", {})
        names = (
            "smoothing_level",
            "smoothing_trend",
            "smoothing_seasonal",
            "initial_level",
            "initial_trend",
        )
        parameters: list[tuple[str, float]] = []
        for name in names:
            value = raw_parameters.get(name)
            if isinstance(value, bool):
                continue
            try:
                normalized = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(normalized):
                parameters.append((name, normalized))
        return tuple(parameters)

    @staticmethod
    def _result_value(result: Any, name: str, *, default: object) -> object:
        if isinstance(result, dict):
            return result.get(name, default)
        return getattr(result, name, default)

    @staticmethod
    def _failed_output(_cause: BaseException | None = None) -> ForecastingAdapterOutput:
        return ForecastingAdapterOutput(
            status=ForecastingStatus.FAILED,
            predicted_values=(),
            diagnostics=(
                ForecastDiagnostic(
                    code="forecast_fit_failed",
                    message="Holt-Winters fitting failed.",
                    severity="error",
                ),
            ),
        )
