from __future__ import annotations

import math
from datetime import datetime

from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.json_value import JsonValue
from optees.application.contracts.solution_validation import (
    SolutionValidation,
    ValidationCheck,
    ValidationCheckStatus,
    ValidationViolation,
)
from optees.domain.entities.forecasting import (
    ForecastEvaluationFold,
    ForecastMetricSet,
    ForecastPoint,
    ForecastSegment,
    ForecastingSolution,
    PredictionInterval,
)
from optees.domain.models.forecasting import ForecastingModel
from optees.domain.value_objects.forecasting import (
    EvaluationStrategy,
    ForecastEvaluationStatus,
    ForecastingMethod,
    ForecastingStatus,
)


class ForecastingIndependentSolutionValidator:
    """Verify public forecasting arithmetic and temporal accounting."""

    def __init__(
        self,
        *,
        absolute_tolerance: float = 1e-9,
        relative_tolerance: float = 1e-9,
    ) -> None:
        for value in (absolute_tolerance, relative_tolerance):
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError(
                    "Forecast validation tolerances must be finite and non-negative"
                )
        self._absolute_tolerance = float(absolute_tolerance)
        self._relative_tolerance = float(relative_tolerance)

    def __call__(
        self,
        model: ForecastingModel,
        serialized: SerializedResult,
    ) -> SolutionValidation:
        if serialized.mathematical_status is not MathematicalStatus.FEASIBLE:
            return SolutionValidation.not_available(
                "No complete forecast is available for independent validation."
            )

        checks: list[ValidationCheck] = []
        violations: list[ValidationViolation] = []
        try:
            solution = _solution_from_public_result(serialized.result)
        except (KeyError, TypeError, ValueError) as exc:
            violation = _violation(
                "invalid_forecast_result_contract",
                "forecast.public_result",
                "$.result",
                "The public forecast result does not match schema version 1.",
                {"reason": str(exc)},
            )
            return SolutionValidation.from_checks(
                (
                    _check(
                        "forecast.public_result",
                        False,
                        "The serialized result contains the complete Forecasting v1 structure.",
                        {},
                    ),
                ),
                violations=(violation,),
                tolerances={
                    "absolute": self._absolute_tolerance,
                    "relative": self._relative_tolerance,
                },
            )

        temporal_violations = self._validate_temporal_structure(model, solution)
        violations.extend(temporal_violations)
        checks.append(
            _check(
                "forecast.temporal_structure",
                not temporal_violations,
                "Forecast rows and evaluation folds match the declared chronological windows.",
                {
                    "forecast_point_count": len(solution.points),
                    "evaluation_fold_count": len(solution.evaluation_folds),
                },
            )
        )

        arithmetic_violations = self._validate_arithmetic(model, solution)
        violations.extend(arithmetic_violations)
        checks.append(
            _check(
                "forecast.arithmetic",
                not arithmetic_violations,
                "Actual values, residuals, and published metrics recompute from public rows.",
                {"evaluated_prediction_count": self._evaluated_count(solution)},
            )
        )

        method_violations = self._validate_method_invariants(model, solution)
        violations.extend(method_violations)
        checks.append(
            _check(
                "forecast.method_invariants",
                not method_violations,
                "Published rows and parameters satisfy invariants of the declared method.",
                {"method": model.method.value},
            )
        )

        limitations: tuple[str, ...] = ()
        partial = solution.evaluation_status in {
            ForecastEvaluationStatus.PARTIAL,
            ForecastEvaluationStatus.FAILED,
        }
        if model.method is ForecastingMethod.HOLT_WINTERS_ADDITIVE:
            partial = True
            limitations = (
                "Independent validation does not refit the Holt-Winters estimator.",
            )
        return SolutionValidation.from_checks(
            tuple(checks),
            violations=tuple(violations),
            tolerances={
                "absolute": self._absolute_tolerance,
                "relative": self._relative_tolerance,
            },
            limitations=limitations,
            partial=partial,
        )

    def _validate_temporal_structure(
        self,
        model: ForecastingModel,
        solution: ForecastingSolution,
    ) -> list[ValidationViolation]:
        mismatches: list[str] = []
        if solution.method is not model.method:
            mismatches.append("method")
        if solution.origin != model.forecast_origin:
            mismatches.append("origin")

        fitted = tuple(
            point for point in solution.points if point.segment is ForecastSegment.FITTED
        )
        future = tuple(
            point for point in solution.points if point.segment is ForecastSegment.FUTURE
        )
        historical_by_timestamp = {
            observation.timestamp: observation for observation in model.observations
        }
        if any(point.timestamp not in historical_by_timestamp for point in fitted):
            mismatches.append("fitted_timestamps")
        if tuple(point.timestamp for point in future) != model.future_timestamps():
            mismatches.append("future_timestamps")

        expected_windows = self._evaluation_windows(model)
        actual_windows = tuple(
            (
                fold.training_size,
                len(fold.points),
                fold.origin,
                tuple(point.timestamp for point in fold.points),
            )
            for fold in solution.evaluation_folds
        )
        if model.evaluation.strategy is EvaluationStrategy.NONE:
            if (
                solution.evaluation_status is not ForecastEvaluationStatus.NOT_REQUESTED
                or actual_windows
            ):
                mismatches.append("evaluation_not_requested")
        else:
            expected_by_training_size = {
                training_size: (
                    target_size,
                    model.observations[training_size - 1].timestamp,
                    tuple(
                        observation.timestamp
                        for observation in model.observations[
                            training_size : training_size + target_size
                        ]
                    ),
                )
                for training_size, target_size in expected_windows
            }
            seen_training_sizes: set[int] = set()
            for training_size, target_size, origin, timestamps in actual_windows:
                expected = expected_by_training_size.get(training_size)
                if (
                    expected is None
                    or training_size in seen_training_sizes
                    or expected != (target_size, origin, timestamps)
                ):
                    mismatches.append(f"evaluation_fold_{training_size}")
                seen_training_sizes.add(training_size)
            if (
                solution.evaluation_status is ForecastEvaluationStatus.EVALUATED
                and seen_training_sizes != set(expected_by_training_size)
            ):
                mismatches.append("evaluation_fold_accounting")

        if not mismatches:
            return []
        return [
            _violation(
                "forecast_temporal_mismatch",
                "forecast.temporal_structure",
                "$.result",
                "Forecast timestamps or evaluation windows do not match the model.",
                {"mismatches": sorted(set(mismatches))},
            )
        ]

    def _validate_arithmetic(
        self,
        model: ForecastingModel,
        solution: ForecastingSolution,
    ) -> list[ValidationViolation]:
        mismatches: list[str] = []
        historical_by_timestamp = {
            observation.timestamp: observation.value for observation in model.observations
        }
        for index, point in enumerate(solution.points):
            if point.segment is ForecastSegment.FUTURE:
                continue
            expected_actual = historical_by_timestamp.get(point.timestamp)
            if (
                expected_actual is None
                or point.actual is None
                or point.residual is None
                or not self._close(point.actual, expected_actual)
                or not self._close(point.residual, expected_actual - point.predicted)
            ):
                mismatches.append(f"point_{index}")

        scales: list[float | None] = []
        all_evaluation_points: list[ForecastPoint] = []
        for index, fold in enumerate(solution.evaluation_folds):
            scale = self._mase_scale(model, fold.training_size)
            expected_metrics = self._metrics(
                fold.points,
                scales=(scale,) * len(fold.points),
            )
            if not self._metric_sets_close(fold.metrics, expected_metrics):
                mismatches.append(f"fold_metrics_{index}")
            for point in fold.points:
                expected_actual = historical_by_timestamp.get(point.timestamp)
                if (
                    expected_actual is None
                    or point.actual is None
                    or point.residual is None
                    or not self._close(point.actual, expected_actual)
                    or not self._close(point.residual, expected_actual - point.predicted)
                ):
                    mismatches.append(f"fold_point_{index}")
            all_evaluation_points.extend(fold.points)
            scales.extend((scale,) * len(fold.points))

        expected_aggregate = self._metrics(
            tuple(all_evaluation_points),
            scales=tuple(scales),
        )
        if not self._metric_sets_close(solution.metrics, expected_aggregate):
            mismatches.append("aggregate_metrics")
        if not mismatches:
            return []
        return [
            _violation(
                "forecast_arithmetic_mismatch",
                "forecast.arithmetic",
                "$.result",
                "Forecast values, residuals, or metrics failed independent recomputation.",
                {"mismatches": sorted(set(mismatches))},
            )
        ]

    def _validate_method_invariants(
        self,
        model: ForecastingModel,
        solution: ForecastingSolution,
    ) -> list[ValidationViolation]:
        mismatches: list[str] = []
        if any(point.interval is not None for point in solution.points) or any(
            point.interval is not None
            for fold in solution.evaluation_folds
            for point in fold.points
        ):
            mismatches.append("unsupported_interval")

        parameters = dict(solution.parameters)
        if model.method is ForecastingMethod.NAIVE:
            if not self._close(parameters.get("last_value"), model.observations[-1].value):
                mismatches.append("last_value_parameter")
        elif model.method is ForecastingMethod.SEASONAL_NAIVE:
            if not self._close(parameters.get("season_length"), float(model.season_length)):
                mismatches.append("season_length_parameter")

        for index, fold in enumerate(solution.evaluation_folds):
            expected = self._expected_baseline_predictions(
                model,
                training_size=fold.training_size,
                count=len(fold.points),
            )
            if expected is not None and not self._predictions_close(fold.points, expected):
                mismatches.append(f"evaluation_predictions_{index}")

        future = tuple(
            point for point in solution.points if point.segment is ForecastSegment.FUTURE
        )
        expected_future = self._expected_baseline_predictions(
            model,
            training_size=len(model.observations),
            count=model.horizon,
        )
        if expected_future is not None and not self._predictions_close(
            future, expected_future
        ):
            mismatches.append("future_predictions")

        fitted = tuple(
            point for point in solution.points if point.segment is ForecastSegment.FITTED
        )
        expected_fitted = self._expected_baseline_fitted(model)
        if expected_fitted is not None:
            published_fitted = {
                point.timestamp: point.predicted for point in fitted
            }
            if set(published_fitted) != set(expected_fitted) or any(
                not self._close(published_fitted[timestamp], prediction)
                for timestamp, prediction in expected_fitted.items()
            ):
                mismatches.append("fitted_predictions")

        if not mismatches:
            return []
        return [
            _violation(
                "forecast_method_invariant_mismatch",
                "forecast.method_invariants",
                "$.result",
                "Forecast output violates an invariant of the declared method.",
                {"mismatches": sorted(set(mismatches))},
            )
        ]

    @staticmethod
    def _evaluation_windows(model: ForecastingModel) -> tuple[tuple[int, int], ...]:
        options = model.evaluation
        if options.strategy is EvaluationStrategy.NONE:
            return ()
        if options.strategy is EvaluationStrategy.HOLDOUT:
            return ((len(model.observations) - options.holdout_size, options.holdout_size),)
        last_training_size = len(model.observations) - options.evaluation_horizon
        first_training_size = last_training_size - (options.origin_count - 1) * options.step
        return tuple(
            (
                first_training_size + index * options.step,
                options.evaluation_horizon,
            )
            for index in range(options.origin_count)
        )

    def _mase_scale(self, model: ForecastingModel, training_size: int) -> float | None:
        training = model.observations[:training_size]
        lag = model.season_length or 1
        if len(training) <= lag:
            return None
        differences = tuple(
            abs(training[index].value - training[index - lag].value)
            for index in range(lag, len(training))
        )
        scale = sum(differences) / len(differences)
        return scale if scale > 0 else None

    def _metrics(
        self,
        points: tuple[ForecastPoint, ...],
        *,
        scales: tuple[float | None, ...],
    ) -> ForecastMetricSet:
        if not points:
            return ForecastMetricSet()
        if any(point.actual is None for point in points):
            return ForecastMetricSet()
        errors = tuple(float(point.actual) - point.predicted for point in points)
        absolute_errors = tuple(abs(error) for error in errors)
        actuals = tuple(float(point.actual) for point in points)
        mae = sum(absolute_errors) / len(points)
        rmse = math.sqrt(sum(error * error for error in errors) / len(points))
        mape = (
            None
            if any(actual == 0 for actual in actuals)
            else 100
            * sum(
                abs(error / actual)
                for error, actual in zip(errors, actuals, strict=True)
            )
            / len(points)
        )
        mase = (
            None
            if len(scales) != len(points) or any(scale is None for scale in scales)
            else sum(
                error / scale
                for error, scale in zip(absolute_errors, scales, strict=True)
                if scale is not None
            )
            / len(points)
        )
        return ForecastMetricSet(mae=mae, rmse=rmse, mape=mape, mase=mase)

    def _metric_sets_close(
        self,
        published: ForecastMetricSet,
        expected: ForecastMetricSet,
    ) -> bool:
        return all(
            self._optional_close(getattr(published, name), getattr(expected, name))
            for name in ("mae", "rmse", "mape", "mase")
        )

    def _optional_close(
        self,
        actual: float | None,
        expected: float | None,
    ) -> bool:
        return (
            actual is None and expected is None
            or actual is not None
            and expected is not None
            and self._close(actual, expected)
        )

    def _close(self, actual: float | None, expected: float) -> bool:
        return actual is not None and math.isclose(
            actual,
            expected,
            abs_tol=self._absolute_tolerance,
            rel_tol=self._relative_tolerance,
        )

    def _expected_baseline_predictions(
        self,
        model: ForecastingModel,
        *,
        training_size: int,
        count: int,
    ) -> tuple[float, ...] | None:
        if model.method is ForecastingMethod.NAIVE:
            return (model.observations[training_size - 1].value,) * count
        if model.method is ForecastingMethod.SEASONAL_NAIVE:
            assert model.season_length is not None
            season = model.observations[
                training_size - model.season_length : training_size
            ]
            return tuple(
                season[index % model.season_length].value for index in range(count)
            )
        return None

    @staticmethod
    def _expected_baseline_fitted(
        model: ForecastingModel,
    ) -> dict[datetime, float] | None:
        if model.method is ForecastingMethod.NAIVE:
            return {
                model.observations[index].timestamp: model.observations[index - 1].value
                for index in range(1, len(model.observations))
            }
        if model.method is ForecastingMethod.SEASONAL_NAIVE:
            assert model.season_length is not None
            return {
                model.observations[index].timestamp: model.observations[
                    index - model.season_length
                ].value
                for index in range(model.season_length, len(model.observations))
            }
        return None

    def _predictions_close(
        self,
        points: tuple[ForecastPoint, ...],
        expected: tuple[float, ...],
    ) -> bool:
        return len(points) == len(expected) and all(
            self._close(point.predicted, prediction)
            for point, prediction in zip(points, expected, strict=True)
        )

    @staticmethod
    def _evaluated_count(solution: ForecastingSolution) -> int:
        return sum(len(fold.points) for fold in solution.evaluation_folds)


