# src/optees/domain/entities/lp/variable.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from optees.domain.value_objects.lp.bounds import Bounds

@dataclass(frozen=True)
class Variable:
    """Domain entity for a decision variable."""
    name: str
    label: str = ""
    bounds: Bounds = field(default_factory=lambda: Bounds(0.0, None))

    def rename(self, new_name: str) -> "Variable":
        return Variable(name=new_name, label=self.label, bounds=self.bounds)

    def relabel(self, new_label: str) -> "Variable":
        return Variable(name=self.name, label=new_label, bounds=self.bounds)

    def with_bounds(self, lb: Optional[float], ub: Optional[float]) -> "Variable":
        return Variable(name=self.name, label=self.label, bounds=Bounds(lb, ub))
    
    # --- Compatibility shims (read-only) ---
    @property
    def lb(self) -> Optional[float]:
        """Deprecated: use variable.bounds.lb"""
        return self.bounds.lb

    @property
    def ub(self) -> Optional[float]:
        """Deprecated: use variable.bounds.ub"""
        return self.bounds.ub
