from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from optees.domain.value_objects.lp.objective_sense import ObjectiveSense


@dataclass(frozen=True)
class QPObjective:
    """Domain entity for a quadratic objective: 0.5 * x^T * Q * x + c^T * x + offset."""

    sense: ObjectiveSense = ObjectiveSense.MIN
    linear_coefs: Tuple[float, ...] = ()
    quadratic_matrix: Tuple[Tuple[float, ...], ...] = ()
    offset: float = 0.0

    def with_sense(self, sense: ObjectiveSense) -> QPObjective:
        return QPObjective(sense, self.linear_coefs, self.quadratic_matrix, self.offset)

    def with_offset(self, offset: float) -> QPObjective:
        return QPObjective(self.sense, self.linear_coefs, self.quadratic_matrix, float(offset))
