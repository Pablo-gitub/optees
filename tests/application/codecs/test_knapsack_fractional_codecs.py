from __future__ import annotations

import pytest

from optees.application.codecs.knapsack_fractional_problem_codec import (
    knapsack_fractional_model_from_dict,
)
from optees.application.codecs.knapsack_fractional_result_codec import (
    KnapsackFractionalResultCodec,
)
from optees.domain.entities.knapsack.fractional_item import FractionalKnapsackItem
from optees.domain.entities.knapsack.fractional_solution import (
    FractionalKnapsackSolution,
)
from optees.domain.models.knapsack.fractional_knapsack_model import (
    FractionalKnapsackModel,
)


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "fractional",
        "capacity": 50.5,
        "items": [
            {"name": "A", "value": 60, "weight": 10.5},
            {"name": "B", "value": 100, "weight": 20},
            {"name": "C", "value": 120, "weight": 30},
        ],
    }


def test_problem_codec_preserves_decimal_capacity_and_weights():
    model = knapsack_fractional_model_from_dict(_payload())

    assert model.capacity == pytest.approx(50.5)
    assert model.item_names() == ("A", "B", "C")
    assert model.values() == pytest.approx((60.0, 100.0, 120.0))
    assert model.weights() == pytest.approx((10.5, 20.0, 30.0))


def test_problem_codec_rejects_unbounded_variant():
    payload = _payload()
    payload["variant"] = "unbounded"

    with pytest.raises(ValueError, match="requires variant 'fractional'"):
        knapsack_fractional_model_from_dict(payload)


def test_problem_codec_rejects_zero_weight():
    payload = _payload()
    payload["items"][0]["weight"] = 0

    with pytest.raises(ValueError, match="weight must be positive"):
        knapsack_fractional_model_from_dict(payload)


def test_result_codec_preserves_fractional_selection_and_diagnostics():
    model = FractionalKnapsackModel.from_parts(
        (
            FractionalKnapsackItem("A", 60, 10),
            FractionalKnapsackItem("B", 100, 20),
            FractionalKnapsackItem("C", 120, 30),
        ),
        capacity=50,
    )
    solution = FractionalKnapsackSolution.from_model_result(
        model,
        status="Optimal",
        objective=240,
        fractions=[1, 1, 2 / 3],
        extras={
            "method": "fractional_greedy_density",
            "complexity": "O(n log n)",
            "item_count": 3,
            "capacity": 50.0,
            "max_items": 1_000_000,
            "success": True,
        },
    )

    serialized = KnapsackFractionalResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "optimal"
    assert serialized.result["objective"] == pytest.approx(240.0)
    assert serialized.result["fractions"] == pytest.approx([1.0, 1.0, 2 / 3])
    assert serialized.result["selected_items"] == [
        {"index": 0, "name": "A", "fraction": 1.0},
        {"index": 1, "name": "B", "fraction": 1.0},
        {"index": 2, "name": "C", "fraction": pytest.approx(2 / 3)},
    ]
    assert serialized.result["total_weight"] == pytest.approx(50.0)
    assert serialized.result["remaining_capacity"] == pytest.approx(0.0)
    assert serialized.diagnostics["max_items"] == 1_000_000
