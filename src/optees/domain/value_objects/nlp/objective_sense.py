from __future__ import annotations

from enum import Enum


class NLPObjectiveSense(str, Enum):
    MIN = "min"
    MAX = "max"

    @classmethod
    def from_str(cls, value: object) -> "NLPObjectiveSense":
        normalized = str(value or "").strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(f"invalid NLP objective sense: {value!r}") from exc

    def is_min(self) -> bool:
        return self is NLPObjectiveSense.MIN

    def is_max(self) -> bool:
        return self is NLPObjectiveSense.MAX
