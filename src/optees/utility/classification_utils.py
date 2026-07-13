"""Numerical helpers for transparent local binary logistic regression."""

from __future__ import annotations

from collections import Counter
from typing import Mapping

import numpy as np


def solve_classification(problem: Mapping[str, object]) -> dict[str, object]:
    """Fit binary logistic regression without leaking the test partition.

    Given standardized training features ``X`` and binary labels ``y``, the
    model minimizes the regularized logistic loss

    ``mean(log(1 + exp(z)) - y z) + alpha / 2 * ||w||^2``, with
    ``z = b + X w``. Full-batch gradient descent applies the corresponding
    gradients to ``b`` and ``w``. Means and scales are fitted *only* on the
    stratified training rows, then reused unchanged for test predictions.
    """
    names, features, labels = _read_dataset(problem)
    method = str(problem.get("method", "LogisticRegression"))
    test_fraction = _positive_fraction(problem.get("test_fraction", 0.25), "test_fraction")
    random_seed = _non_negative_int(problem.get("random_seed", 42), "random_seed")
    learning_rate = _positive_float(problem.get("learning_rate", 0.1), "learning_rate")
    max_iterations = _positive_int(problem.get("max_iterations", 2_000), "max_iterations")
    l2_alpha = _non_negative_float(problem.get("l2_alpha", 0.0), "l2_alpha")
    if _normalize_method(method) != "logistic":
        raise ValueError(f"unsupported classification method: {method!r}")

    negative_label, positive_label = tuple(sorted(set(labels)))
    encoded = np.asarray([1.0 if label == positive_label else 0.0 for label in labels])
    train_indices, test_indices = _stratified_split(
        labels=labels,
        test_fraction=test_fraction,
        random_seed=random_seed,
    )
    train_features, test_features = features[train_indices], features[test_indices]
    train_targets, test_targets = encoded[train_indices], encoded[test_indices]
    means = train_features.mean(axis=0)
    scales = train_features.std(axis=0)
    scales[scales < 1e-12] = 1.0
    train_standardized = (train_features - means) / scales
    test_standardized = (test_features - means) / scales

    intercept, weights, iterations, converged = _fit_logistic(
        train_standardized,
        train_targets,
        learning_rate=learning_rate,
        max_iterations=max_iterations,
        l2_alpha=l2_alpha,
    )
    train_probabilities = _probabilities(train_standardized, intercept, weights)
    test_probabilities = _probabilities(test_standardized, intercept, weights)
    train_predicted = (train_probabilities >= 0.5).astype(int)
    test_predicted = (test_probabilities >= 0.5).astype(int)
    predictions = _prediction_rows(
        train_indices,
        labels,
        train_probabilities,
        train_predicted,
        negative_label,
        positive_label,
        "train",
    )
    predictions.extend(
        _prediction_rows(
            test_indices,
            labels,
            test_probabilities,
            test_predicted,
            negative_label,
            positive_label,
            "test",
        )
    )
    predictions.sort(key=lambda value: int(value["row_index"]))

    return {
        "status": "Trained",
        "negative_label": negative_label,
        "positive_label": positive_label,
        "intercept": float(intercept),
        "coefficients": {name: float(weight) for name, weight in zip(names, weights, strict=True)},
        "train_metrics": _metrics(train_targets, train_predicted),
        "test_metrics": _metrics(test_targets, test_predicted),
        "train_confusion": _confusion(train_targets, train_predicted),
        "test_confusion": _confusion(test_targets, test_predicted),
        "predictions": predictions,
        "extras": {
            "method": "LogisticRegression",
            "train_count": int(len(train_indices)),
            "test_count": int(len(test_indices)),
            "random_seed": random_seed,
            "iterations": iterations,
            "converged": converged,
            "learning_rate": learning_rate,
            "l2_alpha": l2_alpha,
            "feature_means": {name: float(value) for name, value in zip(names, means, strict=True)},
            "feature_scales": {name: float(value) for name, value in zip(names, scales, strict=True)},
        },
    }


