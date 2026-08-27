from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class QPKKTResiduals:
    primal_residual: Optional[float] = None
    dual_residual: Optional[float] = None
    duality_gap: Optional[float] = None
    complementarity_residual: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> QPKKTResiduals:
        return cls(
            primal_residual=data.get("primal_residual"),
            dual_residual=data.get("dual_residual"),
            duality_gap=data.get("duality_gap"),
            complementarity_residual=data.get("complementarity_residual"),
        )
