from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from optees.application.contracts.solution_validation import SolutionValidationStatus
from optees.application.usecases.forecast_time_series_usecase import (
    ForecastTimeSeriesUseCase,
)
from optees.application.validation import ForecastingIndependentSolutionValidator
from optees.data.adapters.forecasting import BaselineForecastingAdapter
from optees.domain.entities.forecasting import (
    ForecastMetricSet,
    ForecastPoint,
    ForecastSegment,
    PredictionInterval,
)
from optees.domain.models.forecasting import (
    ForecastingEvaluationOptions,
    ForecastingModel,
)
from optees.domain.entities.forecasting import ForecastObservation
from optees.domain.value_objects.forecasting import (
    EvaluationStrategy,
    ForecastingFrequency,
    ForecastingMethod,
)


def _model() -> ForecastingModel:
    origin = datetime(2026, 1, 1)
    return ForecastingModel(
        target_name="demand",
        observations=tuple(
            ForecastObservation(origin + timedelta(days=index), value)
            for index, value in enumerate((10, 12, 14, 16, 18, 20))
        ),
        method=ForecastingMethod.NAIVE,
        horizon=2,
        frequency=ForecastingFrequency.DAILY,
        evaluation=ForecastingEvaluationOptions(
            strategy=EvaluationStrategy.ROLLING_ORIGIN,
            origin_count=2,
            step=1,
            evaluation_horizon=2,
            minimum_training_size=2,
        ),
    )


def _solution():
    model = _model()
    solution = ForecastTimeSeriesUseCase(
        {ForecastingMethod.NAIVE: BaselineForecastingAdapter()}
    ).execute(model)
    return model, solution


def test_valid_baseline_forecast_is_independently_verified() -> None:
    model, solution = _solution()

    report = ForecastingIndependentSolutionValidator()(model, solution)

    assert report.status is SolutionValidationStatus.VERIFIED
    assert {check.code for check in report.checks} == {
        "forecast.temporal_structure",
        "forecast.arithmetic",
        "forecast.method_invariants",
    }


def test_tampered_future_timestamp_is_rejected() -> None:
    model, solution = _solution()
    points = list(solution.points)
    future_index = next(
        index
        for index, point in enumerate(points)
        if point.segment is ForecastSegment.FUTURE
    )
    original = points[future_index]
    points[future_index] = ForecastPoint(
        timestamp=original.timestamp + timedelta(hours=1),
        predicted=original.predicted,
        segment=ForecastSegment.FUTURE,
    )
    tampered = replace(solution, points=tuple(points))

    report = ForecastingIndependentSolutionValidator()(model, tampered)

    assert report.status is SolutionValidationStatus.FAILED
    assert report.violations[0].code == "forecast_temporal_mismatch"


def test_tampered_split_accounting_is_rejected() -> None:
    model, solution = _solution()
    first_fold = solution.evaluation_folds[0]
    tampered_fold = replace(
        first_fold,
        origin=model.observations[1].timestamp,
        training_size=2,
    )
    tampered = replace(
        solution,
        evaluation_folds=(tampered_fold,) + solution.evaluation_folds[1:],
    )

    report = ForecastingIndependentSolutionValidator()(model, tampered)

    assert report.status is SolutionValidationStatus.FAILED
    assert any(
        violation.code == "forecast_temporal_mismatch"
        for violation in report.violations
    )


def test_tampered_metrics_are_recomputed_and_rejected() -> None:
    model, solution = _solution()
    first_fold = replace(
        solution.evaluation_folds[0],
        metrics=ForecastMetricSet(mae=999, rmse=999, mape=999, mase=999),
    )
    tampered = replace(
        solution,
        metrics=ForecastMetricSet(mae=999, rmse=999, mape=999, mase=999),
        evaluation_folds=(first_fold,) + solution.evaluation_folds[1:],
    )

    report = ForecastingIndependentSolutionValidator()(model, tampered)

    assert report.status is SolutionValidationStatus.FAILED
    assert any(
        violation.code == "forecast_arithmetic_mismatch"
        for violation in report.violations
    )


def test_tampered_historical_actual_and_residual_are_rejected() -> None:
    model, solution = _solution()
    points = list(solution.points)
    fitted_index = next(
        index
        for index, point in enumerate(points)
        if point.segment is ForecastSegment.FITTED
    )
    original = points[fitted_index]
    assert original.actual is not None
    altered_actual = original.actual + 1
    points[fitted_index] = ForecastPoint(
        timestamp=original.timestamp,
        predicted=original.predicted,
        actual=altered_actual,
        residual=altered_actual - original.predicted,
        segment=ForecastSegment.FITTED,
    )
    tampered = replace(solution, points=tuple(points))

    report = ForecastingIndependentSolutionValidator()(model, tampered)

    assert report.status is SolutionValidationStatus.FAILED
    assert any(
        violation.code == "forecast_arithmetic_mismatch"
        for violation in report.violations
    )


def test_tampered_baseline_prediction_and_parameter_are_rejected() -> None:
    model, solution = _solution()
    points = list(solution.points)
    last = points[-1]
    points[-1] = ForecastPoint(
        timestamp=last.timestamp,
        predicted=last.predicted + 1,
        segment=ForecastSegment.FUTURE,
    )
    tampered = replace(
        solution,
        points=tuple(points),
        parameters=(("last_value", 999),),
    )

    report = ForecastingIndependentSolutionValidator()(model, tampered)

    assert report.status is SolutionValidationStatus.FAILED
    assert any(
        violation.code == "forecast_method_invariant_mismatch"
        for violation in report.violations
    )


def test_unsupported_interval_is_rejected_for_initial_methods() -> None:
    model, solution = _solution()
    points = list(solution.points)
    last = points[-1]
    points[-1] = ForecastPoint(
        timestamp=last.timestamp,
        predicted=last.predicted,
        segment=ForecastSegment.FUTURE,
        interval=PredictionInterval(
            lower=last.predicted - 1,
            upper=last.predicted + 1,
            coverage=0.95,
        ),
    )
    tampered = replace(solution, points=tuple(points))

    report = ForecastingIndependentSolutionValidator()(model, tampered)

    assert report.status is SolutionValidationStatus.FAILED
    assert any(
        "unsupported_interval" in violation.measurements["mismatches"]
        for violation in report.violations
        if violation.code == "forecast_method_invariant_mismatch"
    )
