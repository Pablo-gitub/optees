from __future__ import annotations

import json

import pytest

from optees.application.codecs.knapsack_unbounded_problem_codec import (
    knapsack_unbounded_model_from_dict,
)
from optees.application.codecs.knapsack_unbounded_result_codec import (
    KnapsackUnboundedResultCodec,
)
from optees.domain.entities.knapsack.unbounded_item import UnboundedKnapsackItem
from optees.domain.entities.knapsack.unbounded_solution import (
    UnboundedKnapsackSolution,
)
from optees.domain.models.knapsack.unbounded_knapsack_model import (
    UnboundedKnapsackModel,
)


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "unbounded",
        "capacity": 8,
        "items": [
            {"name": "A", "value": 10, "weight": 1},
            {"name": "B", "value": 30, "weight": 2},
            {"name": "C", "value": 44, "weight": 3},
        ],
    }


def test_problem_codec_maps_payload_to_unbounded_domain_model():
    model = knapsack_unbounded_model_from_dict(_payload())

    assert model.capacity == 8
    assert model.item_names() == ("A", "B", "C")
    assert model.values() == (10.0, 30.0, 44.0)
    assert model.weights() == (1, 2, 3)


def test_problem_codec_rejects_bounded_variant():
    payload = _payload()
    payload["variant"] = "bounded"

    with pytest.raises(ValueError, match="requires variant 'unbounded'"):
        knapsack_unbounded_model_from_dict(payload)


def test_result_codec_preserves_full_quantity_vector():
    model = UnboundedKnapsackModel.from_parts(
        (
            UnboundedKnapsackItem("A", 10, 1),
            UnboundedKnapsackItem("B", 30, 2),
            UnboundedKnapsackItem("C", 44, 3),
        ),
        capacity=8,
    )
    solution = UnboundedKnapsackSolution.from_model_result(
        model,
        status="Optimal",
        objective=120,
        quantities=[0, 4, 0],
        extras={
            "method": "unbounded_dynamic_programming",
            "complexity": "O(n * capacity)",
            "item_count": 3,
            "capacity": 8,
            "dp_cells": 27,
            "max_dp_cells": 5_000_000,
            "success": True,
        },
    )

    serialized = KnapsackUnboundedResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "optimal"
    assert serialized.result == {
        "objective": 120.0,
        "quantities": [0, 4, 0],
        "selected_indices": [1],
        "selected_items": [{"index": 1, "name": "B", "quantity": 4}],
        "total_value": 120.0,
        "total_weight": 8,
        "remaining_capacity": 0,
    }


def test_result_codec_represents_unbounded_objective_as_strict_json_null():
    model = UnboundedKnapsackModel.from_parts(
        (UnboundedKnapsackItem("Free value", 1, 0),),
        capacity=8,
    )
    solution = UnboundedKnapsackSolution.from_model_result(
        model,
        status="Unbounded",
        objective=None,
        quantities=[],
        extras={
            "method": "unbounded_dynamic_programming",
            "message": "A positive-value zero-weight item can be repeated.",
            "item_count": 1,
            "capacity": 8,
            "success": False,
        },
    )

    serialized = KnapsackUnboundedResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "unbounded"
    assert serialized.result["objective"] is None
    assert serialized.result["quantities"] == [0]
    json.dumps(serialized.result, allow_nan=False)
