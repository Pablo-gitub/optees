from __future__ import annotations

import importlib.util

import pytest

from optees.application.usecases.solve_single_container_packing_usecase import (
    SolveSingleContainerPackingUseCase,
)
from optees.data.adapters.packing.ortools_single_container_packing_adapter import (
    OrtoolsSingleContainerPackingAdapter,
    _reached_time_limit,
)
from optees.domain.entities.packing.container import PackingContainer
from optees.domain.entities.packing.geometry import Dimensions3D
from optees.domain.entities.packing.item import PackingItem
from optees.domain.entities.packing.resource import ResourceCapacity, ResourceConsumption
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus
from optees.domain.value_objects.packing.rotation_policy import RotationPolicy
from optees.domain.value_objects.packing.selection_policy import PackingSelectionPolicy


pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("ortools") is None,
    reason="ortools not installed",
)


def _solve(model):
    return SolveSingleContainerPackingUseCase(
        OrtoolsSingleContainerPackingAdapter()
    ).execute(model)


def test_required_rotation_is_selected_to_fit_the_container():
    model = SingleContainerPackingModel.from_parts(
        PackingContainer("c1", "Container", Dimensions3D(4, 3, 2)),
        (
            PackingItem.from_parts(
                "box",
                "Rotated box",
                Dimensions3D(3, 4, 2),
                rotation_policy=RotationPolicy.KEEP_UPRIGHT,
            ),
        ),
        selection_policy=PackingSelectionPolicy.ALL_REQUIRED,
        mip_gap=0.01,
    )

    result = _solve(model).requested

    assert result.status is MILPSolveStatus.OPTIMAL
    assert len(result.placements) == 1
    assert result.placements[0].orientation_code == "WLH"
    assert (
        result.placements[0].length,
        result.placements[0].width,
        result.placements[0].height,
    ) == pytest.approx((4, 3, 2))
    assert result.extras["backend"] in {"scip", "cbc"}
    assert result.extras["mip_gap_applied"] is (result.extras["backend"] == "scip")


def test_two_loaded_items_do_not_overlap():
    model = SingleContainerPackingModel.from_parts(
        PackingContainer("c1", "Container", Dimensions3D(4, 2, 2)),
        (
            PackingItem.from_parts(
                "cube",
                "Cube",
                Dimensions3D(2, 2, 2),
                quantity=2,
                rotation_policy=RotationPolicy.ANY_ORTHOGONAL,
            ),
        ),
        selection_policy=PackingSelectionPolicy.ALL_REQUIRED,
    )

    result = _solve(model).requested

    assert result.status is MILPSolveStatus.OPTIMAL
    assert len(result.placements) == 2
    assert not _overlap(result.placements[0], result.placements[1])
    assert result.extras["item_pair_count"] == 1
    assert result.extras["separation_binary_count"] == 6


@pytest.mark.parametrize(
    ("container_dimensions", "axis"),
    [((4, 2, 2), "x"), ((2, 4, 2), "y"), ((2, 2, 4), "z")],
)
def test_pairwise_disjunction_can_separate_on_each_axis(container_dimensions, axis):
    model = SingleContainerPackingModel.from_parts(
        PackingContainer("c1", "Container", Dimensions3D(*container_dimensions)),
        (
            PackingItem.from_parts(
                "cube", "Cube", Dimensions3D(2, 2, 2), quantity=2,
                rotation_policy=RotationPolicy.FIXED,
            ),
        ),
        selection_policy=PackingSelectionPolicy.ALL_REQUIRED,
    )

    placements = _solve(model).requested.placements

    assert len(placements) == 2
    first, second = placements
    size = {"x": "length", "y": "width", "z": "height"}[axis]
    assert (
        getattr(first, axis) + getattr(first, size) <= getattr(second, axis) + 1e-7
        or getattr(second, axis) + getattr(second, size) <= getattr(first, axis) + 1e-7
    )


