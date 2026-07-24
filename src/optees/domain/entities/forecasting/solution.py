from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from optees.domain.value_objects.forecasting import ForecastingMethod, ForecastingStatus


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


def _optional_finite(value: object, label: str) -> Optional[float]:
    return None if value is None else _finite(value, label)


class ForecastSegment(str, Enum):
    FITTED = "fitted"
    HOLDOUT = "holdout"
    FUTURE = "future"


@dataclass(frozen=True)
class PredictionInterval:
    lower: float
    upper: float
    coverage: float

    def __post_init__(self) -> None:
        lower = _finite(self.lower, "Prediction interval lower bound")
        upper = _finite(self.upper, "Prediction interval upper bound")
        coverage = _finite(self.coverage, "Prediction interval coverage")
        if lower > upper:
            raise ValueError("Prediction interval lower bound must not exceed upper bound")
        if not 0 < coverage < 1:
            raise ValueError("Prediction interval coverage must be between 0 and 1")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "coverage", coverage)


@dataclass(frozen=True)
class ForecastPoint:
    timestamp: datetime
    predicted: float
    segment: ForecastSegment
    actual: Optional[float] = None
    residual: Optional[float] = None
    interval: Optional[PredictionInterval] = None

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Forecast point timestamp must be a datetime")
        predicted = _finite(self.predicted, "Forecast point prediction")
        segment = (
            self.segment
            if isinstance(self.segment, ForecastSegment)
            else ForecastSegment(str(self.segment))
        )
        actual = _optional_finite(self.actual, "Forecast point actual value")
        residual = _optional_finite(self.residual, "Forecast point residual")
        if segment is ForecastSegment.FUTURE and (actual is not None or residual is not None):
            raise ValueError("Future forecast points cannot contain actual values or residuals")
        if (actual is None) != (residual is None):
            raise ValueError("Actual value and residual must be present together")
        if self.interval is not None and not isinstance(self.interval, PredictionInterval):
            raise ValueError("Forecast point interval must be a PredictionInterval")
        if actual is not None and not math.isclose(
            residual, actual - predicted, abs_tol=1e-9  # type: ignore[arg-type]
        ):
            raise ValueError("Forecast residual must equal actual minus predicted")
        object.__setattr__(self, "predicted", predicted)
        object.__setattr__(self, "segment", segment)
        object.__setattr__(self, "actual", actual)
        object.__setattr__(self, "residual", residual)


@dataclass(frozen=True)
class ForecastMetricSet:
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    mase: Optional[float] = None

    def __post_init__(self) -> None:
        for field_name in ("mae", "rmse", "mape", "mase"):
            value = _optional_finite(getattr(self, field_name), f"Forecast metric {field_name}")
            if value is not None and value < 0:
                raise ValueError(f"Forecast metric {field_name} must be non-negative")
            object.__setattr__(self, field_name, value)


@dataclass(frozen=True)
class ForecastDiagnostic:
    code: str
    message: str
    severity: str = "warning"

    def __post_init__(self) -> None:
        code = str(self.code).strip()
        message = str(self.message).strip()
        severity = str(self.severity).strip().lower()
        if not code or not message:
            raise ValueError("Forecast diagnostics require a code and message")
        if severity not in {"info", "warning", "error"}:
            raise ValueError("Forecast diagnostic severity is invalid")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "severity", severity)


@dataclass(frozen=True)
class ForecastingSolution:
    status: ForecastingStatus
    method: ForecastingMethod
    origin: datetime
    points: tuple[ForecastPoint, ...] = ()
    metrics: ForecastMetricSet = ForecastMetricSet()
    parameters: tuple[tuple[str, float], ...] = ()
    diagnostics: tuple[ForecastDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        status = (
            self.status
            if isinstance(self.status, ForecastingStatus)
            else ForecastingStatus(str(self.status))
        )
        method = (
            self.method
            if isinstance(self.method, ForecastingMethod)
            else ForecastingMethod.from_value(self.method)
        )
        if not isinstance(self.origin, datetime):
            raise ValueError("Forecast origin must be a datetime")
        points = tuple(self.points)
        if any(not isinstance(point, ForecastPoint) for point in points):
            raise ValueError("Forecast solution points must contain ForecastPoint values")
        if any(
            point.timestamp <= points[index - 1].timestamp
            for index, point in enumerate(points)
            if index
        ):
            raise ValueError("Forecast solution timestamps must be strictly increasing")
        origin_is_aware = self.origin.tzinfo is not None
        for point in points:
            if (point.timestamp.tzinfo is not None) != origin_is_aware:
                raise ValueError("Forecast solution cannot mix aware and naive timestamps")
            if point.segment is ForecastSegment.FUTURE and point.timestamp <= self.origin:
                raise ValueError("Future forecast points must occur after the forecast origin")
            if point.segment is not ForecastSegment.FUTURE and point.timestamp > self.origin:
                raise ValueError("Historical forecast points cannot occur after the forecast origin")
        if not isinstance(self.metrics, ForecastMetricSet):
            raise ValueError("Forecast solution metrics must be a ForecastMetricSet")
        diagnostics = tuple(self.diagnostics)
        if any(not isinstance(item, ForecastDiagnostic) for item in diagnostics):
            raise ValueError("Forecast solution diagnostics must contain ForecastDiagnostic values")
        parameters: list[tuple[str, float]] = []
        seen: set[str] = set()
        for raw_name, raw_value in self.parameters:
            name = str(raw_name).strip()
            if not name or name in seen:
                raise ValueError("Forecast parameter names must be non-empty and unique")
            seen.add(name)
            parameters.append((name, _finite(raw_value, f"Forecast parameter {name}")))
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "parameters", tuple(parameters))
        object.__setattr__(self, "diagnostics", diagnostics)
