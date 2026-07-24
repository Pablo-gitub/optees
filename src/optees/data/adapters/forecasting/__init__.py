"""Local deterministic and maintained-library forecasting adapters."""

from .baseline_forecasting_adapter import BaselineForecastingAdapter
from .holt_winters_forecasting_adapter import HoltWintersForecastingAdapter

__all__ = ["BaselineForecastingAdapter", "HoltWintersForecastingAdapter"]
