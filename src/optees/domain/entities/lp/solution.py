from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from optees.domain.value_objects.lp.solve_status import SolveStatus
from optees.domain.value_objects.lp.solver_diagnostics import SolverDiagnostics

@dataclass(frozen=True)
class LPSolution:
    """Domain result for a solved LP."""
    status: SolveStatus
    objective: Optional[float]
    values: Dict[str, float]           # var_name -> value
    diagnostics: SolverDiagnostics

    @staticmethod
    def from_utility_tuple(
        status: str,
        objective: Optional[float],
        x_dict: Dict[str, float],
        extras: Dict[str, object],
    ) -> "LPSolution":
        return LPSolution(
            status=SolveStatus.from_str(status),
            objective=objective,
            values=dict(x_dict or {}),
            diagnostics=SolverDiagnostics.from_extras(extras or {}),
        )

    def is_optimal(self) -> bool:
        return self.status == SolveStatus.OPTIMAL
