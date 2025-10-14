# src/optees/domain/entities/lp/constraint.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple

from optees.domain.value_objects.lp.relation import Relation

@dataclass(frozen=True)
class Constraint:
    """Sum_i coefs[i] * x_i (relation) rhs."""
    coefs: Tuple[Optional[float], ...]
    relation: Relation = Relation.LE
    rhs: Optional[float] = None

    def __post_init__(self):
        # No length validation here (it depends on model's n_vars).
        # Keep coefs as an immutable tuple to avoid accidental in-place edits.
        pass

    def with_size(self, n: int) -> "Constraint":
        """Resize coefficient vector to length n, padding with None or truncating."""
        cur = len(self.coefs)
        if cur == n:
            return self
        if cur < n:
            return Constraint(self.coefs + (None,) * (n - cur), self.relation, self.rhs)
        return Constraint(self.coefs[:n], self.relation, self.rhs)

    def with_coef(self, idx: int, value: Optional[float]) -> "Constraint":
        coefs = list(self.coefs)
        if 0 <= idx < len(coefs):
            coefs[idx] = value
        return Constraint(tuple(coefs), self.relation, self.rhs)

    def with_relation(self, rel: Relation) -> "Constraint":
        return Constraint(self.coefs, rel, self.rhs)

    def with_rhs(self, rhs: Optional[float]) -> "Constraint":
        return Constraint(self.coefs, self.relation, rhs)
