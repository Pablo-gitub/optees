from __future__ import annotations

from enum import Enum


class EvaluationStrategy(str, Enum):
    """Chronological evaluation protocols supported by Forecasting v1."""

    NONE = "none"
    HOLDOUT = "holdout"
    ROLLING_ORIGIN = "rolling_origin"

    @classmethod
    def from_value(cls, value: object) -> "EvaluationStrategy":
        normalized = str(value or "").strip().lower().replace("-", "_")
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(f"Unsupported forecasting evaluation strategy: {value!r}") from exc
