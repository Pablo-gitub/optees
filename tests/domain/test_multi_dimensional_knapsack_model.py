from __future__ import annotations

import pytest

from optees.domain.entities.knapsack.multi_dimensional_item import (
    MultiDimensionalKnapsackItem,
)
from optees.domain.entities.knapsack.multi_dimensional_resource import (
    MultiDimensionalKnapsackResource,
)
from optees.domain.models.knapsack.multi_dimensional_knapsack_model import (
    MultiDimensionalKnapsackModel,
)


def _resources() -> tuple[MultiDimensionalKnapsackResource, ...]:
    return (
        MultiDimensionalKnapsackResource("weight", 10),
        MultiDimensionalKnapsackResource("volume", 6),
    )


def _small_model() -> MultiDimensionalKnapsackModel:
    return MultiDimensionalKnapsackModel.from_parts(
        _resources(),
        (
            MultiDimensionalKnapsackItem("A", value=8, resource_usage=(4, 1.5)),
            MultiDimensionalKnapsackItem("B", value=9, resource_usage=(5, 2)),
        ),
    )


def test_multi_dimensional_model_exposes_canonical_vectors():
    model = _small_model()

    assert model.n_resources() == 2
    assert model.n_items() == 2
    assert model.resource_names() == ("weight", "volume")
    assert model.capacities() == (10.0, 6.0)
    assert model.item_names() == ("A", "B")
    assert model.values() == (8.0, 9.0)
    assert model.usage_matrix() == ((4.0, 1.5), (5.0, 2.0))


def test_multi_dimensional_model_updates_immutably():
    model = _small_model()

    updated = (
        model.set_resource_name(0, "mass")
        .set_resource_capacity(1, 7.5)
        .set_item_name(0, "A1")
        .set_item_value(1, 11)
        .set_item_resource_amount(1, 0, 4.5)
    )

    assert model.resource_names() == ("weight", "volume")
    assert model.capacities() == (10.0, 6.0)
    assert model.item(0).name == "A"
    assert model.item(1).value == pytest.approx(9.0)
    assert model.usage_matrix() == ((4.0, 1.5), (5.0, 2.0))

    assert updated.resource_names() == ("mass", "volume")
    assert updated.capacities() == (10.0, 7.5)
    assert updated.item(0).name == "A1"
    assert updated.item(1).value == pytest.approx(11.0)
    assert updated.usage_matrix() == ((4.0, 1.5), (4.5, 2.0))


def test_multi_dimensional_model_adds_and_removes_resources_consistently():
    model = _small_model()

    expanded = model.add_resource(MultiDimensionalKnapsackResource("time", 3))
    reduced = expanded.remove_resource(1)

    assert expanded.resource_names() == ("weight", "volume", "time")
    assert expanded.capacities() == (10.0, 6.0, 3.0)
    assert expanded.usage_matrix() == ((4.0, 1.5, 0.0), (5.0, 2.0, 0.0))

    assert reduced.resource_names() == ("weight", "time")
    assert reduced.usage_matrix() == ((4.0, 0.0), (5.0, 0.0))


def test_multi_dimensional_model_adds_and_removes_items():
    model = MultiDimensionalKnapsackModel.empty(
        1,
        resources=(MultiDimensionalKnapsackResource("weight", 5),),
    )

    assert model.resource_names() == ("weight",)
    assert model.item_names() == ("Item 1",)
    assert model.usage_matrix() == ((0.0,),)

    added = model.add_item(MultiDimensionalKnapsackItem("Custom", 2, (1.25,)))
    removed = added.remove_item(0)

    assert added.item_names() == ("Item 1", "Custom")
    assert added.usage_matrix() == ((0.0,), (1.25,))
    assert removed.item_names() == ("Custom",)


def test_multi_dimensional_model_rejects_invalid_domain_values():
    with pytest.raises(ValueError):
        MultiDimensionalKnapsackModel.from_parts((), ())

    with pytest.raises(ValueError):
        MultiDimensionalKnapsackModel.from_parts(
            (
                MultiDimensionalKnapsackResource("weight", 5),
                MultiDimensionalKnapsackResource("WEIGHT", 6),
            ),
            (),
        )

    with pytest.raises(ValueError):
        MultiDimensionalKnapsackModel.from_parts(
            _resources(),
            (MultiDimensionalKnapsackItem("bad", 1, (1, 2, 3)),),
        )

    with pytest.raises(ValueError):
        MultiDimensionalKnapsackResource("", 5)

    with pytest.raises(ValueError):
        MultiDimensionalKnapsackResource("bad", -1)

    with pytest.raises(ValueError):
        MultiDimensionalKnapsackItem("", 1, (1,))

    with pytest.raises(ValueError):
        MultiDimensionalKnapsackItem("bad", -1, (1,))

    with pytest.raises(ValueError):
        MultiDimensionalKnapsackItem("bad", 1, ())

    with pytest.raises(ValueError):
        MultiDimensionalKnapsackItem("bad", 1, (-1,))
