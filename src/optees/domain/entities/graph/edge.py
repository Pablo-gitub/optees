from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GraphEdge:
    """A weighted arc; an undirected model uses it in both directions."""

    source: str
    target: str
    weight: float

    def __post_init__(self) -> None:
        source = str(self.source or "").strip()
        target = str(self.target or "").strip()
        if not source or not target:
            raise ValueError("graph edge endpoints must not be empty")
        if source == target:
            raise ValueError("graph self-loops are not supported in this workflow")
        if isinstance(self.weight, bool):
            raise ValueError("graph edge weight must be a finite non-negative number")
        try:
            weight = float(self.weight)
        except (TypeError, ValueError) as exc:
            raise ValueError("graph edge weight must be a finite non-negative number") from exc
        if not math.isfinite(weight) or weight < 0:
            raise ValueError("Dijkstra requires finite non-negative edge weights")
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "weight", weight)
