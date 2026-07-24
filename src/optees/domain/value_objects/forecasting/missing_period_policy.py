from __future__ import annotations

from enum import Enum


class MissingPeriodPolicy(str, Enum):
    """Explicit handling of absent periods in the first public contract."""

    REJECT = "reject"

    @classmethod
    def from_value(cls, value: object) -> "MissingPeriodPolicy":
        normalized = str(value or "").strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(f"Unsupported missing-period policy: {value!r}") from exc
