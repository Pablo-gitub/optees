from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from optees.domain.value_objects.milp.solve_status import MILPSolveStatus
from optees.domain.value_objects.milp.solver_diagnostics import MILPSolverDiagnostics


@dataclass(frozen=True)
class PackingPlacement:
    instance_id: str
    item_id: str
    item_name: str
    unit_index: int
    orientation_code: str
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float
    value: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PackingPlacement":
        return PackingPlacement(
            instance_id=str(data["instance_id"]),
            item_id=str(data["item_id"]),
            item_name=str(data["item_name"]),
            unit_index=int(data["unit_index"]),
            orientation_code=str(data["orientation_code"]),
            x=float(data["x"]),
            y=float(data["y"]),
            z=float(data["z"]),
            length=float(data["length"]),
            width=float(data["width"]),
            height=float(data["height"]),
            value=float(data["value"]),
        )

    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass(frozen=True)
class PackingSolution:
    status: MILPSolveStatus
    objective: Optional[float]
    placements: Tuple[PackingPlacement, ...]
    excluded_instance_ids: Tuple[str, ...]
    total_value: float
    used_volume: float
    diagnostics: MILPSolverDiagnostics
    extras: Dict[str, object]

    @staticmethod
    def from_solver_result(raw: Dict[str, Any]) -> "PackingSolution":
        extras = dict(raw.get("extras", {}) or {})
        placements = tuple(
            PackingPlacement.from_dict(dict(placement))
            for placement in raw.get("placements", ())
        )
        objective = raw.get("objective")
        return PackingSolution(
            status=MILPSolveStatus.from_str(raw.get("status", "NotSolved")),
            objective=None if objective is None else float(objective),
            placements=placements,
            excluded_instance_ids=tuple(str(value) for value in raw.get("excluded_instance_ids", ())),
            total_value=float(sum(placement.value for placement in placements)),
            used_volume=float(sum(placement.volume() for placement in placements)),
            diagnostics=MILPSolverDiagnostics.from_extras(extras),
            extras=extras,
        )

    def has_incumbent(self) -> bool:
        return self.status in (MILPSolveStatus.OPTIMAL, MILPSolveStatus.FEASIBLE)


@dataclass(frozen=True)
class PackingSolveResult:
    requested: PackingSolution
    recovery: Optional[PackingSolution] = None

    def has_recovery(self) -> bool:
        return self.recovery is not None and self.recovery.has_incumbent()
