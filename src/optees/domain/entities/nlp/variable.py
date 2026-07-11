from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Optional

from optees.utility.nlp_expression import ALLOWED_FUNCTION_NAMES


_VARIABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


@dataclass(frozen=True)
class NLPVariable:
    """A continuous decision variable with an initial point and box bounds."""

    name: str
    label: str = ""
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    initial_value: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _VARIABLE_NAME.fullmatch(self.name):
            raise ValueError("NLP variable name must be a valid identifier")
        if self.name in ALLOWED_FUNCTION_NAMES:
            raise ValueError(f"NLP variable name {self.name!r} is reserved for a function")

        lower = _normalize_bound(self.lower_bound, "lower bound")
        upper = _normalize_bound(self.upper_bound, "upper bound")
        initial = _normalize_finite(self.initial_value, "initial value")
        if lower is not None and upper is not None and lower > upper:
            raise ValueError("NLP lower bound must not exceed upper bound")
        if lower is not None and initial < lower:
            raise ValueError("NLP initial value must satisfy the lower bound")
        if upper is not None and initial > upper:
            raise ValueError("NLP initial value must satisfy the upper bound")

        object.__setattr__(self, "label", str(self.label or "").strip())
        object.__setattr__(self, "lower_bound", lower)
        object.__setattr__(self, "upper_bound", upper)
        object.__setattr__(self, "initial_value", initial)

    def is_bounded(self) -> bool:
        return self.lower_bound is not None or self.upper_bound is not None

    def contains(self, value: float) -> bool:
        if self.lower_bound is not None and value < self.lower_bound:
            return False
        if self.upper_bound is not None and value > self.upper_bound:
            return False
        return True


def _normalize_bound(value: object, description: str) -> Optional[float]:
    if value is None:
        return None
    return _normalize_finite(value, description)


def _normalize_finite(value: object, description: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"NLP {description} must be a finite number")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"NLP {description} must be a finite number") from exc
    if not math.isfinite(normalized):
        raise ValueError(f"NLP {description} must be a finite number")
    return normalized
