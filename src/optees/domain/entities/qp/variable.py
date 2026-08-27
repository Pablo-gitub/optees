from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from optees.domain.value_objects.lp.bounds import Bounds


@dataclass(frozen=True)
class QPVariable:
    """Domain entity for a continuous QP decision variable."""

    name: str
    label: str = ""
    bounds: Bounds = field(default_factory=lambda: Bounds(None, None))

    def rename(self, new_name: str) -> QPVariable:
        return QPVariable(name=new_name, label=self.label, bounds=self.bounds)

    def relabel(self, new_label: str) -> QPVariable:
        return QPVariable(name=self.name, label=new_label, bounds=self.bounds)

    def with_bounds(self, lb: Optional[float], ub: Optional[float]) -> QPVariable:
        return QPVariable(name=self.name, label=self.label, bounds=Bounds(lb, ub))
