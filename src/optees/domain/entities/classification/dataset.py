from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence


def _finite_float(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be a finite number")
    return result


@dataclass(frozen=True)
class ClassificationDataset:
    """Finite numeric features and two categorical labels for supervised learning.

    Each class needs at least three observations. This guarantees that a
    stratified train/test split can keep both classes in both partitions.
    """

    feature_names: tuple[str, ...]
    target_name: str
    feature_rows: tuple[tuple[float, ...], ...]
    target_values: tuple[str, ...]

    def __post_init__(self) -> None:
        feature_names = tuple(str(name).strip() for name in self.feature_names)
        target_name = str(self.target_name).strip()
        feature_rows = tuple(tuple(row) for row in self.feature_rows)
        target_values = tuple(
            value.strip() if isinstance(value, str) else "" for value in self.target_values
        )

        if not feature_names:
            raise ValueError("Classification dataset must contain at least one feature")
        if any(not name for name in feature_names) or len(set(feature_names)) != len(feature_names):
            raise ValueError("Classification feature names must be non-empty and unique")
        if not target_name or target_name in feature_names:
            raise ValueError("Classification target name must be non-empty and differ from feature names")
        if len(feature_rows) != len(target_values):
            raise ValueError("Classification feature rows and targets must have the same length")
        if len(feature_rows) < 6:
            raise ValueError("Classification dataset must contain at least six rows")
        if any(not value for value in target_values):
            raise ValueError("Classification target labels must be non-empty strings")

        labels = tuple(sorted(set(target_values)))
        if len(labels) != 2:
            raise ValueError("Classification dataset must contain exactly two target labels")
        counts = Counter(target_values)
        if any(count < 3 for count in counts.values()):
            raise ValueError("Classification dataset must contain at least three rows per label")

        normalized_rows: list[tuple[float, ...]] = []
        for row_index, row in enumerate(feature_rows):
            if len(row) != len(feature_names):
                raise ValueError(
                    f"Classification row {row_index} must contain {len(feature_names)} feature values"
                )
            normalized_rows.append(
                tuple(
                    _finite_float(value, f"Classification row {row_index} feature {column_index}")
                    for column_index, value in enumerate(row)
                )
            )

        object.__setattr__(self, "feature_names", feature_names)
        object.__setattr__(self, "target_name", target_name)
        object.__setattr__(self, "feature_rows", tuple(normalized_rows))
        object.__setattr__(self, "target_values", target_values)

    @classmethod
    def from_rows(
        cls,
        *,
        feature_names: Sequence[str],
        target_name: str,
        rows: Iterable[tuple[Sequence[object], object]],
    ) -> "ClassificationDataset":
        materialized = list(rows)
        return cls(
            feature_names=tuple(feature_names),
            target_name=target_name,
            feature_rows=tuple(tuple(features) for features, _target in materialized),
            target_values=tuple(_target for _features, _target in materialized),  # type: ignore[arg-type]
        )

    @property
    def labels(self) -> tuple[str, str]:
        values = tuple(sorted(set(self.target_values)))
        return values[0], values[1]

    @property
    def row_count(self) -> int:
        return len(self.target_values)
