from __future__ import annotations

import pytest

from optees.application.codecs.knapsack_multi_dimensional_problem_codec import (
    knapsack_multi_dimensional_request_from_dict,
)
from optees.application.codecs.knapsack_multi_dimensional_result_codec import (
    KnapsackMultiDimensionalResultCodec,
)
from optees.domain.entities.knapsack.multi_dimensional_item import (
    MultiDimensionalKnapsackItem,
)
from optees.domain.entities.knapsack.multi_dimensional_quantity_solution import (
    MultiDimensionalQuantityKnapsackSolution,
)
from optees.domain.entities.knapsack.multi_dimensional_resource import (
    MultiDimensionalKnapsackResource,
)
from optees.domain.models.knapsack.multi_dimensional_knapsack_model import (
    MultiDimensionalKnapsackModel,
)


def _payload(*, domain: str = "zero_one") -> dict:
    return {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "multi_dimensional",
        "domain": domain,
        "resources": [
            {"name": "weight", "capacity": 10},
            {"name": "volume", "capacity": 6},
        ],
        "items": [
            {"name": "A", "value": 8, "usage": [4, 1.5]},
            {"name": "B", "value": 9, "usage": [5, 2]},
        ],
    }


def test_problem_codec_maps_resources_items_and_binary_bounds():
    request = knapsack_multi_dimensional_request_from_dict(_payload())

    assert request.domain == "zero_one"
    assert request.model.resource_names() == ("weight", "volume")
    assert request.model.capacities() == pytest.approx((10.0, 6.0))
    assert request.model.usage_matrix() == ((4.0, 1.5), (5.0, 2.0))
    assert request.upper_bounds == (1.0, 1.0)


def test_problem_codec_requires_finite_bounds_for_bounded_domain():
    payload = _payload(domain="bounded")

    with pytest.raises(ValueError, match="max_quantity is required"):
        knapsack_multi_dimensional_request_from_dict(payload)

    payload["items"][0]["max_quantity"] = 3
    payload["items"][1]["max_quantity"] = 2
    request = knapsack_multi_dimensional_request_from_dict(payload)
    assert request.upper_bounds == (3.0, 2.0)


def test_problem_codec_normalizes_fractional_upper_bounds():
    payload = _payload(domain="fractional")
    payload["items"][1]["max_quantity"] = "inf"

    request = knapsack_multi_dimensional_request_from_dict(payload)

    assert request.upper_bounds == (1.0, None)


def test_problem_codec_rejects_mismatched_usage_vector():
    payload = _payload()
    payload["items"][0]["usage"] = [4]

    with pytest.raises(ValueError, match="must contain 2 values"):
        knapsack_multi_dimensional_request_from_dict(payload)


def test_result_codec_preserves_quantities_and_per_resource_usage():
    model = MultiDimensionalKnapsackModel.from_parts(
        (
            MultiDimensionalKnapsackResource("weight", 12),
            MultiDimensionalKnapsackResource("volume", 6),
        ),
        (
            MultiDimensionalKnapsackItem("A", 8, (4, 1.5)),
            MultiDimensionalKnapsackItem("B", 9, (5, 2)),
        ),
    )
    solution = MultiDimensionalQuantityKnapsackSolution.from_model_quantities(
        model,
        status="Optimal",
        objective=21.5,
        quantities=[1, 1.5],
        extras={
            "method": "multidimensional_fractional_lp",
            "multi_domain": "fractional",
            "item_count": 2,
            "resource_count": 2,
            "resource_names": ["weight", "volume"],
            "capacities": [12, 6],
            "success": True,
        },
    )

    serialized = KnapsackMultiDimensionalResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "optimal"
    assert serialized.result["quantities"] == pytest.approx([1.0, 1.5])
    assert serialized.result["selected_items"] == [
        {"index": 0, "name": "A", "quantity": 1.0},
        {"index": 1, "name": "B", "quantity": 1.5},
    ]
    assert serialized.result["resources"] == [
        {"index": 0, "name": "weight", "capacity": 12.0, "used": 11.5, "remaining": 0.5},
        {"index": 1, "name": "volume", "capacity": 6.0, "used": 4.5, "remaining": 1.5},
    ]
    assert serialized.diagnostics["domain"] == "fractional"
