from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta

from optees.application.codecs.forecasting_result_codec import ForecastingResultCodec
from optees.application.contracts.execution import SerializedResult
from optees.application.contracts.json_value import JsonValue
from optees.application.contracts.solution_validation import SolutionValidationStatus
from optees.application.usecases.forecast_time_series_usecase import (
    ForecastTimeSeriesUseCase,
)
from optees.application.validation import ForecastingIndependentSolutionValidator
from optees.data.adapters.forecasting import BaselineForecastingAdapter
from optees.domain.entities.forecasting import ForecastObservation
from optees.domain.models.forecasting import (
    ForecastingEvaluationOptions,
    ForecastingModel,
)
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


def _serialized() -> tuple[ForecastingModel, SerializedResult]:
    model = _model()
    solution = ForecastTimeSeriesUseCase(
        {ForecastingMethod.NAIVE: BaselineForecastingAdapter()}
    ).execute(model)
    return model, ForecastingResultCodec().serialize(solution)


def _tamper(
    serialized: SerializedResult,
    mutation,
) -> SerializedResult:
    result = deepcopy(serialized.result)
    mutation(result)
    return replace(serialized, result=result)


def _rows(result: dict[str, JsonValue]) -> list[dict[str, JsonValue]]:
    rows = result["points"]
    assert isinstance(rows, list)
    assert all(isinstance(row, dict) for row in rows)
    return rows  # type: ignore[return-value]


def test_valid_baseline_forecast_is_independently_verified() -> None:
    model, serialized = _serialized()

    report = ForecastingIndependentSolutionValidator()(model, serialized)

    assert report.status is SolutionValidationStatus.VERIFIED
    assert {check.code for check in report.checks} == {
        "forecast.temporal_structure",
        "forecast.arithmetic",
        "forecast.method_invariants",
    }


def test_tampered_future_timestamp_is_rejected() -> None:
    model, serialized = _serialized()

    tampered = _tamper(
        serialized,
        lambda result: _rows(result)[-1].update(
            {"timestamp": "2026-01-22T01:00:00"}
        ),
    )
    report = ForecastingIndependentSolutionValidator()(model, tampered)

    assert report.status is SolutionValidationStatus.FAILED
    assert report.violations[0].code == "forecast_temporal_mismatch"


def test_tampered_split_accounting_is_rejected() -> None:
    model, serialized = _serialized()

    def mutate(result: dict[str, JsonValue]) -> None:
        evaluation = result["evaluation"]
        assert isinstance(evaluation, dict)
        folds = evaluation["folds"]
        assert isinstance(folds, list)
        assert isinstance(folds[0], dict)
        folds[0]["training_size"] = 2
        folds[0]["origin"] = "2026-01-02T00:00:00"

    report = ForecastingIndependentSolutionValidator()(
        model,
        _tamper(serialized, mutate),
    )

    assert report.status is SolutionValidationStatus.FAILED
    assert any(
        violation.code == "forecast_temporal_mismatch"
        for violation in report.violations
    )


def test_tampered_metrics_are_recomputed_and_rejected() -> None:
    model, serialized = _serialized()

    def mutate(result: dict[str, JsonValue]) -> None:
        metrics = result["metrics"]
        assert isinstance(metrics, dict)
        metrics.update({"mae": 999, "rmse": 999, "mape": 999, "mase": 999})
        evaluation = result["evaluation"]
        assert isinstance(evaluation, dict)
        folds = evaluation["folds"]
        assert isinstance(folds, list)
        assert isinstance(folds[0], dict)
        fold_metrics = folds[0]["metrics"]
        assert isinstance(fold_metrics, dict)
        fold_metrics.update({"mae": 999, "rmse": 999, "mape": 999, "mase": 999})

    report = ForecastingIndependentSolutionValidator()(
        model,
        _tamper(serialized, mutate),
    )

    assert report.status is SolutionValidationStatus.FAILED
    assert any(
        violation.code == "forecast_arithmetic_mismatch"
        for violation in report.violations
    )


def test_tampered_historical_actual_and_residual_are_rejected() -> None:
    model, serialized = _serialized()

    def mutate(result: dict[str, JsonValue]) -> None:
        row = _rows(result)[0]
        assert isinstance(row["actual"], (int, float))
        actual = float(row["actual"]) + 1
        row["actual"] = actual
        row["residual"] = actual - float(row["predicted"])

    report = ForecastingIndependentSolutionValidator()(
        model,
        _tamper(serialized, mutate),
    )

    assert report.status is SolutionValidationStatus.FAILED
    assert any(
        violation.code == "forecast_arithmetic_mismatch"
        for violation in report.violations
    )


def test_tampered_baseline_prediction_and_parameter_are_rejected() -> None:
    model, serialized = _serialized()

    def mutate(result: dict[str, JsonValue]) -> None:
        row = _rows(result)[-1]
        row["predicted"] = float(row["predicted"]) + 1
        parameters = result["parameters"]
        assert isinstance(parameters, list)
        assert isinstance(parameters[0], dict)
        parameters[0]["value"] = 999

    report = ForecastingIndependentSolutionValidator()(
        model,
        _tamper(serialized, mutate),
    )

    assert report.status is SolutionValidationStatus.FAILED
    assert any(
        violation.code == "forecast_method_invariant_mismatch"
        for violation in report.violations
    )


def test_unsupported_interval_is_rejected_for_initial_methods() -> None:
    model, serialized = _serialized()

    def mutate(result: dict[str, JsonValue]) -> None:
        row = _rows(result)[-1]
        predicted = float(row["predicted"])
        row["interval"] = {
            "lower": predicted - 1,
            "upper": predicted + 1,
            "coverage": 0.95,
        }

    report = ForecastingIndependentSolutionValidator()(
        model,
        _tamper(serialized, mutate),
    )

    assert report.status is SolutionValidationStatus.FAILED
    assert any(
        "unsupported_interval" in violation.measurements["mismatches"]
        for violation in report.violations
        if violation.code == "forecast_method_invariant_mismatch"
    )


def test_malformed_public_result_is_rejected_before_arithmetic_checks() -> None:
    model, serialized = _serialized()
    tampered = _tamper(serialized, lambda result: result.pop("points"))

    report = ForecastingIndependentSolutionValidator()(model, tampered)

    assert report.status is SolutionValidationStatus.FAILED
    assert report.violations[0].code == "invalid_forecast_result_contract"
