from __future__ import annotations

from optees.application.contracts.capability_ids import FORECASTING_CAPABILITY_ID
from optees.application.contracts.execution import (
    MathematicalStatus,
    SerializedResult,
    TerminationReason,
)
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.domain.entities.forecasting import (
    ForecastEvaluationFold,
    ForecastMetricSet,
    ForecastPoint,
    ForecastingSolution,
    PredictionInterval,
)
from optees.domain.value_objects.forecasting import ForecastingStatus


class ForecastingResultCodec:
    capability_id = FORECASTING_CAPABILITY_ID
    result_schema_version = "1"

    def serialize(self, solution: ForecastingSolution) -> SerializedResult:
        available = solution.status in {
            ForecastingStatus.FORECASTED,
            ForecastingStatus.PARTIAL,
        }
        result = _strict_payload(
            {
                "forecast_available": available,
                "method": solution.method.value,
                "origin": solution.origin.isoformat(),
                "points": [_point(point) for point in solution.points],
                "metrics": _metrics(solution.metrics),
                "evaluation": {
                    "status": solution.evaluation_status.value,
                    "folds": [_fold(fold) for fold in solution.evaluation_folds],
                },
                "parameters": [
                    {"name": name, "value": value}
                    for name, value in solution.parameters
                ],
            },
            path="$.result",
        )
        diagnostics = _strict_payload(
            {
                "solver_status": solution.status.value,
                "items": [
                    {
                        "code": item.code,
                        "message": item.message,
                        "severity": item.severity,
                    }
                    for item in solution.diagnostics
                ],
            },
            path="$.diagnostics",
        )
        return SerializedResult(
            mathematical_status=(
                MathematicalStatus.FEASIBLE
                if available
                else MathematicalStatus.NOT_SOLVED
            ),
            result=result,
            diagnostics=diagnostics,
            warnings=_warnings(solution),
            termination_reason=(
                TerminationReason.CANCELLED
                if solution.status is ForecastingStatus.CANCELLED
                else TerminationReason.COMPLETED
            ),
        )


def _point(point: ForecastPoint) -> dict[str, object]:
    return {
        "timestamp": point.timestamp.isoformat(),
        "actual": point.actual,
        "predicted": point.predicted,
        "residual": point.residual,
        "interval": _interval(point.interval),
        "segment": point.segment.value,
    }


def _interval(interval: PredictionInterval | None) -> dict[str, float] | None:
    if interval is None:
        return None
    return {
        "lower": interval.lower,
        "upper": interval.upper,
        "coverage": interval.coverage,
    }


def _metrics(metrics: ForecastMetricSet) -> dict[str, float | None]:
    return {
        "mae": metrics.mae,
        "rmse": metrics.rmse,
        "mape": metrics.mape,
        "mase": metrics.mase,
    }


def _fold(fold: ForecastEvaluationFold) -> dict[str, object]:
    return {
        "origin": fold.origin.isoformat(),
        "training_size": fold.training_size,
        "points": [_point(point) for point in fold.points],
        "metrics": _metrics(fold.metrics),
    }


def _warnings(solution: ForecastingSolution) -> tuple[str, ...]:
    warnings = tuple(
        item.message
        for item in solution.diagnostics
        if item.severity == "warning"
    )
    if solution.status in {ForecastingStatus.FORECASTED, ForecastingStatus.PARTIAL}:
        return warnings + (
            "Forecasts are estimates based on historical temporal patterns; "
            "they do not establish causality or guarantee future outcomes.",
        )
    return warnings + ("No complete future forecast is available.",)


def _strict_payload(payload: dict[str, object], *, path: str) -> dict[str, JsonValue]:
    normalized = require_json_value(payload, path=path)
    assert isinstance(normalized, dict)
    return normalized
