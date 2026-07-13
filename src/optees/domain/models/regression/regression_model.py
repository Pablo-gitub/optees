from __future__ import annotations

import math
from dataclasses import dataclass

from optees.domain.entities.regression.dataset import RegressionDataset
from optees.domain.value_objects.regression.regression_method import RegressionMethod


@dataclass(frozen=True)
class RegressionOptions:
    """Reproducible split and estimator parameters for regression."""

    method: RegressionMethod = RegressionMethod.OLS
    test_fraction: float = 0.2
    random_seed: int = 42
    ridge_alpha: float = 1.0

    def __post_init__(self) -> None:
        method = (
            self.method
            if isinstance(self.method, RegressionMethod)
            else RegressionMethod.from_str(self.method)
        )
        if isinstance(self.test_fraction, bool):
            raise ValueError("Regression test_fraction must be between 0 and 1")
        try:
            test_fraction = float(self.test_fraction)
        except (TypeError, ValueError) as exc:
            raise ValueError("Regression test_fraction must be between 0 and 1") from exc
        if not math.isfinite(test_fraction) or not 0 < test_fraction < 1:
            raise ValueError("Regression test_fraction must be between 0 and 1")
        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int):
            raise ValueError("Regression random_seed must be a non-negative integer")
        if self.random_seed < 0:
            raise ValueError("Regression random_seed must be a non-negative integer")
        if isinstance(self.ridge_alpha, bool):
            raise ValueError("Regression ridge_alpha must be a positive finite number")
        try:
            ridge_alpha = float(self.ridge_alpha)
        except (TypeError, ValueError) as exc:
            raise ValueError("Regression ridge_alpha must be a positive finite number") from exc
        if not math.isfinite(ridge_alpha) or ridge_alpha <= 0:
            raise ValueError("Regression ridge_alpha must be a positive finite number")

        object.__setattr__(self, "method", method)
        object.__setattr__(self, "test_fraction", test_fraction)
        object.__setattr__(self, "ridge_alpha", ridge_alpha)


@dataclass(frozen=True)
class RegressionModel:
    """A numerical dataset plus the transparent estimator selected by the user."""

    dataset: RegressionDataset
    options: RegressionOptions = RegressionOptions()

    def __post_init__(self) -> None:
        if not isinstance(self.dataset, RegressionDataset):
            raise ValueError("Regression model dataset must be a RegressionDataset")
        options = self.options if isinstance(self.options, RegressionOptions) else RegressionOptions(**self.options)
        object.__setattr__(self, "options", options)
