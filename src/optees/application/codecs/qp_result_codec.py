from __future__ import annotations

from typing import Any, Dict, List

from optees.application.contracts.capability_ids import QP_CAPABILITY_ID
from optees.application.contracts.execution import (
    MathematicalStatus,
    SerializedResult,
    TerminationReason,
)
from optees.application.contracts.json_value import require_json_value
from optees.domain.entities.qp.solution import QPSolution
from optees.domain.value_objects.qp.qp_solve_status import QPSolveStatus

_STATUS_MAP = {
    QPSolveStatus.OPTIMAL: MathematicalStatus.OPTIMAL,
    QPSolveStatus.FEASIBLE: MathematicalStatus.FEASIBLE,
    QPSolveStatus.INFEASIBLE: MathematicalStatus.INFEASIBLE,
    QPSolveStatus.UNBOUNDED: MathematicalStatus.UNBOUNDED,
    QPSolveStatus.NOT_SOLVED: MathematicalStatus.NOT_SOLVED,
}


class QPResultCodec:
    capability_id = QP_CAPABILITY_ID
    result_schema_version = "1"

    def serialize(self, solution: QPSolution) -> SerializedResult:
        math_status = _STATUS_MAP.get(solution.status, MathematicalStatus.NOT_SOLVED)

        result_dict: Dict[str, Any] = {
            "objective": solution.objective,
            "objective_sense": str(solution.extras.get("objective_sense", "min")),
            "variables": [
                {"name": name, "value": value} for name, value in solution.values.items()
            ],
        }

        if solution.dual_values is not None:
            result_dict["dual_values"] = {
                "constraints": list(solution.dual_values.constraints),
                "lower_bounds": list(solution.dual_values.lower_bounds),
                "upper_bounds": list(solution.dual_values.upper_bounds),
            }

        if solution.kkt_residuals is not None:
            result_dict["kkt_residuals"] = {
                key: value
                for key, value in {
                    "primal_residual": solution.kkt_residuals.primal_residual,
                    "dual_residual": solution.kkt_residuals.dual_residual,
                    "duality_gap": solution.kkt_residuals.duality_gap,
                    "complementarity_residual": solution.kkt_residuals.complementarity_residual,
                }.items()
                if value is not None
            }

        diag = solution.diagnostics
        diagnostics_dict: Dict[str, Any] = {
            "backend": diag.backend,
            "backend_version": diag.backend_version,
            "status": diag.status,
            "status_code": diag.status_code,
            "iterations": diag.iterations,
            "solve_time_seconds": diag.solve_time_seconds,
            "setup_time_seconds": diag.setup_time_seconds,
            "pri_res": solution.extras.get("pri_res"),
            "dua_res": solution.extras.get("dua_res"),
            "message": diag.message,
            "success": diag.success,
        }

        warnings: List[str] = []
        if solution.status == QPSolveStatus.FEASIBLE:
            warnings.append(
                "The solver returned a feasible candidate that has not met the full optimal stopping criteria."
            )

        normalized_result = require_json_value(result_dict, path="$.result")
        normalized_diag = require_json_value(diagnostics_dict, path="$.diagnostics")
        assert isinstance(normalized_result, dict)
        assert isinstance(normalized_diag, dict)

        try:
            termination_reason = TerminationReason(solution.termination_reason)
        except ValueError:
            termination_reason = TerminationReason.INTERNAL_ERROR

        return SerializedResult(
            mathematical_status=math_status,
            result=normalized_result,
            diagnostics=normalized_diag,
            warnings=tuple(warnings),
            termination_reason=termination_reason,
        )
