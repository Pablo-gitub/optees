from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence


def _finite_float(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(normalized):
        raise ValueError(f"{label} must be a finite number")
    return normalized


@dataclass(frozen=True)
class RegressionDataset:
    """Numeric tabular observations used by a supervised regression model.

    At least four rows are required so both training and test partitions can
    contain two observations. That makes the reported test metrics meaningful.
    """

    feature_names: tuple[str, ...]
    target_name: str
    feature_rows: tuple[tuple[float, ...], ...]
    target_values: tuple[float, ...]

    def __post_init__(self) -> None:
        feature_names = tuple(str(name).strip() for name in self.feature_names)
        target_name = str(self.target_name).strip()
        feature_rows = tuple(tuple(row) for row in self.feature_rows)
        target_values = tuple(self.target_values)

        if not feature_names:
            raise ValueError("Regression dataset must contain at least one feature")
        if any(not name for name in feature_names):
            raise ValueError("Regression feature names must be non-empty")
        if len(set(feature_names)) != len(feature_names):
            raise ValueError("Regression feature names must be unique")
        if not target_name:
            raise ValueError("Regression target name must be non-empty")
        if target_name in feature_names:
            raise ValueError("Regression target name must differ from feature names")
        if len(feature_rows) != len(target_values):
            raise ValueError("Regression feature rows and targets must have the same length")
        if len(feature_rows) < 4:
            raise ValueError("Regression dataset must contain at least four rows")

        normalized_rows: list[tuple[float, ...]] = []
        for row_index, row in enumerate(feature_rows):
            if len(row) != len(feature_names):
                raise ValueError(
                    f"Regression row {row_index} must contain {len(feature_names)} feature values"
                )
            normalized_rows.append(
                tuple(
                    _finite_float(value, f"Regression row {row_index} feature {column_index}")
                    for column_index, value in enumerate(row)
                )
            )
        normalized_targets = tuple(
            _finite_float(value, f"Regression target {index}")
            for index, value in enumerate(target_values)
        )

        object.__setattr__(self, "feature_names", feature_names)
        object.__setattr__(self, "target_name", target_name)
        object.__setattr__(self, "feature_rows", tuple(normalized_rows))
        object.__setattr__(self, "target_values", normalized_targets)

    @classmethod
    def from_rows(
        cls,
        *,
        feature_names: Sequence[str],
        target_name: str,
        rows: Iterable[tuple[Sequence[object], object]],
    ) -> "RegressionDataset":
        """Create a dataset from ``(features, target)`` observations."""
        materialized = list(rows)
        return cls(
            feature_names=tuple(feature_names),
            target_name=target_name,
            feature_rows=tuple(tuple(features) for features, _target in materialized),
            target_values=tuple(target for _features, target in materialized),
        )

    @property
    def row_count(self) -> int:
        return len(self.target_values)
