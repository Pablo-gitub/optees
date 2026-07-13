from __future__ import annotations

import math
from dataclasses import dataclass, field

from optees.domain.entities.classification.dataset import ClassificationDataset
from optees.domain.value_objects.classification.classification_method import ClassificationMethod


@dataclass(frozen=True)
class ClassificationOptions:
    """Deterministic optimization and evaluation parameters for logistic regression."""

    method: ClassificationMethod = ClassificationMethod.LOGISTIC_REGRESSION
    test_fraction: float = 0.25
    random_seed: int = 42
    learning_rate: float = 0.1
    max_iterations: int = 2_000
    l2_alpha: float = 0.0

    def __post_init__(self) -> None:
        method = self.method if isinstance(self.method, ClassificationMethod) else ClassificationMethod.from_str(self.method)
        test_fraction = _positive_fraction(self.test_fraction, "Classification test_fraction")
        learning_rate = _positive_finite(self.learning_rate, "Classification learning_rate")
        l2_alpha = _non_negative_finite(self.l2_alpha, "Classification l2_alpha")
        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int) or self.random_seed < 0:
            raise ValueError("Classification random_seed must be a non-negative integer")
        if isinstance(self.max_iterations, bool) or not isinstance(self.max_iterations, int) or self.max_iterations < 1:
            raise ValueError("Classification max_iterations must be a positive integer")
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "test_fraction", test_fraction)
        object.__setattr__(self, "learning_rate", learning_rate)
        object.__setattr__(self, "l2_alpha", l2_alpha)


@dataclass(frozen=True)
class BinaryClassificationModel:
    dataset: ClassificationDataset
    options: ClassificationOptions = field(default_factory=ClassificationOptions)

    def __post_init__(self) -> None:
        if not isinstance(self.dataset, ClassificationDataset):
            raise ValueError("Classification model dataset must be a ClassificationDataset")
        options = self.options if isinstance(self.options, ClassificationOptions) else ClassificationOptions(**self.options)
        object.__setattr__(self, "options", options)


def _positive_fraction(value: object, label: str) -> float:
    result = _positive_finite(value, label)
    if result >= 1:
        raise ValueError(f"{label} must be between 0 and 1")
    return result


def _positive_finite(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive finite number")
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive finite number") from exc
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{label} must be a positive finite number")
    return result


def _non_negative_finite(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a non-negative finite number")
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a non-negative finite number") from exc
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{label} must be a non-negative finite number")
    return result
