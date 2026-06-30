from __future__ import annotations

import pytest

from optees.domain.entities.knapsack.fractional_item import FractionalKnapsackItem
from optees.domain.models.knapsack.fractional_knapsack_model import (
    FractionalKnapsackModel,
)


def _small_model() -> FractionalKnapsackModel:
    return FractionalKnapsackModel.from_parts(
        (
            FractionalKnapsackItem("A", value=60, weight=10),
            FractionalKnapsackItem("B", value=100, weight=20),
        ),
        capacity=25,
    )


def test_fractional_model_exposes_canonical_vectors_and_densities():
    model = _small_model()

    assert model.capacity == pytest.approx(25.0)
    assert model.n_items() == 2
    assert model.item_names() == ("A", "B")
    assert model.values() == (60.0, 100.0)
    assert model.weights() == (10.0, 20.0)
    assert model.value_densities() == (6.0, 5.0)


def test_fractional_model_updates_immutably():
    model = _small_model()

    updated = (
        model.set_capacity(12.5)
        .set_item_name(0, "A1")
        .set_item_value(1, 120)
        .set_item_weight(1, 24)
    )

    assert model.capacity == pytest.approx(25.0)
    assert model.item(0).name == "A"
    assert model.item(1).value == pytest.approx(100.0)
    assert model.item(1).weight == pytest.approx(20.0)

    assert updated.capacity == pytest.approx(12.5)
    assert updated.item(0).name == "A1"
    assert updated.item(1).value == pytest.approx(120.0)
    assert updated.item(1).weight == pytest.approx(24.0)
    assert updated.item(1).value_density == pytest.approx(5.0)


def test_fractional_model_adds_and_removes_items():
    model = FractionalKnapsackModel.empty(1, capacity=5.5)

    assert model.item_names() == ("Item 1",)
    assert model.weights() == (1.0,)

    added = model.add_item(FractionalKnapsackItem("Custom", 2.5, 1.25))
    removed = added.remove_item(0)

    assert added.item_names() == ("Item 1", "Custom")
    assert removed.item_names() == ("Custom",)


def test_fractional_model_rejects_invalid_domain_values():
    with pytest.raises(ValueError):
        FractionalKnapsackModel.from_parts([], capacity=-1)

    with pytest.raises(ValueError):
        FractionalKnapsackItem("", value=1, weight=1)

    with pytest.raises(ValueError):
        FractionalKnapsackItem("bad", value=-1, weight=1)

    with pytest.raises(ValueError):
        FractionalKnapsackItem("bad", value=1, weight=0)

    with pytest.raises(ValueError):
        FractionalKnapsackItem("bad", value=1, weight=True)
