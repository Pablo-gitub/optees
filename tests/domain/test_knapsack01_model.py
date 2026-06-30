from __future__ import annotations

from optees.domain.entities.knapsack.item import KnapsackItem
from optees.domain.models.knapsack import Knapsack01Model


def test_knapsack01_model_exposes_canonical_vectors():
    model = Knapsack01Model.from_parts(
        (KnapsackItem("A", 3, 2),),
        capacity=5,
    )

    assert model.item_names() == ("A",)
    assert model.values() == (3.0,)
    assert model.weights() == (2,)
