from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from optees.domain.entities.forecasting import ForecastObservation
from optees.domain.value_objects.forecasting import (
    EvaluationStrategy,
    ForecastingFrequency,
    ForecastingMethod,
    MissingPeriodPolicy,
)


def _bounded_int(value: object, label: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer between {minimum} and {maximum}")
    return value


@dataclass(frozen=True)
class ForecastingEvaluationOptions:
    """Bounded chronological evaluation controls."""

    strategy: EvaluationStrategy = EvaluationStrategy.HOLDOUT
    holdout_size: int = 1
    origin_count: int = 3
    step: int = 1
    evaluation_horizon: int = 1
    minimum_training_size: int = 2

    def __post_init__(self) -> None:
        strategy = (
            self.strategy
            if isinstance(self.strategy, EvaluationStrategy)
            else EvaluationStrategy.from_value(self.strategy)
        )
        object.__setattr__(self, "strategy", strategy)
        object.__setattr__(
            self,
            "holdout_size",
            _bounded_int(self.holdout_size, "Forecast holdout size", minimum=1, maximum=10_000),
        )
        object.__setattr__(
            self,
            "origin_count",
            _bounded_int(self.origin_count, "Forecast origin count", minimum=1, maximum=100),
        )
        object.__setattr__(
            self,
            "step",
            _bounded_int(self.step, "Forecast evaluation step", minimum=1, maximum=10_000),
        )
        object.__setattr__(
            self,
            "evaluation_horizon",
            _bounded_int(
                self.evaluation_horizon,
                "Forecast evaluation horizon",
                minimum=1,
                maximum=10_000,
            ),
        )
        object.__setattr__(
            self,
            "minimum_training_size",
            _bounded_int(
                self.minimum_training_size,
                "Forecast minimum training size",
                minimum=2,
                maximum=100_000,
            ),
        )


@dataclass(frozen=True)
class ForecastingMethodOptions:
    """Numerical limits shared by maintained iterative adapters."""

    max_iterations: int = 1_000
    tolerance: float = 1e-8

    def __post_init__(self) -> None:
        max_iterations = _bounded_int(
            self.max_iterations,
            "Forecast max iterations",
            minimum=1,
            maximum=100_000,
        )
        if isinstance(self.tolerance, bool):
            raise ValueError("Forecast tolerance must be a positive finite number")
        try:
            tolerance = float(self.tolerance)
        except (TypeError, ValueError) as exc:
            raise ValueError("Forecast tolerance must be a positive finite number") from exc
        if not math.isfinite(tolerance) or tolerance <= 0:
            raise ValueError("Forecast tolerance must be a positive finite number")
        object.__setattr__(self, "max_iterations", max_iterations)
        object.__setattr__(self, "tolerance", tolerance)


@dataclass(frozen=True)
class ForecastingModel:
    """Validated regular univariate history plus explicit forecast semantics."""

    target_name: str
    observations: tuple[ForecastObservation, ...]
    method: ForecastingMethod
    horizon: int
    frequency: ForecastingFrequency
    season_length: Optional[int] = None
    missing_period_policy: MissingPeriodPolicy = MissingPeriodPolicy.REJECT
    evaluation: ForecastingEvaluationOptions = ForecastingEvaluationOptions()
    method_options: ForecastingMethodOptions = ForecastingMethodOptions()

    def __post_init__(self) -> None:
        target_name = str(self.target_name).strip()
        observations = tuple(self.observations)
        method = (
            self.method
            if isinstance(self.method, ForecastingMethod)
            else ForecastingMethod.from_value(self.method)
        )
        frequency = (
            self.frequency
            if isinstance(self.frequency, ForecastingFrequency)
            else ForecastingFrequency.from_value(self.frequency)
        )
        missing_policy = (
            self.missing_period_policy
            if isinstance(self.missing_period_policy, MissingPeriodPolicy)
            else MissingPeriodPolicy.from_value(self.missing_period_policy)
        )
        evaluation = (
            self.evaluation
            if isinstance(self.evaluation, ForecastingEvaluationOptions)
            else ForecastingEvaluationOptions(**self.evaluation)
        )
        method_options = (
            self.method_options
            if isinstance(self.method_options, ForecastingMethodOptions)
            else ForecastingMethodOptions(**self.method_options)
        )

        if not target_name:
            raise ValueError("Forecast target name must be non-empty")
        if len(observations) < 2:
            raise ValueError("Forecast history must contain at least two observations")
        if any(not isinstance(item, ForecastObservation) for item in observations):
            raise ValueError("Forecast history must contain ForecastObservation values")
        horizon = _bounded_int(
            self.horizon,
            "Forecast horizon",
            minimum=1,
            maximum=10_000,
        )

        aware = observations[0].timestamp.tzinfo is not None
        if any((item.timestamp.tzinfo is not None) != aware for item in observations):
            raise ValueError("Forecast history cannot mix timezone-aware and naive timestamps")
        origin = observations[0].timestamp
        for index, observation in enumerate(observations):
            if index and observation.timestamp <= observations[index - 1].timestamp:
                raise ValueError("Forecast timestamps must be strictly increasing")
            if observation.timestamp != frequency.advance(origin, index):
                raise ValueError("Forecast history contains a missing or off-frequency period")

        season_length = self.season_length
        if method.requires_season_length:
            season_length = _bounded_int(
                season_length,
                "Forecast season length",
                minimum=2,
                maximum=10_000,
            )
            if len(observations) < season_length * 2:
                raise ValueError("Seasonal forecasting requires at least two complete seasons")
        elif season_length is not None:
            raise ValueError("Naive forecasting does not accept a season length")

        minimum_fit_size = season_length * 2 if season_length is not None else 2
        if evaluation.strategy is EvaluationStrategy.HOLDOUT:
            available_training = len(observations) - evaluation.holdout_size
            if available_training < max(minimum_fit_size, evaluation.minimum_training_size):
                raise ValueError("Forecast holdout leaves insufficient training history")
        elif evaluation.strategy is EvaluationStrategy.ROLLING_ORIGIN:
            required = (
                evaluation.minimum_training_size
                + evaluation.evaluation_horizon
                + (evaluation.origin_count - 1) * evaluation.step
            )
            if len(observations) < required or evaluation.minimum_training_size < minimum_fit_size:
                raise ValueError("Rolling-origin evaluation requires more historical observations")

        object.__setattr__(self, "target_name", target_name)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "horizon", horizon)
        object.__setattr__(self, "frequency", frequency)
        object.__setattr__(self, "season_length", season_length)
        object.__setattr__(self, "missing_period_policy", missing_policy)
        object.__setattr__(self, "evaluation", evaluation)
        object.__setattr__(self, "method_options", method_options)

    @property
    def forecast_origin(self) -> datetime:
        return self.observations[-1].timestamp

    def future_timestamps(self) -> tuple[datetime, ...]:
        return tuple(
            self.frequency.advance(self.forecast_origin, period)
            for period in range(1, self.horizon + 1)
        )
