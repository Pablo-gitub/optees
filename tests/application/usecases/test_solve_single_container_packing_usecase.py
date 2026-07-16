from __future__ import annotations

import pytest

from optees.application.usecases.solve_single_container_packing_usecase import (
    SolveSingleContainerPackingUseCase,
)
from optees.domain.entities.packing.container import PackingContainer
from optees.domain.entities.packing.geometry import Dimensions3D
from optees.domain.entities.packing.item import PackingItem
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus
from optees.domain.value_objects.packing.selection_policy import PackingSelectionPolicy
from optees.domain.value_objects.packing.gravity_mode import PackingGravityMode


class RecordingPackingPort:
    def __init__(self, results):
        self.results = list(results)
        self.problems = []

    def solve(self, problem):
        self.problems.append(problem)
        return self.results.pop(0)

    def cancel(self):
        self.cancelled = True
        return True


def _model(
    selection_policy=PackingSelectionPolicy.OPTIONAL,
    gravity_mode=PackingGravityMode.SIMPLE,
):
    return SingleContainerPackingModel.from_parts(
        PackingContainer("c1", "Container", Dimensions3D(5, 4, 3)),
        (
            PackingItem.from_parts(
                "box",
                "Box",
                Dimensions3D(2, 1, 1),
                quantity=2,
                value=5,
            ),
        ),
        selection_policy=selection_policy,
        gravity_mode=gravity_mode,
    )


def test_maps_quantities_to_indivisible_units():
    port = RecordingPackingPort(
        [{"status": "Optimal", "objective": 10, "placements": (), "extras": {}}]
    )

    result = SolveSingleContainerPackingUseCase(port).execute(_model())

    assert result.requested.status is MILPSolveStatus.OPTIMAL
    assert [unit["instance_id"] for unit in port.problems[0]["items"]] == [
        "box#1",
        "box#2",
    ]
    assert port.problems[0]["all_items_required"] is False
    assert len(port.problems[0]["items"][0]["orientations"]) == 3


def test_infeasible_required_request_triggers_separate_recovery_solve():
    port = RecordingPackingPort(
        [
            {"status": "Infeasible", "objective": None, "placements": (), "extras": {}},
            {"status": "Optimal", "objective": 5, "placements": (), "extras": {}},
        ]
    )

    result = SolveSingleContainerPackingUseCase(port).execute(
        _model(PackingSelectionPolicy.ALL_REQUIRED)
    )

    assert result.requested.status is MILPSolveStatus.INFEASIBLE
    assert result.has_recovery()
    assert port.problems[0]["all_items_required"] is True
    assert port.problems[0]["solve_role"] == "requested"
    assert port.problems[1]["all_items_required"] is False
    assert port.problems[1]["solve_role"] == "maximum_feasible_recovery"


def test_non_infeasible_required_result_does_not_change_the_problem():
    port = RecordingPackingPort(
        [{"status": "NotSolved", "objective": None, "placements": (), "extras": {}}]
    )

    result = SolveSingleContainerPackingUseCase(port).execute(
        _model(PackingSelectionPolicy.ALL_REQUIRED)
    )

    assert result.recovery is None
    assert len(port.problems) == 1


def test_cancel_is_delegated_to_solver_port():
    port = RecordingPackingPort([])

    assert SolveSingleContainerPackingUseCase(port).cancel() is True
    assert port.cancelled is True


def test_cancelled_infeasible_request_does_not_start_recovery():
    class CancellingPort(RecordingPackingPort):
        callback = None

        def solve(self, problem):
            if self.callback is not None:
                self.callback()
            return super().solve(problem)

    port = CancellingPort(
        [{"status": "Infeasible", "objective": None, "placements": (), "extras": {}}]
    )
    usecase = SolveSingleContainerPackingUseCase(port)
    port.callback = usecase.cancel

    result = usecase.execute(_model(PackingSelectionPolicy.ALL_REQUIRED))

    assert result.requested.status is MILPSolveStatus.INFEASIBLE
    assert result.recovery is None
    assert len(port.problems) == 1


@pytest.mark.parametrize(
    ("raw_status", "expected"),
    [
        ("Optimal", MILPSolveStatus.OPTIMAL),
        ("Feasible", MILPSolveStatus.FEASIBLE),
        ("Infeasible", MILPSolveStatus.INFEASIBLE),
        ("Unbounded", MILPSolveStatus.UNBOUNDED),
        ("NotSolved", MILPSolveStatus.NOT_SOLVED),
    ],
)
def test_preserves_every_normalized_solver_status(raw_status, expected):
    port = RecordingPackingPort(
        [{"status": raw_status, "objective": None, "placements": (), "extras": {}}]
    )

    result = SolveSingleContainerPackingUseCase(port).execute(_model())

    assert result.requested.status is expected
    assert result.recovery is None


def test_simple_gravity_lowers_boxes_to_floor_or_first_support():
    port = RecordingPackingPort([{
        "status": "Optimal",
        "objective": 10,
        "placements": [
            {
                "instance_id": "box#1", "item_id": "box", "item_name": "Box",
                "unit_index": 1, "orientation_code": "LWH", "x": 0, "y": 0,
                "z": 1, "length": 2, "width": 1, "height": 1, "value": 5,
            },
            {
                "instance_id": "box#2", "item_id": "box", "item_name": "Box",
                "unit_index": 2, "orientation_code": "LWH", "x": 0, "y": 0,
                "z": 2.5, "length": 2, "width": 1, "height": 1, "value": 5,
            },
        ],
        "extras": {},
    }])

    result = SolveSingleContainerPackingUseCase(port).execute(_model()).requested

    assert [placement.z for placement in result.placements] == [0, 1]
    assert result.extras["gravity_mode"] == "simple"


def test_no_gravity_preserves_solver_coordinates():
    port = RecordingPackingPort([{
        "status": "Optimal",
        "objective": 5,
        "placements": [{
            "instance_id": "box#1", "item_id": "box", "item_name": "Box",
            "unit_index": 1, "orientation_code": "LWH", "x": 0, "y": 0,
            "z": 1.75, "length": 2, "width": 1, "height": 1, "value": 5,
        }],
        "extras": {},
    }])

    result = SolveSingleContainerPackingUseCase(port).execute(
        _model(gravity_mode=PackingGravityMode.NONE)
    ).requested

    assert result.placements[0].z == 1.75
    assert "gravity_mode" not in result.extras