def test_adapter_forwards_interrupt_to_active_ortools_solver():
    class InterruptibleSolver:
        def __init__(self):
            self.calls = 0

        def InterruptSolve(self):
            self.calls += 1
            return True

    adapter = OrtoolsSingleContainerPackingAdapter()
    solver = InterruptibleSolver()
    adapter._register_solver(solver)

    assert adapter.cancel() is True
    assert solver.calls == 1


def test_adapter_accepts_cancellation_before_solver_registration():
    adapter = OrtoolsSingleContainerPackingAdapter()

    assert adapter.cancel() is True


def test_adapter_marks_only_early_stopped_runs_near_configured_time_limit():
    assert _reached_time_limit("Feasible", 10, 9500) is True
    assert _reached_time_limit("Feasible", 10, 1000) is False
    assert _reached_time_limit("Optimal", 10, 10000) is False


def test_weight_capacity_selects_the_most_valuable_feasible_item():
    container = PackingContainer.from_parts(
        "c1",
        "Container",
        Dimensions3D(5, 5, 5),
        (ResourceCapacity("weight", 5),),
    )
    model = SingleContainerPackingModel.from_parts(
        container,
        (
            PackingItem.from_parts(
                "heavy",
                "Heavy",
                Dimensions3D(1, 1, 1),
                value=10,
                consumptions=(ResourceConsumption("WEIGHT", 5),),
            ),
            PackingItem.from_parts(
                "light",
                "Light",
                Dimensions3D(1, 1, 1),
                value=6,
                consumptions=(ResourceConsumption("weight", 3),),
            ),
        ),
    )

    result = _solve(model).requested

    assert result.status is MILPSolveStatus.OPTIMAL
    assert result.objective == pytest.approx(10)
    assert [placement.item_id for placement in result.placements] == ["heavy"]
    assert result.excluded_instance_ids == ("light#1",)


def test_optional_mode_excludes_an_item_that_cannot_fit_in_any_orientation():
    model = SingleContainerPackingModel.from_parts(
        PackingContainer("c1", "Container", Dimensions3D(3, 3, 3)),
        (
            PackingItem.from_parts("large", "Large", Dimensions3D(4, 4, 1), value=20),
            PackingItem.from_parts("small", "Small", Dimensions3D(2, 2, 2), value=5),
        ),
    )

    result = _solve(model).requested

    assert result.status is MILPSolveStatus.OPTIMAL
    assert result.objective == pytest.approx(5)
    assert [placement.item_id for placement in result.placements] == ["small"]
    assert result.excluded_instance_ids == ("large#1",)


def test_infeasible_all_required_returns_a_distinct_maximum_value_recovery():
    model = SingleContainerPackingModel.from_parts(
        PackingContainer("c1", "Container", Dimensions3D(2, 2, 2)),
        (
            PackingItem.from_parts("a", "A", Dimensions3D(2, 2, 2), value=8),
            PackingItem.from_parts("b", "B", Dimensions3D(2, 2, 2), value=5),
        ),
        selection_policy=PackingSelectionPolicy.ALL_REQUIRED,
    )

    result = _solve(model)

    assert result.requested.status is MILPSolveStatus.INFEASIBLE
    assert result.recovery is not None
    assert result.recovery.status is MILPSolveStatus.OPTIMAL
    assert result.recovery.objective == pytest.approx(8)
    assert [placement.item_id for placement in result.recovery.placements] == ["a"]
    assert result.recovery.extras["solve_role"] == "maximum_feasible_recovery"


def _overlap(a, b, tolerance=1e-7):
    separated = (
        a.x + a.length <= b.x + tolerance
        or b.x + b.length <= a.x + tolerance
        or a.y + a.width <= b.y + tolerance
        or b.y + b.width <= a.y + tolerance
        or a.z + a.height <= b.z + tolerance
        or b.z + b.height <= a.z + tolerance
    )
    return not separated
