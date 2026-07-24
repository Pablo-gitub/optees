from __future__ import annotations

from enum import Enum


class ForecastingMethod(str, Enum):
    """Stable identifiers for the initial univariate method set."""

    NAIVE = "naive"
    SEASONAL_NAIVE = "seasonal_naive"
    HOLT_WINTERS_ADDITIVE = "holt_winters_additive"

    @classmethod
    def from_value(cls, value: object) -> "ForecastingMethod":
        normalized = str(value or "").strip().lower().replace("-", "_")
        aliases = {
            "naive": cls.NAIVE,
            "seasonal_naive": cls.SEASONAL_NAIVE,
            "seasonalnaive": cls.SEASONAL_NAIVE,
            "holt_winters_additive": cls.HOLT_WINTERS_ADDITIVE,
            "holtwintersadditive": cls.HOLT_WINTERS_ADDITIVE,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"Unsupported forecasting method: {value!r}") from exc

    @property
    def requires_season_length(self) -> bool:
        return self in {
            ForecastingMethod.SEASONAL_NAIVE,
            ForecastingMethod.HOLT_WINTERS_ADDITIVE,
        }
