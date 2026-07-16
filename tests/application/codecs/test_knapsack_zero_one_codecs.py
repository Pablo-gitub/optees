from __future__ import annotations

import pytest

from optees.application.codecs.knapsack_zero_one_problem_codec import (
    knapsack_zero_one_model_from_dict,
)
from optees.application.codecs.knapsack_zero_one_result_codec import (
    KnapsackZeroOneResultCodec,
)
from optees.domain.entities.knapsack.item import KnapsackItem
from optees.domain.entities.knapsack.solution import KnapsackSolution
from optees.domain.models.knapsack.knapsack01_model import Knapsack01Model


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "zero_one",
        "capacity": 5,
        "items": [
            {"name": "A", "value": 6, "weight": 2},
            {"name": "B", "value": 10, "weight": 4},
            {"name": "C", "value": 5, "weight": 3},
        ],
    }


def test_problem_codec_maps_shared_json_contract_to_zero_one_domain_model():
    model = knapsack_zero_one_model_from_dict(_payload())

    assert model.capacity == 5
    assert model.item_names() == ("A", "B", "C")
    assert model.values() == (6.0, 10.0, 5.0)
    assert model.weights() == (2, 4, 3)


def test_problem_codec_rejects_another_knapsack_variant():
    payload = _payload()
    payload["variant"] = "bounded"

    with pytest.raises(ValueError, match="requires variant 'zero_one'"):
        knapsack_zero_one_model_from_dict(payload)


def test_problem_codec_requires_explicit_versioned_contract_fields():
    payload = _payload()
    del payload["version"]
    del payload["variant"]

    with pytest.raises(ValueError, match="version, variant"):
        knapsack_zero_one_model_from_dict(payload)


def test_result_codec_preserves_zero_one_selection_and_dp_diagnostics():
    model = Knapsack01Model.from_parts(
        (
            KnapsackItem("A", 6, 2),
            KnapsackItem("B", 10, 4),
            KnapsackItem("C", 5, 3),
        ),
        capacity=5,
    )
    solution = KnapsackSolution.from_model_result(
        model,
        status="Optimal",
        objective=11,
        selected_indices=[0, 2],
        extras={
            "method": "dynamic_programming",
            "complexity": "O(n * capacity)",
            "item_count": 3,
            "capacity": 5,
            "dp_cells": 24,
            "max_dp_cells": 5_000_000,
            "success": True,
        },
    )

    serialized = KnapsackZeroOneResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "optimal"
    assert serialized.result == {
        "objective": 11.0,
        "selected_indices": [0, 2],
        "selected_items": [
            {"index": 0, "name": "A"},
            {"index": 2, "name": "C"},
        ],
        "total_value": 11.0,
        "total_weight": 5,
        "remaining_capacity": 0,
    }
    assert serialized.diagnostics["dp_cells"] == 24
    assert serialized.diagnostics["success"] is True
