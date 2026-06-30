from __future__ import annotations

import pytest

from optees.domain.entities.knapsack.bounded_item import BoundedKnapsackItem
from optees.domain.models.knapsack.bounded_knapsack_model import BoundedKnapsackModel


def _small_model() -> BoundedKnapsackModel:
    return BoundedKnapsackModel.from_parts(
        (
            BoundedKnapsackItem("A", value=3, weight=2, max_quantity=4),
            BoundedKnapsackItem("B", value=5, weight=3, max_quantity=2),
        ),
        capacity=10,
    )


def test_bounded_model_exposes_canonical_vectors():
    model = _small_model()

    assert model.capacity == 10
    assert model.n_items() == 2
    assert model.item_names() == ("A", "B")
    assert model.values() == (3.0, 5.0)
    assert model.weights() == (2, 3)
    assert model.max_quantities() == (4, 2)


def test_bounded_model_updates_immutably():
    model = _small_model()

    updated = (
        model.set_capacity(8)
        .set_item_name(0, "A1")
        .set_item_value(1, 7.5)
        .set_item_weight(1, 4)
        .set_item_max_quantity(0, 3)
    )

    assert model.capacity == 10
    assert model.item(0).name == "A"
    assert model.item(0).max_quantity == 4
    assert model.item(1).value == pytest.approx(5.0)
    assert model.item(1).weight == 3

    assert updated.capacity == 8
    assert updated.item(0).name == "A1"
    assert updated.item(0).max_quantity == 3
    assert updated.item(1).value == pytest.approx(7.5)
    assert updated.item(1).weight == 4


def test_bounded_model_adds_and_removes_items():
    model = BoundedKnapsackModel.empty(1, capacity=5)

    assert model.item_names() == ("Item 1",)
    assert model.max_quantities() == (1,)

    added = model.add_item(BoundedKnapsackItem("Custom", 2, 1, 6))
    removed = added.remove_item(0)

    assert added.item_names() == ("Item 1", "Custom")
    assert added.max_quantities() == (1, 6)
    assert removed.item_names() == ("Custom",)


def test_bounded_model_rejects_invalid_domain_values():
    with pytest.raises(ValueError):
        BoundedKnapsackModel.from_parts([], capacity=2.5)

    with pytest.raises(ValueError):
        BoundedKnapsackItem("", value=1, weight=1, max_quantity=1)

    with pytest.raises(ValueError):
        BoundedKnapsackItem("bad", value=-1, weight=1, max_quantity=1)

    with pytest.raises(ValueError):
        BoundedKnapsackItem("bad", value=1, weight=1.5, max_quantity=1)

    with pytest.raises(ValueError):
        BoundedKnapsackItem("bad", value=1, weight=1, max_quantity=-1)

    with pytest.raises(ValueError):
        BoundedKnapsackItem("bad", value=1, weight=1, max_quantity=True)
