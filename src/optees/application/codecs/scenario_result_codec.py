from __future__ import annotations

import math
from typing import Any

from optees.application.contracts.execution import (
    MathematicalStatus,
    SerializedResult,
    TerminationReason,
)
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.domain.models.scenario.scenario_result import (
    ScenarioResult,
    ScenarioSolveStatus,
)

_STATUS_MAP = {
    ScenarioSolveStatus.OPTIMAL: MathematicalStatus.OPTIMAL,
    ScenarioSolveStatus.FEASIBLE: MathematicalStatus.FEASIBLE,
    ScenarioSolveStatus.INFEASIBLE: MathematicalStatus.INFEASIBLE,
    ScenarioSolveStatus.UNBOUNDED: MathematicalStatus.UNBOUNDED,
    ScenarioSolveStatus.NOT_SOLVED: MathematicalStatus.NOT_SOLVED,
}


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Expected numeric value for {name}, got {type(value).__name__}")
    val = float(value)
    if not math.isfinite(val):
        raise ValueError(f"Non-finite value for {name}: {val}")
    return val


def _termination_reason(solution: ScenarioResult) -> TerminationReason:
    delegated = solution.delegated_solution
    if hasattr(delegated, "termination_reason") and delegated.termination_reason:
        try:
            return TerminationReason(delegated.termination_reason)
        except ValueError:
            pass
    if solution.status in (
        ScenarioSolveStatus.OPTIMAL,
        ScenarioSolveStatus.FEASIBLE,
        ScenarioSolveStatus.INFEASIBLE,
        ScenarioSolveStatus.UNBOUNDED,
    ):
        return TerminationReason.COMPLETED
    msg = str(delegated.diagnostics.message or "").lower()
    if "time" in msg or "timeout" in msg:
        return TerminationReason.TIME_LIMIT
    if "iteration" in msg:
        return TerminationReason.ITERATION_LIMIT
    return TerminationReason.COMPLETED


class ScenarioResultCodec:
    """Serializes a pure domain ScenarioResult into the frozen public JSON DTO (version 1)."""

    result_schema_version = "1"

    def serialize(self, solution: ScenarioResult) -> SerializedResult:
        if not isinstance(solution, ScenarioResult):
            raise TypeError(f"Expected ScenarioResult instance, got {type(solution).__name__}")

        math_status = _STATUS_MAP[solution.status]

        if solution.has_candidate():
            assert solution.variables is not None
            assert solution.guaranteed_value is not None
            variables_list: list[dict[str, JsonValue]] = [
                {
                    "name": name,
                    "value": _finite(solution.variables[name], f"variables.{name}"),
                }
                for name in solution.original_variable_order
            ]
            scenario_values_list: list[dict[str, JsonValue]] = [
                {
                    "scenario_id": sv.scenario_id,
                    "value": _finite(sv.value, f"scenario_values.{sv.scenario_id}"),
                    "is_binding": bool(sv.is_binding),
                }
                for sv in solution.scenario_values
            ]
            binding_ids: list[JsonValue] = list(solution.binding_scenario_ids)
            guaranteed_val: JsonValue = _finite(solution.guaranteed_value, "guaranteed_value")
        else:
            variables_list = []
            scenario_values_list = []
            binding_ids = []
            guaranteed_val = None

        result_dict: dict[str, Any] = {
            "orientation": solution.orientation.value,
            "guaranteed_value": guaranteed_val,
            "variables": variables_list,
            "scenario_values": scenario_values_list,
            "binding_scenario_ids": binding_ids,
        }

        # Diagnostics: forward delegated solver diagnostics
        delegated = solution.delegated_solution
        diag = delegated.diagnostics
        diag_dict: dict[str, Any] = {}

        backend = getattr(diag, "backend", None) or delegated.extras.get("backend")
        if not backend and hasattr(diag, "method") and diag.method:
            backend = (
                "scipy.linprog.highs" if diag.method == "highs" else f"scipy.linprog.{diag.method}"
            )
        if backend:
            diag_dict["backend"] = str(backend)

        message = getattr(diag, "message", None)
        if message is not None:
            diag_dict["message"] = str(message)

        status_code = getattr(diag, "status_code", None)
        if status_code is not None and not isinstance(status_code, bool):
            diag_dict["status_code"] = int(status_code)

        wall_time = getattr(diag, "wall_time", None) or delegated.extras.get("wall_time")
        if (
            wall_time is not None
            and isinstance(wall_time, (int, float))
            and not isinstance(wall_time, bool)
            and math.isfinite(wall_time)
        ):
            diag_dict["wall_time"] = float(wall_time)

        iterations = getattr(diag, "iterations", None) or getattr(diag, "nit", None)
        if (
            iterations is not None
            and isinstance(iterations, int)
            and not isinstance(iterations, bool)
        ):
            diag_dict["iterations"] = int(iterations)

        success = getattr(diag, "success", None)
        if success is not None and isinstance(success, bool):
            diag_dict["success"] = bool(success)

        normalized_result = require_json_value(result_dict, path="$.result")
        normalized_diag = require_json_value(diag_dict, path="$.diagnostics")
        assert isinstance(normalized_result, dict)
        assert isinstance(normalized_diag, dict)

        warnings: tuple[str, ...] = ()
        if solution.status == ScenarioSolveStatus.FEASIBLE:
            warnings = (
                "The solver returned a feasible candidate that has not met full optimality criteria.",
            )

        return SerializedResult(
            mathematical_status=math_status,
            result=normalized_result,
            diagnostics=normalized_diag,
            warnings=warnings,
            termination_reason=_termination_reason(solution),
        )
