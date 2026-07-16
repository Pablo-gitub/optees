from __future__ import annotations

import math

from optees.application.contracts.execution import MathematicalStatus
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus
from optees.domain.value_objects.knapsack.solver_diagnostics import (
    KnapsackSolverDiagnostics,
)


_STATUS_MAP = {
    KnapsackSolveStatus.OPTIMAL: MathematicalStatus.OPTIMAL,
    KnapsackSolveStatus.FEASIBLE: MathematicalStatus.FEASIBLE,
    KnapsackSolveStatus.INFEASIBLE: MathematicalStatus.INFEASIBLE,
    KnapsackSolveStatus.UNBOUNDED: MathematicalStatus.UNBOUNDED,
    KnapsackSolveStatus.NOT_SOLVED: MathematicalStatus.NOT_SOLVED,
}


def mathematical_status(status: KnapsackSolveStatus) -> MathematicalStatus:
    return _STATUS_MAP[status]


def optional_finite(value: object, path: str) -> float | None:
    if value is None:
        return None
    return finite(value, path)


def finite(value: object, path: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{path} must be a finite number.")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be a finite number.") from exc
    if not math.isfinite(normalized):
        raise ValueError(f"{path} must be a finite number.")
    return normalized


def diagnostics_payload(
    diagnostics: KnapsackSolverDiagnostics,
    extras: dict[str, object],
) -> dict[str, JsonValue]:
    payload = {
        "method": diagnostics.method,
        "message": diagnostics.message,
        "item_count": diagnostics.item_count,
        "capacity": diagnostics.capacity,
        "dp_cells": diagnostics.dp_cells,
        "max_dp_cells": diagnostics.max_dp_cells,
        "complexity": diagnostics.complexity,
        "success": _optional_bool(extras.get("success")),
    }
    normalized = require_json_value(payload, path="$.diagnostics")
    assert isinstance(normalized, dict)
    return normalized


def not_solved_warning(
    status: KnapsackSolveStatus,
    *,
    solver_label: str,
) -> tuple[str, ...]:
    if status is KnapsackSolveStatus.NOT_SOLVED:
        return (f"The {solver_label} produced no solution.",)
    return ()


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None
