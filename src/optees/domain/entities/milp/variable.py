from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.milp.integrality import Integrality


@dataclass(frozen=True)
class MILPVariable:
    """Decision variable with LP bounds plus MILP integrality metadata."""

    name: str
    label: str = ""
    bounds: Bounds = field(default_factory=lambda: Bounds(0.0, None))
    integrality: Integrality = Integrality.CONTINUOUS

    def rename(self, new_name: str) -> "MILPVariable":
        return MILPVariable(new_name, self.label, self.bounds, self.integrality)

    def relabel(self, new_label: str) -> "MILPVariable":
        return MILPVariable(self.name, new_label, self.bounds, self.integrality)

    def with_bounds(self, lb: Optional[float], ub: Optional[float]) -> "MILPVariable":
        return MILPVariable(self.name, self.label, Bounds(lb, ub), self.integrality)

    def with_integrality(self, integrality: Integrality | str | None) -> "MILPVariable":
        kind = Integrality.from_token(integrality)
        if kind is Integrality.BINARY:
            return MILPVariable(self.name, self.label, Bounds(0.0, 1.0), kind)
        return MILPVariable(self.name, self.label, self.bounds, kind)
