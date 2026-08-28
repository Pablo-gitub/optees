from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional


@dataclass(frozen=True)
class ScenarioOptions:
    """Solver and validation tolerances for robust scenario models."""

    tolerance: float = 1e-7
    binding_tolerance: float = 1e-6
    time_limit_seconds: Optional[float] = None

    def __post_init__(self) -> None:
        if not (
            not isinstance(self.tolerance, bool)
            and isinstance(self.tolerance, (int, float))
            and math.isfinite(self.tolerance)
            and self.tolerance > 0
        ):
            raise ValueError(
                f"options.tolerance must be a finite positive number, got {self.tolerance!r}"
            )
        if not (
            not isinstance(self.binding_tolerance, bool)
            and isinstance(self.binding_tolerance, (int, float))
            and math.isfinite(self.binding_tolerance)
            and self.binding_tolerance > 0
        ):
            raise ValueError(
                f"options.binding_tolerance must be a finite positive number, got {self.binding_tolerance!r}"
            )
        if self.time_limit_seconds is not None:
            if not (
                not isinstance(self.time_limit_seconds, bool)
                and isinstance(self.time_limit_seconds, (int, float))
                and math.isfinite(self.time_limit_seconds)
                and self.time_limit_seconds > 0
            ):
                raise ValueError(
                    f"options.time_limit_seconds must be a finite positive number or null, got {self.time_limit_seconds!r}"
                )
            object.__setattr__(self, "time_limit_seconds", float(self.time_limit_seconds))
        object.__setattr__(self, "tolerance", float(self.tolerance))
        object.__setattr__(self, "binding_tolerance", float(self.binding_tolerance))
