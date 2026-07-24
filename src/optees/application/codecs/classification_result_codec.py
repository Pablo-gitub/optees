from __future__ import annotations

import math
from collections.abc import Mapping

from optees.application.contracts.capability_ids import CLASSIFICATION_CAPABILITY_ID
from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.domain.entities.classification.solution import (
    ClassificationMetrics,
    ClassificationSolution,
    ConfusionMatrix,
)
from optees.domain.value_objects.classification.classification_status import (
    ClassificationStatus,
)


class ClassificationResultCodec:
    capability_id = CLASSIFICATION_CAPABILITY_ID
    result_schema_version = "1"

    def serialize(self, solution: ClassificationSolution) -> SerializedResult:
        trained = solution.status is ClassificationStatus.TRAINED
        result = _strict_payload(
            {
                "trained_model": trained,
                "negative_label": solution.negative_label,
                "positive_label": solution.positive_label,
                "intercept": solution.intercept,
                "coefficients": [
                    {"feature": name, "value": value}
                    for name, value in solution.coefficients.items()
                ],
                "feature_scaling": _feature_scaling(solution),
                "decision_threshold": 0.5,
                "train_metrics": _metrics(solution.train_metrics),
                "test_metrics": _metrics(solution.test_metrics),
                "train_confusion": _confusion(solution.train_confusion),
                "test_confusion": _confusion(solution.test_confusion),
                "predictions": [
                    {
                        "row_index": prediction.row_index,
                        "actual": prediction.actual,
                        "predicted": prediction.predicted,
                        "probability_positive": prediction.probability_positive,
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
                "iterations": _optional_non_negative_int(
                    solution.extras.get("iterations")
                ),
                "converged": _optional_bool(solution.extras.get("converged")),
                "learning_rate": _optional_finite_number(
                    solution.extras.get("learning_rate")
                ),
                "l2_alpha": _optional_finite_number(
                    solution.extras.get("l2_alpha")
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
            warnings=_warnings(solution, trained),
        )


def _metrics(metrics: ClassificationMetrics) -> dict[str, float | None]:
    return {
        "accuracy": metrics.accuracy,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
    }


def _confusion(confusion: ConfusionMatrix) -> dict[str, int]:
    return {
        "true_negative": confusion.true_negative,
        "false_positive": confusion.false_positive,
        "false_negative": confusion.false_negative,
        "true_positive": confusion.true_positive,
    }


def _feature_scaling(solution: ClassificationSolution) -> list[dict[str, object]]:
    raw_means = solution.extras.get("feature_means")
    raw_scales = solution.extras.get("feature_scales")
    means = raw_means if isinstance(raw_means, Mapping) else {}
    scales = raw_scales if isinstance(raw_scales, Mapping) else {}
    return [
        {
            "feature": name,
            "mean": _optional_finite_number(means.get(name)),
            "scale": _optional_finite_number(scales.get(name)),
        }
        for name in solution.coefficients
    ]


def _warnings(
    solution: ClassificationSolution,
    trained: bool,
) -> tuple[str, ...]:
    if not trained:
        return ("The binary classification model was not trained successfully.",)
    warnings = [
        "Metrics describe this deterministic train/test split and do not "
        "guarantee future classification performance."
    ]
    if solution.extras.get("converged") is False:
        warnings.append(
            "Gradient descent reached its iteration limit before satisfying the "
            "convergence tolerance."
        )
    return tuple(warnings)


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


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_finite_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    return normalized if math.isfinite(normalized) else None


def _strict_payload(payload: dict[str, object], *, path: str) -> dict[str, JsonValue]:
    normalized = require_json_value(payload, path=path)
    assert isinstance(normalized, dict)
    return normalized
