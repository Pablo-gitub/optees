from __future__ import annotations

import pytest

from optees.domain.entities.packing.container import PackingContainer
from optees.domain.entities.packing.geometry import Dimensions3D, generate_orientations
from optees.domain.entities.packing.item import PackingItem
from optees.domain.entities.packing.resource import ResourceCapacity, ResourceConsumption
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)
from optees.domain.value_objects.packing.rotation_policy import RotationPolicy


def test_any_orthogonal_generates_six_orientations_for_distinct_dimensions():
    orientations = generate_orientations(
        Dimensions3D(2, 3, 5), RotationPolicy.ANY_ORTHOGONAL
    )

    assert len(orientations) == 6
    assert {orientation.dimensions.as_tuple() for orientation in orientations} == {
        (2.0, 3.0, 5.0),
        (2.0, 5.0, 3.0),
        (3.0, 2.0, 5.0),
        (3.0, 5.0, 2.0),
        (5.0, 2.0, 3.0),
        (5.0, 3.0, 2.0),
    }


@pytest.mark.parametrize(
    ("dimensions", "expected_count"),
    [
        (Dimensions3D(2, 2, 5), 3),
        (Dimensions3D(4, 4, 4), 1),
    ],
)
def test_equal_dimensions_remove_duplicate_orientations(dimensions, expected_count):
    orientations = generate_orientations(dimensions, RotationPolicy.ANY_ORTHOGONAL)

    assert len(orientations) == expected_count
    assert len({orientation.dimensions.as_tuple() for orientation in orientations}) == expected_count


def test_rotation_policies_generate_only_allowed_dimension_swaps():
    dimensions = Dimensions3D(2, 3, 5)

    assert [o.dimensions.as_tuple() for o in generate_orientations(dimensions, RotationPolicy.FIXED)] == [
        (2.0, 3.0, 5.0)
    ]
    assert {o.dimensions.as_tuple() for o in generate_orientations(dimensions, RotationPolicy.X_ONLY)} == {
        (2.0, 3.0, 5.0),
        (2.0, 5.0, 3.0),
    }
    assert {o.dimensions.as_tuple() for o in generate_orientations(dimensions, RotationPolicy.Y_ONLY)} == {
        (2.0, 3.0, 5.0),
        (5.0, 3.0, 2.0),
    }
    assert {o.dimensions.as_tuple() for o in generate_orientations(dimensions, RotationPolicy.KEEP_UPRIGHT)} == {
        (2.0, 3.0, 5.0),
        (3.0, 2.0, 5.0),
    }


def test_custom_policy_requires_valid_orientation_codes_and_deduplicates_cube():
    cube = Dimensions3D(2, 2, 2)

    orientations = generate_orientations(
        cube,
        RotationPolicy.CUSTOM,
        ("LWH", "HWL", "WLH"),
    )

    assert len(orientations) == 1
    with pytest.raises(ValueError, match="at least one orientation"):
        generate_orientations(cube, RotationPolicy.CUSTOM)


def test_item_rejects_custom_codes_for_a_non_custom_policy():
    with pytest.raises(ValueError, match="only with the custom rotation policy"):
        PackingItem.from_parts(
            "i1",
            "Box",
            Dimensions3D(1, 2, 3),
            rotation_policy=RotationPolicy.FIXED,
            custom_orientation_codes=("LWH",),
        )


def test_model_rejects_item_resource_missing_from_container():
    container = PackingContainer("c1", "Container", Dimensions3D(10, 10, 10))
    item = PackingItem.from_parts(
        "i1",
        "Box",
        Dimensions3D(1, 1, 1),
        consumptions=(ResourceConsumption("weight", 2),),
    )

    with pytest.raises(ValueError, match="absent from the container"):
        SingleContainerPackingModel.from_parts(container, (item,))


def test_model_accepts_named_capacity_and_integer_quantity():
    container = PackingContainer.from_parts(
        "c1",
        "Container",
        Dimensions3D(10, 10, 10),
        (ResourceCapacity("weight", 100),),
    )
    item = PackingItem.from_parts(
        "i1",
        "Box",
        Dimensions3D(1, 2, 3),
        quantity=4,
        consumptions=(ResourceConsumption("weight", 5),),
    )

    model = SingleContainerPackingModel.from_parts(container, (item,))

    assert model.unit_count() == 4
    assert model.container.capacity("WEIGHT") == pytest.approx(100)
    assert item.consumption("Weight") == pytest.approx(5)
