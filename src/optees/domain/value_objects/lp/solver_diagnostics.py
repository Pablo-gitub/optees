# src/optees/domain/value_objects/lp/solver_diagnostics.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass(frozen=True)
class SolverDiagnostics:
    # Generic, solver-agnostic diagnostics. Keep optional and pass-through friendly.
    method: Optional[str] = None
    nit: Optional[int] = None
    crossover_nit: Optional[int] = None
    message: Optional[str] = None
    status_code: Optional[int] = None
    success: Optional[bool] = None
    # Optional HiGHS-specific blocks (keep as raw dicts to avoid hard coupling)
    eqlin: Optional[Dict[str, Any]] = None
    ineqlin: Optional[Dict[str, Any]] = None
    lower: Optional[Dict[str, Any]] = None
    upper: Optional[Dict[str, Any]] = None

    @staticmethod
    def from_extras(extras: Dict[str, Any]) -> "SolverDiagnostics":
        return SolverDiagnostics(
            method=extras.get("method"),
            nit=extras.get("nit"),
            crossover_nit=extras.get("crossover_nit"),
            message=extras.get("message"),
            status_code=extras.get("status_code"),
            success=extras.get("success"),
            eqlin=extras.get("eqlin"),
            ineqlin=extras.get("ineqlin"),
            lower=extras.get("lower"),
            upper=extras.get("upper"),
        )
