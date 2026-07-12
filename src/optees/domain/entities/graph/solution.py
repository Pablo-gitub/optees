from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Optional

from optees.domain.value_objects.graph.shortest_path_status import ShortestPathStatus


@dataclass(frozen=True)
class ShortestPathSolution:
    """Outcome of one Dijkstra run, including the settled-node explanation."""

    status: ShortestPathStatus
    distance: Optional[float]
    path: tuple[str, ...] = ()
    settled_order: tuple[str, ...] = ()
    settled_distances: dict[str, float] = field(default_factory=dict)
    message: str = ""

    @classmethod
    def from_solver_result(
        cls,
        *,
        status: object,
        distance: object,
        path: object,
        extras: Mapping[str, object] | None = None,
    ) -> "ShortestPathSolution":
        data = dict(extras or {})
        normalized_status = ShortestPathStatus.from_str(status)
        normalized_path = tuple(str(node) for node in path or ())
        if normalized_status is ShortestPathStatus.PATH_FOUND and not normalized_path:
            normalized_status = ShortestPathStatus.NOT_SOLVED
        return cls(
            status=normalized_status,
            distance=_finite_float_or_none(distance),
            path=normalized_path,
            settled_order=tuple(str(node) for node in data.get("settled_order", ()) or ()),
            settled_distances={
                str(node): value
                for node, raw_value in dict(data.get("settled_distances", {}) or {}).items()
                if (value := _finite_float_or_none(raw_value)) is not None
            },
            message=str(data.get("message") or "").strip(),
        )

    def found(self) -> bool:
        return self.status is ShortestPathStatus.PATH_FOUND


def _finite_float_or_none(value: object) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None
