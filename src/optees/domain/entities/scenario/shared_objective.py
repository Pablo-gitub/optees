from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence, Tuple


@dataclass(frozen=True)
class ScenarioSharedObjective:
    """Optional shared base linear objective coefficients and offset across all scenarios."""

    coefficients: Tuple[float, ...] = ()
    offset: float = 0.0

    def __post_init__(self) -> None:
        coefs = tuple(float(c) for c in self.coefficients)
        for idx, c in enumerate(coefs):
            if not math.isfinite(c):
                raise ValueError(
                    f"ScenarioSharedObjective coefficient at index {idx} must be a finite number, got {c!r}"
                )
        object.__setattr__(self, "coefficients", coefs)

        off = float(self.offset) if self.offset is not None else 0.0
        if not math.isfinite(off):
            raise ValueError(f"ScenarioSharedObjective offset must be a finite number, got {off!r}")
        object.__setattr__(self, "offset", off)

    def with_size(self, n: int) -> ScenarioSharedObjective:
        current = list(self.coefficients)
        if len(current) < n:
            current.extend([0.0] * (n - len(current)))
        elif len(current) > n:
            current = current[:n]
        return ScenarioSharedObjective(coefficients=tuple(current), offset=self.offset)

    def with_coefficients(self, coefs: Sequence[float]) -> ScenarioSharedObjective:
        return ScenarioSharedObjective(
            coefficients=tuple(float(c) for c in coefs),
            offset=self.offset,
        )

    def with_offset(self, offset: float) -> ScenarioSharedObjective:
        return ScenarioSharedObjective(
            coefficients=self.coefficients,
            offset=float(offset),
        )
