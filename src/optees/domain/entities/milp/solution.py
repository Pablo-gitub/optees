from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional

from optees.domain.value_objects.milp.solve_status import MILPSolveStatus
from optees.domain.value_objects.milp.solver_diagnostics import MILPSolverDiagnostics
from optees.domain.value_objects.immutable import freeze_mapping


@dataclass(frozen=True)
class MILPSolution:
    """Domain result for a MILP solve, including feasible-but-not-proven states."""

    status: MILPSolveStatus
    objective: Optional[float]
    values: Dict[str, float]
    diagnostics: MILPSolverDiagnostics
    extras: Dict[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", freeze_mapping(self.values))
        object.__setattr__(self, "extras", freeze_mapping(self.extras))

    @staticmethod
    def from_utility_tuple(
        status: str,
        objective: Optional[float],
        x_dict: Dict[str, float],
        extras: Dict[str, object],
    ) -> "MILPSolution":
        extras = dict(extras or {})
        return MILPSolution(
            status=MILPSolveStatus.from_str(status),
            objective=objective,
            values=dict(x_dict or {}),
            diagnostics=MILPSolverDiagnostics.from_extras(extras),
            extras=extras,
        )

    def is_optimal(self) -> bool:
        return self.status is MILPSolveStatus.OPTIMAL

    def has_incumbent(self) -> bool:
        return self.status in (MILPSolveStatus.OPTIMAL, MILPSolveStatus.FEASIBLE)
