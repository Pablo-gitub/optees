from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Optional

from optees.domain.value_objects.classification.classification_status import ClassificationStatus


def _optional_float(value: object) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _optional_int(value: object) -> Optional[int]:
    if isinstance(value, bool):
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class ClassificationMetrics:
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None

    @classmethod
    def from_mapping(cls, value: object) -> "ClassificationMetrics":
        raw = value if isinstance(value, Mapping) else {}
        return cls(
            accuracy=_optional_float(raw.get("accuracy")),
            precision=_optional_float(raw.get("precision")),
            recall=_optional_float(raw.get("recall")),
            f1=_optional_float(raw.get("f1")),
        )


@dataclass(frozen=True)
class ConfusionMatrix:
    true_negative: int = 0
    false_positive: int = 0
    false_negative: int = 0
    true_positive: int = 0

    @classmethod
    def from_mapping(cls, value: object) -> "ConfusionMatrix":
        raw = value if isinstance(value, Mapping) else {}
        return cls(
            true_negative=max(0, _optional_int(raw.get("true_negative")) or 0),
            false_positive=max(0, _optional_int(raw.get("false_positive")) or 0),
            false_negative=max(0, _optional_int(raw.get("false_negative")) or 0),
            true_positive=max(0, _optional_int(raw.get("true_positive")) or 0),
        )


@dataclass(frozen=True)
class ClassificationPrediction:
    row_index: int
    actual: str
    predicted: str
    probability_positive: float
    partition: str

    @classmethod
    def from_mapping(cls, value: object) -> Optional["ClassificationPrediction"]:
        if not isinstance(value, Mapping):
            return None
        row_index = _optional_int(value.get("row_index"))
        probability = _optional_float(value.get("probability_positive"))
        actual = str(value.get("actual", "")).strip()
        predicted = str(value.get("predicted", "")).strip()
        partition = str(value.get("partition", "")).strip().lower()
        if (
            row_index is None
            or row_index < 0
            or probability is None
            or not 0 <= probability <= 1
            or not actual
            or not predicted
            or partition not in {"train", "test"}
        ):
            return None
        return cls(row_index, actual, predicted, probability, partition)


@dataclass(frozen=True)
class ClassificationSolution:
    """Normalized local binary-classification result and held-out diagnostics."""

    status: ClassificationStatus
    negative_label: str = ""
    positive_label: str = ""
    intercept: Optional[float] = None
    coefficients: dict[str, float] = field(default_factory=dict)
    train_metrics: ClassificationMetrics = ClassificationMetrics()
    test_metrics: ClassificationMetrics = ClassificationMetrics()
    train_confusion: ConfusionMatrix = ConfusionMatrix()
    test_confusion: ConfusionMatrix = ConfusionMatrix()
    predictions: tuple[ClassificationPrediction, ...] = ()
    extras: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_solver_result(cls, raw: Mapping[str, object]) -> "ClassificationSolution":
        raw_coefficients = raw.get("coefficients")
        coefficients = {
            str(name): value
            for name, raw_value in (raw_coefficients.items() if isinstance(raw_coefficients, Mapping) else ())
            if (value := _optional_float(raw_value)) is not None
        }
        raw_predictions = raw.get("predictions")
        predictions = tuple(
            prediction
            for row in (raw_predictions if isinstance(raw_predictions, list) else ())
            if (prediction := ClassificationPrediction.from_mapping(row)) is not None
        )
        raw_extras = raw.get("extras")
        return cls(
            status=ClassificationStatus.from_str(raw.get("status")),
            negative_label=str(raw.get("negative_label", "")).strip(),
            positive_label=str(raw.get("positive_label", "")).strip(),
            intercept=_optional_float(raw.get("intercept")),
            coefficients=coefficients,
            train_metrics=ClassificationMetrics.from_mapping(raw.get("train_metrics")),
            test_metrics=ClassificationMetrics.from_mapping(raw.get("test_metrics")),
            train_confusion=ConfusionMatrix.from_mapping(raw.get("train_confusion")),
            test_confusion=ConfusionMatrix.from_mapping(raw.get("test_confusion")),
            predictions=predictions,
            extras=dict(raw_extras) if isinstance(raw_extras, Mapping) else {},
        )

    def trained(self) -> bool:
        return self.status is ClassificationStatus.TRAINED
