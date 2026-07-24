from __future__ import annotations

from enum import Enum


class ForecastingStatus(str, Enum):
    """Mathematical outcome, independent from asynchronous job lifecycle."""

    FORECASTED = "forecasted"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