def _check(
    code: str,
    passed: bool,
    description: str,
    measurements: dict[str, object],
) -> ValidationCheck:
    return ValidationCheck(
        code=code,
        status=(
            ValidationCheckStatus.PASSED if passed else ValidationCheckStatus.FAILED
        ),
        description=description,
        measurements=measurements,  # type: ignore[arg-type]
    )


def _violation(
    code: str,
    check_code: str,
    path: str,
    message: str,
    measurements: dict[str, object],
) -> ValidationViolation:
    return ValidationViolation(
        code=code,
        check_code=check_code,
        path=path,
        message=message,
        measurements=measurements,  # type: ignore[arg-type]
    )


def _solution_from_public_result(
    result: dict[str, JsonValue],
) -> ForecastingSolution:
    required = {
        "forecast_available",
        "method",
        "origin",
        "points",
        "metrics",
        "evaluation",
        "parameters",
    }
    if set(result) != required:
        raise ValueError("result fields do not match the Forecasting v1 contract")
    if result["forecast_available"] is not True:
        raise ValueError("forecast_available must be true for a feasible result")
    evaluation = _object(result["evaluation"], "$.result.evaluation")
    if set(evaluation) != {"status", "folds"}:
        raise ValueError("$.result.evaluation has invalid fields")
    raw_folds = _array(evaluation["folds"], "$.result.evaluation.folds")
    raw_parameters = _array(result["parameters"], "$.result.parameters")
    return ForecastingSolution(
        status=ForecastingStatus.FORECASTED,
        method=ForecastingMethod.from_value(
            _string(result["method"], "$.result.method")
        ),
        origin=_timestamp(result["origin"], "$.result.origin"),
        points=tuple(
            _point(row, f"$.result.points[{index}]")
            for index, row in enumerate(
                _array(result["points"], "$.result.points")
            )
        ),
        metrics=_metric_set(result["metrics"], "$.result.metrics"),
        evaluation_status=ForecastEvaluationStatus(
            _string(evaluation["status"], "$.result.evaluation.status")
        ),
        evaluation_folds=tuple(
            _fold(row, f"$.result.evaluation.folds[{index}]")
            for index, row in enumerate(raw_folds)
        ),
        parameters=tuple(
            _parameter(row, f"$.result.parameters[{index}]")
            for index, row in enumerate(raw_parameters)
        ),
    )


