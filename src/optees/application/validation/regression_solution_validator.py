from __future__ import annotations

import math
from collections import Counter

from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.json_value import JsonValue
from optees.application.contracts.solution_validation import (
    SolutionValidation,
    ValidationCheck,
    ValidationCheckStatus,
    ValidationViolation,
)
from optees.domain.models.regression.regression_model import RegressionModel


class RegressionIndependentSolutionValidator:
    """Recompute regression predictions and metrics from the public result."""

    def __init__(
        self,
        *,
        absolute_tolerance: float = 1e-8,
        relative_tolerance: float = 1e-7,
    ) -> None:
        for value in (absolute_tolerance, relative_tolerance):
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError(
                    "Regression validation tolerances must be finite and non-negative"
                )
        self._absolute_tolerance = float(absolute_tolerance)
        self._relative_tolerance = float(relative_tolerance)

    def __call__(
        self,
        model: RegressionModel,
        serialized: SerializedResult,
    ) -> SolutionValidation:
        if serialized.mathematical_status is not MathematicalStatus.FEASIBLE:
            return SolutionValidation.not_available(
                "No trained regression model is available for independent validation."
            )

        checks: list[ValidationCheck] = []
        violations: list[ValidationViolation] = []
        parameters, parameter_violations = self._parameters(
            model, serialized.result
        )
        violations.extend(parameter_violations)
        checks.append(
            _check(
                "regression.parameters",
                not parameter_violations,
                "The result contains one finite coefficient for every feature and a finite intercept.",
                {"feature_count": len(model.dataset.feature_names)},
            )
        )
        if parameter_violations:
            return self._report(checks, violations)

        intercept, coefficients = parameters
        predictions, prediction_violations = self._predictions(
            model,
            serialized.result,
            intercept=intercept,
            coefficients=coefficients,
        )
        violations.extend(prediction_violations)
        checks.append(
            _check(
                "regression.predictions",
                not prediction_violations,
                "Every published prediction and residual matches the fitted public parameters.",
                {
                    "dataset_rows": len(model.dataset.target_values),
                    "prediction_rows": len(predictions),
                },
            )
        )
        if prediction_violations:
            return self._report(checks, violations)

        split_violations = self._split(model, predictions)
        violations.extend(split_violations)
        counts = Counter(row["partition"] for row in predictions.values())
        checks.append(
            _check(
                "regression.split",
                not split_violations,
                "Train and test partitions are complete, disjoint, and have the expected sizes.",
                {
                    "train_count": counts["train"],
                    "test_count": counts["test"],
                },
            )
        )

        metric_violations = self._metrics(serialized.result, predictions)
        violations.extend(metric_violations)
        checks.append(
            _check(
                "regression.metrics",
                not metric_violations,
                "Published train and test metrics match values recomputed from predictions.",
                {"partition_count": 2},
            )
        )
        return self._report(checks, violations)

    def _parameters(
        self,
        model: RegressionModel,
        result: dict[str, JsonValue],
    ) -> tuple[
        tuple[float, dict[str, float]],
        list[ValidationViolation],
    ]:
        violations: list[ValidationViolation] = []
        intercept = _finite_number(result.get("intercept"))
        raw_coefficients = result.get("coefficients")
        coefficients: dict[str, float] = {}
        duplicates: list[str] = []
        invalid_rows: list[int] = []
        if isinstance(raw_coefficients, list):
            for index, row in enumerate(raw_coefficients):
                if not isinstance(row, dict):
                    invalid_rows.append(index)
                    continue
                feature = row.get("feature")
                value = _finite_number(row.get("value"))
                if not isinstance(feature, str) or not feature.strip() or value is None:
                    invalid_rows.append(index)
                    continue
                if feature in coefficients:
                    duplicates.append(feature)
                    continue
                coefficients[feature] = value

        expected = set(model.dataset.feature_names)
        if (
            intercept is None
            or set(coefficients) != expected
            or duplicates
            or invalid_rows
        ):
            violations.append(
                _violation(
                    "invalid_regression_parameters",
                    "regression.parameters",
                    "$.result",
                    "Regression parameters do not match the declared feature vector.",
                    {
                        "missing": sorted(expected - set(coefficients)),
                        "unknown": sorted(set(coefficients) - expected),
                        "duplicates": sorted(set(duplicates)),
                        "invalid_rows": invalid_rows,
                        "finite_intercept": intercept is not None,
                    },
                )
            )
        return (intercept or 0.0, coefficients), violations

    def _predictions(
        self,
        model: RegressionModel,
        result: dict[str, JsonValue],
        *,
        intercept: float,
        coefficients: dict[str, float],
    ) -> tuple[dict[int, dict[str, object]], list[ValidationViolation]]:
        raw_predictions = result.get("predictions")
        rows: dict[int, dict[str, object]] = {}
        invalid_indexes: list[int] = []
        duplicate_indexes: list[int] = []
        mismatched_indexes: list[int] = []
        if isinstance(raw_predictions, list):
            for position, row in enumerate(raw_predictions):
                if not isinstance(row, dict):
                    invalid_indexes.append(position)
                    continue
                row_index = row.get("row_index")
                actual = _finite_number(row.get("actual"))
                predicted = _finite_number(row.get("predicted"))
                residual = _finite_number(row.get("residual"))
                partition = row.get("partition")
                if (
                    isinstance(row_index, bool)
                    or not isinstance(row_index, int)
                    or not 0 <= row_index < len(model.dataset.target_values)
                    or actual is None
                    or predicted is None
                    or residual is None
                    or partition not in {"train", "test"}
                ):
                    invalid_indexes.append(position)
                    continue
                if row_index in rows:
                    duplicate_indexes.append(row_index)
                    continue
                features = model.dataset.feature_rows[row_index]
                expected_actual = model.dataset.target_values[row_index]
                expected_prediction = intercept + sum(
                    coefficients[name] * value
                    for name, value in zip(
                        model.dataset.feature_names, features, strict=True
                    )
                )
                expected_residual = expected_actual - expected_prediction
                if not all(
                    (
                        self._close(actual, expected_actual),
                        self._close(predicted, expected_prediction),
                        self._close(residual, expected_residual),
                    )
                ):
                    mismatched_indexes.append(row_index)
                rows[row_index] = {
                    "actual": actual,
                    "predicted": predicted,
                    "residual": residual,
                    "partition": partition,
                }

        missing = sorted(set(range(len(model.dataset.target_values))) - set(rows))
        violations: list[ValidationViolation] = []
        if (
            not isinstance(raw_predictions, list)
            or missing
            or invalid_indexes
            or duplicate_indexes
            or mismatched_indexes
        ):
            violations.append(
                _violation(
                    "invalid_regression_predictions",
                    "regression.predictions",
                    "$.result.predictions",
                    "Predictions are incomplete or inconsistent with the dataset and fitted parameters.",
                    {
                        "missing_rows": missing,
                        "invalid_rows": invalid_indexes,
                        "duplicate_rows": sorted(set(duplicate_indexes)),
                        "mismatched_rows": sorted(set(mismatched_indexes)),
                    },
                )
            )
        return rows, violations

    def _split(
        self,
        model: RegressionModel,
        predictions: dict[int, dict[str, object]],
    ) -> list[ValidationViolation]:
        counts = Counter(row["partition"] for row in predictions.values())
        row_count = len(model.dataset.target_values)
        expected_test = max(
            2,
            min(row_count - 2, int(round(row_count * model.options.test_fraction))),
        )
        if counts["test"] == expected_test and counts["train"] == row_count - expected_test:
            return []
        return [
            _violation(
                "invalid_regression_split",
                "regression.split",
                "$.result.predictions",
                "Train and test partition sizes do not match the declared test fraction.",
                {
                    "expected_train_count": row_count - expected_test,
                    "expected_test_count": expected_test,
                    "actual_train_count": counts["train"],
                    "actual_test_count": counts["test"],
                },
            )
        ]

    def _metrics(
        self,
        result: dict[str, JsonValue],
        predictions: dict[int, dict[str, object]],
    ) -> list[ValidationViolation]:
        mismatches: list[str] = []
        for partition in ("train", "test"):
            rows = [
                row for row in predictions.values() if row["partition"] == partition
            ]
            actual = [float(row["actual"]) for row in rows]
            predicted = [float(row["predicted"]) for row in rows]
            expected = _metrics(actual, predicted)
            published = result.get(f"{partition}_metrics")
            if not isinstance(published, dict):
                mismatches.append(partition)
                continue
            for name, expected_value in expected.items():
                published_value = published.get(name)
                if expected_value is None:
                    if published_value is not None:
                        mismatches.append(f"{partition}.{name}")
                elif not self._close(_finite_number(published_value), expected_value):
                    mismatches.append(f"{partition}.{name}")
        if not mismatches:
            return []
        return [
            _violation(
                "regression_metric_mismatch",
                "regression.metrics",
                "$.result",
                "Published regression metrics differ from independently recomputed values.",
                {"mismatches": sorted(set(mismatches))},
            )
        ]

    def _close(self, actual: float | None, expected: float) -> bool:
        return actual is not None and math.isclose(
            actual,
            expected,
            abs_tol=self._absolute_tolerance,
            rel_tol=self._relative_tolerance,
        )

    def _report(
        self,
        checks: list[ValidationCheck],
        violations: list[ValidationViolation],
    ) -> SolutionValidation:
        return SolutionValidation.from_checks(
            tuple(checks),
            violations=tuple(violations),
            tolerances={
                "absolute": self._absolute_tolerance,
                "relative": self._relative_tolerance,
            },
            limitations=(
                "Arithmetic consistency does not establish causality, generalization, fairness, or forecasting suitability.",
                "The validator does not prove that the chosen features, split strategy, or model family fit the business question.",
            ),
        )


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    normalized = float(value)
    return normalized if math.isfinite(normalized) else None


