"""Entities returned and consumed by univariate forecasting."""

from .observation import ForecastObservation
from .solution import (
    ForecastDiagnostic,
    ForecastEvaluationFold,
    ForecastMetricSet,
    ForecastPoint,
    ForecastSegment,
    ForecastingSolution,
    PredictionInterval,
)

__all__ = [
    "ForecastDiagnostic",
    "ForecastEvaluationFold",
    "ForecastMetricSet",
    "ForecastObservation",
    "ForecastPoint",
    "ForecastSegment",
    "ForecastingSolution",
    "PredictionInterval",
]
