from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from optees.domain.value_objects.lp.relation import Relation


@dataclass(frozen=True)
class QPConstraint:
    """Linear constraint for QP: Sum_j coefs[j] * x_j (relation) rhs."""

    name: str = ""
    coefs: Tuple[float, ...] = ()
    relation: Relation = Relation.LE
    rhs: float = 0.0

    def with_relation(self, rel: Relation) -> QPConstraint:
        return QPConstraint(self.name, self.coefs, rel, self.rhs)

    def with_rhs(self, rhs: float) -> QPConstraint:
        return QPConstraint(self.name, self.coefs, self.relation, float(rhs))
