from __future__ import annotations

import math

from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.domain.entities.packing.solution import (
    PackingSolution,
    PackingSolveResult,
)
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus


_STATUS_MAP = {
    MILPSolveStatus.OPTIMAL: MathematicalStatus.OPTIMAL,
    MILPSolveStatus.FEASIBLE: MathematicalStatus.FEASIBLE,
    MILPSolveStatus.INFEASIBLE: MathematicalStatus.INFEASIBLE,
    MILPSolveStatus.UNBOUNDED: MathematicalStatus.UNBOUNDED,
    MILPSolveStatus.NOT_SOLVED: MathematicalStatus.NOT_SOLVED,
}


class PackingResultCodec:
    capability_id = "packing.single_container_3d"
    result_schema_version = "1"

    def serialize(self, solve_result: PackingSolveResult) -> SerializedResult:
        requested = solve_result.requested
        result = _strict_payload(
            {
                "requested": _solution_payload(requested),
                "recovery": (
                    _solution_payload(solve_result.recovery)
                    if solve_result.recovery is not None
                    else None
                ),
            },
            path="$.result",
        )
        diagnostics = _strict_payload(
            {
                "requested": _diagnostics_payload(requested),
                "recovery": (
                    _diagnostics_payload(solve_result.recovery)
                    if solve_result.recovery is not None
                    else None
                ),
            },
            path="$.diagnostics",
        )
        return SerializedResult(
            mathematical_status=_STATUS_MAP[requested.status],
            result=result,
            diagnostics=diagnostics,
            warnings=_warnings(solve_result),
        )


def _solution_payload(solution: PackingSolution) -> dict[str, object]:
    return {
        "objective": _optional_finite(solution.objective),
        "total_value": _finite(solution.total_value),
        "used_volume": _finite(solution.used_volume),
        "placements": [
            {
                "instance_id": placement.instance_id,
                "item_id": placement.item_id,
                "item_name": placement.item_name,
                "unit_index": placement.unit_index,
                "orientation_code": placement.orientation_code,
                "position": {
                    "x": _finite(placement.x),
                    "y": _finite(placement.y),
                    "z": _finite(placement.z),
                },
                "dimensions": {
                    "length": _finite(placement.length),
                    "width": _finite(placement.width),
                    "height": _finite(placement.height),
                },
                "value": _finite(placement.value),
            }
            for placement in solution.placements
        ],
        "excluded_instance_ids": list(solution.excluded_instance_ids),
    }


def _diagnostics_payload(solution: PackingSolution) -> dict[str, object]:
    extras = solution.extras
    return {
        "solver_status": solution.status.value,
        "backend": solution.diagnostics.backend,
        "message": solution.diagnostics.message,
        "status_code": solution.diagnostics.status_code,
        "best_bound": _optional_finite(solution.diagnostics.best_bound),
        "relative_gap": _optional_finite(solution.diagnostics.relative_gap),
        "wall_time_ms": solution.diagnostics.wall_time_ms,
        "nodes": solution.diagnostics.nodes,
        "solve_role": _optional_string(extras.get("solve_role")),
        "gravity_mode": _optional_string(extras.get("gravity_mode")),
        "mip_gap_requested": _optional_finite(extras.get("mip_gap_requested")),
        "mip_gap_applied": _optional_bool(extras.get("mip_gap_applied")),
        "variable_count": _optional_non_negative_int(extras.get("variable_count")),
        "constraint_count": _optional_non_negative_int(
            extras.get("constraint_count")
        ),
        "item_pair_count": _optional_non_negative_int(extras.get("item_pair_count")),
        "separation_binary_count": _optional_non_negative_int(
            extras.get("separation_binary_count")
        ),
    }


def _warnings(result: PackingSolveResult) -> tuple[str, ...]:
    status = result.requested.status
    if status is MILPSolveStatus.FEASIBLE:
        return (
            "The solver returned a feasible packing without proving global optimality.",
        )
    if status is MILPSolveStatus.INFEASIBLE and result.has_recovery():
        return (
            "The requested all-items packing is infeasible; recovery contains a "
            "separate maximum-value feasible packing with excluded items.",
        )
    if status is MILPSolveStatus.INFEASIBLE:
        return ("The requested packing has no feasible placement.",)
    if status is MILPSolveStatus.NOT_SOLVED:
        return ("The packing backend produced no usable placement.",)
    return ()


def _finite(value: object) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError("packing result contains a non-finite number")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("packing result contains a non-finite number") from exc
    if not math.isfinite(normalized):
        raise ValueError("packing result contains a non-finite number")
    return normalized


def _optional_finite(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    return normalized if math.isfinite(normalized) else None


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_non_negative_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        normalized = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    return normalized if normalized >= 0 else None


def _strict_payload(payload: dict[str, object], *, path: str) -> dict[str, JsonValue]:
    normalized = require_json_value(payload, path=path)
    assert isinstance(normalized, dict)
    return normalized
