from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime

from optees.application.contracts.json_value import JsonValue
from optees.domain.entities.forecasting import ForecastObservation
from optees.domain.models.forecasting import (
    ForecastingEvaluationOptions,
    ForecastingMethodOptions,
    ForecastingModel,
)
from optees.domain.value_objects.forecasting import (
    EvaluationStrategy,
    ForecastingFrequency,
    ForecastingMethod,
    MissingPeriodPolicy,
)

FORECASTING_JSON_VERSION = "1"
FORECASTING_PROBLEM_TYPE = "univariate_forecasting"

_ROOT_FIELDS = {
    "version",
    "problem_type",
    "target_name",
    "frequency",
    "horizon",
    "method",
    "season_length",
    "missing_period_policy",
    "observations",
    "evaluation",
    "method_options",
}
_REQUIRED_ROOT_FIELDS = {
    "version",
    "problem_type",
    "target_name",
    "frequency",
    "horizon",
    "method",
    "observations",
}
_OBSERVATION_FIELDS = {"timestamp", "value"}
_EVALUATION_FIELDS = {
    "strategy",
    "holdout_size",
    "origin_count",
    "step",
    "evaluation_horizon",
    "minimum_training_size",
}
_METHOD_OPTION_FIELDS = {"max_iterations", "tolerance"}


def forecasting_model_from_public_dict(
    payload: dict[str, JsonValue],
) -> ForecastingModel:
    _reject_unknown(payload, _ROOT_FIELDS, path="$")
    missing = sorted(_REQUIRED_ROOT_FIELDS - payload.keys())
    if missing:
        raise _error(
            "missing_field",
            "$",
            "missing required fields: " + ", ".join(missing),
        )
    if payload["version"] != FORECASTING_JSON_VERSION:
        raise _error(
            "unsupported_version",
            "$.version",
            f"must equal {FORECASTING_JSON_VERSION!r}",
        )
    if payload["problem_type"] != FORECASTING_PROBLEM_TYPE:
        raise _error(
            "invalid_problem_type",
            "$.problem_type",
            f"must equal {FORECASTING_PROBLEM_TYPE!r}",
        )

    observations = _parse_observations(payload["observations"])
    evaluation = _parse_evaluation(payload.get("evaluation"))
    method_options = _parse_method_options(payload.get("method_options"))
    season_length = payload.get("season_length")
    if season_length is not None:
        season_length = _integer(season_length, "$.season_length")

    try:
        return ForecastingModel(
            target_name=_string(payload["target_name"], "$.target_name"),
            observations=observations,
            method=ForecastingMethod.from_value(
                _canonical_enum(
                    payload["method"],
                    "$.method",
                    {item.value for item in ForecastingMethod},
                )
            ),
            horizon=_integer(payload["horizon"], "$.horizon"),
            frequency=ForecastingFrequency.from_value(
                _canonical_enum(
                    payload["frequency"],
                    "$.frequency",
                    {item.value for item in ForecastingFrequency},
                )
            ),
            season_length=season_length,
            missing_period_policy=MissingPeriodPolicy.from_value(
                _canonical_enum(
                    payload.get("missing_period_policy", "reject"),
                    "$.missing_period_policy",
                    {item.value for item in MissingPeriodPolicy},
                )
            ),
            evaluation=evaluation,
            method_options=method_options,
        )
    except ValueError as exc:
        raise _error("invalid_model", "$", str(exc)) from exc


def _parse_observations(value: JsonValue) -> tuple[ForecastObservation, ...]:
    if not isinstance(value, list):
        raise _error("invalid_type", "$.observations", "must be an array")
    observations: list[ForecastObservation] = []
    for index, row in enumerate(value):
        path = f"$.observations[{index}]"
        if not isinstance(row, dict):
            raise _error("invalid_type", path, "must be an object")
        _reject_unknown(row, _OBSERVATION_FIELDS, path=path)
        missing = sorted(_OBSERVATION_FIELDS - row.keys())
        if missing:
            raise _error(
                "missing_field",
                path,
                "missing required fields: " + ", ".join(missing),
            )
        observations.append(
            ForecastObservation(
                timestamp=_timestamp(row["timestamp"], f"{path}.timestamp"),
                value=_finite_number(row["value"], f"{path}.value"),
            )
        )
    return tuple(observations)


def _parse_evaluation(value: JsonValue | None) -> ForecastingEvaluationOptions:
    if value is None:
        return ForecastingEvaluationOptions()
    if not isinstance(value, dict):
        raise _error("invalid_type", "$.evaluation", "must be an object")
    _reject_unknown(value, _EVALUATION_FIELDS, path="$.evaluation")
    try:
        return ForecastingEvaluationOptions(
            strategy=EvaluationStrategy.from_value(
                _canonical_enum(
                    value.get("strategy", "holdout"),
                    "$.evaluation.strategy",
                    {item.value for item in EvaluationStrategy},
                )
            ),
            holdout_size=_integer(
                value.get("holdout_size", 1),
                "$.evaluation.holdout_size",
            ),
            origin_count=_integer(
                value.get("origin_count", 3),
                "$.evaluation.origin_count",
            ),
            step=_integer(value.get("step", 1), "$.evaluation.step"),
            evaluation_horizon=_integer(
                value.get("evaluation_horizon", 1),
                "$.evaluation.evaluation_horizon",
            ),
            minimum_training_size=_integer(
                value.get("minimum_training_size", 2),
                "$.evaluation.minimum_training_size",
            ),
        )
    except ValueError as exc:
        raise _error("invalid_evaluation", "$.evaluation", str(exc)) from exc


def _parse_method_options(value: JsonValue | None) -> ForecastingMethodOptions:
    if value is None:
        return ForecastingMethodOptions()
    if not isinstance(value, dict):
        raise _error("invalid_type", "$.method_options", "must be an object")
    _reject_unknown(value, _METHOD_OPTION_FIELDS, path="$.method_options")
    try:
        return ForecastingMethodOptions(
            max_iterations=_integer(
                value.get("max_iterations", 1_000),
                "$.method_options.max_iterations",
            ),
            tolerance=_finite_number(
                value.get("tolerance", 1e-8),
                "$.method_options.tolerance",
            ),
        )
    except ValueError as exc:
        raise _error("invalid_method_options", "$.method_options", str(exc)) from exc


def _reject_unknown(
    value: Mapping[str, JsonValue],
    allowed: set[str],
    *,
    path: str,
) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise _error(
            "unknown_field",
            path,
            "unknown fields: " + ", ".join(unknown),
        )


def _string(value: JsonValue, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _error("invalid_type", path, "must be a non-empty string")
    return value.strip()


def _canonical_enum(value: JsonValue, path: str, allowed: set[str]) -> str:
    parsed = _string(value, path)
    if parsed not in allowed:
        raise _error(
            "invalid_value",
            path,
            "must be one of: " + ", ".join(sorted(allowed)),
        )
    return parsed


def _integer(value: JsonValue, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error("invalid_type", path, "must be an integer")
    return value


def _finite_number(value: JsonValue, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _error("invalid_type", path, "must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise _error("invalid_value", path, "must be a finite number")
    return number


def _timestamp(value: JsonValue, path: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise _error("invalid_type", path, "must be a non-empty ISO 8601 string")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise _error("invalid_timestamp", path, "must be a valid ISO 8601 timestamp") from exc


def _error(code: str, path: str, message: str) -> ValueError:
    return ValueError(f"forecast.{code}: {path} {message}")
