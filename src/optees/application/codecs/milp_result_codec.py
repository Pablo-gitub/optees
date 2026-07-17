from __future__ import annotations

import math

from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.domain.entities.milp.solution import MILPSolution
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus


_STATUS_MAP = {
    MILPSolveStatus.OPTIMAL: MathematicalStatus.OPTIMAL,
    MILPSolveStatus.FEASIBLE: MathematicalStatus.FEASIBLE,
    MILPSolveStatus.INFEASIBLE: MathematicalStatus.INFEASIBLE,
    MILPSolveStatus.UNBOUNDED: MathematicalStatus.UNBOUNDED,
    MILPSolveStatus.NOT_SOLVED: MathematicalStatus.NOT_SOLVED,
}


class MILPResultCodec:
    capability_id = "milp.linear"
    result_schema_version = "1"

    def serialize(self, solution: MILPSolution) -> SerializedResult:
        variables = [
            {"name": name, "value": _finite(value, f"variables.{name}")}
            for name, value in solution.values.items()
        ]
        result = _strict_payload(
            {
                "objective": _optional_finite(solution.objective, "objective"),
                "variables": variables,
            },
            path="$.result",
        )
        diagnostics = _strict_payload(
            {
                "backend": solution.diagnostics.backend,
                "message": solution.diagnostics.message,
                "status_code": solution.diagnostics.status_code,
                "status": solution.diagnostics.status_str,
                "best_bound": _optional_diagnostic_number(
                    solution.diagnostics.best_bound
                ),
                "relative_gap": _optional_diagnostic_number(
                    solution.diagnostics.relative_gap
                ),
                "wall_time": _optional_diagnostic_number(
                    solution.diagnostics.wall_time
                ),
                "wall_time_ms": solution.diagnostics.wall_time_ms,
                "nodes": solution.diagnostics.nodes,
                "branches": solution.diagnostics.branches,
                "conflicts": solution.diagnostics.conflicts,
                "success": _optional_bool(solution.extras.get("success")),
            },
            path="$.diagnostics",
        )
        return SerializedResult(
            mathematical_status=_STATUS_MAP[solution.status],
            result=result,
            diagnostics=diagnostics,
            warnings=_warnings(solution.status),
        )


def _warnings(status: MILPSolveStatus) -> tuple[str, ...]:
    if status is MILPSolveStatus.FEASIBLE:
        return (
            "The solver returned a feasible incumbent without proving global "
            "optimality.",
        )
    if status is MILPSolveStatus.NOT_SOLVED:
        return ("The MILP solver produced no usable solution.",)
    return ()


def _finite(value: object, path: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{path} must be a finite number.")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be a finite number.") from exc
    if not math.isfinite(normalized):
        raise ValueError(f"{path} must be a finite number.")
    return normalized


def _optional_finite(value: object, path: str) -> float | None:
    return None if value is None else _finite(value, path)


def _optional_diagnostic_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return normalized if math.isfinite(normalized) else None


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _strict_payload(payload: dict[str, object], *, path: str) -> dict[str, JsonValue]:
    normalized = require_json_value(payload, path=path)
    assert isinstance(normalized, dict)
    return normalized
