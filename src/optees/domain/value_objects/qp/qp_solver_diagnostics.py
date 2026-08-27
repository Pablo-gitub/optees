from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class QPSolverDiagnostics:
    backend: Optional[str] = None
    backend_version: Optional[str] = None
    status: Optional[str] = None
    status_code: Optional[int] = None
    iterations: Optional[int] = None
    solve_time_seconds: Optional[float] = None
    setup_time_seconds: Optional[float] = None
    message: Optional[str] = None
    success: Optional[bool] = None

    @classmethod
    def from_extras(cls, extras: Mapping[str, Any]) -> QPSolverDiagnostics:
        return cls(
            backend=extras.get("backend"),
            backend_version=extras.get("backend_version"),
            status=extras.get("status"),
            status_code=extras.get("status_code"),
            iterations=extras.get("iterations"),
            solve_time_seconds=extras.get("solve_time_seconds"),
            setup_time_seconds=extras.get("setup_time_seconds"),
            message=extras.get("message"),
            success=extras.get("success"),
        )