def _metrics(
    actual: list[float],
    predicted: list[float],
) -> dict[str, float | None]:
    residuals = [a - p for a, p in zip(actual, predicted, strict=True)]
    mse = sum(value * value for value in residuals) / len(residuals)
    mean = sum(actual) / len(actual)
    total = sum((value - mean) ** 2 for value in actual)
    return {
        "mae": sum(abs(value) for value in residuals) / len(residuals),
        "mse": mse,
        "rmse": math.sqrt(mse),
        "r_squared": (
            None
            if math.isclose(total, 0.0)
            else 1.0 - sum(value * value for value in residuals) / total
        ),
    }


def _check(
    code: str,
    passed: bool,
    description: str,
    measurements: dict[str, JsonValue],
) -> ValidationCheck:
    return ValidationCheck(
        code=code,
        status=(
            ValidationCheckStatus.PASSED
            if passed
            else ValidationCheckStatus.FAILED
        ),
        description=description,
        measurements=measurements,
    )


def _violation(
    code: str,
    check_code: str,
    path: str,
    message: str,
    measurements: dict[str, JsonValue] | None = None,
) -> ValidationViolation:
    return ValidationViolation(
        code=code,
        check_code=check_code,
        path=path,
        message=message,
        measurements=measurements or {},
    )
