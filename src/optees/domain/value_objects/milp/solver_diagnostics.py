from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class MILPSolverDiagnostics:
    """Solver-agnostic diagnostics that matter for branch-and-bound MILP runs."""

    backend: Optional[str] = None
    message: Optional[str] = None
    status_code: Optional[int] = None
    status_str: Optional[str] = None
    best_bound: Optional[float] = None
    relative_gap: Optional[float] = None
    wall_time: Optional[float] = None
    wall_time_ms: Optional[int] = None
    nodes: Optional[int] = None
    branches: Optional[int] = None
    conflicts: Optional[int] = None

    @staticmethod
    def from_extras(extras: Dict[str, Any]) -> "MILPSolverDiagnostics":
        return MILPSolverDiagnostics(
            backend=extras.get("backend"),
            message=extras.get("message") or extras.get("error"),
            status_code=extras.get("status_code") or extras.get("result_status"),
            status_str=extras.get("status_str"),
            best_bound=_optional_float(extras.get("best_bound")),
            relative_gap=_optional_float(extras.get("relative_gap")),
            wall_time=_optional_float(extras.get("wall_time")),
            wall_time_ms=_optional_int(extras.get("wall_time_ms")),
            nodes=_optional_int(extras.get("nodes")),
            branches=_optional_int(extras.get("branches")),
            conflicts=_optional_int(extras.get("conflicts")),
        )


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
