from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ForecastObservation:
    """One immutable, normalized observation in a univariate series."""

    timestamp: datetime
    value: float

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Forecasting observation timestamp must be a datetime")
        if isinstance(self.value, bool):
            raise ValueError("Forecasting observation value must be finite")
        try:
            value = float(self.value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Forecasting observation value must be finite") from exc
        if not math.isfinite(value):
            raise ValueError("Forecasting observation value must be finite")

        timestamp = self.timestamp
        if timestamp.tzinfo is not None:
            if timestamp.utcoffset() is None:
                raise ValueError("Forecasting timestamp timezone must have a UTC offset")
            timestamp = timestamp.astimezone(timezone.utc)

        object.__setattr__(self, "timestamp", timestamp)
        object.__setattr__(self, "value", value)
