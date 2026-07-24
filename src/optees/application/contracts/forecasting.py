from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from optees.domain.entities.forecasting import (
    ForecastDiagnostic,
    ForecastEvaluationFold,
    ForecastMetricSet,
)
from optees.domain.value_objects.forecasting import (
    ForecastEvaluationStatus,
    ForecastingStatus,
)


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be finite")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite") from exc
    if not math.isfinite(normalized):
        raise ValueError(f"{label} must be finite")
    return normalized


@dataclass(frozen=True)
class ForecastingAdapterOutput:
    """Validated numerical output before temporal segments are assembled."""

    status: ForecastingStatus
    predicted_values: tuple[float, ...]
    fitted_values: tuple[Optional[float], ...] = ()
    parameters: tuple[tuple[str, float], ...] = ()
    diagnostics: tuple[ForecastDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        status = (
            self.status
            if isinstance(self.status, ForecastingStatus)
            else ForecastingStatus(str(self.status))
        )
        predictions = tuple(
            _finite(value, "Forecast adapter prediction") for value in self.predicted_values
        )
        fitted_values = tuple(
            None if value is None else _finite(value, "Forecast adapter fitted value")
            for value in self.fitted_values
        )
        parameters: list[tuple[str, float]] = []
        seen: set[str] = set()
        for raw_name, raw_value in self.parameters:
            name = str(raw_name).strip()
            value = _finite(raw_value, f"Forecast adapter parameter {name or '<empty>'}")
            if not name or name in seen:
                raise ValueError("Forecast adapter parameter names must be non-empty and unique")
            seen.add(name)
            parameters.append((name, value))
        diagnostics = tuple(self.diagnostics)
        if any(not isinstance(item, ForecastDiagnostic) for item in diagnostics):
            raise ValueError("Forecast adapter diagnostics must be ForecastDiagnostic values")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "predicted_values", predictions)
        object.__setattr__(self, "fitted_values", fitted_values)
        object.__setattr__(self, "parameters", tuple(parameters))
        object.__setattr__(self, "diagnostics", diagnostics)


@dataclass(frozen=True)
class ForecastingEvaluationOutput:
    """Chronological evaluation outcome before final future forecasting."""

    status: ForecastEvaluationStatus
    folds: tuple[ForecastEvaluationFold, ...] = ()
    metrics: ForecastMetricSet = ForecastMetricSet()
    diagnostics: tuple[ForecastDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        status = (
            self.status
            if isinstance(self.status, ForecastEvaluationStatus)
            else ForecastEvaluationStatus(str(self.status))
        )
        folds = tuple(self.folds)
        if any(not isinstance(fold, ForecastEvaluationFold) for fold in folds):
            raise ValueError("Forecast evaluation output contains an invalid fold")
        if status is ForecastEvaluationStatus.NOT_REQUESTED and folds:
            raise ValueError("A non-requested evaluation cannot contain folds")
        if status is ForecastEvaluationStatus.EVALUATED and not folds:
            raise ValueError("A completed evaluation must contain folds")
        if not isinstance(self.metrics, ForecastMetricSet):
            raise ValueError("Forecast evaluation output metrics are invalid")
        diagnostics = tuple(self.diagnostics)
        if any(not isinstance(item, ForecastDiagnostic) for item in diagnostics):
            raise ValueError("Forecast evaluation output diagnostics are invalid")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "folds", folds)
        object.__setattr__(self, "diagnostics", diagnostics)
