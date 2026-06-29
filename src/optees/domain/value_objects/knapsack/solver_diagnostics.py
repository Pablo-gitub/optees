from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class KnapsackSolverDiagnostics:
    method: Optional[str] = None
    message: Optional[str] = None
    item_count: Optional[int] = None
    capacity: Optional[int] = None
    dp_cells: Optional[int] = None
    max_dp_cells: Optional[int] = None
    complexity: Optional[str] = None

    @staticmethod
    def from_extras(extras: Dict[str, Any]) -> "KnapsackSolverDiagnostics":
        return KnapsackSolverDiagnostics(
            method=extras.get("method"),
            message=extras.get("message") or extras.get("error"),
            item_count=_optional_int(extras.get("item_count")),
            capacity=_optional_int(extras.get("capacity")),
            dp_cells=_optional_int(extras.get("dp_cells")),
            max_dp_cells=_optional_int(extras.get("max_dp_cells")),
            complexity=extras.get("complexity"),
        )


def _optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

