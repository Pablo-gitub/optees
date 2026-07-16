from __future__ import annotations

from optees.application.contracts.json_value import JsonValue
from optees.domain.entities.knapsack.bounded_item import BoundedKnapsackItem
from optees.domain.models.knapsack.bounded_knapsack_model import BoundedKnapsackModel
from optees.utility.knapsack_json_io import (
    DOMAIN_BOUNDED,
    VARIANT_BOUNDED,
    KnapsackJsonProblem,
    knapsack_problem_from_dict,
)


def knapsack_bounded_model_from_dict(
    payload: dict[str, JsonValue],
) -> BoundedKnapsackModel:
    required = ("version", "problem_type", "variant", "capacity", "items")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            "knapsack.bounded is missing required fields: " + ", ".join(missing)
        )
    problem = knapsack_problem_from_dict(payload)
    return knapsack_bounded_model_from_problem(problem)


def knapsack_bounded_model_from_problem(
    problem: KnapsackJsonProblem,
) -> BoundedKnapsackModel:
    if problem.variant != VARIANT_BOUNDED or problem.domain != DOMAIN_BOUNDED:
        raise ValueError(
            "knapsack.bounded requires variant 'bounded' and the bounded domain"
        )
    if problem.capacity is None:
        raise ValueError("capacity is required for knapsack.bounded")

    items = []
    for index, item in enumerate(problem.items):
        if item.weight is None:
            raise ValueError(f"items[{index}].weight is required")
        if item.max_quantity is None:
            raise ValueError(f"items[{index}].max_quantity is required")
        items.append(
            BoundedKnapsackItem(
                name=item.name,
                value=item.value,
                weight=item.weight,
                max_quantity=item.max_quantity,
            )
        )
    return BoundedKnapsackModel.from_parts(items, capacity=int(problem.capacity))
