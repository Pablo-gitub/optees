from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from enum import Enum


class ForecastingFrequency(str, Enum):
    """Regular intervals accepted by Forecasting schema version 1."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

    @classmethod
    def from_value(cls, value: object) -> "ForecastingFrequency":
        normalized = str(value or "").strip().lower().replace("-", "_")
        aliases = {
            "h": cls.HOURLY,
            "hour": cls.HOURLY,
            "hourly": cls.HOURLY,
            "d": cls.DAILY,
            "day": cls.DAILY,
            "daily": cls.DAILY,
            "w": cls.WEEKLY,
            "week": cls.WEEKLY,
            "weekly": cls.WEEKLY,
            "m": cls.MONTHLY,
            "month": cls.MONTHLY,
            "monthly": cls.MONTHLY,
            "q": cls.QUARTERLY,
            "quarter": cls.QUARTERLY,
            "quarterly": cls.QUARTERLY,
            "y": cls.YEARLY,
            "year": cls.YEARLY,
            "yearly": cls.YEARLY,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"Unsupported forecasting frequency: {value!r}") from exc

    def advance(self, origin: datetime, periods: int = 1) -> datetime:
        """Advance from the original anchor without accumulating calendar drift."""
        if isinstance(periods, bool) or not isinstance(periods, int) or periods < 0:
            raise ValueError("Forecasting periods must be a non-negative integer")
        if self is ForecastingFrequency.HOURLY:
            return origin + timedelta(hours=periods)
        if self is ForecastingFrequency.DAILY:
            return origin + timedelta(days=periods)
        if self is ForecastingFrequency.WEEKLY:
            return origin + timedelta(weeks=periods)
        months = {
            ForecastingFrequency.MONTHLY: periods,
            ForecastingFrequency.QUARTERLY: periods * 3,
            ForecastingFrequency.YEARLY: periods * 12,
        }[self]
        absolute_month = origin.year * 12 + origin.month - 1 + months
        year, month_index = divmod(absolute_month, 12)
        month = month_index + 1
        day = min(origin.day, calendar.monthrange(year, month)[1])
        return origin.replace(year=year, month=month, day=day)
