from __future__ import annotations

import math

from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.json_value import require_json_value
from optees.domain.entities.knapsack.solution import KnapsackSolution
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus


class KnapsackZeroOneResultCodec:
    capability_id = "knapsack.zero_one"
    result_schema_version = "1"

    def serialize(self, solution: KnapsackSolution) -> SerializedResult:
        selected_items = [
            {"index": index, "name": name}
            for index, name in zip(
                solution.selected_indices,
                solution.selected_item_names,
                strict=True,
            )
        ]
        result: dict[str, object] = {
            "objective": _optional_finite(solution.objective, "objective"),
            "selected_indices": list(solution.selected_indices),
            "selected_items": selected_items,
            "total_value": _finite(solution.total_value, "total_value"),
            "total_weight": solution.total_weight,
            "remaining_capacity": solution.remaining_capacity,
        }
        diagnostics = {
            "method": solution.diagnostics.method,
            "message": solution.diagnostics.message,
            "item_count": solution.diagnostics.item_count,
            "capacity": solution.diagnostics.capacity,
            "dp_cells": solution.diagnostics.dp_cells,
            "max_dp_cells": solution.diagnostics.max_dp_cells,
            "complexity": solution.diagnostics.complexity,
            "success": _optional_bool(solution.extras.get("success")),
        }
        normalized_result = require_json_value(result, path="$.result")
        normalized_diagnostics = require_json_value(
            diagnostics, path="$.diagnostics"
        )
        assert isinstance(normalized_result, dict)
        assert isinstance(normalized_diagnostics, dict)
        return SerializedResult(
            mathematical_status=_STATUS_MAP[solution.status],
            result=normalized_result,
            diagnostics=normalized_diagnostics,
            warnings=_warnings(solution),
        )


_STATUS_MAP = {
    KnapsackSolveStatus.OPTIMAL: MathematicalStatus.OPTIMAL,
    KnapsackSolveStatus.FEASIBLE: MathematicalStatus.FEASIBLE,
    KnapsackSolveStatus.INFEASIBLE: MathematicalStatus.INFEASIBLE,
    KnapsackSolveStatus.UNBOUNDED: MathematicalStatus.UNBOUNDED,
    KnapsackSolveStatus.NOT_SOLVED: MathematicalStatus.NOT_SOLVED,
}


def _optional_finite(value: object, path: str) -> float | None:
    if value is None:
        return None
    return _finite(value, path)


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


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _warnings(solution: KnapsackSolution) -> tuple[str, ...]:
    if solution.status is KnapsackSolveStatus.NOT_SOLVED:
        return ("The exact dynamic-programming solver produced no solution.",)
    return ()
