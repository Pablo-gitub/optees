from __future__ import annotations

import pytest

from optees.domain.entities.knapsack.unbounded_item import UnboundedKnapsackItem
from optees.domain.models.knapsack.unbounded_knapsack_model import (
    UnboundedKnapsackModel,
)


def _small_model() -> UnboundedKnapsackModel:
    return UnboundedKnapsackModel.from_parts(
        (
            UnboundedKnapsackItem("A", value=3, weight=2),
            UnboundedKnapsackItem("B", value=5, weight=3),
        ),
        capacity=10,
    )


def test_unbounded_model_exposes_canonical_vectors():
    model = _small_model()

    assert model.capacity == 10
    assert model.n_items() == 2
    assert model.item_names() == ("A", "B")
    assert model.values() == (3.0, 5.0)
    assert model.weights() == (2, 3)


def test_unbounded_model_updates_immutably():
    model = _small_model()

    updated = (
        model.set_capacity(8)
        .set_item_name(0, "A1")
        .set_item_value(1, 7.5)
        .set_item_weight(1, 4)
    )

    assert model.capacity == 10
    assert model.item(0).name == "A"
    assert model.item(1).value == pytest.approx(5.0)
    assert model.item(1).weight == 3

    assert updated.capacity == 8
    assert updated.item(0).name == "A1"
    assert updated.item(1).value == pytest.approx(7.5)
    assert updated.item(1).weight == 4


def test_unbounded_model_adds_and_removes_items():
    model = UnboundedKnapsackModel.empty(1, capacity=5)

    assert model.item_names() == ("Item 1",)

    added = model.add_item(UnboundedKnapsackItem("Custom", 2, 1))
    removed = added.remove_item(0)

    assert added.item_names() == ("Item 1", "Custom")
    assert removed.item_names() == ("Custom",)


def test_unbounded_model_rejects_invalid_domain_values():
    with pytest.raises(ValueError):
        UnboundedKnapsackModel.from_parts([], capacity=2.5)

    with pytest.raises(ValueError):
        UnboundedKnapsackItem("", value=1, weight=1)

    with pytest.raises(ValueError):
        UnboundedKnapsackItem("bad", value=-1, weight=1)

    with pytest.raises(ValueError):
        UnboundedKnapsackItem("bad", value=1, weight=1.5)

    with pytest.raises(ValueError):
        UnboundedKnapsackItem("bad", value=1, weight=True)
