from __future__ import annotations

from datetime import datetime

from optees.application.contracts.forecasting import ForecastingAdapterOutput
from optees.application.ports.forecasting_solver_port import ForecastingSolverPort
from optees.domain.entities.forecasting import ForecastObservation
from optees.domain.models.forecasting import ForecastingModel
from optees.domain.value_objects.forecasting import ForecastingMethod, ForecastingStatus


class BaselineForecastingAdapter(ForecastingSolverPort):
    """Exact naive baselines over a validated chronological training prefix."""

    _SUPPORTED_METHODS = {
        ForecastingMethod.NAIVE,
        ForecastingMethod.SEASONAL_NAIVE,
    }

    def fit_and_predict(
        self,
        model: ForecastingModel,
        training_observations: tuple[ForecastObservation, ...],
        prediction_timestamps: tuple[datetime, ...],
    ) -> ForecastingAdapterOutput:
        training = tuple(training_observations)
        timestamps = tuple(prediction_timestamps)
        self._validate_request(model, training, timestamps)

        if model.method is ForecastingMethod.NAIVE:
            value = training[-1].value
            return ForecastingAdapterOutput(
                status=ForecastingStatus.FORECASTED,
                predicted_values=(value,) * len(timestamps),
                parameters=(("last_value", value),),
            )

        assert model.season_length is not None
        season = tuple(item.value for item in training[-model.season_length :])
        return ForecastingAdapterOutput(
            status=ForecastingStatus.FORECASTED,
            predicted_values=tuple(
                season[index % model.season_length] for index in range(len(timestamps))
            ),
            parameters=(("season_length", float(model.season_length)),),
        )

    def _validate_request(
        self,
        model: ForecastingModel,
        training: tuple[ForecastObservation, ...],
        timestamps: tuple[datetime, ...],
    ) -> None:
        if model.method not in self._SUPPORTED_METHODS:
            raise ValueError(f"Unsupported baseline forecasting method: {model.method.value}")
        if not training:
            raise ValueError("Forecast training history must not be empty")
        if training != model.observations[: len(training)]:
            raise ValueError("Forecast training history must be an exact model-history prefix")
        if len(training) < model.evaluation.minimum_training_size:
            raise ValueError("Forecast training history is shorter than the declared minimum")
        if not timestamps:
            raise ValueError("Forecast prediction timestamps must not be empty")
        for index, timestamp in enumerate(timestamps, start=1):
            expected = model.frequency.advance(training[-1].timestamp, index)
            if timestamp != expected:
                raise ValueError(
                    "Forecast prediction timestamps must immediately follow training frequency"
                )
        if model.method is ForecastingMethod.SEASONAL_NAIVE:
            assert model.season_length is not None
            if len(training) < model.season_length * 2:
                raise ValueError("Seasonal-naive training requires two complete seasons")
