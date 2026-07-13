from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Optional

from optees.domain.value_objects.regression.regression_status import RegressionStatus


def _optional_finite_float(value: object) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return normalized if math.isfinite(normalized) else None


@dataclass(frozen=True)
class RegressionMetrics:
    """Evaluation metrics computed on one partition of the dataset."""

    mae: Optional[float] = None
    mse: Optional[float] = None
    rmse: Optional[float] = None
    r_squared: Optional[float] = None

    @classmethod
    def from_mapping(cls, value: object) -> "RegressionMetrics":
        raw = value if isinstance(value, Mapping) else {}
        return cls(
            mae=_optional_finite_float(raw.get("mae")),
            mse=_optional_finite_float(raw.get("mse")),
            rmse=_optional_finite_float(raw.get("rmse")),
            r_squared=_optional_finite_float(raw.get("r_squared")),
        )


@dataclass(frozen=True)
class RegressionPrediction:
    """One prediction kept for the solution table and later charts."""

    row_index: int
    actual: float
    predicted: float
    residual: float
    partition: str

    @classmethod
    def from_mapping(cls, value: object) -> Optional["RegressionPrediction"]:
        if not isinstance(value, Mapping):
            return None
        try:
            row_index = int(value.get("row_index"))
        except (TypeError, ValueError):
            return None
        actual = _optional_finite_float(value.get("actual"))
        predicted = _optional_finite_float(value.get("predicted"))
        residual = _optional_finite_float(value.get("residual"))
        partition = str(value.get("partition", "")).strip().lower()
        if row_index < 0 or None in (actual, predicted, residual) or partition not in {"train", "test"}:
            return None
        return cls(row_index, actual, predicted, residual, partition)  # type: ignore[arg-type]


@dataclass(frozen=True)
class RegressionSolution:
    """Result of a local OLS or Ridge fit; evaluation is not a causal claim."""

    status: RegressionStatus
    intercept: Optional[float]
    coefficients: dict[str, float]
    train_metrics: RegressionMetrics = RegressionMetrics()
    test_metrics: RegressionMetrics = RegressionMetrics()
    predictions: tuple[RegressionPrediction, ...] = ()
    extras: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_solver_result(cls, raw: Mapping[str, object]) -> "RegressionSolution":
        raw_coefficients = raw.get("coefficients")
        coefficients = {
            str(name): value
            for name, raw_value in (raw_coefficients.items() if isinstance(raw_coefficients, Mapping) else ())
            if (value := _optional_finite_float(raw_value)) is not None
        }
        raw_predictions = raw.get("predictions")
        predictions = tuple(
            prediction
            for raw_prediction in (raw_predictions if isinstance(raw_predictions, list) else ())
            if (prediction := RegressionPrediction.from_mapping(raw_prediction)) is not None
        )
        raw_extras = raw.get("extras")
        return cls(
            status=RegressionStatus.from_str(raw.get("status")),
            intercept=_optional_finite_float(raw.get("intercept")),
            coefficients=coefficients,
            train_metrics=RegressionMetrics.from_mapping(raw.get("train_metrics")),
            test_metrics=RegressionMetrics.from_mapping(raw.get("test_metrics")),
            predictions=predictions,
            extras=dict(raw_extras) if isinstance(raw_extras, Mapping) else {},
        )

    def trained(self) -> bool:
        return self.status is RegressionStatus.TRAINED
