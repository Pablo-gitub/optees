"""Numerical helpers for the first transparent supervised-regression slice."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np


def solve_regression(problem: Mapping[str, object]) -> dict[str, object]:
    """Fit OLS or Ridge without leaking test observations into training.

    For the augmented training matrix ``Z = [1, X]``, OLS minimizes
    ``||Z beta - y||^2``. Ridge instead solves
    ``(Z^T Z + alpha P) beta = Z^T y`` where ``P[0, 0] = 0``: the intercept
    remains unpenalized while feature coefficients are shrunk.
    """
    feature_names, features, targets = _read_dataset(problem)
    method = str(problem.get("method", "OLS"))
    test_fraction = _finite_float(problem.get("test_fraction", 0.2), "test_fraction")
    random_seed = _non_negative_int(problem.get("random_seed", 42), "random_seed")
    ridge_alpha = _finite_float(problem.get("ridge_alpha", 1.0), "ridge_alpha")
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    if ridge_alpha <= 0:
        raise ValueError("ridge_alpha must be positive")

    train_indices, test_indices = _split_indices(
        row_count=len(targets),
        test_fraction=test_fraction,
        random_seed=random_seed,
    )
    train_features, train_targets = features[train_indices], targets[train_indices]
    test_features, test_targets = features[test_indices], targets[test_indices]

    beta = _fit(train_features, train_targets, method, ridge_alpha)
    train_predictions = _predict(train_features, beta)
    test_predictions = _predict(test_features, beta)
    predictions = _prediction_rows(train_indices, train_targets, train_predictions, "train")
    predictions.extend(_prediction_rows(test_indices, test_targets, test_predictions, "test"))
    predictions.sort(key=lambda row: int(row["row_index"]))

    return {
        "status": "Trained",
        "intercept": float(beta[0]),
        "coefficients": {
            name: float(value) for name, value in zip(feature_names, beta[1:], strict=True)
        },
        "train_metrics": _metrics(train_targets, train_predictions),
        "test_metrics": _metrics(test_targets, test_predictions),
        "predictions": predictions,
        "extras": {
            "method": method,
            "train_count": int(len(train_indices)),
            "test_count": int(len(test_indices)),
            "random_seed": random_seed,
        },
    }


def _read_dataset(problem: Mapping[str, object]) -> tuple[tuple[str, ...], np.ndarray, np.ndarray]:
    raw_names = problem.get("feature_names")
    raw_rows = problem.get("feature_rows")
    raw_targets = problem.get("target_values")
    if not isinstance(raw_names, list) or not raw_names:
        raise ValueError("feature_names must be a non-empty list")
    feature_names = tuple(str(name).strip() for name in raw_names)
    if any(not name for name in feature_names) or len(set(feature_names)) != len(feature_names):
        raise ValueError("feature_names must be non-empty and unique")
    if not isinstance(raw_rows, list) or not isinstance(raw_targets, list):
        raise ValueError("feature_rows and target_values must be lists")
    if len(raw_rows) != len(raw_targets) or len(raw_rows) < 4:
        raise ValueError("Regression data must contain at least four aligned rows")
    try:
        features = np.asarray(raw_rows, dtype=float)
        targets = np.asarray(raw_targets, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Regression data must be numeric") from exc
    if features.ndim != 2 or features.shape != (len(targets), len(feature_names)):
        raise ValueError("feature_rows shape does not match feature_names and target_values")
    if targets.ndim != 1 or not np.isfinite(features).all() or not np.isfinite(targets).all():
        raise ValueError("Regression data must contain only finite numbers")
    return feature_names, features, targets


def _split_indices(*, row_count: int, test_fraction: float, random_seed: int) -> tuple[np.ndarray, np.ndarray]:
    test_count = int(round(row_count * test_fraction))
    test_count = max(2, min(row_count - 2, test_count))
    shuffled = np.random.default_rng(random_seed).permutation(row_count)
    return np.sort(shuffled[test_count:]), np.sort(shuffled[:test_count])


def _fit(features: np.ndarray, targets: np.ndarray, method: str, ridge_alpha: float) -> np.ndarray:
    design = np.column_stack((np.ones(features.shape[0]), features))
    normalized_method = method.strip().lower().replace("_", "-")
    if normalized_method in {"ols", "linear", "linear-regression", "ordinary-least-squares"}:
        return np.linalg.lstsq(design, targets, rcond=None)[0]
    if normalized_method in {"ridge", "ridge-regression"}:
        penalty = np.eye(design.shape[1])
        penalty[0, 0] = 0.0
        system = design.T @ design + ridge_alpha * penalty
        return np.linalg.lstsq(system, design.T @ targets, rcond=None)[0]
    raise ValueError(f"unsupported regression method: {method!r}")


def _predict(features: np.ndarray, beta: np.ndarray) -> np.ndarray:
    return beta[0] + features @ beta[1:]


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float | None]:
    residuals = actual - predicted
    mse = float(np.mean(np.square(residuals)))
    total_sum_squares = float(np.sum(np.square(actual - np.mean(actual))))
    r_squared = None if np.isclose(total_sum_squares, 0.0) else float(1.0 - np.sum(np.square(residuals)) / total_sum_squares)
    return {
        "mae": float(np.mean(np.abs(residuals))),
        "mse": mse,
        "rmse": float(np.sqrt(mse)),
        "r_squared": r_squared,
    }


def _prediction_rows(
    indices: np.ndarray,
    actual: np.ndarray,
    predicted: np.ndarray,
    partition: str,
) -> list[dict[str, object]]:
    return [
        {
            "row_index": int(index),
            "actual": float(actual_value),
            "predicted": float(predicted_value),
            "residual": float(actual_value - predicted_value),
            "partition": partition,
        }
        for index, actual_value, predicted_value in zip(indices, actual, predicted, strict=True)
    ]


def _finite_float(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not np.isfinite(normalized):
        raise ValueError(f"{label} must be a finite number")
    return normalized


def _non_negative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value
