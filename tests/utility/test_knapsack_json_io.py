from __future__ import annotations

import pytest

from optees.utility.knapsack_json_io import (
    DOMAIN_BOUNDED,
    DOMAIN_FRACTIONAL,
    DOMAIN_ZERO_ONE,
    VARIANT_BOUNDED,
    VARIANT_FRACTIONAL,
    VARIANT_MULTI_DIMENSIONAL,
    VARIANT_ZERO_ONE,
    knapsack_problem_from_dict,
    knapsack_problem_to_dict,
)


def test_imports_zero_one_knapsack_json():
    problem = knapsack_problem_from_dict(
        {
            "version": "1",
            "problem_type": "knapsack",
            "variant": "0/1",
            "capacity": 5,
            "items": [
                {"name": "A", "value": 3, "weight": 2},
                {"name": "B", "value": 4, "weight": 3},
            ],
        }
    )

    assert problem.variant == VARIANT_ZERO_ONE
    assert problem.domain == DOMAIN_ZERO_ONE
    assert problem.capacity == 5.0
    assert problem.items[0].name == "A"
    assert problem.items[1].weight == 3.0


def test_imports_bounded_knapsack_json_with_integer_limits():
    problem = knapsack_problem_from_dict(
        {
            "version": "1",
            "variant": "bounded",
            "capacity": 7,
            "items": [
                {"name": "Pen", "value": 2, "weight": 1, "max_quantity": 4},
                {"name": "Mug", "value": 8, "weight": 3, "max_quantity": 2},
            ],
        }
    )

    assert problem.variant == VARIANT_BOUNDED
    assert problem.domain == DOMAIN_BOUNDED
    assert problem.items[0].max_quantity == 4.0
    assert problem.items[1].max_quantity == 2.0


def test_imports_fractional_knapsack_json_with_decimal_weight():
    problem = knapsack_problem_from_dict(
        {
            "version": "1",
            "variant": "fractional",
            "capacity": 50.5,
            "items": [
                {"name": "A", "value": 60, "weight": 10.5},
                {"name": "B", "value": 100, "weight": 20},
            ],
        }
    )

    assert problem.variant == VARIANT_FRACTIONAL
    assert problem.domain == DOMAIN_FRACTIONAL
    assert problem.capacity == 50.5
    assert problem.items[0].weight == 10.5


def test_imports_multi_dimensional_bounded_json():
    problem = knapsack_problem_from_dict(
        {
            "version": "1",
            "variant": "multi-dimensional",
            "domain": "bounded",
            "resources": [
                {"name": "weight", "capacity": 10},
                {"name": "volume", "capacity": 6},
            ],
            "items": [
                {"name": "A", "value": 8, "usage": [4, 1.5], "max_quantity": 3},
                {"name": "B", "value": 9, "usage": [5, 2], "max_quantity": 2},
            ],
        }
    )

    assert problem.variant == VARIANT_MULTI_DIMENSIONAL
    assert problem.domain == DOMAIN_BOUNDED
    assert problem.resources[0].name == "weight"
    assert problem.resources[1].capacity == 6.0
    assert problem.items[0].usage == (4.0, 1.5)
    assert problem.items[0].max_quantity == 3.0


def test_imports_multi_dimensional_fractional_infinite_limit():
    problem = knapsack_problem_from_dict(
        {
            "version": "1",
            "variant": "multi-dimensional",
            "domain": "fractional",
            "resources": [{"name": "weight", "capacity": 10}],
            "items": [
                {"name": "A", "value": 8, "usage": [4], "max_quantity": "inf"},
            ],
        }
    )

    assert problem.variant == VARIANT_MULTI_DIMENSIONAL
    assert problem.domain == DOMAIN_FRACTIONAL
    assert problem.items[0].max_quantity == float("inf")
    assert knapsack_problem_to_dict(problem)["items"][0]["max_quantity"] == "inf"


def test_round_trips_imported_problem_to_dict():
    problem = knapsack_problem_from_dict(
        {
            "version": "1",
            "variant": "fractional",
            "capacity": 10,
            "items": [{"name": "A", "value": 1, "weight": 2}],
        }
    )

    data = knapsack_problem_to_dict(problem)

    assert data["version"] == "1"
    assert data["variant"] == "fractional"
    assert data["capacity"] == 10.0
    assert data["items"] == [{"name": "A", "value": 1.0, "weight": 2.0}]


def test_rejects_invalid_multi_dimensional_usage_length():
    with pytest.raises(ValueError, match="usage must contain 2 values"):
        knapsack_problem_from_dict(
            {
                "version": "1",
                "variant": "multi_dimensional",
                "resources": [
                    {"name": "weight", "capacity": 10},
                    {"name": "volume", "capacity": 6},
                ],
                "items": [{"name": "A", "value": 8, "usage": [4]}],
            }
        )


def test_rejects_non_integer_weight_for_integer_variants():
    with pytest.raises(ValueError, match="items\\[0\\].weight"):
        knapsack_problem_from_dict(
            {
                "version": "1",
                "variant": "bounded",
                "capacity": 5,
                "items": [{"name": "A", "value": 1, "weight": 1.5}],
            }
        )
