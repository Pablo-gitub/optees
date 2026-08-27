from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from optees.domain.value_objects.qp.qp_dual_values import QPDualValues
from optees.domain.value_objects.qp.qp_kkt_residuals import QPKKTResiduals
from optees.domain.value_objects.qp.qp_solve_status import QPSolveStatus
from optees.domain.value_objects.qp.qp_solver_diagnostics import QPSolverDiagnostics


@dataclass(frozen=True)
class QPSolution:
    """Domain entity representing the result of solving a Convex QP."""

    status: QPSolveStatus
    objective: Optional[float]
    values: dict[str, float]
    dual_values: Optional[QPDualValues] = None
    kkt_residuals: Optional[QPKKTResiduals] = None
    diagnostics: QPSolverDiagnostics = field(default_factory=QPSolverDiagnostics)
    termination_reason: str = "completed"
    extras: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_solver_result(
        cls,
        *,
        status: str | QPSolveStatus,
        objective: Optional[float],
        values: Mapping[str, float],
        dual_values: Optional[QPDualValues] = None,
        kkt_residuals: Optional[QPKKTResiduals] = None,
        diagnostics: Optional[QPSolverDiagnostics] = None,
        termination_reason: str = "completed",
        extras: Optional[Mapping[str, Any]] = None,
    ) -> QPSolution:
        status_enum = (
            status if isinstance(status, QPSolveStatus) else QPSolveStatus.from_str(str(status))
        )
        extras_dict = dict(extras or {})
        diag = diagnostics or QPSolverDiagnostics.from_extras(extras_dict)
        return cls(
            status=status_enum,
            objective=objective,
            values=dict(values or {}),
            dual_values=dual_values,
            kkt_residuals=kkt_residuals,
            diagnostics=diag,
            termination_reason=termination_reason,
            extras=extras_dict,
        )

    def is_optimal(self) -> bool:
        return self.status == QPSolveStatus.OPTIMAL
