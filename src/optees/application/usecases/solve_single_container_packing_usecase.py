from __future__ import annotations

from dataclasses import replace
from threading import Event
from typing import Any, Dict, List

from optees.application.ports.packing_solver_port import PackingSolverPort
from optees.domain.entities.packing.solution import (
    PackingPlacement,
    PackingSolution,
    PackingSolveResult,
)
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus
from optees.domain.value_objects.packing.selection_policy import PackingSelectionPolicy
from optees.domain.value_objects.packing.gravity_mode import PackingGravityMode


class SolveSingleContainerPackingUseCase:
    """Solve the requested model and, when needed, a labelled recovery model."""

    def __init__(self, solver_port: PackingSolverPort):
        self._solver = solver_port
        self._cancel_requested = Event()

    def execute(self, model: SingleContainerPackingModel) -> PackingSolveResult:
        try:
            requested_problem = self._map_model_to_problem(model)
            requested = self._solution(self._solver.solve(requested_problem), model.gravity_mode)

            recovery = None
            if (
                not self._cancel_requested.is_set()
                and model.selection_policy is PackingSelectionPolicy.ALL_REQUIRED
                and requested.status is MILPSolveStatus.INFEASIBLE
            ):
                recovery_problem = dict(requested_problem)
                recovery_problem["all_items_required"] = False
                recovery_problem["solve_role"] = "maximum_feasible_recovery"
                recovery = self._solution(self._solver.solve(recovery_problem), model.gravity_mode)

            return PackingSolveResult(requested=requested, recovery=recovery)
        finally:
            self._cancel_requested.clear()

    def cancel(self) -> bool:
        """Cooperatively interrupt the current backend solve."""
        self._cancel_requested.set()
        cancel = getattr(self._solver, "cancel", None)
        if not callable(cancel):
            return False
        cancel()
        return True

    @staticmethod
    def _solution(raw: Dict[str, Any], gravity_mode: PackingGravityMode) -> PackingSolution:
        solution = PackingSolution.from_solver_result(raw)
        if gravity_mode is not PackingGravityMode.SIMPLE or not solution.has_incumbent():
            return solution
        placements = _compact_downward(solution.placements)
        extras = dict(solution.extras)
        extras["gravity_mode"] = gravity_mode.value
        return replace(solution, placements=placements, extras=extras)

    @staticmethod
    def _map_model_to_problem(model: SingleContainerPackingModel) -> Dict[str, Any]:
        units: List[Dict[str, Any]] = []
        for item in model.items:
            orientations = [
                {
                    "code": orientation.code,
                    "dimensions": list(orientation.dimensions.as_tuple()),
                }
                for orientation in item.orientations()
            ]
            consumptions = {
                consumption.name.casefold(): consumption.amount
                for consumption in item.consumptions
            }
            for unit_index in range(1, item.quantity + 1):
                units.append(
                    {
                        "instance_id": f"{item.item_id}#{unit_index}",
                        "item_id": item.item_id,
                        "item_name": item.name,
                        "unit_index": unit_index,
                        "value": item.value,
                        "volume": item.dimensions.volume(),
                        "orientations": orientations,
                        "consumptions": consumptions,
                    }
                )

        problem: Dict[str, Any] = {
            "container": {
                "container_id": model.container.container_id,
                "name": model.container.name,
                "dimensions": list(model.container.dimensions.as_tuple()),
                "capacities": {
                    capacity.name.casefold(): capacity.limit
                    for capacity in model.container.capacities
                },
            },
            "items": units,
            "all_items_required": model.selection_policy
            is PackingSelectionPolicy.ALL_REQUIRED,
            "solve_role": "requested",
            "time_limit": model.time_limit,
            "mip_gap": model.mip_gap,
        }
        return problem


def _compact_downward(
    placements: tuple[PackingPlacement, ...],
) -> tuple[PackingPlacement, ...]:
    """Lower boxes without changing X/Y, orientation, or pairwise feasibility.

    Boxes are processed from bottom to top. A box stops at the highest upper
    face below it whose horizontal footprint overlaps, otherwise at z=0. This
    is geometric compaction, not a stability or minimum-support-area model.
    """

    lowered: list[PackingPlacement] = []
    by_instance: dict[str, PackingPlacement] = {}
    for placement in sorted(placements, key=lambda value: (value.z, value.instance_id)):
        support_height = 0.0
        for support in lowered:
            if _footprints_overlap(placement, support):
                support_height = max(support_height, support.z + support.height)
        compacted = replace(placement, z=support_height)
        lowered.append(compacted)
        by_instance[compacted.instance_id] = compacted
    return tuple(by_instance[placement.instance_id] for placement in placements)


def _footprints_overlap(first: PackingPlacement, second: PackingPlacement) -> bool:
    tolerance = 1e-9
    overlap_x = min(first.x + first.length, second.x + second.length) - max(first.x, second.x)
    overlap_y = min(first.y + first.width, second.y + second.width) - max(first.y, second.y)
    return overlap_x > tolerance and overlap_y > tolerance
