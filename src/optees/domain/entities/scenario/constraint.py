from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence, Tuple, Union

from optees.domain.value_objects.lp.relation import Relation


@dataclass(frozen=True)
class ScenarioConstraint:
    """Shared linear constraint over all decision variables."""

    name: str = ""
    coefficients: Tuple[float, ...] = ()
    relation: Relation = Relation.LE
    rhs: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", str(self.name or ""))
        coefs = tuple(float(c) for c in self.coefficients)
        for idx, c in enumerate(coefs):
            if not math.isfinite(c):
                raise ValueError(
                    f"ScenarioConstraint coefficient at index {idx} must be a finite number, got {c!r}"
                )
        object.__setattr__(self, "coefficients", coefs)

        rel = (
            self.relation
            if isinstance(self.relation, Relation)
            else Relation.from_symbol(str(self.relation))
        )
        object.__setattr__(self, "relation", rel)

        rhs_val = float(self.rhs) if self.rhs is not None else 0.0
        if not math.isfinite(rhs_val):
            raise ValueError(f"ScenarioConstraint rhs must be a finite number, got {rhs_val!r}")
        object.__setattr__(self, "rhs", rhs_val)

    def with_size(self, n: int) -> ScenarioConstraint:
        current = list(self.coefficients)
        if len(current) < n:
            current.extend([0.0] * (n - len(current)))
        elif len(current) > n:
            current = current[:n]
        return ScenarioConstraint(
            name=self.name,
            coefficients=tuple(current),
            relation=self.relation,
            rhs=self.rhs,
        )

    def with_coefficients(self, coefs: Sequence[float]) -> ScenarioConstraint:
        return ScenarioConstraint(
            name=self.name,
            coefficients=tuple(float(c) for c in coefs),
            relation=self.relation,
            rhs=self.rhs,
        )

    def with_relation(self, relation: Union[str, Relation]) -> ScenarioConstraint:
        r = Relation.from_symbol(relation) if isinstance(relation, str) else relation
        return ScenarioConstraint(
            name=self.name,
            coefficients=self.coefficients,
            relation=r,
            rhs=self.rhs,
        )

    def with_rhs(self, rhs: float) -> ScenarioConstraint:
        return ScenarioConstraint(
            name=self.name,
            coefficients=self.coefficients,
            relation=self.relation,
            rhs=float(rhs),
        )
