from __future__ import annotations

from enum import Enum


class ForecastEvaluationStatus(str, Enum):
    """Availability of chronological evaluation, separate from model execution."""

    NOT_REQUESTED = "not_requested"
    EVALUATED = "evaluated"
    PARTIAL = "partial"
    FAILED = "failed"
