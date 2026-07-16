from pathlib import Path

import pytest

pytest.importorskip("ortools")

from optees.application.usecases.solve_single_container_packing_usecase import (
    SolveSingleContainerPackingUseCase,
)
from optees.data.adapters.packing.ortools_single_container_packing_adapter import (
    OrtoolsSingleContainerPackingAdapter,
)
from optees.domain.entities.packing.container import PackingContainer
from optees.domain.entities.packing.geometry import Dimensions3D
from optees.domain.entities.packing.item import PackingItem
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus
from optees.domain.value_objects.packing.rotation_policy import RotationPolicy
from optees.domain.value_objects.packing.selection_policy import PackingSelectionPolicy
from optees.utility.orlib_thpack_io import read_orlib_thpack


DATA = Path(__file__).parents[1] / "data" / "packing" / "orlib" / "thpack1.txt"


def test_orlib_thpack1_first_type_derived_subset() -> None:
    source = read_orlib_thpack(DATA)[0]
    box = source.box_types[0]
    box_volume = box.dimensions[0] * box.dimensions[1] * box.dimensions[2]
    model = SingleContainerPackingModel.from_parts(
        PackingContainer(
            "orlib-1",
            "OR-Library thpack1 problem 1",
            Dimensions3D(*source.container_dimensions),
        ),
        (
            PackingItem.from_parts(
                "type-1",
                "Published type 1 (two-copy CI subset)",
                Dimensions3D(*box.dimensions),
                quantity=2,
                value=box_volume,
                rotation_policy=RotationPolicy.FIXED,
            ),
        ),
        selection_policy=PackingSelectionPolicy.ALL_REQUIRED,
        time_limit=10,
    )

    result = SolveSingleContainerPackingUseCase(
        OrtoolsSingleContainerPackingAdapter()
    ).execute(model).requested

    assert result.status is MILPSolveStatus.OPTIMAL
    assert len(result.placements) == 2
    assert result.objective == pytest.approx(2 * box_volume)