def _read_dataset(problem: Mapping[str, object]) -> tuple[tuple[str, ...], np.ndarray, tuple[str, ...]]:
    raw_names = problem.get("feature_names")
    raw_rows = problem.get("feature_rows")
    raw_targets = problem.get("target_values")
    if not isinstance(raw_names, list) or not raw_names:
        raise ValueError("feature_names must be a non-empty list")
    names = tuple(str(name).strip() for name in raw_names)
    if any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError("feature_names must be non-empty and unique")
    if not isinstance(raw_rows, list) or not isinstance(raw_targets, list):
        raise ValueError("feature_rows and target_values must be lists")
    if len(raw_rows) != len(raw_targets) or len(raw_rows) < 6:
        raise ValueError("Classification data must contain at least six aligned rows")
    labels = tuple(value.strip() if isinstance(value, str) else "" for value in raw_targets)
    if any(not label for label in labels) or len(set(labels)) != 2:
        raise ValueError("Classification data must contain exactly two non-empty labels")
    if any(count < 3 for count in Counter(labels).values()):
        raise ValueError("Classification data must contain at least three rows per label")
    try:
        features = np.asarray(raw_rows, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Classification features must be numeric") from exc
    if features.ndim != 2 or features.shape != (len(labels), len(names)):
        raise ValueError("feature_rows shape does not match feature_names and target_values")
    if not np.isfinite(features).all():
        raise ValueError("Classification features must contain only finite numbers")
    return names, features, labels


def _stratified_split(
    *, labels: tuple[str, ...], test_fraction: float, random_seed: int
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(random_seed)
    test_parts: list[np.ndarray] = []
    train_parts: list[np.ndarray] = []
    all_labels = np.asarray(labels)
    for label in sorted(set(labels)):
        indices = np.flatnonzero(all_labels == label)
        shuffled = rng.permutation(indices)
        test_count = int(round(len(indices) * test_fraction))
        test_count = max(1, min(len(indices) - 1, test_count))
        test_parts.append(shuffled[:test_count])
        train_parts.append(shuffled[test_count:])
    return np.sort(np.concatenate(train_parts)), np.sort(np.concatenate(test_parts))


def _fit_logistic(
    features: np.ndarray,
    targets: np.ndarray,
    *,
    learning_rate: float,
    max_iterations: int,
    l2_alpha: float,
) -> tuple[float, np.ndarray, int, bool]:
    intercept = 0.0
    weights = np.zeros(features.shape[1], dtype=float)
    converged = False
    for iteration in range(1, max_iterations + 1):
        probabilities = _probabilities(features, intercept, weights)
        residuals = probabilities - targets
        gradient_intercept = float(residuals.mean())
        gradient_weights = (features.T @ residuals) / len(features) + l2_alpha * weights
        intercept -= learning_rate * gradient_intercept
        weights -= learning_rate * gradient_weights
        if max(abs(gradient_intercept), float(np.max(np.abs(gradient_weights)))) < 1e-7:
            converged = True
            return intercept, weights, iteration, converged
    return intercept, weights, max_iterations, converged


def _probabilities(features: np.ndarray, intercept: float, weights: np.ndarray) -> np.ndarray:
    logits = np.clip(intercept + features @ weights, -500.0, 500.0)
    return 1.0 / (1.0 + np.exp(-logits))


def _prediction_rows(
    indices: np.ndarray,
    labels: tuple[str, ...],
    probabilities: np.ndarray,
    predictions: np.ndarray,
    negative_label: str,
    positive_label: str,
    partition: str,
) -> list[dict[str, object]]:
    return [
        {
            "row_index": int(index),
            "actual": labels[int(index)],
            "predicted": positive_label if int(prediction) else negative_label,
            "probability_positive": float(probability),
            "partition": partition,
        }
        for index, probability, prediction in zip(indices, probabilities, predictions, strict=True)
    ]


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float | None]:
    confusion = _confusion(actual, predicted)
    tp, fp, fn = confusion["true_positive"], confusion["false_positive"], confusion["false_negative"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    return {
        "accuracy": float(np.mean(actual == predicted)),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _confusion(actual: np.ndarray, predicted: np.ndarray) -> dict[str, int]:
    return {
        "true_negative": int(np.sum((actual == 0) & (predicted == 0))),
        "false_positive": int(np.sum((actual == 0) & (predicted == 1))),
        "false_negative": int(np.sum((actual == 1) & (predicted == 0))),
        "true_positive": int(np.sum((actual == 1) & (predicted == 1))),
    }


def _normalize_method(method: str) -> str:
    normalized = method.strip().lower().replace("_", "-")
    return "logistic" if normalized in {"logistic", "logistic-regression", "logisticregression"} else normalized


def _positive_fraction(value: object, label: str) -> float:
    result = _positive_float(value, label)
    if result >= 1:
        raise ValueError(f"{label} must be between 0 and 1")
    return result


def _positive_float(value: object, label: str) -> float:
    result = _finite_float(value, label)
    if result <= 0:
        raise ValueError(f"{label} must be positive")
    return result


def _non_negative_float(value: object, label: str) -> float:
    result = _finite_float(value, label)
    if result < 0:
        raise ValueError(f"{label} must be non-negative")
    return result


def _finite_float(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not np.isfinite(result):
        raise ValueError(f"{label} must be a finite number")
    return result


def _non_negative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value