def _point(value: JsonValue, path: str) -> ForecastPoint:
    row = _object(value, path)
    if set(row) != {
        "timestamp",
        "actual",
        "predicted",
        "residual",
        "interval",
        "segment",
    }:
        raise ValueError(f"{path} has invalid fields")
    interval_value = row["interval"]
    interval = None
    if interval_value is not None:
        interval_row = _object(interval_value, f"{path}.interval")
        if set(interval_row) != {"lower", "upper", "coverage"}:
            raise ValueError(f"{path}.interval has invalid fields")
        interval = PredictionInterval(
            lower=_number(interval_row["lower"], f"{path}.interval.lower"),
            upper=_number(interval_row["upper"], f"{path}.interval.upper"),
            coverage=_number(
                interval_row["coverage"],
                f"{path}.interval.coverage",
            ),
        )
    return ForecastPoint(
        timestamp=_timestamp(row["timestamp"], f"{path}.timestamp"),
        actual=_optional_number(row["actual"], f"{path}.actual"),
        predicted=_number(row["predicted"], f"{path}.predicted"),
        residual=_optional_number(row["residual"], f"{path}.residual"),
        interval=interval,
        segment=ForecastSegment(_string(row["segment"], f"{path}.segment")),
    )


def _fold(value: JsonValue, path: str) -> ForecastEvaluationFold:
    row = _object(value, path)
    if set(row) != {"origin", "training_size", "points", "metrics"}:
        raise ValueError(f"{path} has invalid fields")
    training_size = row["training_size"]
    if isinstance(training_size, bool) or not isinstance(training_size, int):
        raise ValueError(f"{path}.training_size must be an integer")
    return ForecastEvaluationFold(
        origin=_timestamp(row["origin"], f"{path}.origin"),
        training_size=training_size,
        points=tuple(
            _point(item, f"{path}.points[{index}]")
            for index, item in enumerate(_array(row["points"], f"{path}.points"))
        ),
        metrics=_metric_set(row["metrics"], f"{path}.metrics"),
    )


