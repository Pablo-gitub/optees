from __future__ import annotations

from datetime import datetime
from typing import Protocol

from optees.domain.entities.forecasting import ForecastObservation, ForecastPoint
from optees.domain.models.forecasting import ForecastingModel


class ForecastingSolverPort(Protocol):
    """Numerical boundary for one fitted univariate forecasting method."""

    def fit_and_predict(
        self,
        model: ForecastingModel,
        training_observations: tuple[ForecastObservation, ...],
        prediction_timestamps: tuple[datetime, ...],
    ) -> tuple[ForecastPoint, ...]:
        """Fit only on supplied history and predict the requested timestamps."""
        ...
