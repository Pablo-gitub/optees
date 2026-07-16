from __future__ import annotations

import pytest

from optees.application.codecs.knapsack_bounded_problem_codec import (
    knapsack_bounded_model_from_dict,
)
from optees.application.codecs.knapsack_bounded_result_codec import (
    KnapsackBoundedResultCodec,
)
from optees.domain.entities.knapsack.bounded_item import BoundedKnapsackItem
from optees.domain.entities.knapsack.bounded_solution import BoundedKnapsackSolution
from optees.domain.models.knapsack.bounded_knapsack_model import BoundedKnapsackModel


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "bounded",
        "capacity": 10,
        "items": [
            {"name": "A", "value": 6, "weight": 2, "max_quantity": 3},
            {"name": "B", "value": 10, "weight": 3, "max_quantity": 2},
        ],
    }


def test_problem_codec_maps_quantities_to_bounded_domain_model():
    model = knapsack_bounded_model_from_dict(_payload())

    assert model.capacity == 10
    assert model.item_names() == ("A", "B")
    assert model.values() == (6.0, 10.0)
    assert model.weights() == (2, 3)
    assert model.max_quantities() == (3, 2)


def test_problem_codec_requires_max_quantity_for_every_item():
    payload = _payload()
    del payload["items"][0]["max_quantity"]

    with pytest.raises(ValueError, match="max_quantity is required"):
        knapsack_bounded_model_from_dict(payload)


def test_problem_codec_rejects_unbounded_variant():
    payload = _payload()
    payload["variant"] = "unbounded"

    with pytest.raises(ValueError, match="requires variant 'bounded'"):
        knapsack_bounded_model_from_dict(payload)


def test_result_codec_preserves_full_quantity_vector():
    model = BoundedKnapsackModel.from_parts(
        (
            BoundedKnapsackItem("A", 6, 2, 3),
            BoundedKnapsackItem("B", 10, 3, 2),
        ),
        capacity=10,
    )
    solution = BoundedKnapsackSolution.from_model_result(
        model,
        status="Optimal",
        objective=32,
        quantities=[2, 2],
        extras={
            "method": "bounded_dynamic_programming",
            "complexity": "O(capacity * sum_i feasible_quantity_i)",
            "item_count": 2,
            "capacity": 10,
            "dp_cells": 77,
            "max_dp_cells": 5_000_000,
            "success": True,
        },
    )

    serialized = KnapsackBoundedResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "optimal"
    assert serialized.result == {
        "objective": 32.0,
        "quantities": [2, 2],
        "selected_indices": [0, 1],
        "selected_items": [
            {"index": 0, "name": "A", "quantity": 2},
            {"index": 1, "name": "B", "quantity": 2},
        ],
        "total_value": 32.0,
        "total_weight": 10,
        "remaining_capacity": 0,
    }
    assert serialized.diagnostics["dp_cells"] == 77
