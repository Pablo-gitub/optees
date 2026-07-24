from __future__ import annotations

from optees.application.contracts.capability_ids import REGRESSION_CAPABILITY_ID
from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.domain.entities.regression.solution import RegressionMetrics, RegressionSolution
from optees.domain.value_objects.regression.regression_status import RegressionStatus


class RegressionResultCodec:
    capability_id = REGRESSION_CAPABILITY_ID
    result_schema_version = "1"

    def serialize(self, solution: RegressionSolution) -> SerializedResult:
        trained = solution.status is RegressionStatus.TRAINED
        result = _strict_payload(
            {
                "trained_model": trained,
                "intercept": solution.intercept,
                "coefficients": [
                    {"feature": name, "value": value}
                    for name, value in solution.coefficients.items()
                ],
                "train_metrics": _metrics(solution.train_metrics),
                "test_metrics": _metrics(solution.test_metrics),
                "predictions": [
                    {
                        "row_index": prediction.row_index,
                        "actual": prediction.actual,
                        "predicted": prediction.predicted,
                        "residual": prediction.residual,
                        "partition": prediction.partition,
                    }
                    for prediction in solution.predictions
                ],
            },
            path="$.result",
        )
        diagnostics = _strict_payload(
            {
                "solver_status": solution.status.value,
                "method": _optional_string(solution.extras.get("method")),
                "train_count": _optional_non_negative_int(
                    solution.extras.get("train_count")
                ),
                "test_count": _optional_non_negative_int(
                    solution.extras.get("test_count")
                ),
                "random_seed": _optional_non_negative_int(
                    solution.extras.get("random_seed")
                ),
                "message": _optional_string(solution.extras.get("message")),
            },
            path="$.diagnostics",
        )
        return SerializedResult(
            mathematical_status=(
                MathematicalStatus.FEASIBLE
                if trained
                else MathematicalStatus.NOT_SOLVED
            ),
            result=result,
            diagnostics=diagnostics,
            warnings=_warnings(trained),
        )


def _metrics(metrics: RegressionMetrics) -> dict[str, float | None]:
    return {
        "mae": metrics.mae,
        "mse": metrics.mse,
        "rmse": metrics.rmse,
        "r_squared": metrics.r_squared,
    }


def _warnings(trained: bool) -> tuple[str, ...]:
    if not trained:
        return ("The regression model was not trained successfully.",)
    return (
        "Metrics describe this deterministic train/test split; they do not "
        "establish causality or guarantee future predictive performance.",
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_non_negative_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        normalized = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    return normalized if normalized >= 0 else None


def _strict_payload(payload: dict[str, object], *, path: str) -> dict[str, JsonValue]:
    normalized = require_json_value(payload, path=path)
    assert isinstance(normalized, dict)
    return normalized