def _metric_set(value: JsonValue, path: str) -> ForecastMetricSet:
    row = _object(value, path)
    if set(row) != {"mae", "rmse", "mape", "mase"}:
        raise ValueError(f"{path} has invalid fields")
    return ForecastMetricSet(
        mae=_optional_number(row["mae"], f"{path}.mae"),
        rmse=_optional_number(row["rmse"], f"{path}.rmse"),
        mape=_optional_number(row["mape"], f"{path}.mape"),
        mase=_optional_number(row["mase"], f"{path}.mase"),
    )


def _parameter(value: JsonValue, path: str) -> tuple[str, float]:
    row = _object(value, path)
    if set(row) != {"name", "value"}:
        raise ValueError(f"{path} has invalid fields")
    return (
        _string(row["name"], f"{path}.name"),
        _number(row["value"], f"{path}.value"),
    )


def _object(value: JsonValue, path: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    return value


def _array(value: JsonValue, path: str) -> list[JsonValue]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    return value


def _string(value: JsonValue, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value.strip()


def _timestamp(value: JsonValue, path: str) -> datetime:
    raw = _string(value, path)
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{path} must be a valid ISO 8601 timestamp") from exc


def _number(value: JsonValue, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{path} must be a finite number")
    return number


def _optional_number(value: JsonValue, path: str) -> float | None:
    return None if value is None else _number(value, path)
