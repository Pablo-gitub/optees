# src/optees/domain/entities/lp/objective.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple

from optees.domain.value_objects.lp.objective_sense import ObjectiveSense

@dataclass(frozen=True)
class Objective:
    sense: ObjectiveSense = ObjectiveSense.MAX
    coefs: Tuple[Optional[float], ...] = ()
    offset: float = 0.0

    def with_size(self, n: int) -> "Objective":
        cur = len(self.coefs)
        if cur == n:
            return self
        if cur < n:
            return Objective(self.sense, self.coefs + (None,) * (n - cur), self.offset)
        return Objective(self.sense, self.coefs[:n], self.offset)

    def with_coef(self, idx: int, value: Optional[float]) -> "Objective":
        coefs = list(self.coefs)
        if 0 <= idx < len(coefs):
            coefs[idx] = value
        return Objective(self.sense, tuple(coefs), self.offset)

    def with_sense(self, sense: ObjectiveSense) -> "Objective":
        return Objective(sense, self.coefs, self.offset)

    def with_offset(self, offset: float) -> "Objective":
        return Objective(self.sense, self.coefs, float(offset))
